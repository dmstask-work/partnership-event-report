"""
callbacks/data_management.py
============================
Callbacks for the Update Data and Delete Data tabs.

Security notes
--------------
• All user-supplied search keywords are passed via SQLAlchemy :parameter
  placeholders — never interpolated into the SQL string.
• Table names come from a RadioItems with fixed options; they are validated
  against _ALLOWED_TABLES whitelist before any query is executed.
• Column names used in UPDATE SET clauses come from _EDITABLE_COLS, a
  hard-coded set defined here — not from user input.
"""

from __future__ import annotations

import pandas as pd
from dash import Input, Output, State, no_update
from dash.exceptions import PreventUpdate
from sqlalchemy import text
import dash_bootstrap_components as dbc
from dash import html

from dash_instance import app
from data import _get_engine
import auth  # RBAC role checks


# ── Security: table-name whitelist ────────────────────────────────────────
_ALLOWED_TABLES: set[str] = {"hadir_data", "wp_data"}

# ── Editable columns per table (id / created_at / updated_at are immutable)
_EDITABLE_COLS: dict[str, set[str]] = {
    "hadir_data": {
        "email", "nama", "no_whatsapp", "kota_provinsi", "tempat_kegiatan",
        "tanggal", "sesi", "jumlah_sesi", "tahun", "bulan", "kategori",
        "nama_event", "lokasi_event", "gender", "kota", "provinsi",
        "usia", "kelompok_usia", "profesi_asli", "kategori_profesi",
        "harapan_asli", "topik_harapan", "keluhan_asli", "topik_keluhan",
        "wilayah", "workshop_yang_diikuti",
    },
    "wp_data": {
        "email", "nama", "no_whatsapp", "kota_provinsi", "tempat_kegiatan",
        "tanggal", "sesi", "jumlah_sesi", "tahun", "bulan", "kategori",
        "nama_event", "lokasi_event", "gender", "kota", "provinsi",
        "district", "country",
    },
}

_IMMUTABLE: set[str] = {"id", "created_at", "updated_at"}


# ── Helpers ────────────────────────────────────────────────────────────────

def _validate_table(table_name: str) -> str:
    """Raise ValueError if table_name is not in the allowed whitelist."""
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(f"Tabel tidak diizinkan: '{table_name}'")
    return table_name


def _alert(msg: str, color: str = "success") -> dbc.Alert:
    return dbc.Alert(
        msg, color=color, dismissable=True,
        duration=7000, className="mb-0",
    )


def _search_db(table_name: str, keyword: str) -> pd.DataFrame:
    """
    Case-insensitive search across nama, email, and nama_event columns.
    Returns at most 200 rows ordered by primary key.

    The table name is validated against a whitelist; the keyword is
    fully parameterized — no SQL injection is possible.
    """
    _validate_table(table_name)
    kw  = f"%{keyword.strip()}%"
    # table_name is whitelisted above; only :kw is user-supplied
    sql = text(
        f"SELECT * FROM {table_name} "          # noqa: S608 (table whitelisted)
        "WHERE nama       ILIKE :kw "
        "   OR email      ILIKE :kw "
        "   OR nama_event ILIKE :kw "
        "ORDER BY id "
        "LIMIT 200"
    )
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(sql, {"kw": kw})
        rows   = result.fetchall()
        return pd.DataFrame(rows, columns=list(result.keys()))


# ═══════════════════════════════════════════════════════════════════════════
# UPDATE TAB callbacks
# ═══════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("update-data-table",     "data"),
    Output("update-data-table",     "columns"),
    Output("update-original-store", "data"),
    Output("update-alert",          "children"),
    Output("update-row-count",      "children"),
    Input("update-search-btn",      "n_clicks"),
    State("update-search-field",    "value"),
    State("update-target-table",    "value"),
    prevent_initial_call=True,
)
def search_update(_, keyword, table_name):
    """Search the DB and populate the editable DataTable."""
    # Defence-in-depth: reject even if the tab is hidden for viewer accounts
    if auth.get_current_user_role() != "admin":
        raise PreventUpdate
    if not keyword or not keyword.strip():
        return (no_update, no_update, no_update,
                _alert("Masukkan kata kunci pencarian.", "warning"),
                no_update)

    try:
        df = _search_db(table_name, keyword)
    except Exception as exc:
        return (no_update, no_update, no_update,
                _alert(f"Kesalahan database: {exc}", "danger"),
                no_update)

    if df.empty:
        return ([], [], [],
                _alert("Tidak ada data yang cocok dengan kata kunci tersebut.", "info"),
                "0 baris ditemukan")

    # Mark immutable columns as non-editable in each column spec
    columns = [
        {"name": col, "id": col, "editable": col not in _IMMUTABLE}
        for col in df.columns
    ]
    records    = df.to_dict("records")
    count_text = f"✔ {len(records)} baris ditemukan"
    # Store original snapshot for change-detection in save_updates
    return records, columns, records, None, count_text


