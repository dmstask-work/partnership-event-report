"""
callbacks/auth_callbacks.py
===========================
Login and logout callbacks.

Login flow
----------
1. User fills in the form on layout/login.py and clicks "Login" (or presses
   Enter in either input field via n_submit).
2. handle_login() validates credentials via auth.authenticate_user().
3. On success → auth.login() writes the username to the Flask session and
   the callback sets href on dcc.Location(id="login-redirect", refresh=True),
   which triggers a full browser reload.
4. app.layout (a function in app.py) re-runs, sees the session, and returns
   the role-filtered dashboard layout instead of the login form.

Logout flow
-----------
1. User clicks "Logout" in the header (layout/header.py).
2. handle_logout() calls auth.logout(), which calls session.clear().
3. The callback sets href on dcc.Location(id="logout-location", refresh=True),
   triggering a full browser reload.
4. app.layout re-runs, sees no session, and returns the login form.
"""

from __future__ import annotations

from dash import Input, Output, State, callback, clientside_callback, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

import auth


# ── Password visibility toggle (client-side — zero network round-trip) ────────

clientside_callback(
    """
    function(n_clicks, current_type) {
        // Suppress on initial load
        if (!n_clicks) return [window.dash_clientside.no_update,
                               window.dash_clientside.no_update];
        var reveal = current_type === 'password';
        return [
            reveal ? 'text'     : 'password',
            reveal ? 'Hide'     : 'Show'
        ];
    }
    """,
    Output("login-password",        "type"),
    Output("login-password-toggle", "children"),
    Input("login-password-toggle",  "n_clicks"),
    State("login-password",         "type"),
    prevent_initial_call=True,
)


# ── Login callback ────────────────────────────────────────────────────────────

@callback(
    Output("login-redirect", "href"),
    Output("login-error",    "children"),
    Input("login-btn",       "n_clicks"),
    Input("login-username",  "n_submit"),
    Input("login-password",  "n_submit"),
    State("login-username",  "value"),
    State("login-password",  "value"),
    prevent_initial_call=True,
)
def handle_login(
    n_clicks:      int,
    n_submit_user: int,
    n_submit_pass: int,
    username:      str | None,
    password:      str | None,
):
    """
    Validate credentials and, on success, write the username to the
    Flask session before redirecting to the dashboard.
    """
    # Guard: only fire when the user actually triggered a submit action
    if not any([n_clicks, n_submit_user, n_submit_pass]):
        raise PreventUpdate

    if not username or not password:
        return no_update, dbc.Alert(
            "Username dan password wajib diisi.",
            color="warning",
            dismissable=True,
            className="py-2 mb-0",
        )

    if auth.authenticate_user(username.strip(), password):
        auth.login(username.strip())
        # "/" triggers app.layout to re-run with the new session
        return "/", no_update

    return no_update, dbc.Alert(
        "Username atau password salah. Silakan coba lagi.",
        color="danger",
        dismissable=True,
        className="py-2 mb-0",
    )


# ── Logout callback ───────────────────────────────────────────────────────────

@callback(
    Output("logout-location", "href"),
    Input("logout-btn",       "n_clicks"),
    prevent_initial_call=True,
)
def handle_logout(n_clicks: int):
    """
    Clear the Flask session and redirect to the login page.

    The dcc.Location component (id="logout-location", refresh=True) lives in
    layout/header.py so it is always present in the dashboard layout tree.
    """
    if not n_clicks:
        raise PreventUpdate

    auth.logout()
    # Return "/" — app.layout will re-run and serve the login form
    return "/"
