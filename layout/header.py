from dash import html
import dash_bootstrap_components as dbc


def build_header():
    return dbc.Row(
        dbc.Col(
            html.Div([
                html.H3("📊 Dashboard Report Partnership & Event",
                        className="mb-0 fw-bold"),
                html.P("Summary data partnership & event",
                       className="mb-0 text-black-50 small"),
            ], className="py-3 px-4"),
        ),
        style={
            "background": "linear-gradient(135deg, #ADD3FA 0%, #B9EBFA 100%)",
            "borderRadius": "0 0 16px 16px",
            "marginBottom": "1.5rem",
        },
    )
