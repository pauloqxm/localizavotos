from __future__ import annotations

import altair as alt
import pandas as pd

def chart_top_locais(df: pd.DataFrame, top_n: int = 13):
    by_local = (
        df.groupby("local_votacao", dropna=False)["qt_votos"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    by_local = by_local[by_local["local_votacao"].astype(str).str.strip() != ""].head(top_n)
    if by_local.empty:
        return None
    return (
        alt.Chart(by_local)
        .mark_bar()
        .encode(
            x=alt.X("qt_votos:Q", title="Votos"),
            y=alt.Y("local_votacao:N", sort="-x", title="Local de votação"),
            tooltip=["local_votacao:N", alt.Tooltip("qt_votos:Q", format=",.0f")],
        )
        .properties(height=340)
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
