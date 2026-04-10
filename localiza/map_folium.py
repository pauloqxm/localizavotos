from __future__ import annotations

from typing import Any, Tuple

import folium
from folium.plugins import MeasureControl, Fullscreen, Draw, MousePosition, HeatMap

from .schema import circle_radius


def add_base_tiles(m: folium.Map):
    tile_layers = [
        {"name": "Top Map", "url": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", "attr": "© OpenTopoMap"},
        {"name": "CartoDB Positron", "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", "attr": "© CARTO"},
        {"name": "CartoDB Dark", "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", "attr": "© CARTO"},
        {"name": "Esri World Imagery", "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "attr": "Tiles © Esri"},
        {"name": "OpenStreetMap", "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", "attr": "© OpenStreetMap contributors"},
    ]
    for t in tile_layers:
        folium.TileLayer(tiles=t["url"], attr=t["attr"], name=t["name"], control=True).add_to(m)


def build_map(center: list[float], zoom_start: int = 11) -> folium.Map:
    m = folium.Map(location=center, zoom_start=zoom_start, tiles=None, control_scale=True)
    add_base_tiles(m)

    # Fullscreen no lado esquerdo
    Fullscreen(
        position="topleft",
        force_separate_button=True,
        title="Tela Cheia",
        title_cancel="Sair da Tela Cheia",
    ).add_to(m)

    # MeasureControl no lado direito
    MeasureControl(
        position="topright",
        primary_length_unit="meters",
        secondary_length_unit="kilometers",
        primary_area_unit="hectares",
        secondary_area_unit="sqmeters",
    ).add_to(m)

    # MousePosition no lado direito
    MousePosition(position="bottomright").add_to(m)

    # Draw no lado direito, sem export
    Draw(
        export=False,
        position="topright",
        draw_options={
            "polyline": True,
            "polygon": {"allowIntersection": False, "showArea": True},
            "rectangle": {"showArea": True},
            "circle": {"showArea": True},
            "circlemarker": False,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    return m


def _to_float(x):
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _rescale_to_range(value: float, limit: float, max_divs: int = 12) -> float:
    """
    Se vier como inteiro sem vírgula (ex: -382093835), divide por 10 até caber na faixa.
    """
    v = float(value)
    divs = 0
    while abs(v) > limit and divs < max_divs:
        v = v / 10.0
        divs += 1
    return v


def _fix_latlon(lat, lon) -> Tuple[float, float] | None:
    """
    Retorna (lat, lon) prontos pro Folium.
    Corrige escala quebrada e inversão.
    """
    lat_f = _to_float(lat)
    lon_f = _to_float(lon)
    if lat_f is None or lon_f is None:
        return None

    # 1) Corrige escala antes de qualquer coisa
    lat_f = _rescale_to_range(lat_f, 90)
    lon_f = _rescale_to_range(lon_f, 180)

    # 2) Se ainda estiver estranho, tenta inverter e reescalar de novo
    if (abs(lat_f) > 90 and abs(lon_f) <= 90) or (abs(lon_f) > 180 and abs(lat_f) <= 180):
        lat_f, lon_f = lon_f, lat_f
        lat_f = _rescale_to_range(lat_f, 90)
        lon_f = _rescale_to_range(lon_f, 180)

    # 3) Validação final
    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        return None

    return lat_f, lon_f


def add_geojson_layer(m: folium.Map, name: str, geojson: dict[str, Any], style: dict[str, Any]):
    # Simbologia graduada para polígonos (ex: renda)
    if style.get("mode") == "graduated" and geojson.get("features"):
        first_geom = geojson["features"][0].get("geometry", {}).get("type")
        if first_geom in ("Polygon", "MultiPolygon"):
            field = style.get("field", "renda_media")
            num_classes = style.get("classes", 5)
            colors = style.get("colors", ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"])
            
            # Coletar valores do campo
            values = []
            for feature in geojson["features"]:
                val = feature.get("properties", {}).get(field)
                if val is not None:
                    try:
                        values.append(float(val))
                    except:
                        pass
            
            if values:
                # Calcular quebras naturais (quantis)
                values_sorted = sorted(values)
                n = len(values_sorted)
                breaks = [values_sorted[0]]
                for i in range(1, num_classes):
                    idx = int((i / num_classes) * n)
                    if idx < n:
                        breaks.append(values_sorted[idx])
                breaks.append(values_sorted[-1])
                
                def get_color(value):
                    if value is None:
                        return "#cccccc"
                    try:
                        val = float(value)
                        for i in range(len(breaks) - 1):
                            if breaks[i] <= val <= breaks[i + 1]:
                                return colors[min(i, len(colors) - 1)]
                        return colors[-1]
                    except:
                        return "#cccccc"
                
                def style_function(feature):
                    val = feature.get("properties", {}).get(field)
                    color = get_color(val)
                    return {
                        "fillColor": color,
                        "color": style.get("color", "#000000"),
                        "weight": style.get("weight", 1),
                        "opacity": style.get("opacity", 0.8),
                        "fillOpacity": style.get("fillOpacity", 0.6)
                    }
                
                # Tooltip personalizado com formatação
                def format_currency(val):
                    try:
                        return f"R$ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    except:
                        return str(val)
                
                def format_number(val):
                    try:
                        return f"{int(val):,}".replace(",", ".")
                    except:
                        return str(val)
                
                # Criar GeoJson com tooltip formatado
                def create_tooltip(feature):
                    props = feature.get("properties", {})
                    nm_mun = props.get("NM_MUN", "N/A")
                    situacao = props.get("SITUACAO", "N/A")
                    
                    # Detectar se é renda ou população
                    if field == "renda_media":
                        valor = props.get("renda_media")
                        valor_fmt = format_currency(valor) if valor is not None else "N/A"
                        label = "Renda Média"
                    elif field == "v0001":
                        valor = props.get("v0001")
                        valor_fmt = format_number(valor) if valor is not None else "N/A"
                        label = "População"
                    else:
                        valor = props.get(field)
                        valor_fmt = str(valor) if valor is not None else "N/A"
                        label = field
                    
                    return f"<b>Município:</b> {nm_mun}<br><b>Situação:</b> {situacao}<br><b>{label}:</b> {valor_fmt}"
                
                for feature in geojson["features"]:
                    tooltip_text = create_tooltip(feature)
                    feature["properties"]["_tooltip"] = tooltip_text
                
                folium.GeoJson(
                    geojson,
                    name=name,
                    style_function=style_function,
                    tooltip=folium.GeoJsonTooltip(fields=["_tooltip"], aliases=[""], labels=False, style="background-color: white; color: #333; font-family: arial; font-size: 12px; padding: 10px;"),
                    show=bool(style.get("show", True)),
                ).add_to(m)
                return
    
    # Colorir por região se for ce_regioes
    if "ce_regioes" in name.lower() or "regioes" in name.lower():
        region_colors = {
            "Centro-Sul": "#e74c3c", "Grande Fortaleza": "#3498db", "Litoral Leste": "#2ecc71",
            "Litoral Norte": "#f39c12", "Litoral Oeste": "#9b59b6", "Maciço de Baturité": "#1abc9c",
            "Serra da Ibiapaba": "#e67e22", "Sertão Central": "#34495e", "Sertão de Canindé": "#16a085",
            "Sertão de Cratéus": "#c0392b", "Sertão de Inhamuns": "#8e44ad", "Sertão de Senador Pompeu": "#d35400",
            "Sertão dos Inhamuns": "#27ae60", "Vale do Jaguaribe": "#2980b9",
        }
        
        def _style(feature):
            region = feature.get("properties", {}).get("Região", "")
            color = region_colors.get(region, "#95a5a6")
            return {"color": color, "weight": 2, "opacity": 0.8, "fillColor": color, "fillOpacity": 0.3}
        
        tooltip_fields = []
        if geojson.get("features"):
            props = geojson["features"][0].get("properties", {})
            tooltip_fields = [k for k in props.keys() if k and props[k]]
        
        folium.GeoJson(
            geojson,
            name=name,
            style_function=_style,
            tooltip=folium.GeoJsonTooltip(fields=tooltip_fields[:5]) if tooltip_fields else folium.Tooltip(name),
            show=bool(style.get("show", True)),
        ).add_to(m)
        return
    
    # Suporte para ícones customizados em pontos
    if style.get("mode") == "icon" and geojson.get("features"):
        first_geom = geojson["features"][0].get("geometry", {}).get("type")
        if first_geom == "Point":
            fg = folium.FeatureGroup(name=name, show=bool(style.get("show", True)))
            
            # Detectar se é camada de líderes para tooltip especial
            is_lider = "lider" in name.lower()
            
            for feature in geojson.get("features", []):
                geom = feature.get("geometry", {})
                props = feature.get("properties", {})
                
                if isinstance(geom, dict) and geom.get("type") == "Point":
                    coords = geom.get("coordinates", [])
                    if len(coords) >= 2:
                        icon_url = style.get("iconUrl", style.get("iconPath"))
                        icon_size = style.get("iconSize", 25)
                        
                        icon = folium.CustomIcon(icon_url, icon_size=(icon_size, icon_size))
                        
                        # Tooltip melhorado para líderes
                        if is_lider:
                            tooltip_lines = []
                            # Campos prioritários para líderes
                            priority_fields = ["nome", "NOME", "Nome", "local", "LOCAL", "Local", "telefone", "TELEFONE", "Telefone"]
                            for field in priority_fields:
                                if field in props and props[field]:
                                    emoji = "👤" if "nome" in field.lower() else "📍" if "local" in field.lower() else "📞"
                                    tooltip_lines.append(f"{emoji} <b>{field}</b>: {props[field]}")
                            # Adicionar outros campos
                            for k, v in props.items():
                                if k not in priority_fields and v and len(tooltip_lines) < 5:
                                    tooltip_lines.append(f"<b>{k}</b>: {v}")
                            tooltip_text = "<br>".join(tooltip_lines)
                        else:
                            tooltip_text = "<br>".join([f"<b>{k}</b>: {v}" for k, v in props.items() if v][:5])
                        
                        folium.Marker(
                            location=[coords[1], coords[0]],
                            icon=icon,
                            tooltip=folium.Tooltip(tooltip_text) if tooltip_text else None,
                            popup=folium.Popup(tooltip_text, max_width=300) if tooltip_text else None,
                        ).add_to(fg)
            
            fg.add_to(m)
            return
    
    # Simbologia graduada para pontos de votos
    if "votos" in name.lower() and geojson.get("features"):
        first_geom = geojson["features"][0].get("geometry", {}).get("type")
        if first_geom == "Point":
            fg = folium.FeatureGroup(name=name, show=bool(style.get("show", True)))
            
            # Detectar qual coluna de votos usar (case-insensitive)
            is_municipios = "municipios" in name.lower()
            
            # Tentar encontrar coluna de votos (maiúsculas ou minúsculas)
            first_props = geojson["features"][0].get("properties", {})
            votos_col = None
            for key in first_props.keys():
                if key.upper() == "QT_VOTOS":
                    votos_col = key
                    break
            
            if not votos_col:
                votos_col = "QT_VOTOS"  # fallback
            
            # Calcular min/max para graduação
            votos_vals = [_to_float(f.get("properties", {}).get(votos_col)) or 0 for f in geojson["features"]]
            min_votos = min(votos_vals) if votos_vals else 0
            max_votos = max(votos_vals) if votos_vals else 0
            
            # Mapeamento de campos com emojis (case-insensitive)
            if is_municipios:
                field_map = {
                    "NM_MUNICIPIO": "🏛️ Município",
                    "NM_VOTAVEL": "👤 Nome",
                    "NR_VOTAVEL": "🔢 N°",
                    votos_col: "🗳️ Total Votos",
                }
            else:
                field_map = {
                    "NM_MUNICIPIO": "🏛️ Município",
                    "NM_LOCAL_VOTACAO": "📍 Local de Votação",
                    "NM_VOTAVEL": "👤 Nome",
                    "NR_VOTAVEL": "🔢 N°",
                    votos_col: "🗳️ Quant. Votos",
                    "NR_ZONA": "📍 Zona"
                }
            
            # Coletar pontos para visualização alternativa se for municipios
            markers_data = []
            
            for feature in geojson.get("features", []):
                geom = feature.get("geometry", {})
                props = feature.get("properties", {})
                
                if isinstance(geom, dict) and geom.get("type") == "Point":
                    coords = geom.get("coordinates", [])
                    if len(coords) >= 2:
                        votos = _to_float(props.get(votos_col)) or 0
                        radius = _calculate_graduated_size(votos, min_votos, max_votos)
                        
                        # Coletar dados para marcadores com números se for municipios
                        if is_municipios and votos > 0:
                            markers_data.append({
                                "coords": [coords[1], coords[0]],
                                "votos": votos,
                                "municipio": props.get("NM_MUNICIPIO", "")
                            })
                        
                        # Criar tooltip customizado
                        tooltip_lines = []
                        for field, label in field_map.items():
                            if field in props and props[field]:
                                tooltip_lines.append(f"<b>{label}</b>: {props[field]}")
                        tooltip_text = "<br>".join(tooltip_lines)
                        
                        folium.CircleMarker(
                            location=[coords[1], coords[0]],
                            radius=radius,
                            color=style.get("color", "#1f6feb"),
                            weight=2,
                            fill=True,
                            fill_color=style.get("fillColor", "#1f6feb"),
                            fill_opacity=0.6,
                            tooltip=folium.Tooltip(tooltip_text) if tooltip_text else None,
                            popup=folium.Popup(tooltip_text, max_width=300) if tooltip_text else None,
                        ).add_to(fg)
            
            fg.add_to(m)
            
            # Adicionar camada com números de votos para municipios
            if is_municipios and markers_data:
                fg_numbers = folium.FeatureGroup(name=f"{name} - Números", show=False)
                
                for data in markers_data:
                    votos_int = int(data["votos"])
                    # Determinar cor baseada na quantidade de votos
                    if votos_int >= max_votos * 0.7:
                        color = "#d32f2f"  # Vermelho escuro
                    elif votos_int >= max_votos * 0.4:
                        color = "#f57c00"  # Laranja
                    else:
                        color = "#1976d2"  # Azul
                    
                    icon_html = f"""
                    <div style="
                        background-color: {color};
                        color: white;
                        border: 2px solid white;
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        font-size: 11px;
                        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                    ">{votos_int}</div>
                    """
                    
                    folium.Marker(
                        location=data["coords"],
                        icon=folium.DivIcon(html=icon_html),
                        tooltip=f"<b>{data['municipio']}</b><br>{votos_int} votos"
                    ).add_to(fg_numbers)
                
                fg_numbers.add_to(m)
            
            return
    
    # Estilo padrão para polígonos e linhas
    def _style(_):
        return {
            "color": style.get("color", "#2b6cb0"),
            "weight": style.get("weight", 2),
            "opacity": style.get("opacity", 0.9),
            "fillColor": style.get("fillColor", style.get("color", "#2b6cb0")),
            "fillOpacity": style.get("fillOpacity", 0.15),
        }

    tooltip_fields = []
    if geojson.get("features"):
        props = geojson["features"][0].get("properties", {})
        tooltip_fields = [k for k in props.keys() if k and props[k]]
    
    folium.GeoJson(
        geojson,
        name=name,
        style_function=_style,
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields[:5]) if tooltip_fields else folium.Tooltip(name),
        show=bool(style.get("show", True)),
    ).add_to(m)


def _calculate_graduated_size(value: float, min_val: float, max_val: float, num_classes: int = 5) -> float:
    """Calcula o tamanho do círculo baseado em classes de intervalo igual."""
    if max_val == min_val:
        return 8
    
    interval = (max_val - min_val) / num_classes
    class_idx = min(int((value - min_val) / interval), num_classes - 1)
    
    # Tamanhos de 4 a 20 pixels
    sizes = [4, 8, 12, 16, 20]
    return sizes[class_idx]


def add_points_layer(
    m: folium.Map,
    name: str,
    df_points,
    style: dict[str, Any],
    popup_cols: list[str] | None = None,
    use_heatmap: bool = False,
):
    popup_cols = popup_cols or ["nome", "municipio", "Bairro/Distrito", "Endereço", "qt_votos"]

    color = style.get("color", "#2b6cb0")
    fill = style.get("fillColor", color)
    radius = float(style.get("radius", 6))
    mode = style.get("mode", "circle")
    graduated = style.get("graduated", False)

    fg = folium.FeatureGroup(name=name, show=bool(style.get("show", True)))
    fg.add_to(m)

    heat_pts = []
    
    # Calcular min/max para simbologia graduada
    min_votos = max_votos = 0
    if graduated and "qt_votos" in df_points.columns:
        votos_vals = df_points["qt_votos"].dropna()
        if len(votos_vals) > 0:
            min_votos = float(votos_vals.min())
            max_votos = float(votos_vals.max())

    for _, r in df_points.iterrows():
        fixed = _fix_latlon(r.get("lat"), r.get("lon"))
        if not fixed:
            continue
        lat_f, lon_f = fixed

        votos = _to_float(r.get("qt_votos")) or 0.0

        if use_heatmap:
            heat_pts.append([lat_f, lon_f, max(0.1, float(votos))])

        html = "<div style='min-width:240px'>"
        tooltip_text = ""
        for c in popup_cols:
            try:
                if c in r.index:
                    val = r.get(c, '')
                    html += f"<div><b>{c}</b>: {val}</div>"
                    if c in ["local_votacao", "qt_votos"]:
                        tooltip_text += f"{c}: {val}\n"
            except Exception:
                val = r.get(c, "")
                if val != "":
                    html += f"<div><b>{c}</b>: {val}</div>"
        html += "</div>"
        popup = folium.Popup(html, max_width=380)
        tooltip = folium.Tooltip(tooltip_text.strip() or "Clique para detalhes")
        
        # Determinar tamanho do círculo
        if graduated:
            circle_size = _calculate_graduated_size(votos, min_votos, max_votos)
        elif style.get("radius_mode") == "votes":
            circle_size = circle_radius(votos)
        else:
            circle_size = radius

        if mode == "circle":
            folium.Circle(
                location=[lat_f, lon_f],
                radius=circle_size if not graduated else circle_size * 5,
                color=color,
                weight=float(style.get("weight", 2)),
                fill=True,
                fill_color=fill,
                fill_opacity=float(style.get("fillOpacity", 0.7)),
                popup=popup,
                tooltip=tooltip,
            ).add_to(fg)
        else:
            folium.CircleMarker(
                location=[lat_f, lon_f],
                radius=circle_size if graduated else radius,
                color=color,
                weight=float(style.get("weight", 2)),
                fill=True,
                fill_color=fill,
                fill_opacity=float(style.get("fillOpacity", 0.85)),
                popup=popup,
                tooltip=tooltip,
            ).add_to(fg)

    if use_heatmap and heat_pts:
        HeatMap(heat_pts, name=f"{name} Heat", show=False, min_opacity=0.3).add_to(m)


def finalize_map(m: folium.Map):
    folium.LayerControl(position='topleft', collapsed=True).add_to(m)
    
    # CSS moderno para menu de camadas e legendas
    css = """
    <style>
    /* Menu expandido */
    .leaflet-control-layers-expanded {
        padding: 16px !important;
        background: white !important;
        border-radius: 12px !important;
        min-width: 280px !important;
        max-height: 500px !important;
        overflow-y: auto !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    
    /* Título das seções */
    .leaflet-control-layers-base::before {
        content: '🗺️ Mapas Base';
        display: block;
        font-weight: bold;
        font-size: 14px;
        color: #2563eb;
        margin-bottom: 6px;
        padding-bottom: 6px;
        border-bottom: 2px solid #2563eb;
    }
    
    .leaflet-control-layers-overlays::before {
        content: '📊 Camadas de Dados';
        display: block;
        font-weight: bold;
        font-size: 14px;
        color: #3b82f6;
        margin: 12px 0 6px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #3b82f6;
    }
    
    /* Estilo dos itens - espaçamento reduzido */
    .leaflet-control-layers label {
        padding: 4px 4px !important;
        margin: 2px 0 !important;
        border-radius: 6px !important;
        transition: background 0.2s ease !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        line-height: 1.2 !important;
    }
    
    /* Mapas base com fonte menor e espaçamento reduzido */
    .leaflet-control-layers-base label {
        font-size: 11px !important;
        padding: 2px 4px !important;
        margin: 0.5px 0 !important;
        line-height: 1.1 !important;
    }
    
    .leaflet-control-layers label:hover {
        background: rgba(59, 130, 246, 0.1) !important;
    }
    
    .leaflet-control-layers input[type="radio"],
    .leaflet-control-layers input[type="checkbox"] {
        margin-right: 8px !important;
        cursor: pointer !important;
    }
    
    /* Scrollbar customizada */
    .leaflet-control-layers-expanded::-webkit-scrollbar {
        width: 8px;
    }
    
    .leaflet-control-layers-expanded::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .leaflet-control-layers-expanded::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        border-radius: 10px;
    }
    
    .leaflet-control-layers-expanded::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%);
    }
    
    /* Forçar containers do lado direito a ficarem visíveis */
    .leaflet-top.leaflet-right,
    .leaflet-bottom.leaflet-right {
        position: absolute !important;
        right: 0 !important;
        z-index: 9999 !important;
        pointer-events: auto !important;
    }
    
    .leaflet-top.leaflet-right {
        top: 0 !important;
    }
    
    .leaflet-bottom.leaflet-right {
        bottom: 0 !important;
    }
    
    /* Garantir que os controles sejam visíveis */
    .leaflet-draw,
    .leaflet-control-measure,
    .leaflet-control-mouseposition {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        margin: 10px !important;
    }
    
    /* Responsivo */
    @media (max-width: 768px) {
        .leaflet-draw,
        .leaflet-control-measure,
        .leaflet-control-mouseposition {
            margin: 5px !important;
        }
        
        .leaflet-control-layers-expanded {
            max-height: 400px !important;
            min-width: 240px !important;
        }
        
        .map-legend {
            font-size: 10px !important;
            padding: 8px 12px !important;
        }
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(css))
    
    # JavaScript para controlar visibilidade das legendas
    js = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Aguardar o mapa carregar
        setTimeout(function() {
            // Encontrar todos os checkboxes de camadas
            var layerInputs = document.querySelectorAll('.leaflet-control-layers-overlays input[type="checkbox"]');
            
            layerInputs.forEach(function(input) {
                input.addEventListener('change', function() {
                    var layerName = this.nextSibling.textContent.trim();
                    var legendId = 'legend_' + layerName.replace(/\s+/g, '_');
                    var legend = document.getElementById(legendId);
                    
                    if (legend) {
                        legend.style.display = this.checked ? 'block' : 'none';
                    }
                });
            });
        }, 1000);
    });
    </script>
    """
    m.get_root().html.add_child(folium.Element(js))
