from __future__ import annotations

from pathlib import Path
import streamlit as st

def main():
    st.set_page_config(page_title="LocalizaVotos", layout="wide")
    
    st.markdown(
        """
        <style>
          .block-container { padding-top: 1.2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <div style='text-align: center; padding: 40px;'>
            <h1>🗳️ LocalizaVotos</h1>
            <p style='font-size: 18px; margin-top: 20px;'>Sistema de visualização de votos por candidato</p>
            <p style='margin-top: 30px;'>Selecione um candidato no menu lateral para visualizar os dados.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
