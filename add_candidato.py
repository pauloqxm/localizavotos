#!/usr/bin/env python3
"""
Script para adicionar um novo candidato ao LocalizaVotos

Uso:
    python add_candidato.py "Nome do Candidato" "Subtítulo opcional"
    
Exemplo:
    python add_candidato.py "João Silva" "Mapa de votos por local de votação"
"""

import sys
from pathlib import Path
import re

def slugify(text):
    """Converte texto para formato slug (nome_do_arquivo)"""
    text = text.lower()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9]+', '_', text)
    text = text.strip('_')
    return text

def create_candidate(name, subtitle=None):
    """Cria estrutura completa para um novo candidato"""
    
    if not subtitle:
        subtitle = "Mapa de votos por local de votação"
    
    slug = slugify(name)
    
    # Diretórios
    base_dir = Path(__file__).parent
    candidatos_dir = base_dir / "candidatos" / slug
    pages_dir = base_dir / "pages"
    
    # Criar pasta do candidato
    candidatos_dir.mkdir(parents=True, exist_ok=True)
    
    # Contar páginas existentes para determinar o número
    existing_pages = list(pages_dir.glob("*.py"))
    page_number = len(existing_pages) + 1
    
    # 1. Criar arquivo Python do candidato
    candidate_py = candidatos_dir / f"{slug}.py"
    candidate_content = f'''from __future__ import annotations

from pathlib import Path
from localiza.ui import render_candidate

# ===== CONFIG DO CANDIDATO =====
CANDIDATE_TITLE = "{name}"
CANDIDATE_SUBTITLE = "{subtitle}"

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
'''
    
    with open(candidate_py, 'w', encoding='utf-8') as f:
        f.write(candidate_content)
    
    # 2. Criar página Streamlit
    page_file = pages_dir / f"{page_number}_{slug}.py"
    page_content = f'''from pathlib import Path
import sys
import streamlit as st

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from localiza.ui import hide_sidebar
from candidatos.{slug}.{slug} import render

if __name__ == "__main__":
    hide_sidebar()
    # Configurar path da pasta data
    st.session_state["COMMON_DATA_DIR"] = str(Path(__file__).resolve().parent.parent / "data")
    render()
'''
    
    with open(page_file, 'w', encoding='utf-8') as f:
        f.write(page_content)
    
    # 3. Criar arquivo README com instruções
    readme_file = candidatos_dir / "README.md"
    readme_content = f'''# {name}

## Arquivos necessários

Adicione os seguintes arquivos GeoJSON nesta pasta:

- `votos_fortaleza.geojson` - Votos por local de votação em Fortaleza
- `votos_municipios.geojson` - Votos agregados por município (opcional)

## Estrutura dos arquivos GeoJSON

### votos_fortaleza.geojson
Deve conter pontos com as seguintes propriedades:
- `NM_MUNICIPIO` - Nome do município
- `NM_LOCAL_VOTACAO` - Nome do local de votação
- `NM_VOTAVEL` - Nome do candidato
- `NR_VOTAVEL` - Número do candidato
- `QT_VOTOS` - Quantidade de votos
- `NR_ZONA` - Número da zona eleitoral

### votos_municipios.geojson
Deve conter pontos com as seguintes propriedades:
- `NM_MUNICIPIO` - Nome do município
- `NM_VOTAVEL` - Nome do candidato
- `NR_VOTAVEL` - Número do candidato
- `TOTAL_VOTOS_MUNICIPIO` - Total de votos no município

## URL de acesso

Após adicionar os arquivos, a página estará disponível em:
`http://seu-dominio/{slug}`
'''
    
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ Candidato '{name}' criado com sucesso!")
    print(f"\n📁 Pasta criada: {candidatos_dir}")
    print(f"📄 Arquivo Python: {candidate_py}")
    print(f"🌐 Página Streamlit: {page_file}")
    print(f"\n📋 Próximos passos:")
    print(f"1. Adicione os arquivos GeoJSON em: {candidatos_dir}/")
    print(f"   - votos_fortaleza.geojson")
    print(f"   - votos_municipios.geojson (opcional)")
    print(f"2. Commit e push para o GitHub")
    print(f"3. Acesse: http://seu-dominio/{slug}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python add_candidato.py \"Nome do Candidato\" \"Subtítulo opcional\"")
        print("\nExemplo:")
        print('  python add_candidato.py "João Silva" "Mapa de votos por local de votação"')
        sys.exit(1)
    
    name = sys.argv[1]
    subtitle = sys.argv[2] if len(sys.argv) > 2 else None
    
    create_candidate(name, subtitle)
