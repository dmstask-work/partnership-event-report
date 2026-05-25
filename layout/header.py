from dash import dcc, html
import dash_bootstrap_components as dbc

import auth


def build_header():
    """
    Top-of-page header bar.

    Title, subtitle, and user info are all stacked vertically and
    centre-aligned.  The logout button and username badge sit directly
    below the subtitle so the lockup reads as a single cohesive block.
    A dcc.Location component (id='logout-location', refresh=True) is
    embedded here to drive a full-page reload on logout.
    """
    username = auth.get_current_username() or ""

    return dbc.Row(
        dbc.Col(
            html.Div([
                # ── App title ──────────────────────────────────────────────
                html.H3(
                    "Dashboard Report Partnership & Event",
                    className="mb-0 fw-bold",
                ),
                # ── Subtitle ───────────────────────────────────────────────
                html.P(
                    "Summary data partnership & event",
                    className="mb-0 text-black-50 small",
                ),
                # ── User badge + Logout — centred below subtitle ───────────
                html.Div([
                    html.Small(
                        [html.Span("👤 "), html.Strong(username)],
                        className="text-secondary me-2",
                    ),
                    dbc.Button(
                        "Logout",
                        id="logout-btn",
                        color="primary",
                        outline=True,
                        size="sm",
                        n_clicks=0,
                        style={"borderRadius": "8px", "fontWeight": "600"},
                    ),
                    # Logout redirect target — must stay in the dashboard layout
                    dcc.Location(id="logout-location", refresh=True),
                ], className="d-flex justify-content-center align-items-center mt-2"),
            ], className="py-3 px-4 text-center"),
        ),
        style={
            "background": "linear-gradient(135deg, #ADD3FA 0%, #B9EBFA 100%)",
            "borderRadius": "0 0 16px 16px",
            "marginBottom": "1.5rem",
        },
    )
