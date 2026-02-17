# 🌐 Adicionar Candidato pelo GitHub Web

## Passo a Passo

### 1️⃣ Criar a Pasta do Candidato

1. Acesse: `https://github.com/seu-usuario/localizavotos`
2. Navegue até a pasta `candidatos/`
3. Clique em **"Add file"** → **"Create new file"**
4. No campo de nome do arquivo, digite: `nome_candidato/nome_candidato.py`
   - Exemplo: `pedro_alves/pedro_alves.py`
   - O GitHub cria a pasta automaticamente quando você usa `/`

### 2️⃣ Copiar o Template do Arquivo Python

Cole este conteúdo (substitua os valores em MAIÚSCULAS):

```python
from __future__ import annotations

from pathlib import Path
from localiza.ui import render_candidate

# ===== CONFIG DO CANDIDATO =====
CANDIDATE_TITLE = "NOME_DO_CANDIDATO"  # Ex: "Pedro Alves"
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
```

3. Clique em **"Commit changes"**

### 3️⃣ Criar a Página Streamlit

1. Navegue até a pasta `pages/`
2. Clique em **"Add file"** → **"Create new file"**
3. Nome do arquivo: `N_nome_candidato.py`
   - `N` = próximo número disponível (3, 4, 5...)
   - Exemplo: `3_pedro_alves.py`

Cole este conteúdo (substitua NOME_CANDIDATO):

```python
from pathlib import Path
import sys
import streamlit as st

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from localiza.ui import hide_sidebar
from candidatos.NOME_CANDIDATO.NOME_CANDIDATO import render

if __name__ == "__main__":
    hide_sidebar()
    # Configurar path da pasta data
    st.session_state["COMMON_DATA_DIR"] = str(Path(__file__).resolve().parent.parent / "data")
    render()
```

4. Clique em **"Commit changes"**

### 4️⃣ Adicionar os Arquivos GeoJSON

1. Navegue até `candidatos/nome_candidato/`
2. Clique em **"Add file"** → **"Upload files"**
3. Faça upload dos arquivos:
   - `votos_fortaleza.geojson` (obrigatório)
   - `votos_municipios.geojson` (opcional)
4. Clique em **"Commit changes"**

---

## 📋 Exemplo Completo

### Para adicionar "Maria Santos":

**Arquivo 1:** `candidatos/maria_santos/maria_santos.py`
```python
CANDIDATE_TITLE = "Maria Santos"
CANDIDATE_SUBTITLE = "Mapa de votos por local de votação"
# ... resto do código igual
```

**Arquivo 2:** `pages/3_maria_santos.py`
```python
from candidatos.maria_santos.maria_santos import render
# ... resto do código igual
```

**Arquivos 3 e 4:** Upload dos GeoJSON na pasta `candidatos/maria_santos/`

---

## ✅ Verificação

Após fazer os commits:
1. Aguarde o deploy automático
2. Acesse: `http://seu-dominio/maria_santos`
3. A página deve carregar com o mapa

---

## 🔍 Estrutura de Pastas Final

```
localizavotos/
├── candidatos/
│   ├── candidato_teste/
│   ├── larissa_gaspar/
│   └── maria_santos/          ← Nova pasta
│       ├── maria_santos.py    ← Arquivo 1
│       ├── votos_fortaleza.geojson
│       └── votos_municipios.geojson
└── pages/
    ├── 1_candidato_teste.py
    ├── 2_larissa_gaspar.py
    └── 3_maria_santos.py      ← Arquivo 2
```

---

## 💡 Dicas

- Use nomes em **minúsculas** e **underscores** (ex: `maria_santos`, não `Maria Santos`)
- O número da página deve ser **sequencial** (1, 2, 3, 4...)
- Sempre faça commit após cada arquivo criado
- Aguarde alguns minutos para o deploy automático

---

## ❓ Problemas Comuns

**Erro 404:** Verifique se o nome da pasta e do arquivo Python são iguais
**Página não carrega:** Verifique se adicionou os arquivos GeoJSON
**Erro de import:** Verifique se o nome no import está correto
