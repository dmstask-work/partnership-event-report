from dash import dcc, html
import dash_bootstrap_components as dbc

from config import SECTION_STYLE
from data import df_wp_raw


def build_tab_wp():
    return dbc.Tab(
        label="📋 WP Report",
        tab_id="tab-wp",
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

            # ── Filters WP ────────────────────────────────────────────────
            dbc.Row([
                dbc.Col([
                    html.Label("Sesi / Nama Event",
                               className="fw-semibold small text-muted mb-1"),
                    dcc.Dropdown(
                        id="wp-dd-sesi",
                        options=[{"label": "✦ Semua Sesi", "value": "ALL"}] + (
                            [{"label": s, "value": s}
                             for s in sorted([
                                 x for x in df_wp_raw["Nama Event"].unique()
                                 if isinstance(x, str) and x not in ("-", "nan")
                             ])]
                            if not df_wp_raw.empty else []
                        ),
                        value="ALL", clearable=False,
                        style={"borderRadius": "8px"},
                    ),
                ], md=5),
                dbc.Col([
                    html.Label("Provinsi",
                               className="fw-semibold small text-muted mb-1"),
                    dcc.Dropdown(
                        id="wp-dd-provinsi",
                        options=[{"label": "✦ Semua Provinsi", "value": "ALL"}] + (
                            [{"label": p, "value": p}
                             for p in sorted([
                                 x for x in df_wp_raw["Provinsi"].dropna().unique()
                                 if isinstance(x, str) and x not in ("-", "nan")
                             ])]
                            if not df_wp_raw.empty else []
                        ),
                        value="ALL", clearable=False,
                        style={"borderRadius": "8px"},
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Country",
                               className="fw-semibold small text-muted mb-1"),
                    dcc.Dropdown(
                        id="wp-dd-country",
                        options=[{"label": "✦ Semua Negara", "value": "ALL"}] + (
                            [{"label": c, "value": c}
                             for c in sorted([
                                 x for x in df_wp_raw["Country"].dropna().unique()
                                 if isinstance(x, str) and x not in ("-", "nan")
                             ])]
                            if not df_wp_raw.empty else []
                        ),
                        value="ALL", clearable=False,
                        style={"borderRadius": "8px"},
                    ),
                ], md=3),
            ], className="mt-3 mb-4 p-3 g-3",
               style={"background": "#f7fafd", "borderRadius": "10px",
                      "boxShadow": "0 1px 4px rgba(0,0,0,0.05)"}),


            # ── KPI ───────────────────────────────────────────────────────
            dbc.Row(id="wp-kpi-row", className="mb-4 g-3"),

            # ── Row 1: Top Sesi + Gender ──────────────────────────────────
            dbc.Row([
                dbc.Col(
                    html.Div(dcc.Graph(id="wp-chart-sesi",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=8),
                dbc.Col(
                    html.Div(dcc.Graph(id="wp-chart-gender",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=4),
            ], className="mb-4 g-3"),

            # ── Row 2: Provinsi + Country ─────────────────────────────────
            dbc.Row([
                dbc.Col(
                    html.Div(dcc.Graph(id="wp-chart-provinsi",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=7),
                dbc.Col(
                    html.Div(dcc.Graph(id="wp-chart-country",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=5),
            ], className="mb-4 g-3"),

            # ── Row 3: District (donut) + Frekuensi Kehadiran ────────────
            dbc.Row([
                dbc.Col(
                    html.Div(dcc.Graph(id="wp-chart-district",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=5),
                dbc.Col(
                    html.Div(dcc.Graph(id="wp-chart-frekuensi",
                                      config={"displayModeBar": False}),
                             style=SECTION_STYLE), md=7),
            ], className="mb-4 g-3"),

            # ── Ringkasan per Event ────────────────────────────────────────
            dbc.Row(dbc.Col(
                html.Div([
                    html.H6("Ringkasan per Event",
                            className="fw-bold mb-3 text-secondary"),
                    html.Div(id="wp-table-summary"),
                ], style=SECTION_STYLE),
            ), className="mb-4"),

            # ── Rekap Peserta WP ──────────────────────────────────────────
            dbc.Row(dbc.Col(
                html.Div([
                    html.H6("Rekap Peserta WP",
                            className="fw-bold mb-3 text-secondary"),
                    html.Div(id="wp-table-peserta"),
                ], style=SECTION_STYLE),
            ), className="mb-4"),

            # ── Riwayat Kehadiran per Peserta ─────────────────────────────
            dbc.Row(dbc.Col(
                html.Div([
                    html.H6("Riwayat Kehadiran per Peserta",
                            className="fw-bold mb-3 text-secondary"),
                    dcc.Dropdown(
                        id="wp-dd-search-peserta",
                        options=(
                            [{"label": n, "value": n}
                             for n in sorted(df_wp_raw["Nama"].dropna().unique())]
                            if not df_wp_raw.empty else []
                        ),
                        placeholder="Cari nama peserta...",
                        clearable=True,
                        style={"borderRadius": "8px", "marginBottom": "12px"},
                    ),
                    html.Div(id="wp-table-riwayat"),
                ], style=SECTION_STYLE),
            ), className="mb-5"),

        ],
    )
