from pathlib import Path
import sys
import streamlit as st

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from candidatos.candidato_teste.candidato_teste import render

if __name__ == "__main__":
    # Configurar path da pasta data
    st.session_state["COMMON_DATA_DIR"] = str(Path(__file__).resolve().parent.parent / "data")
    render()
