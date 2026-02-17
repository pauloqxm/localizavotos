from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

try:
    from shapely.geometry import shape as shp_shape
    from shapely.geometry import Point
except Exception:
    shp_shape = None
    Point = None

from .io_geo import read_geojson
from .schema import normalize_geojson, _flatten_coords

def load_votos_df(votos_file: Path) -> pd.DataFrame:
    gj = read_geojson(votos_file)
    if not gj:
        return pd.DataFrame()

    rows = normalize_geojson(gj, tipo="votacao", force_nome_from="local_votacao")
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # colunas amigáveis pra UI/legado
    df["local_votacao"] = df["nome"]
    df["Endereço"] = df["endereco"]
    df["Município"] = df["municipio"]
    if (df["distrito"].astype(str).str.strip() != "").any():
        df["Bairro/Distrito"] = df["distrito"]
    else:
        df["Bairro/Distrito"] = df["bairro"]

    # Usar sempre qt_votos (já normalizado pelo schema)
    df["qt_votos"] = pd.to_numeric(df["qt_votos"], errors="coerce").fillna(0.0)

    df = df.dropna(subset=["lat", "lon"])
    return df

def filter_points_within_polygon(df_points: pd.DataFrame, poly_geojson: dict[str, Any]):
    if df_points.empty or not poly_geojson:
        return df_points

    geom = poly_geojson.get("geometry") or {}
    gtype = (geom.get("type") or "").lower()
    if gtype not in ("polygon", "multipolygon"):
        return df_points

    if shp_shape is None or Point is None:
        coords = geom.get("coordinates")
        pts = _flatten_coords(coords)
        if not pts:
            return df_points
        lons = [p[0] for p in pts]
        lats = [p[1] for p in pts]
        minlon, maxlon = min(lons), max(lons)
        minlat, maxlat = min(lats), max(lats)
        return df_points[
            (df_points["lon"] >= minlon)
            & (df_points["lon"] <= maxlon)
            & (df_points["lat"] >= minlat)
            & (df_points["lat"] <= maxlat)
        ]

    try:
        poly = shp_shape(geom)
    except Exception:
        return df_points

    inside_mask = []
    for _, r in df_points.iterrows():
        try:
            inside_mask.append(poly.contains(Point(float(r["lon"]), float(r["lat"]))))
        except Exception:
            inside_mask.append(False)

    if not inside_mask:
        return df_points
    return df_points[pd.Series(inside_mask, index=df_points.index)]
