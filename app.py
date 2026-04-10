from __future__ import annotations

from pathlib import Path
import streamlit as st
import hashlib

def check_password():
    """Retorna True se o usuário digitou a senha correta."""
    
    def password_entered():
        """Verifica se a senha está correta."""
        # Hash SHA256 da senha (para segurança)
        # Senha padrão: "admin123" - ALTERE ISSO!
        senha_hash = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
        
        if hashlib.sha256(st.session_state["password"].encode()).hexdigest() == senha_hash:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Não armazenar senha
        else:
            st.session_state["password_correct"] = False

    # CSS para ocultar sidebar antes do login
    st.markdown(
        """
        <style>
          [data-testid="stSidebar"] { display: none !important; }
          [data-testid="stSidebarNav"] { display: none !important; }
          section[data-testid="stSidebar"] { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Primeira execução ou senha incorreta
    if "password_correct" not in st.session_state:
        # Primeira execução, mostrar input
        st.markdown(
            """
            <div style='text-align: center; padding: 40px;'>
                <h1>🔒 LocalizaVotos - Acesso Administrativo</h1>
                <p style='font-size: 18px; margin-top: 20px;'>Digite a senha para acessar</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_input(
            "Senha", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Senha incorreta, mostrar input + erro
        st.markdown(
            """
            <div style='text-align: center; padding: 40px;'>
                <h1>🔒 LocalizaVotos - Acesso Administrativo</h1>
                <p style='font-size: 18px; margin-top: 20px;'>Digite a senha para acessar</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_input(
            "Senha", type="password", on_change=password_entered, key="password"
        )
        st.error("⚠️ Senha incorreta")
        return False
    else:
        # Senha correta
        return True

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
    
    # Verificar senha
    if not check_password():
        st.stop()
    
    # Conteúdo da página principal (após login)
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
