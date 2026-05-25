"""
app.py
======
Application entry point.

app.layout is set to a *function* (serve_layout) instead of a static
component tree.  Dash calls this function on every initial HTTP GET request,
which allows it to inspect the Flask session and return either:
  • the login page  (session is empty / user is not authenticated)
  • the dashboard   (session contains a valid username)
The dashboard layout is further filtered by role so admin-only tabs are
never sent to the browser for viewer accounts.
"""

from dash_instance import app, server  # noqa: F401 — server exposed for WSGI deployment
from layout import build_layout
from layout.login import build_login_layout
import callbacks  # noqa: F401 — importing registers all callbacks via decorators


def serve_layout():
    """
    Dynamic layout factory called by Dash on every page request.

    Checks the Flask session (set by callbacks/auth_callbacks.py) and
    returns the appropriate component tree.
    """
    import auth  # local import avoids circular-import issues at module load

    username = auth.get_current_username()
    if not username:
        return build_login_layout()

    role = auth.get_current_user_role()
    return build_layout(role=role)


# Assign the factory function — Dash detects that it is callable and invokes
# it on every request rather than using a static snapshot.
app.layout = serve_layout

if __name__ == "__main__":
    app.run(debug=False)
