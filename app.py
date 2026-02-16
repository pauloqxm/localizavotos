from __future__ import annotations

from pathlib import Path
import streamlit as st

from localiza.ui import hide_sidebar, discover_candidates, pick_candidate, load_candidate_module

def main():
    hide_sidebar()

    # guarda o path da pasta data (comuns) no session_state pra UI usar sem acoplamento
    st.session_state["COMMON_DATA_DIR"] = str(Path(__file__).resolve().parent / "data")

    candidates = discover_candidates()
    chosen_py = pick_candidate(candidates)
    if chosen_py is None:
        return

    mod = load_candidate_module(chosen_py)

    # contrato simples: o módulo do candidato expõe render()
    if hasattr(mod, "render") and callable(mod.render):
        mod.render()
        return

    st.error(f"O arquivo {chosen_py.name} não tem função render().")

if __name__ == "__main__":
    main()
