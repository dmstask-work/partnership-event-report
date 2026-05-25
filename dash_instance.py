import os

from dash import Dash
import dash_bootstrap_components as dbc

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Partnership & Event Report",
    # Required when app.layout is a callable that returns different component
    # trees (login page vs. dashboard) so Dash doesn't raise errors for
    # callbacks referencing components not in the currently visible layout.
    suppress_callback_exceptions=True,
)

# Expose the underlying Flask server for production WSGI deployment (e.g. gunicorn)
server = app.server

# Flask secret key — mandatory for session cookie encryption.
# Set the SECRET_KEY environment variable in production; the fallback is for
# local development ONLY and must NOT be used in a deployed environment.
server.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-CHANGE-before-deploy")
