from __future__ import annotations

import altair as alt
import pandas as pd

def chart_top_municipios(df: pd.DataFrame, top_n: int = 15):
    """Gráfico dos top municípios com mais votos"""
    col = "Município" if "Município" in df.columns else "municipio"
    by_mun = (
        df.groupby(col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    by_mun = by_mun[by_mun[col].astype(str).str.strip() != ""].head(top_n)
    if by_mun.empty:
        return None
    return (
        alt.Chart(by_mun)
        .mark_bar(color="#2ecc71")
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{col}:N", sort="-x", title="Município"),
            tooltip=[alt.Tooltip(f"{col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=400)
    )

def chart_bottom_municipios(df: pd.DataFrame, bottom_n: int = 15):
    """Gráfico dos municípios com menos votos"""
    col = "Município" if "Município" in df.columns else "municipio"
    by_mun = (
        df.groupby(col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    by_mun = by_mun[by_mun[col].astype(str).str.strip() != ""].head(bottom_n)
    if by_mun.empty:
        return None
    return (
        alt.Chart(by_mun)
        .mark_bar(color="#e74c3c")
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{col}:N", sort="x", title="Município"),
            tooltip=[alt.Tooltip(f"{col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=400)
    )

def chart_top_locais(df: pd.DataFrame, top_n: int = 15):
    # Detectar coluna de local
    local_col = "NM_LOCAL_VOTACAO" if "NM_LOCAL_VOTACAO" in df.columns else "local_votacao"
    
    by_local = (
        df.groupby(local_col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    by_local = by_local[by_local[local_col].astype(str).str.strip() != ""].head(top_n)
    if by_local.empty:
        return None
    return (
        alt.Chart(by_local)
        .mark_bar(color="#2ecc71")
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{local_col}:N", sort="-x", title="Local de votação"),
            tooltip=[alt.Tooltip(f"{local_col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=400)
    )

def chart_bottom_locais(df: pd.DataFrame, bottom_n: int = 15):
    # Detectar coluna de local
    local_col = "NM_LOCAL_VOTACAO" if "NM_LOCAL_VOTACAO" in df.columns else "local_votacao"
    
    by_local = (
        df.groupby(local_col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    by_local = by_local[by_local[local_col].astype(str).str.strip() != ""].head(bottom_n)
    if by_local.empty:
        return None
    return (
        alt.Chart(by_local)
        .mark_bar(color="#e74c3c")
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{local_col}:N", sort="x", title="Local de votação"),
            tooltip=[alt.Tooltip(f"{local_col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=400)
    )

def chart_top_bairros(df: pd.DataFrame, top_n: int = 13):
    col = "Bairro/Distrito" if "Bairro/Distrito" in df.columns else "bairro"
    by_b = (
        df.groupby(col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    by_b = by_b[by_b[col].astype(str).str.strip() != ""].head(top_n)
    if by_b.empty:
        return None
    return (
        alt.Chart(by_b)
        .mark_bar()
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{col}:N", sort="-x", title=col),
            tooltip=[alt.Tooltip(f"{col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=340)
    )

def chart_hist_votos(df: pd.DataFrame):
    # se existir coluna 'secao' ou 'zona' no futuro, dá pra trocar.
    if "qt_votos" not in df.columns:
        return None
    # distribuição simples por faixas
    bins = [0, 10, 30, 60, 100, 200, 500, 1000, 999999]
    labels = ["0-10", "11-30", "31-60", "61-100", "101-200", "201-500", "501-1000", "1000+"]
    s = pd.cut(df["qt_votos"].fillna(0), bins=bins, labels=labels, include_lowest=True)
    h = s.value_counts().reindex(labels).reset_index()
    h.columns = ["faixa", "pontos"]
    return (
        alt.Chart(h)
        .mark_bar()
        .encode(
            x=alt.X("faixa:N", sort=labels, title="Faixa de votos por ponto"),
            y=alt.Y("pontos:Q", title="Quantidade de pontos"),
            tooltip=["faixa:N", "pontos:Q"],
        )
        .properties(height=240)
    )

def chart_concentracao_votos(df: pd.DataFrame):
    """Gráfico de concentração de votos (Curva de Pareto) - mostra quantos locais concentram X% dos votos"""
    local_col = "NM_LOCAL_VOTACAO" if "NM_LOCAL_VOTACAO" in df.columns else "local_votacao"
    
    by_local = (
        df.groupby(local_col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    
    if by_local.empty or by_local["qt_votos"].sum() == 0:
        return None
    
    by_local["percentual_acumulado"] = (by_local["qt_votos"].cumsum() / by_local["qt_votos"].sum() * 100)
    by_local["rank"] = range(1, len(by_local) + 1)
    
    # Gráfico de linha com área
    line = alt.Chart(by_local).mark_line(color="#3498db", size=3).encode(
        x=alt.X("rank:Q", title="Número de locais (ordenados por votos)"),
        y=alt.Y("percentual_acumulado:Q", title="% Acumulado de votos", scale=alt.Scale(domain=[0, 100])),
        tooltip=[
            alt.Tooltip("rank:Q", title="Posição"),
            alt.Tooltip("percentual_acumulado:Q", title="% Acumulado", format=".1f"),
            alt.Tooltip(local_col, title="Local")
        ]
    )
    
    area = alt.Chart(by_local).mark_area(opacity=0.3, color="#3498db").encode(
        x=alt.X("rank:Q"),
        y=alt.Y("percentual_acumulado:Q")
    )
    
    # Linha de referência 80%
    rule = alt.Chart(pd.DataFrame({"y": [80]})).mark_rule(color="red", strokeDash=[5, 5]).encode(y="y:Q")
    
    return (area + line + rule).properties(height=300)

def chart_votos_por_zona(df: pd.DataFrame):
    """Gráfico de barras com votos totais e média por zona eleitoral"""
    if "NR_ZONA" not in df.columns:
        return None
    
    by_zona = df.groupby("NR_ZONA").agg({
        "qt_votos": ["sum", "mean", "count"]
    }).reset_index()
    by_zona.columns = ["zona", "total_votos", "media_votos", "num_locais"]
    by_zona = by_zona.sort_values("total_votos", ascending=False).head(20)
    
    if by_zona.empty:
        return None
    
    # Gráfico de barras com total
    bars = alt.Chart(by_zona).mark_bar(color="#9b59b6").encode(
        x=alt.X("zona:N", title="Zona Eleitoral", sort="-y"),
        y=alt.Y("total_votos:Q", title="Total de Votos"),
        tooltip=[
            alt.Tooltip("zona:N", title="Zona"),
            alt.Tooltip("total_votos:Q", title="Total Votos", format=",.0f"),
            alt.Tooltip("media_votos:Q", title="Média por Local", format=".1f"),
            alt.Tooltip("num_locais:Q", title="Nº Locais")
        ]
    )
    
    # Linha com média
    line = alt.Chart(by_zona).mark_line(color="#e74c3c", size=2, point=True).encode(
        x=alt.X("zona:N", sort="-y"),
        y=alt.Y("media_votos:Q", title="Média de Votos por Local"),
    )
    
    return alt.layer(bars, line).resolve_scale(y="independent").properties(height=350)

def chart_dispersao_geografica(df: pd.DataFrame):
    """Gráfico de dispersão geográfica com tamanho proporcional aos votos"""
    if "lat" not in df.columns or "lon" not in df.columns:
        return None
    
    # Limitar a 200 pontos para performance
    df_sample = df.nlargest(200, "qt_votos") if len(df) > 200 else df.copy()
    
    return (
        alt.Chart(df_sample)
        .mark_circle(opacity=0.6)
        .encode(
            x=alt.X("lon:Q", title="Longitude", scale=alt.Scale(zero=False)),
            y=alt.Y("lat:Q", title="Latitude", scale=alt.Scale(zero=False)),
            size=alt.Size("qt_votos:Q", title="Votos", scale=alt.Scale(range=[50, 1000])),
            color=alt.Color("qt_votos:Q", scale=alt.Scale(scheme="viridis"), title="Votos"),
            tooltip=[
                alt.Tooltip("NM_LOCAL_VOTACAO:N" if "NM_LOCAL_VOTACAO" in df.columns else "local_votacao:N", title="Local"),
                alt.Tooltip("qt_votos:Q", title="Votos", format=",.0f"),
                alt.Tooltip("lat:Q", title="Latitude", format=".4f"),
                alt.Tooltip("lon:Q", title="Longitude", format=".4f")
            ]
        )
        .properties(height=400)
        .interactive()
    )
