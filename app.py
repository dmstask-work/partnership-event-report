from dash_instance import app, server  # noqa: F401 — server exposed for WSGI deployment
from layout import build_layout
import callbacks  # noqa: F401 - importing registers all callbacks via decorators

app.layout = build_layout()

if __name__ == "__main__":
    app.run(debug=True)
