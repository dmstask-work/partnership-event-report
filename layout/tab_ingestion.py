"""
layout/tab_ingestion.py
=======================
UI layout for the "Data Ingestion" tab.

User flow:
  ① Select data type (Hadir / WP)
  ② Upload raw Excel / CSV file
  ③ Preview + inline-edit the ETL-transformed result in an editable DataTable
  ④ Click "Confirm & Sync to Supabase" to push rows to PostgreSQL
"""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

from config import SECTION_STYLE

# ── Shared tab label styles (matches tab_hadir / tab_wp) ──────────────────────
_LABEL_STYLE = {
    "fontWeight": "600",
    "fontSize": "14px",
    "color": "#8a9bb5",
    "padding": "10px 24px",
    "letterSpacing": "0.01em",
}
_ACTIVE_LABEL_STYLE = {
    "color": "#2d7dd6",
    "fontWeight": "700",
    "background": "white",
    "borderRadius": "10px 10px 0 0",
    "borderTop": "3px solid #2d7dd6",
}

# ── Card header helper ─────────────────────────────────────────────────────────
_CARD_HEADER_STYLE = {
    "background": "#f8fbff",
    "borderBottom": "1px solid #dce8f8",
}


def _step_header(label: str, right_slot=None):
    """Two-column card header: step label on the left, optional slot on the right."""
    cols = [dbc.Col(html.Span(label, className="fw-semibold"), className="d-flex align-items-center")]
    if right_slot is not None:
        cols.append(dbc.Col(right_slot, className="text-end"))
    return dbc.CardHeader(dbc.Row(cols, align="center"), style=_CARD_HEADER_STYLE)


