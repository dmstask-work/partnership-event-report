from dash import dcc, html
import dash_bootstrap_components as dbc
from config import FREQ_ORDER, WILAYAH_ORDER, SECTION_STYLE
from data import df_raw


def build_tab_hadir():
    return dbc.Tab(
        label="📋 Hadir Report",
        tab_id="tab-hdr",
        label_style={
            "fontWeight": "600",
            "fontSize": "14px",
            "color": "#8a9bb5",
            "padding": "10px 24px",
            "letterSpacing": "0.01em",
        },
        active_label_style={
            "color": "#2d7dd6",
            "fontWeight": "700",
            "background": "white",
            "borderRadius": "10px 10px 0 0",
            "borderTop": "3px solid #2d7dd6",
        },
        children=[

            # ── Filters ──────────────────────────────────────────────────
            dbc.Row([
                dbc.Col([
                    html.Label("Kategori",
                               className="fw-semibold small text-muted mb-1"),
                    dcc.Dropdown(
                        id="dd-kategori",
                        options=[{"label": "✦ Semua Kategori", "value": "ALL"}] + [
                            {"label": k, "value": k}
                            for k in sorted(df_raw["Kategori"].dropna().unique())
                        ],
                        value="ALL", clearable=False,
                        style={"borderRadius": "8px"},
                    ),
                ], md=3),
                dbc.Col([
                    html.Label("Nama Event",
                               className="fw-semibold small text-muted mb-1"),
                    dcc.Dropdown(
                        id="dd-event",
                        options=[{"label": "✦ Semua Event", "value": "ALL"}] + [
                            {"label": e, "value": e}
                            for e in sorted(df_raw["Event Label"].dropna().unique())
                        ],
                        value="ALL", clearable=False,
                        style={"borderRadius": "8px"},
                    ),
                ], md=5),
                dbc.Col([
                    html.Label("Wilayah",
                               className="fw-semibold small text-muted mb-1"),
                    dcc.Dropdown(
                        id="dd-wilayah",
                        options=[{"label": "✦ Semua Wilayah", "value": "ALL"}] + [
                            {"label": w, "value": w} for w in WILAYAH_ORDER
                        ],
                        value="ALL", clearable=False,
                        style={"borderRadius": "8px"},
                    ),
                ], md=2),
                dbc.Col([
                    html.Label("Frekuensi Kehadiran",
                               className="fw-semibold small text-muted mb-1"),
                    dcc.Dropdown(
                        id="dd-frekuensi",
                        options=[{"label": "✦ Semua", "value": "ALL"}] + [
                            {"label": f, "value": f} for f in FREQ_ORDER
                        ],
                        value="ALL", clearable=False,
                        style={"borderRadius": "8px"},
                    ),
                ], md=2),
            ], className="mt-3 mb-4 p-3 g-3",
               style={"background": "#f7fafd", "borderRadius": "10px",
                      "boxShadow": "0 1px 4px rgba(0,0,0,0.05)"}),


            # ── KPI Cards ────────────────────────────────────────────────
            dbc.Row(id="kpi-row", className="mb-4 g-3"),

            # ── Row 1: Location + Gender ──────────────────────────────────
            dbc.Row([
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-location",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=8),
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-gender",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=4),
            ], className="mb-4 g-3"),

            # ── Row 1.5: Kota ────────────────────────────────────────────
            dbc.Row([
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-kota",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=12),
            ], className="mb-4 g-3"),

            # ── Row 1.7: Wilayah + Frekuensi Kehadiran ───────────────────
            dbc.Row([
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-wilayah",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=5),
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-frekuensi",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=7),
            ], className="mb-4 g-3"),

            # ── Row 2: Age + Profession ───────────────────────────────────
            dbc.Row([
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-age",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=6),
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-profesi",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=6),
            ], className="mb-4 g-3"),

            # ── Row 3: Harapan + Keluhan ──────────────────────────────────
            dbc.Row([
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-harapan",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=6),
                dbc.Col(
                    html.Div(dcc.Graph(id="chart-keluhan",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=6),
            ], className="mb-4 g-3"),

            # ── Table per event ───────────────────────────────────────────
            dbc.Row(dbc.Col(
                html.Div([
                    html.H6("Ringkasan per Event",
                            className="fw-bold mb-3 text-secondary"),
                    html.Div(id="table-summary"),
                ], style=SECTION_STYLE),
            ), className="mb-4"),

            # ── Rekap Kehadiran Peserta ───────────────────────────────────
            dbc.Row(dbc.Col(
                html.Div([
                    html.H6("Rekap Kehadiran Peserta",
                            className="fw-bold mb-3 text-secondary"),
                    html.Div(id="table-peserta"),
                ], style=SECTION_STYLE),
            ), className="mb-4"),

            # ── Riwayat Kehadiran per Peserta ─────────────────────────────
            dbc.Row(dbc.Col(
                html.Div([
                    html.H6("Riwayat Kehadiran per Peserta",
                            className="fw-bold mb-3 text-secondary"),
                    dcc.Dropdown(
                        id="dd-search-peserta",
                        options=[{"label": n, "value": n}
                                 for n in sorted(df_raw["Nama"].dropna().unique())],
                        placeholder="Cari nama peserta...",
                        clearable=True,
                        style={"borderRadius": "8px", "marginBottom": "12px"},
                    ),
                    html.Div(id="table-riwayat"),
                ], style=SECTION_STYLE),
            ), className="mb-5"),

        ],
    )
