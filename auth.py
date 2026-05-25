"""
auth.py
=======
Database-backed Authentication and Role-Based Access Control (RBAC).

Credentials are stored in the `dashboard_users` table on Supabase (PostgreSQL).
Passwords are NEVER stored in plain text — only Werkzeug-hashed values are
written to the database via `manage_users.py`.

Session caching
---------------
At login time, both `username` and `role` are written to the Flask session.
Subsequent calls to `get_current_user_role()` read from the session cookie
(zero DB round-trips), keeping the dashboard fully responsive.

Public API
----------
  authenticate_user(username, password)  -> bool
  login(username)                        -> None  (writes session + role)
  logout()                               -> None  (clears session)
  get_current_username()                 -> str | None
  get_current_user_role()                -> str | None

Usage in callbacks:
    from auth import get_current_user_role
    if get_current_user_role() != "admin":
        raise PreventUpdate   # silently reject unauthorised requests
"""

from __future__ import annotations

import logging

from flask import session
from sqlalchemy import text
from werkzeug.security import check_password_hash

from data import _get_engine

logger = logging.getLogger(__name__)

# ── Constant-time dummy hash ──────────────────────────────────────────────────
# Used when a username is not found so the code still executes a hash
# comparison, preventing timing-based username enumeration.
_DUMMY_HASH = (
    "pbkdf2:sha256:600000$aaaaaaaaaaaaaaaa$"
    + "a" * 64
)


# ── Public API ────────────────────────────────────────────────────────────────

def authenticate_user(username: str, password: str) -> bool:
    """
    Query `dashboard_users` for *username* and verify *password* against the
    stored Werkzeug hash.

    Returns True on success, False for invalid credentials or any DB error.
    Hash comparison is always performed (constant-time path) to prevent
    timing-based username enumeration.
    """
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT password_hash FROM dashboard_users "
                    "WHERE username = :u"
                ),
                {"u": username},
            ).fetchone()
    except Exception as exc:
        logger.error("auth: DB error during authenticate_user: %s", exc)
        # Execute a dummy check to maintain a constant-time code path
        check_password_hash(_DUMMY_HASH, password)
        return False

    if row is None:
        # Username not found — still run a hash check to equalise timing
        check_password_hash(_DUMMY_HASH, password)
        return False

    return check_password_hash(row[0], password)


def _fetch_role(username: str) -> str | None:
    """
    Fetch the role for *username* from `dashboard_users`.
    Called exactly once at login; result is cached in the Flask session.
    """
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT role FROM dashboard_users WHERE username = :u"),
                {"u": username},
            ).fetchone()
        return row[0] if row else None
    except Exception as exc:
        logger.error("auth: DB error during _fetch_role: %s", exc)
        return None


def login(username: str) -> None:
    """
    Write the authenticated username *and* their role to the Flask session.

    The role is fetched from the DB exactly once here and cached so that
    `get_current_user_role()` never needs a DB hit during the session.

    Call this **only** after :func:`authenticate_user` returns True.
    """
    role = _fetch_role(username)
    session["username"] = username
    session["role"]     = role
    session.modified    = True


def logout() -> None:
    """
    Invalidate the current Flask session completely.

    After this call `get_current_username()` returns None and the next
    page load will serve the login form.
    """
    session.clear()


def get_current_username() -> str | None:
    """
    Return the logged-in username, or None when unauthenticated or when
    called outside a Flask request context (e.g. during unit-testing).
    """
    try:
        return session.get("username")
    except RuntimeError:
        return None


def get_current_user_role() -> str | None:
    """
    Return the cached role of the currently logged-in user.

    The role is written to the session by :func:`login` at authentication
    time, so this function never performs a DB query.

    Return values:
      'admin'  - full access (all tabs + CRUD operations)
      'viewer' - read-only  (Hadir Report + WP Report only)
      None     - not authenticated / outside request context
    """
    try:
        return session.get("role")
    except RuntimeError:
        return None