# ══════════════════════════════════════════════════════════════════════════════
def build_tab_ingestion():
    return dbc.Tab(
        label="Add Data",
        tab_id="tab-ingestion",
        label_style=_LABEL_STYLE,
        active_label_style=_ACTIVE_LABEL_STYLE,
        children=[
            dbc.Row(
                dbc.Col([

                    # ── ① Select data type ─────────────────────────────────────────
                    dbc.Card([
                        _step_header("1. Pilih Jenis Data"),
                        dbc.CardBody([
                            dbc.RadioItems(
                                id="ingestion-data-type",
                                options=[
                                    {
                                        "label": html.Span(
                                            ["", html.Strong("Data Hadir"), "  (tabel harmoni diri)"],
                                        ),
                                        "value": "hadir",
                                    },
                                    {
                                        "label": html.Span(
                                            ["", html.Strong("Data WP"), "  (tabel workshop profesional)"],
                                        ),
                                        "value": "wp",
                                    },
                                ],
                                value="hadir",
                                inline=True,
                                className="mt-1",
                                inputClassName="me-1",
                                labelClassName="me-5 small",
                            ),
                        ]),
                    ], style=SECTION_STYLE, className="mb-3"),

                    # ── ② Upload ───────────────────────────────────────────────────
                    dbc.Card([
                        _step_header("2. Upload File  (.xlsx / .xls / .csv)"),
                        dbc.CardBody([
                            dcc.Upload(
                                id="ingestion-upload",
                                children=html.Div([
                                    html.Div(
                                        "☁",
                                        style={
                                            "fontSize": "2.4rem",
                                            "color": "#ADD3FA",
                                            "lineHeight": "1",
                                            "marginBottom": "6px",
                                        },
                                    ),
                                    html.Span("Drag & Drop  atau  "),
                                    html.A(
                                        "Klik untuk pilih file",
                                        style={
                                            "color": "#2d7dd6",
                                            "textDecoration": "underline",
                                            "cursor": "pointer",
                                        },
                                    ),
                                    html.Br(),
                                    html.Small(
                                        "Format yang didukung: .xlsx, .xls, .csv",
                                        className="text-muted",
                                    ),
                                ], className="text-center py-3"),
                                style={
                                    "width": "100%",
                                    "border": "2px dashed #ADD3FA",
                                    "borderRadius": "10px",
                                    "textAlign": "center",
                                    "cursor": "pointer",
                                    "background": "#f8fbff",
                                },
                                multiple=False,
                                accept=".xlsx,.xls,.csv",
                            ),
                            # Shows filename + row count after successful parse
                            html.Div(
                                id="ingestion-filename-display",
                                className="text-muted small mt-2 text-center",
                            ),
                        ]),
                    ], style=SECTION_STYLE, className="mb-3"),

                    # ── ③ Preview & edit ───────────────────────────────────────────
                    dbc.Card([
                        _step_header(
                            "3. Preview & Koreksi Data",
                            right_slot=html.Div(
                                id="ingestion-row-count",
                                className="text-muted small",
                            ),
                        ),
                        dbc.CardBody([
                            # Placeholder shown before any file is uploaded
                            html.Div(
                                id="ingestion-table-placeholder",
                                children=html.P(
                                    "Upload file terlebih dahulu untuk melihat preview data.",
                                    className="text-muted text-center py-4 mb-0",
                                ),
                            ),
                            # Editable DataTable — hidden until ETL result is ready
                            html.Div(
                                id="ingestion-table-wrapper",
                                style={"display": "none"},
                                children=[
                                    dbc.Alert(
                                        [
                                            html.Strong("Tip: "),
                                            "Klik sel mana saja untuk mengedit nilai langsung di tabel "
                                            "sebelum melakukan sync. Kolom berwarna merah menandakan "
                                            "nilai kosong yang perlu diisi.",
                                        ],
                                        color="info",
                                        className="py-2 small mb-2",
                                        dismissable=True,
                                    ),
                                    dash_table.DataTable(
                                        id="ingestion-preview-table",
                                        editable=True,
                                        row_deletable=True,
                                        # ── Use "native" only for sort; avoid filter_action="native"
                                        # on editable tables — native filtering triggers a full
                                        # data re-render that resets the active cell / cursor.
                                        # Users can scroll / page instead.
                                        filter_action="none",
                                        sort_action="native",
                                        page_action="native",
                                        page_size=20,
                                        # ── IMPORTANT: cell_selectable=True (default) is fine;
                                        # the key fix for cursor-jump is whiteSpace="nowrap" below.
                                        style_table={
                                            "overflowX": "auto",
                                            "minWidth": "100%",
                                        },
                                        style_header={
                                            "backgroundColor": "#EBF4FF",
                                            "fontWeight": "700",
                                            "fontSize": "12px",
                                            "color": "#2d5fa8",
                                            "border": "1px solid #dce8f8",
                                            "padding": "8px 10px",
                                            "whiteSpace": "nowrap",
                                        },
                                        style_cell={
                                            "fontSize": "12px",
                                            "padding": "6px 10px",
                                            "border": "1px solid #e8eff8",
                                            "fontFamily": "Segoe UI, sans-serif",
                                            "minWidth": "110px",
                                            "maxWidth": "260px",
                                            # FIX: "nowrap" prevents DOM reflow while typing,
                                            # which is what causes the cursor to jump to the end.
                                            # Do NOT use whiteSpace="normal" on editable tables.
                                            "whiteSpace": "nowrap",
                                            "overflow": "hidden",
                                            "textOverflow": "ellipsis",
                                        },
                                        style_data_conditional=[
                                            {
                                                "if": {"row_index": "odd"},
                                                "backgroundColor": "#f8fbff",
                                            },
                                            # Highlight empty/default-filled cells (value is "-")
                                            # so users know which cells need review.
                                            {
                                                "if": {"filter_query": '{gender} = "-" || {gender} is blank'},
                                                "backgroundColor": "#fff3cd",
                                                "color": "#856404",
                                            },
                                            {
                                                "if": {"filter_query": '{no_whatsapp} = "-" || {no_whatsapp} is blank'},
                                                "backgroundColor": "#fde8e8",
                                                "color": "#842029",
                                            },
                                        ],
                                        style_as_list_view=True,
                                        # Populated dynamically by callback
                                        data=[],
                                        columns=[],
                                    ),
                                ],
                            ),
                        ]),
                    ], style=SECTION_STYLE, className="mb-3"),

                    # ── ④ Sync button ──────────────────────────────────────────────
                    dbc.Row(
                        dbc.Col(
                            dbc.Button(
                                [
                                    html.Span("", style={"marginRight": "8px"}),
                                    "Confirm & Sync to Database",
                                ],
                                id="ingestion-sync-btn",
                                color="primary",
                                size="lg",
                                disabled=True,          # enabled only after successful preview
                                n_clicks=0,
                                className="fw-semibold px-5",
                                style={"borderRadius": "8px"},
                            ),
                            # Centered using Bootstrap flex utilities
                            className="d-flex justify-content-center",
                        ),
                        className="mb-3",
                    ),

                    # ── Notification area (success / error alerts) ─────────────────
                    html.Div(id="ingestion-alert-container"),

                    # Spacer at the bottom of the page
                    html.Div(style={"height": "40px"}),

                ], md=12),
                className="mt-3",
            ),
        ],
    )
