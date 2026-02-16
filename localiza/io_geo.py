from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def read_geojson(path: Path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def discover_layers_geojson(data_dir: Path, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    """Descobre arquivos .geojson em uma pasta e retorna metadados básicos + conteúdo."""
    exclude = exclude or set()
    layers: list[dict[str, Any]] = []
    for p in sorted(data_dir.glob("*.geojson")):
        if p.name in exclude:
            continue
        gj = read_geojson(p)
        if not gj:
            continue
        feats = gj.get("features") or []
        geom0 = (feats[0].get("geometry") or {}).get("type") if feats else None
        layers.append(
            {
                "path": p,
                "stem": p.stem,
                "filename": p.name,
                "geojson": gj,
                "features": len(feats),
                "geom": geom0,
            }
        )
    return layers
