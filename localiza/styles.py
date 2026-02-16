from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import LAYER_STYLE_FILE

def merge_dict(a: dict, b: dict):
    out = dict(a or {})
    for k, v in (b or {}).items():
        out[k] = v
    return out

def geom_kind_from_geom(geom: str | None) -> str:
    g = (geom or "").lower()
    if g in ("point", "multipoint"):
        return "point"
    if g in ("linestring", "multilinestring"):
        return "line"
    if g in ("polygon", "multipolygon"):
        return "polygon"
    return "unknown"

def load_layer_styles(path: Path | None = None) -> dict[str, Any]:
    path = path or LAYER_STYLE_FILE
    if not path.exists():
        return {"defaults": {}, "layers": {}}
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {"defaults": {}, "layers": {}}
    except Exception:
        return {"defaults": {}, "layers": {}}

def default_style_for_kind(layer_type: str, kind: str) -> dict[str, Any]:
    # base bem conservadora (o JSON do usuário costuma sobrepor)
    if kind == "polygon":
        return {"fillColor": "#2b6cb0", "fillOpacity": 0.15, "color": "#2b6cb0", "weight": 2}
    if kind == "line":
        return {"color": "#2b6cb0", "weight": 3, "opacity": 0.9}
    # point
    return {"mode": "circle", "radius": 6, "color": "#2b6cb0", "fillColor": "#2b6cb0", "fillOpacity": 0.85}

def resolve_layer_style(layer_meta: dict[str, Any], styles: dict[str, Any]) -> dict[str, Any]:
    defaults = (styles or {}).get("defaults", {})
    layers_cfg = (styles or {}).get("layers", {})

    kind = geom_kind_from_geom(layer_meta.get("geom"))
    layer_type = (layer_meta.get("type") or "").lower()
    stem = layer_meta.get("stem") or layer_meta.get("filename") or ""

    base = default_style_for_kind(layer_type, kind)
    base = merge_dict(base, (defaults.get(kind) or {}))

    # por nome da camada (stem)
    per = layers_cfg.get(stem) or layers_cfg.get(stem.lower()) or {}
    base = merge_dict(base, per)

    return base
