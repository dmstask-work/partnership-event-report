import dash_bootstrap_components as dbc
from dash import dcc

from .header import build_header
from .tab_hadir import build_tab_hadir
from .tab_wp import build_tab_wp
from .tab_ingestion import build_tab_ingestion
from .tab_update import build_tab_update
from .tab_delete import build_tab_delete


def build_layout(role: str = "viewer") -> dbc.Container:
    """
    Build the main dashboard layout.

    Parameters
    ----------
    role : str
        'admin'  → all five tabs are included (Hadir, WP, Ingestion, Update, Delete).
        'viewer' → only Hadir Report and WP Report tabs are included;
                   the three CRUD tabs are completely absent from the component
                   tree so they are never sent to the browser.
    """
    # Admin-only tabs — omitted entirely for viewer accounts so the components
    # are never serialised to the browser, preventing any client-side inspection.
    admin_tabs = (
        [build_tab_ingestion(), build_tab_update(), build_tab_delete()]
        if role == "admin"
        else []
    )

    return dbc.Container([
        build_header(),
        dbc.Tabs(
            [build_tab_hadir(), build_tab_wp(), *admin_tabs],
            id="main-tabs",
            active_tab="tab-hdr",
            style={
                "borderBottom": "2px solid #dce8f8",
                "background": "transparent",
                "paddingLeft": "4px",
            },
            className="mb-0 mt-1 justify-content-center",
        ),
        # ── Global data stores ────────────────────────────────────────────────
        # data-refresh-ts: integer counter incremented by every CRUD success.
        # Triggers the two cache-loading callbacks below, which pull fresh
        # snapshots from Supabase and store them as JSON.  Report callbacks
        # read the JSON stores on every filter interaction — zero extra DB hits.
        dcc.Store(id="data-refresh-ts",   data=0,    storage_type="memory"),
        dcc.Store(id="hadir-data-cache",  storage_type="memory"),
        dcc.Store(id="wp-data-cache",     storage_type="memory"),
    ], fluid=True, style={
        "fontFamily": "Segoe UI, sans-serif",
        "padding": "0 20px 5px 20px",
        "backgroundColor": "#f0f6fd",
    })
