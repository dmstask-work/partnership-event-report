import dash_bootstrap_components as dbc

from .header import build_header
from .tab_hadir import build_tab_hadir
from .tab_wp import build_tab_wp


def build_layout():
    return dbc.Container([
        build_header(),
        dbc.Tabs([
            build_tab_hadir(),
            build_tab_wp(),
        ], id="main-tabs", active_tab="tab-hdr",
           style={
               "borderBottom": "2px solid #dce8f8",
               "background": "transparent",
               "paddingLeft": "4px",
           },
           className="mb-0 mt-1"),
    ], fluid=True, style={
        "fontFamily": "Segoe UI, sans-serif",
        "padding": "0 20px 5px 20px",
        "backgroundColor": "#f0f6fd",
    })
