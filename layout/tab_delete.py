"""
layout/tab_delete.py
====================
UI layout for the "Delete Data" tab.

User flow:
  ① Pick target table and enter a search keyword
  ② Tick the checkbox on any rows to be removed
  ③ Click 🗑️ Delete Selected → rows are permanently deleted from DB
"""

from dash import html, dash_table
import dash_bootstrap_components as dbc

# ── Card header helper (mirrors tab_ingestion.py) ─────────────────────────────
_CARD_HEADER_STYLE = {
    "background": "#f8fbff",
    "borderBottom": "1px solid #dce8f8",
}


def _step_header(label: str):
    return dbc.CardHeader(
        html.Span(label, className="fw-semibold"),
        style=_CARD_HEADER_STYLE,
    )


# ── Tab label styles (matches other tabs) ─────────────────────────────────────
_LABEL_STYLE = {
    "fontWeight": "600",
    "fontSize": "14px",
    "color": "#8a9bb5",
    "padding": "10px 24px",
    "letterSpacing": "0.01em",
}
_ACTIVE_LABEL_STYLE = {
    "color": "#dc3545",
    "fontWeight": "700",
    "background": "white",
    "borderRadius": "10px 10px 0 0",
    "borderTop": "3px solid #dc3545",
}

# ── DataTable style constants ──────────────────────────────────────────────────
_STYLE_TABLE = {
    "overflowX": "auto",
    "borderRadius": "8px",
    "boxShadow": "0 1px 4px rgba(0,0,0,0.06)",
    "minWidth": "100%",
}
_STYLE_HEADER = {
    "backgroundColor": "#FADDD5",
    "fontWeight": "bold",
    "border": "none",
    "padding": "10px 14px",
    "fontSize": "13px",
    "whiteSpace": "normal",
}
_STYLE_CELL = {
    "padding": "9px 14px",
    "fontFamily": "Segoe UI, sans-serif",
    "fontSize": "13px",
    "border": "1px solid #eef2f7",
    "textAlign": "left",
    "minWidth": "120px",
    "maxWidth": "280px",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
}


def build_tab_delete():
    return dbc.Tab(
        label="Delete Data",
        tab_id="tab-delete",
        label_style=_LABEL_STYLE,
        active_label_style=_ACTIVE_LABEL_STYLE,
        children=[
            dbc.Row(
                dbc.Col([

                    # ── ① Pilih & Cari Data ─────────────────────────────────────
                    dbc.Card([
                        _step_header("1. Pilih & Cari Data"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Target Tabel",
                                               className="fw-semibold small text-muted mb-2"),
                                    dbc.RadioItems(
                                        id="delete-target-table",
                                        options=[
                                            {"label": "  Hadir Data", "value": "hadir_data"},
                                            {"label": "  WP Data",    "value": "wp_data"},
                                        ],
                                        value="hadir_data",
                                        inline=True,
                                    ),
                                ], md=3, className="d-flex flex-column justify-content-center"),

                                dbc.Col([
                                    html.Label(
                                        "Cari berdasarkan Nama / Email / Nama Event",
                                        className="fw-semibold small text-muted mb-1",
                                    ),
                                    dbc.InputGroup([
                                        dbc.Input(
                                            id="delete-search-field",
                                            placeholder="...",
                                            type="text",
                                            style={"borderRadius": "8px 0 0 8px"},
                                        ),
                                        dbc.Button(
                                            " Cari",
                                            id="delete-search-btn",
                                            color="primary",
                                            style={"borderRadius": "0 8px 8px 0"},
                                        ),
                                    ]),
                                ], md=7),

                                dbc.Col(
                                    html.Div(
                                        id="delete-row-count",
                                        className="text-muted small mt-4 text-end fw-semibold",
                                    ),
                                    md=2,
                                ),
                            ], className="g-3"),
                        ]),
                    ], className="mb-3 shadow-sm"),

                    # ── Alert ──────────────────────────────────────────────────
                    html.Div(id="delete-alert", className="mb-3"),

                    # ── ② Preview & Seleksi Data ────────────────────────────────
                    dbc.Card([
                        _step_header("2. Preview & Seleksi Data"),
                        dbc.CardBody([
                            html.P(
                                "⚠️ Centang baris yang ingin dihapus, "
                                "lalu tekan 'Delete Selected'. "
                                "Data yang sudah terhapus tidak dapat dibatalkan.",
                                className="small mb-3",
                                style={"color": "#dc3545"},
                            ),
                            dash_table.DataTable(
                                id="delete-data-table",
                                columns=[],
                                data=[],
                                # Dash DataTable uses the 'id' key in each data
                                # record automatically as the row identifier for
                                # selected_row_ids.
                                row_selectable="multi",
                                selected_rows=[],
                                sort_action="native",
                                filter_action="native",
                                page_size=15,
                                page_action="native",
                                style_table=_STYLE_TABLE,
                                style_header=_STYLE_HEADER,
                                style_cell=_STYLE_CELL,
                                style_data_conditional=[
                                    {"if": {"row_index": "odd"},
                                     "backgroundColor": "#f5faff"},
                                    {"if": {"state": "selected"},
                                     "backgroundColor": "#ffe8e8",
                                     "border": "1px solid #dc3545"},
                                ],
                            ),
                        ]),
                    ], className="mb-0 shadow-sm"),

                    # ── Delete button ──────────────────────────────────────────
                    html.Div(
                        dbc.Button(
                            [html.Span("", className="me-2"), "Delete Selected"],
                            id="delete-btn",
                            color="danger",
                            size="md",
                            style={"borderRadius": "8px", "minWidth": "180px"},
                        ),
                        className="d-flex justify-content-center mt-4 mb-5",
                    ),

                ], md=11, lg=10, xl=10, className="mx-auto"),
                className="mt-3",
            ),
        ],
    )
