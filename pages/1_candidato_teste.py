from pathlib import Path
import sys
import streamlit as st

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from localiza.ui import hide_sidebar
from candidatos.candidato_teste.candidato_teste import render

if __name__ == "__main__":
    hide_sidebar()
    # Configurar path da pasta data
    st.session_state["COMMON_DATA_DIR"] = str(Path(__file__).resolve().parent.parent / "data")
    render()
