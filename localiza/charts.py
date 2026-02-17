from __future__ import annotations

import altair as alt
import pandas as pd

def chart_top_municipios(df: pd.DataFrame, top_n: int = 15):
    """Gráfico dos top municípios com mais votos"""
    col = "Município" if "Município" in df.columns else "municipio"
    by_mun = (
        df.groupby(col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    by_mun = by_mun[by_mun[col].astype(str).str.strip() != ""].head(top_n)
    if by_mun.empty:
        return None
    return (
        alt.Chart(by_mun)
        .mark_bar(color="#2ecc71")
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{col}:N", sort="-x", title="Município"),
            tooltip=[alt.Tooltip(f"{col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=400)
    )

def chart_bottom_municipios(df: pd.DataFrame, bottom_n: int = 15):
    """Gráfico dos municípios com menos votos"""
    col = "Município" if "Município" in df.columns else "municipio"
    by_mun = (
        df.groupby(col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    by_mun = by_mun[by_mun[col].astype(str).str.strip() != ""].head(bottom_n)
    if by_mun.empty:
        return None
    return (
        alt.Chart(by_mun)
        .mark_bar(color="#e74c3c")
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{col}:N", sort="x", title="Município"),
            tooltip=[alt.Tooltip(f"{col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=400)
    )

def chart_top_locais(df: pd.DataFrame, top_n: int = 15):
    # Detectar coluna de local
    local_col = "NM_LOCAL_VOTACAO" if "NM_LOCAL_VOTACAO" in df.columns else "local_votacao"
    
    by_local = (
        df.groupby(local_col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    by_local = by_local[by_local[local_col].astype(str).str.strip() != ""].head(top_n)
    if by_local.empty:
        return None
    return (
        alt.Chart(by_local)
        .mark_bar(color="#2ecc71")
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{local_col}:N", sort="-x", title="Local de votação"),
            tooltip=[alt.Tooltip(f"{local_col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=400)
    )

def chart_bottom_locais(df: pd.DataFrame, bottom_n: int = 15):
    # Detectar coluna de local
    local_col = "NM_LOCAL_VOTACAO" if "NM_LOCAL_VOTACAO" in df.columns else "local_votacao"
    
    by_local = (
        df.groupby(local_col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    by_local = by_local[by_local[local_col].astype(str).str.strip() != ""].head(bottom_n)
    if by_local.empty:
        return None
    return (
        alt.Chart(by_local)
        .mark_bar(color="#e74c3c")
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{local_col}:N", sort="x", title="Local de votação"),
            tooltip=[alt.Tooltip(f"{local_col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=400)
    )

def chart_top_bairros(df: pd.DataFrame, top_n: int = 13):
    col = "Bairro/Distrito" if "Bairro/Distrito" in df.columns else "bairro"
    by_b = (
        df.groupby(col, dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    by_b = by_b[by_b[col].astype(str).str.strip() != ""].head(top_n)
    if by_b.empty:
        return None
    return (
        alt.Chart(by_b)
        .mark_bar()
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y(f"{col}:N", sort="-x", title=col),
            tooltip=[alt.Tooltip(f"{col}:N"), alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=340)
    )

def chart_hist_votos(df: pd.DataFrame):
    # se existir coluna 'secao' ou 'zona' no futuro, dá pra trocar.
    if "qt_votos" not in df.columns:
        return None
    # distribuição simples por faixas
    bins = [0, 10, 30, 60, 100, 200, 500, 1000, 999999]
    labels = ["0-10", "11-30", "31-60", "61-100", "101-200", "201-500", "501-1000", "1000+"]
    s = pd.cut(df["qt_votos"].fillna(0), bins=bins, labels=labels, include_lowest=True)
    h = s.value_counts().reindex(labels).reset_index()
    h.columns = ["faixa", "pontos"]
    return (
        alt.Chart(h)
        .mark_bar()
        .encode(
            x=alt.X("faixa:N", sort=labels, title="Faixa de votos por ponto"),
            y=alt.Y("pontos:Q", title="Quantidade de pontos"),
            tooltip=["faixa:N", "pontos:Q"],
        )
        .properties(height=240)
    )
