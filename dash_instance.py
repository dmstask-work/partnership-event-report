from dash import Dash
import dash_bootstrap_components as dbc

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Partnership & Event Report",
)

# Expose the underlying Flask server for production WSGI deployment (e.g. gunicorn)
server = app.server
