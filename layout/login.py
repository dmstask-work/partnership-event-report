"""
layout/login.py
===============
Full-page login form.

Rendered by app.layout (a function) whenever the Flask session contains no
authenticated username.  After a successful login the Dash callback in
callbacks/auth_callbacks.py writes the username to the session and uses the
dcc.Location component (refresh=True) to trigger a full browser reload,
which causes app.layout to re-run and return the dashboard instead.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc


def build_login_layout() -> dbc.Container:
    return dbc.Container(
        dbc.Row(
            dbc.Col(
                dbc.Card([
                    # ── Card header ──────────────────────────────────────────
                    dbc.CardHeader(
                        html.Div([
                            html.Span("🔐", style={"fontSize": "1.8rem"}),
                            html.H5(
                                "Dashboard Report P&E",
                                className="mb-0 fw-bold mt-1",
                            ),
                            html.P(
                                "Silahkan masukkan kredensial untuk login...",
                                className="mb-0 text-muted small",
                            ),
                        ], className="text-center py-1"),
                        style={
                            "background": "linear-gradient(135deg, #ADD3FA 0%, #B9EBFA 100%)",
                            "borderBottom": "1px solid #dce8f8",
                        },
                    ),

                    # ── Card body (form) ──────────────────────────────────────
                    dbc.CardBody([
                        dbc.Label(
                            "Username",
                            html_for="login-username",
                            className="fw-semibold text-secondary small mb-1",
                        ),
                        dbc.Input(
                            id="login-username",
                            type="text",
                            placeholder="Masukan username...",
                            className="mb-3",
                            n_submit=0,
                            autofocus=True,
                            style={"borderRadius": "8px"},
                        ),

                        dbc.Label(
                            "Password",
                            html_for="login-password",
                            className="fw-semibold text-secondary small mb-1",
                        ),
                        dbc.InputGroup([
                            dbc.Input(
                                id="login-password",
                                type="password",
                                placeholder="••••••••",
                                n_submit=0,
                            ),
                            dbc.Button(
                                "Show",
                                id="login-password-toggle",
                                color="secondary",
                                n_clicks=0,
                                style={
                                    "fontSize": "0.80rem",
                                    "letterSpacing": "0.03em",
                                    "whiteSpace": "nowrap",
                                },
                            ),
                        ], className="mb-3"),

                        # Feedback area — populated by the login callback
                        html.Div(id="login-error", className="mb-3"),

                        dbc.Button(
                            [html.Span("", className="me-2"), "Login"],
                            id="login-btn",
                            color="primary",
                            className="w-100",
                            n_clicks=0,
                            style={"borderRadius": "8px"},
                        ),

                        # dcc.Location drives the post-login full-page redirect.
                        # refresh=True forces a browser reload so app.layout
                        # (a callable) re-executes with the new session state.
                        dcc.Location(id="login-redirect", refresh=True),
                    ]),
                ],
                className="shadow",
                style={"borderRadius": "12px", "border": "none"},
                ),

                # Centre the card both horizontally and vertically
                xs=11, sm=8, md=5, lg=4, xl=3,
                className="mx-auto",
                style={"marginTop": "12vh"},
            ),
        ),
        fluid=True,
        style={
            "minHeight": "100vh",
            "backgroundColor": "#f0f6fd",
            "fontFamily": "Segoe UI, sans-serif",
        },
    )
