from __future__ import annotations

from pathlib import Path

APP_NAME = "Localiza Votos"

BASE_DIR = Path(__file__).resolve().parents[1]
COMMON_DATA_DIR = BASE_DIR / "data"
CANDIDATOS_DIR = BASE_DIR / "candidatos"

LAYER_STYLE_FILE = COMMON_DATA_DIR / "layers_style.json"
ICONS_DIR = COMMON_DATA_DIR / "icons"

# defaults visuais
DEFAULT_MAP_HEIGHT = 720
DEFAULT_MAP_WIDTH = 1200

