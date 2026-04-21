import dash_bootstrap_components as dbc
from dash import html
from config import CARD_STYLE
from data import df_raw, df_wp_raw


def parse_topics(text, known):
    """Greedy match against known topic labels (handles commas inside labels)."""
    if not isinstance(text, str) or not text.strip():
        return []
    remaining = text.strip()
    found = []
    while remaining:
        matched = False
        for t in known:
            if remaining.startswith(t):
                found.append(t)
                remaining = remaining[len(t):].lstrip(", ")
                matched = True
                break
        if not matched:
            idx = remaining.find(", ")
            if idx == -1:
                found.append(remaining.strip())
                break
            found.append(remaining[:idx].strip())
            remaining = remaining[idx + 2:]
    return found


def filter_df(kategori, event, wilayah="ALL", frekuensi="ALL"):
    df = df_raw.copy()
    if kategori != "ALL":
        df = df[df["Kategori"] == kategori]
    if event != "ALL":
        df = df[df["Event Label"] == event]
    if wilayah != "ALL":
        df = df[df["Wilayah"] == wilayah]
    if frekuensi != "ALL":
        df = df[df["Frekuensi Kehadiran"] == frekuensi]
    return df


def filter_wp(sesi, provinsi, country):
    if df_wp_raw.empty:
        return df_wp_raw
    df = df_wp_raw.copy()
    if sesi != "ALL":
        df = df[df["Nama Event"] == sesi]
    if provinsi != "ALL":
        df = df[df["Provinsi"] == provinsi]
    if country != "ALL":
        df = df[df["Country"] == country]
    return df


def kpi_card(label, value, accent):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.P(label, className="text-muted small mb-1",
                       style={"fontSize": "0.75rem", "fontWeight": "600"}),
                html.H4(value, className="fw-bold mb-0", style={"color": "#333"}),
            ]),
            style={**CARD_STYLE, "borderLeft": f"5px solid {accent}",
                   "borderTop": "none", "borderRight": "none", "borderBottom": "none"},
        ),
        md=True,
    )
