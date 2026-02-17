from __future__ import annotations

import math
from typing import Any, Iterable

ALIASES: dict[str, list[str]] = {
    "id": ["id", "ID", "_id", "fid", "objectid", "OBJECTID"],
    "nome": [
        "nome",
        "Nome",
        "Name",
        "NM_DISTRITO",
        "NM_DISTRIT",
        "NM_DIST",
        "NM",
        "NOME",
        "LABEL",
        "label",
        "BAIRRO",
        "BAI_NM",
        "nome_proje",
        "LOCALIDADE",
        "BAIRRO_DISTRITO",
        "Bairro/Distrito",
    ],
    "municipio": ["municipio", "município", "Municipio", "Município", "MUNICIPIO", "Mun"],
    "distrito": [
        "distrito",
        "Distrito",
        "nome_do_distrito",
        "DIST",
        "NM_DISTRITO",
        "NM_DISTR",
        "NM_DIST",
        "BAIRRO_DISTRITO",
        "Bairro/Distrito",
    ],
    "endereco": ["Endereço", "Endereco", "endereco", "address", "logradouro", "LOGRADOURO"],
    "bairro": ["Bairro", "bairro", "Bairro/Distrito", "bairro/distrito", "BAIRRO", "Distrito", "distrito"],
    "local_votacao": ["local_votacao", "local votação", "local", "local_de_votacao", "LOCAL_VOT"],
    "qt_votos": ["qt_votos", "qtvotos", "votos", "qtde_votos", "quantidade_votos", "QT_VOTOS"],
}


def safe_text(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none", "null"):
        return ""
    return s


def safe_number(v: Any) -> float | None:
    """
    Converte valores numéricos aceitando:
    - Padrão internacional: 1234.56
    - Padrão BR: 1.234,56 ou 1234,56
    Importante: NÃO remove ponto decimal de coordenadas como -3.7397117.
    """
    if v is None:
        return None

    # Se já é número, não mexe. Era aqui que quebrava as coordenadas no fluxo anterior.
    if isinstance(v, (int, float)):
        try:
            return float(v)
        except Exception:
            return None

    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "none", "null"):
        return None

    s = s.replace(" ", "")

    # Tem vírgula e ponto: decide qual é o decimal pelo último separador
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # vírgula é decimal, ponto é milhar
            s = s.replace(".", "").replace(",", ".")
        else:
            # ponto é decimal, vírgula é milhar
            s = s.replace(",", "")
    elif "," in s:
        # só vírgula: vírgula é decimal
        s = s.replace(".", "")
        s = s.replace(",", ".")
    else:
        # só ponto ou nenhum separador: mantém
        pass

    try:
        return float(s)
    except Exception:
        return None


def pick_prop(props: dict[str, Any], keys: Iterable[str]) -> Any:
    if not isinstance(props, dict):
        return None
    for k in keys:
        if k in props:
            return props.get(k)
        # tenta case-insensitive
        for kk in props.keys():
            if str(kk).lower() == str(k).lower():
                return props.get(kk)
    return None


def get_latlon(props: dict[str, Any], geom: dict[str, Any]) -> tuple[float | None, float | None]:
    # prioridade: propriedades lat/lon
    lat = pick_prop(props, ["lat", "LAT", "latitude", "Latitude"])
    lon = pick_prop(props, ["lon", "LON", "longitude", "Longitude", "lng", "LNG"])

    latn = safe_number(lat)
    lonn = safe_number(lon)
    if latn is not None and lonn is not None:
        return latn, lonn

    # fallback: geometry Point (GeoJSON: [lon, lat])
    try:
        if (geom or {}).get("type") == "Point":
            coords = (geom or {}).get("coordinates") or []
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                return float(coords[1]), float(coords[0])
    except Exception:
        pass
    return None, None


def normalize_feature(ft: dict[str, Any], tipo: str | None = None, force_nome_from: str | None = None) -> dict[str, Any]:
    props = (ft or {}).get("properties") or {}
    geom = (ft or {}).get("geometry") or {}

    nome = safe_text(pick_prop(props, ALIASES["nome"]))
    municipio = safe_text(pick_prop(props, ALIASES["municipio"]))
    distrito = safe_text(pick_prop(props, ALIASES["distrito"]))
    endereco = safe_text(pick_prop(props, ALIASES["endereco"]))
    bairro = safe_text(pick_prop(props, ALIASES["bairro"]))
    local_votacao = safe_text(pick_prop(props, ALIASES["local_votacao"]))
    qt_votos_raw = pick_prop(props, ALIASES["qt_votos"])
    qt_votos = safe_number(qt_votos_raw) or 0.0

    if force_nome_from:
        forced = safe_text(pick_prop(props, [force_nome_from]))
        if forced:
            nome = forced

    lat, lon = get_latlon(props, geom)
    
    # Preservar QT_VOTOS original nas properties se existir
    if "QT_VOTOS" not in props and qt_votos_raw is not None:
        props["QT_VOTOS"] = qt_votos

    return {
        "tipo": safe_text(tipo),
        "nome": nome,
        "municipio": municipio,
        "distrito": distrito,
        "bairro": bairro,
        "endereco": endereco,
        "local_votacao": local_votacao,
        "qt_votos": qt_votos,
        "lat": lat,
        "lon": lon,
        "properties": props,
        "geometry": geom,
        "id": safe_text(pick_prop(props, ALIASES["id"])),
    }


def normalize_geojson(gj: dict[str, Any], tipo: str | None = None, force_nome_from: str | None = None) -> list[dict[str, Any]]:
    feats = (gj or {}).get("features") or []
    rows: list[dict[str, Any]] = []
    for ft in feats:
        try:
            rows.append(normalize_feature(ft, tipo=tipo, force_nome_from=force_nome_from))
        except Exception:
            continue
    return rows


def circle_radius(votes: float) -> float:
    v = max(0.0, float(votes))
    return 180 + (math.sqrt(v) * 32)


def _flatten_coords(coords):
    out = []
    if coords is None:
        return out
    if (
        isinstance(coords, (list, tuple))
        and len(coords) == 2
        and all(isinstance(x, (int, float)) for x in coords)
    ):
        out.append(coords)
        return out
    if isinstance(coords, (list, tuple)):
        for c in coords:
            out.extend(_flatten_coords(c))
    return out


def bounds_center_from_geojson(gj: dict[str, Any]):
    if not gj:
        return None, None
    lons, lats = [], []
    for ft in (gj.get("features") or []):
        geom = ft.get("geometry") or {}
        coords = geom.get("coordinates")
        pts = _flatten_coords(coords)
        for p in pts:
            try:
                lons.append(float(p[0]))
                lats.append(float(p[1]))
            except Exception:
                pass
    if not lons or not lats:
        return None, None
    minlon, maxlon = min(lons), max(lons)
    minlat, maxlat = min(lats), max(lats)
    bounds = [[minlat, minlon], [maxlat, maxlon]]
    center = [(minlat + maxlat) / 2.0, (minlon + maxlon) / 2.0]
    return bounds, center
