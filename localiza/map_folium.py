from __future__ import annotations

from typing import Any, Tuple

import folium
from folium.plugins import MeasureControl, Fullscreen, Draw, MousePosition, HeatMap

from .schema import circle_radius


def add_base_tiles(m: folium.Map):
    tile_layers = [
        {"name": "Top Map", "url": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", "attr": "© OpenTopoMap"},
        {"name": "OpenStreetMap", "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", "attr": "© OpenStreetMap contributors"},
        {"name": "CartoDB Positron", "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", "attr": "© CARTO"},
        {"name": "CartoDB Dark", "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", "attr": "© CARTO"},
        {"name": "Esri World Imagery", "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "attr": "Tiles © Esri"},
    ]
    for t in tile_layers:
        folium.TileLayer(tiles=t["url"], attr=t["attr"], name=t["name"], control=True).add_to(m)


def build_map(center: list[float], zoom_start: int = 11) -> folium.Map:
    m = folium.Map(location=center, zoom_start=zoom_start, tiles=None, control_scale=True)
    add_base_tiles(m)

    Fullscreen(
        position="topright",
        force_separate_button=True,
        title="Tela Cheia",
        title_cancel="Sair da Tela Cheia",
    ).add_to(m)

    MeasureControl(
        position="topleft",
        primary_length_unit="meters",
        secondary_length_unit="kilometers",
        primary_area_unit="hectares",
        secondary_area_unit="sqmeters",
    ).add_to(m)

    MousePosition().add_to(m)

    Draw(
        export=True,
        position="topleft",
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
    def _style(_):
        return {
            "color": style.get("color", "#2b6cb0"),
            "weight": style.get("weight", 2),
            "opacity": style.get("opacity", 0.9),
            "fillColor": style.get("fillColor", style.get("color", "#2b6cb0")),
            "fillOpacity": style.get("fillOpacity", 0.15),
        }

    folium.GeoJson(
        geojson,
        name=name,
        style_function=_style,
        tooltip=folium.GeoJsonTooltip(fields=[]),
        show=bool(style.get("show", True)),
    ).add_to(m)


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

    fg = folium.FeatureGroup(name=name, show=bool(style.get("show", True)))
    fg.add_to(m)

    heat_pts = []

    for _, r in df_points.iterrows():
        fixed = _fix_latlon(r.get("lat"), r.get("lon"))
        if not fixed:
            continue
        lat_f, lon_f = fixed

        votos = _to_float(r.get("qt_votos")) or 0.0

        if use_heatmap:
            heat_pts.append([lat_f, lon_f, max(0.1, float(votos))])

        html = "<div style='min-width:240px'>"
        for c in popup_cols:
            try:
                if c in r.index:
                    html += f"<div><b>{c}</b>. {r.get(c, '')}</div>"
            except Exception:
                val = r.get(c, "")
                if val != "":
                    html += f"<div><b>{c}</b>. {val}</div>"
        html += "</div>"
        popup = folium.Popup(html, max_width=380)

        if mode == "circle":
            folium.Circle(
                location=[lat_f, lon_f],
                radius=circle_radius(votos) if style.get("radius_mode") == "votes" else radius,
                color=color,
                weight=float(style.get("weight", 2)),
                fill=True,
                fill_color=fill,
                fill_opacity=float(style.get("fillOpacity", 0.7)),
                popup=popup,
            ).add_to(fg)
        else:
            folium.CircleMarker(
                location=[lat_f, lon_f],
                radius=radius,
                color=color,
                weight=float(style.get("weight", 2)),
                fill=True,
                fill_color=fill,
                fill_opacity=float(style.get("fillOpacity", 0.85)),
                popup=popup,
            ).add_to(fg)

    if use_heatmap and heat_pts:
        HeatMap(heat_pts, name=f"{name} Heat", show=False, min_opacity=0.3).add_to(m)


def finalize_map(m: folium.Map):
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # CSS para garantir visibilidade do LayerControl em todas as telas
    css = """
    <style>
    .leaflet-control-layers {
        z-index: 1000 !important;
        margin-top: 60px !important;
    }
    @media (max-width: 768px) {
        .leaflet-control-layers {
            margin-top: 10px !important;
            margin-right: 10px !important;
        }
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(css))
