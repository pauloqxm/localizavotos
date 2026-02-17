from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import streamlit as st
import pandas as pd

from .config import APP_NAME, CANDIDATOS_DIR
from .analytics import load_votos_df, filter_points_within_polygon
from .io_geo import discover_layers_geojson, read_geojson
from .schema import bounds_center_from_geojson
from .styles import load_layer_styles, resolve_layer_style
from .map_folium import build_map, add_geojson_layer, add_points_layer, finalize_map
from .charts import chart_top_locais, chart_top_bairros, chart_hist_votos, chart_top_municipios, chart_bottom_municipios

try:
    from streamlit_folium import st_folium
except Exception:
    st_folium = None

@dataclass
class CandidateSpec:
    key: str
    title: str
    subtitle: str
    folder: Path
    votos_files: list[Path]
    base_bounds_file: Path | None = None

def hide_sidebar():
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.markdown(
        """
        <style>
          [data-testid="stSidebar"] { display: none !important; }
          [data-testid="stSidebarNav"] { display: none !important; }
          [data-testid="collapsedControl"] { display: none !important; }
          .block-container { padding-top: 1.2rem; }
          .lv-header { 
            width: 100%;
            padding: 20px 32px;
            border-radius: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            margin-bottom: 24px;
            transition: box-shadow 0.2s;
          }
          .lv-header:hover {
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
          }
          .lv-title { 
            font-size: 28px;
            font-weight: 800;
            margin: 0;
            line-height: 1.2;
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
          }
          .lv-sub { 
            opacity: 0.95;
            margin-top: 4px;
            color: rgba(255,255,255,0.9);
            font-size: 14px;
          }
          .lv-card { padding:12px 14px; border-radius:14px; border:1px solid rgba(255,255,255,.06);
                     background: rgba(15,27,48,.55); }
          .lv-kpi { display:flex; flex-direction:column; gap:4px; }
          .lv-kpi .v { font-size:20px; font-weight:800; }
          .lv-kpi .l { opacity:.85; font-size:12px; }
          
          /* Garantir que controles do mapa não sejam cortados */
          iframe {
            overflow: visible !important;
          }
          
          [data-testid="stIFrame"] {
            overflow: visible !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

def header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="lv-header">
          <div>
            <div class="lv-title">{title}</div>
            <div class="lv-sub">{subtitle}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def discover_candidates(candidatos_dir: Path = CANDIDATOS_DIR) -> list[Path]:
    out = []
    if not candidatos_dir.exists():
        return out
    for d in sorted([p for p in candidatos_dir.iterdir() if p.is_dir()]):
        # pega o primeiro .py como entry
        py = list(d.glob("*.py"))
        if py:
            out.append(py[0])
    return out

def load_candidate_module(py_file: Path):
    spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não consegui importar {py_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module

def pick_candidate(candidates_py: list[Path]) -> Path | None:
    if not candidates_py:
        st.error("Nenhum candidato encontrado em ./candidatos.")
        return None

    items = []
    for py in candidates_py:
        folder = py.parent
        label = folder.name.replace("_", " ").strip()
        items.append((label, py))

    labels = [x[0] for x in items]
    chosen = st.selectbox("Escolha o candidato", labels, index=0)
    for lbl, py in items:
        if lbl == chosen:
            return py
    return items[0][1]

def render_candidate(candidate_folder: Path, title: str, subtitle: str, votos_files: list[Path], bounds_file: Path | None = None):
    header(title, subtitle)

    # ---- filtros na página (sem sidebar)
    col1, col2, col3, col4 = st.columns([2,2,2,2])

    votos_file = votos_files[0] if votos_files else None
    with col1:
        if len(votos_files) > 1:
            votos_file = st.selectbox(
                "Base de votos",
                votos_files,
                format_func=lambda p: p.stem.replace("_", " "),
            )
        else:
            st.caption(f"Base de votos. {votos_file.name if votos_file else 'Sem arquivo'}")

    df = load_votos_df(votos_file) if votos_file else pd.DataFrame()

    if df.empty:
        st.error("Sem dados de votos ou sem coordenadas válidas.")
        st.stop()

    # Detectar colunas a usar (priorizar colunas originais do GeoJSON)
    if "NM_MUNICIPIO" in df.columns:
        municipios = sorted([m for m in df["NM_MUNICIPIO"].dropna().astype(str).unique() if m.strip()])
        mun_col = "NM_MUNICIPIO"
    else:
        municipios = sorted([m for m in df["Município"].dropna().astype(str).unique() if m.strip()]) if "Município" in df.columns else []
        mun_col = "Município"
    
    bairros = sorted([b for b in df["Bairro/Distrito"].dropna().astype(str).unique() if b.strip()]) if "Bairro/Distrito" in df.columns else []
    
    if "NM_LOCAL_VOTACAO" in df.columns:
        locais = sorted([l for l in df["NM_LOCAL_VOTACAO"].dropna().astype(str).unique() if l.strip()])
        local_col = "NM_LOCAL_VOTACAO"
    else:
        locais = sorted([l for l in df["local_votacao"].dropna().astype(str).unique() if l.strip()]) if "local_votacao" in df.columns else []
        local_col = "local_votacao"

    with col2:
        mun = st.multiselect("Município", municipios, default=[])
    with col3:
        bai = st.multiselect("Bairro/Distrito", bairros, default=[])
    with col4:
        loc = st.multiselect("Local de votação", locais, default=[])

    df_f = df.copy()
    if mun:
        df_f = df_f[df_f[mun_col].isin(mun)]
    if bai and "Bairro/Distrito" in df_f.columns:
        df_f = df_f[df_f["Bairro/Distrito"].isin(bai)]
    if loc:
        df_f = df_f[df_f[local_col].isin(loc)]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    
    # Detectar se é arquivo de municípios
    is_municipios = "municipios" in (votos_file.stem.lower() if votos_file else "")
    
    total_votos = int(df_f["qt_votos"].sum()) if not df_f.empty else 0
    total_pontos = int(len(df_f))
    
    # Formatar números sem vírgula (usar ponto como separador de milhar)
    def format_number(n):
        return f"{n:,}".replace(",", ".")
    
    if is_municipios:
        # KPIs para municípios
        top_mun = (
            df_f.groupby(mun_col)["qt_votos"].sum().sort_values(ascending=False).head(1)
            if not df_f.empty else pd.Series(dtype=float)
        )
        top_mun_name = (top_mun.index[0] if len(top_mun) else "Sem dados")
        top_mun_v = int(top_mun.iloc[0]) if len(top_mun) else 0
        
        c1.markdown(f"<div class='lv-card lv-kpi'><div class='v'>{format_number(total_votos)}</div><div class='l'>Total de votos</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='lv-card lv-kpi'><div class='v'>{format_number(total_pontos)}</div><div class='l'>Municípios</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='lv-card lv-kpi'><div class='v'>{format_number(top_mun_v)}</div><div class='l'>Maior votação</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='lv-card lv-kpi'><div class='v'>{top_mun_name}</div><div class='l'>Município destaque</div></div>", unsafe_allow_html=True)
    else:
        # KPIs para locais de votação
        top_local = (
            df_f.groupby(local_col)["qt_votos"].sum().sort_values(ascending=False).head(1)
            if (not df_f.empty and local_col in df_f.columns) else pd.Series(dtype=float)
        )
        top_local_name = (top_local.index[0] if len(top_local) else "Sem dados")
        top_local_v = int(top_local.iloc[0]) if len(top_local) else 0
        
        c1.markdown(f"<div class='lv-card lv-kpi'><div class='v'>{format_number(total_votos)}</div><div class='l'>Votos no filtro</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='lv-card lv-kpi'><div class='v'>{format_number(total_pontos)}</div><div class='l'>Pontos mapeados</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='lv-card lv-kpi'><div class='v'>{format_number(top_local_v)}</div><div class='l'>Top local</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='lv-card lv-kpi'><div class='v'>{top_local_name}</div><div class='l'>Onde apertar</div></div>", unsafe_allow_html=True)

    # ---- Mapa
    st.subheader("🗺️ Mapa")

    # Se for municípios, usar bounds do ce_regioes
    if is_municipios:
        # Procurar ce_regioes nas camadas comuns
        common_data_dir = Path(st.session_state.get("COMMON_DATA_DIR", "data"))
        ce_regioes_file = common_data_dir / "ce_regioes.geojson"
        
        if ce_regioes_file.exists():
            ce_regioes_gj = read_geojson(ce_regioes_file)
            if ce_regioes_gj:
                bounds, center = bounds_center_from_geojson(ce_regioes_gj)
                zoom_start = 7  # Zoom mais afastado para ver todo o estado
            else:
                bounds_gj = read_geojson(bounds_file) if bounds_file else {}
                bounds, center = bounds_center_from_geojson(bounds_gj) if bounds_gj else (None, None)
                zoom_start = 11
        else:
            bounds_gj = read_geojson(bounds_file) if bounds_file else {}
            bounds, center = bounds_center_from_geojson(bounds_gj) if bounds_gj else (None, None)
            zoom_start = 11
    else:
        bounds_gj = read_geojson(bounds_file) if bounds_file else {}
        bounds, center = bounds_center_from_geojson(bounds_gj) if bounds_gj else (None, None)
        zoom_start = 11
    
    if center is None:
        center = [float(df_f["lat"].mean()), float(df_f["lon"].mean())]
        zoom_start = 11

    m = build_map(center=center, zoom_start=zoom_start)
    
    # Ajustar bounds do mapa se for municípios e tiver bounds
    if is_municipios and bounds:
        m.fit_bounds(bounds)

    # camadas comuns e do candidato
    exclude = {votos_file.name} if votos_file else set()
    common_layers = discover_layers_geojson(Path(st.session_state.get("COMMON_DATA_DIR", "data")), exclude=exclude)
    cand_layers = discover_layers_geojson(candidate_folder, exclude=exclude)

    styles = load_layer_styles()
    
    # Verificar se Fortaleza está no filtro de municípios
    fortaleza_ativo = not mun or "FORTALEZA" in [m.upper() for m in mun]

    for layer in common_layers + cand_layers:
        # Pular camadas de Fortaleza se Fortaleza não estiver no filtro
        if not fortaleza_ativo and ("fortaleza" in layer["stem"].lower() or "fortaleza" in layer["filename"].lower()):
            continue
            
        meta = {
            "stem": layer["stem"],
            "filename": layer["filename"],
            "geom": layer.get("geom"),
            "type": layer["stem"],
        }
        stl = resolve_layer_style(meta, styles)
        add_geojson_layer(m, layer["stem"], layer["geojson"], stl)
    
    # Adicionar o arquivo de votos selecionado (filtrado)
    if votos_file and votos_file.exists():
        votos_gj = read_geojson(votos_file)
        if votos_gj:
            # Filtrar features do GeoJSON baseado no df_f
            if not df_f.empty:
                # Criar conjunto de coordenadas filtradas para comparação rápida
                filtered_coords = set(zip(df_f["lat"].round(6), df_f["lon"].round(6)))
                
                # Filtrar features
                filtered_features = []
                for feature in votos_gj.get("features", []):
                    geom = feature.get("geometry", {})
                    if geom.get("type") == "Point":
                        coords = geom.get("coordinates", [])
                        if len(coords) >= 2:
                            # Coordenadas em GeoJSON são [lon, lat]
                            lat_rounded = round(coords[1], 6)
                            lon_rounded = round(coords[0], 6)
                            if (lat_rounded, lon_rounded) in filtered_coords:
                                filtered_features.append(feature)
                
                # Criar novo GeoJSON com features filtradas
                if filtered_features:
                    votos_gj_filtered = {
                        "type": "FeatureCollection",
                        "features": filtered_features
                    }
                    
                    meta = {
                        "stem": votos_file.stem,
                        "filename": votos_file.name,
                        "geom": "Point",
                        "type": votos_file.stem,
                    }
                    stl = resolve_layer_style(meta, styles)
                    add_geojson_layer(m, votos_file.stem, votos_gj_filtered, stl)

    finalize_map(m)

    if st_folium is None:
        st.warning("Instale streamlit-folium para renderizar o mapa.")
        st.stop()

    out = st_folium(
        m,
        width=None,
        height=800,
        returned_objects=["all_drawings", "last_active_drawing"],
        key=f"folium_{candidate_folder.name}",
    )

    # seleção por polígono
    last = out.get("last_active_drawing")
    if isinstance(last, dict) and last.get("geometry"):
        gtype = (last.get("geometry") or {}).get("type")
        if str(gtype).lower() in ("polygon", "multipolygon"):
            st.session_state["selection_geojson"] = last

    df_sel = df_f
    if st.session_state.get("selection_geojson"):
        df_sel = filter_points_within_polygon(df_f, st.session_state["selection_geojson"])
        
        # Formatar números sem vírgula
        total_sel = int(df_sel["qt_votos"].sum())
        pontos_sel = len(df_sel)

        st.markdown(
            f"<div class='lv-card'><b>Seleção por polígono</b><br/>Total de votos na área: <b>{total_sel:,}".replace(",", ".") + f"</b><br/>Pontos dentro: <b>{pontos_sel:,}".replace(",", ".") + "</b></div>",
            unsafe_allow_html=True,
        )

    # ---- Gráficos
    st.subheader("📊 Gráficos")
    base_df = df_sel if st.session_state.get("selection_geojson") else df_f
    if base_df.empty:
        st.info("Sem dados para gráficos com os filtros e a seleção atual.")
        return

    # Detectar tipo de arquivo para mostrar gráficos apropriados
    if is_municipios:
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("🏆 Top 15 municípios com mais votos")
            ch = chart_top_municipios(base_df, top_n=15)
            if ch is None:
                st.info("Sem dados de municípios.")
            else:
                st.altair_chart(ch, use_container_width=True)

        with g2:
            st.markdown("📉 15 municípios com menos votos")
            ch = chart_bottom_municipios(base_df, bottom_n=15)
            if ch is None:
                st.info("Sem dados de municípios.")
            else:
                st.altair_chart(ch, use_container_width=True)
    else:
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("Top locais")
            ch = chart_top_locais(base_df)
            if ch is None:
                st.info("Sem locais preenchidos.")
            else:
                st.altair_chart(ch, use_container_width=True)

        with g2:
            st.markdown("Top bairros/distritos")
            ch = chart_top_bairros(base_df)
            if ch is None:
                st.info("Sem bairros preenchidos.")
            else:
                st.altair_chart(ch, use_container_width=True)

        st.markdown("Distribuição por faixa de votos")
        ch3 = chart_hist_votos(base_df)
        if ch3 is not None:
            st.altair_chart(ch3, use_container_width=True)

    st.subheader("📄 Tabela")
    if is_municipios:
        # Usar coluna original se existir
        cols_show = [mun_col, "qt_votos", "lat", "lon"]
    else:
        # Usar colunas originais se existirem
        cols_show = [local_col, mun_col, "Bairro/Distrito", "Endereço", "qt_votos", "lat", "lon"]
    cols_show = [c for c in cols_show if c in base_df.columns]
    st.dataframe(base_df[cols_show].sort_values("qt_votos", ascending=False), use_container_width=True)
