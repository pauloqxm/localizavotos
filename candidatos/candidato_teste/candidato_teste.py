from __future__ import annotations

from pathlib import Path
from localiza.ui import render_candidate

# ===== CONFIG DO CANDIDATO =====
CANDIDATE_TITLE = "Candidato Teste"
CANDIDATE_SUBTITLE = "Mapa de votos por local de votação"

BASE_DIR = Path(__file__).resolve().parent

VOTOS_FILES = [
    BASE_DIR / "votos_municipios.geojson",
    BASE_DIR / "votos_fortaleza.geojson",
]

# opcional: arquivo de bounds (ex: regionais, bairros, etc.)
BOUNDS_FILE = None  # BASE_DIR / "limites.geojson"

def render():
    # renderiza a página do candidato (filtros na própria página)
    render_candidate(
        candidate_folder=BASE_DIR,
        title=CANDIDATE_TITLE,
        subtitle=CANDIDATE_SUBTITLE,
        votos_files=[p for p in VOTOS_FILES if p.exists()],
        bounds_file=BOUNDS_FILE if (BOUNDS_FILE and BOUNDS_FILE.exists()) else None,
    )