@app.callback(
    Output("update-alert", "children", allow_duplicate=True),
    Input("update-save-btn",       "n_clicks"),
    State("update-data-table",     "data"),
    State("update-original-store", "data"),
    State("update-target-table",   "value"),
    prevent_initial_call=True,
)
def save_updates(_, current_data, original_data, table_name):
    """
    Compare the current DataTable state with the original snapshot.
    Only rows that have actually changed are written to the database,
    using a fully parameterized UPDATE statement per row.
    """
    # Defence-in-depth: reject even if the tab is hidden for viewer accounts
    if auth.get_current_user_role() != "admin":
        raise PreventUpdate
    if not current_data:
        return _alert("Tidak ada data untuk disimpan.", "warning")

    allowed_cols = _EDITABLE_COLS.get(table_name, set())
    original_map = {row["id"]: row for row in (original_data or [])}
    engine       = _get_engine()
    updated, errors = 0, []

    for row in current_data:
        row_id = row.get("id")
        if row_id is None:
            continue

        original_row = original_map.get(row_id, {})

        # Diff: only editable columns that have actually changed
        changed = {
            col: row[col]
            for col in row
            if col in allowed_cols
            and row.get(col) != original_row.get(col)
        }
        if not changed:
            continue

        # Column names come from _EDITABLE_COLS (hard-coded), not user input
        # → f-string interpolation of column names is safe here
        set_clause = ", ".join(f'"{col}" = :{col}' for col in changed)
        params     = {**changed, "_row_id": row_id}
        sql        = text(f"UPDATE {table_name} SET {set_clause} WHERE id = :_row_id")

        try:
            with engine.begin() as conn:
                conn.execute(sql, params)
            updated += 1
        except Exception as exc:
            errors.append(f"id={row_id}: {exc}")

    if errors:
        detail = "; ".join(errors[:3]) + ("…" if len(errors) > 3 else "")
        return _alert(
            f"⚠️ {updated} baris diupdate, {len(errors)} baris gagal. {detail}",
            "warning",
        )
    if updated == 0:
        return _alert("ℹ️ Tidak ada perubahan yang terdeteksi.", "info")

    return _alert(f"✅ {updated} baris berhasil diupdate ke {table_name}.", "success")


# ═══════════════════════════════════════════════════════════════════════════
# DELETE TAB callbacks
# ═══════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("delete-data-table", "data"),
    Output("delete-data-table", "columns"),
    Output("delete-alert",      "children"),
    Output("delete-row-count",  "children"),
    Input("delete-search-btn",  "n_clicks"),
    State("delete-search-field","value"),
    State("delete-target-table","value"),
    prevent_initial_call=True,
)
def search_delete(_, keyword, table_name):
    """Search the DB and populate the selectable (read-only) DataTable."""
    # Defence-in-depth: reject even if the tab is hidden for viewer accounts
    if auth.get_current_user_role() != "admin":
        raise PreventUpdate
    if not keyword or not keyword.strip():
        return (no_update, no_update,
                _alert("Masukkan kata kunci pencarian.", "warning"),
                no_update)

    try:
        df = _search_db(table_name, keyword)
    except Exception as exc:
        return (no_update, no_update,
                _alert(f"Kesalahan database: {exc}", "danger"),
                no_update)

    if df.empty:
        return ([], [],
                _alert("Tidak ada data yang cocok dengan kata kunci tersebut.", "info"),
                "0 baris ditemukan")

    columns    = [{"name": col, "id": col} for col in df.columns]
    records    = df.to_dict("records")
    count_text = f"✔ {len(records)} baris ditemukan"
    return records, columns, None, count_text


@app.callback(
    Output("delete-data-table", "data",          allow_duplicate=True),
    Output("delete-data-table", "selected_rows", allow_duplicate=True),
    Output("delete-alert",      "children",      allow_duplicate=True),
    Input("delete-btn",                "n_clicks"),
    State("delete-data-table", "selected_row_ids"),   # actual DB id values
    State("delete-target-table",       "value"),
    prevent_initial_call=True,
)
def delete_selected(_, selected_ids, table_name):
    """
    Delete every row whose primary-key id is in selected_row_ids.

    Uses individual :id_N parameters rather than ANY() to stay compatible
    with all psycopg2 / SQLAlchemy version combinations.
    """
    # Defence-in-depth: reject even if the tab is hidden for viewer accounts
    if auth.get_current_user_role() != "admin":
        raise PreventUpdate
    if not selected_ids:
        return (no_update, no_update,
                _alert("Pilih minimal satu baris untuk dihapus.", "warning"))

    try:
        _validate_table(table_name)
        engine = _get_engine()

        # Fully parameterized — no injection possible
        placeholders = ", ".join(f":id_{i}" for i in range(len(selected_ids)))
        params       = {f"id_{i}": id_val for i, id_val in enumerate(selected_ids)}
        sql          = text(
            f"DELETE FROM {table_name} WHERE id IN ({placeholders})"
        )
        with engine.begin() as conn:
            conn.execute(sql, params)

    except Exception as exc:
        return (no_update, no_update,
                _alert(f"Gagal menghapus data: {exc}", "danger"))

    count = len(selected_ids)
    return (
        [],   # clear the table
        [],   # clear selection state
        _alert(f"🗑️ {count} baris berhasil dihapus dari {table_name}.", "success"),
    )
