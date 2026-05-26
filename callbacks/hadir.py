import io
from collections import Counter
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, dash_table, dcc, html
from dash.exceptions import PreventUpdate

from dash_instance import app
from config import (
    FREQ_ORDER, WILAYAH_ORDER, PALETTE,
    BLUE_SCALE, WARM_SCALE, PEACH_SCALE,
    CHART_LAYOUT, KNOWN_HARAPAN, KNOWN_KELUHAN,
)
from data import load_hadir_df
from utils import filter_df, kpi_card, parse_topics


# ── Cache loader ─────────────────────────────────────────────────────────────
# Fires on page load (data-refresh-ts == 0) and after every CRUD/upload
# success (incremented counter).  Stores the full hadir DataFrame as JSON
# so report callbacks never hit the DB directly.
@app.callback(
    Output("hadir-data-cache", "data"),
    Input("data-refresh-ts", "data"),
)
def load_hadir_cache(_ts):
    df = load_hadir_df()
    return df.to_json(date_format="iso", orient="split")


@app.callback(
    Output("dd-event", "options"),
    Input("dd-kategori", "value"),
    Input("dd-wilayah", "value"),
    Input("dd-frekuensi", "value"),
    Input("hadir-data-cache", "data"),
)
def cascade_event(kategori, wilayah, frekuensi, hadir_json):
    if not hadir_json:
        return [{"label": "✦ Semua Event", "value": "ALL"}]
    df = pd.read_json(io.StringIO(hadir_json), orient="split")
    if kategori != "ALL":
        df = df[df["Kategori"] == kategori]
    if wilayah != "ALL":
        df = df[df["Wilayah"] == wilayah]
    if frekuensi != "ALL":
        df = df[df["Frekuensi Kehadiran"] == frekuensi]
    events = sorted(df["Event Label"].dropna().unique())
    return [{"label": "✦ Semua Event", "value": "ALL"}] + [
        {"label": e, "value": e} for e in events
    ]


@app.callback(
    Output("kpi-row",              "children"),
    Output("chart-location",       "figure"),
    Output("chart-gender",         "figure"),
    Output("chart-age",            "figure"),
    Output("chart-profesi",        "figure"),
    Output("chart-kota",           "figure"),
    Output("chart-harapan",        "figure"),
    Output("chart-keluhan",        "figure"),
    Output("chart-wilayah",        "figure"),
    Output("chart-frekuensi",      "figure"),
    Output("table-summary",        "children"),
    Output("table-peserta",        "children"),
    Output("store-rekap-peserta",  "data"),
    Input("dd-kategori",  "value"),
    Input("dd-event",     "value"),
    Input("dd-wilayah",   "value"),
    Input("dd-frekuensi", "value"),
    Input("hadir-data-cache", "data"),
)
def update_all(kategori, event, wilayah, frekuensi, hadir_json):
    if not hadir_json:
        raise PreventUpdate
    df_full = pd.read_json(io.StringIO(hadir_json), orient="split")
    df      = filter_df(df_full, kategori, event, wilayah, frekuensi)
    df_uniq = df.drop_duplicates(subset="Nama", keep="first")
    n       = df_uniq.shape[0]

    # ── KPI ──────────────────────────────────────────────────────────────
    avg_age  = df_uniq["Usia"].mean() if n else 0
    pct_f    = (df_uniq["Gender"] == "Female").sum() / n * 100 if n else 0
    top_prov = df_uniq["Wilayah"].value_counts().idxmax() if n else "-"
    n_events = df["Event Label"].nunique()

    kpis = [
        kpi_card("Peserta",            str(n),              "#ADD3FA"),
        kpi_card("Jumlah Event",       str(n_events),       "#B9EBFA"),
        kpi_card("Rata-rata Usia",     f"{avg_age:.1f} th", "#FAFAD5"),
        kpi_card("Proporsi Perempuan", f"{pct_f:.0f}%",     "#FADFAA"),
        kpi_card("Wilayah Terbanyak",  top_prov,            "#FAD4C8"),
    ]

    # ── Location ─────────────────────────────────────────────────────────
    prov = df_uniq["Provinsi"].value_counts().reset_index()
    prov.columns = ["Provinsi", "Peserta"]
    fig_loc = px.bar(
        prov, x="Peserta", y="Provinsi", orientation="h",
        title="Lokasi Peserta per Provinsi",
        color="Peserta", color_continuous_scale=BLUE_SCALE, text="Peserta",
    )
    fig_loc.update_traces(textposition="outside", marker_line_width=0)
    fig_loc.update_layout(
        **CHART_LAYOUT, coloraxis_showscale=False,
        yaxis=dict(categoryorder="total ascending", title=""),
        xaxis=dict(title=""),
    )

    # ── Gender ───────────────────────────────────────────────────────────
    gen = df_uniq["Gender"].value_counts()
    label_map = {"Female": "Perempuan", "Male": "Laki-laki"}
    gen.index = [label_map.get(i, i) for i in gen.index]
    fig_gen = go.Figure(go.Pie(
        labels=gen.index, values=gen.values, hole=0.58,
        marker_colors=["#ADD3FA", "#FADFAA"],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} peserta<extra></extra>",
        direction="clockwise", sort=False,
    ))
    fig_gen.update_layout(
        **CHART_LAYOUT, title="Komposisi Gender", showlegend=False,
        annotations=[dict(
            text=f"<b>{n}</b><br>"
                 f"<span style='font-size:11px;color:#888'>Peserta</span>",
            x=0.5, y=0.5, font_size=16, showarrow=False,
        )],
    )

    # ── Age ──────────────────────────────────────────────────────────────
    age_order = ["≤12", "13-17", "18-25", "26-35", "36-45", "46-55", "56-65", "66+"]
    age_c = (
        df_uniq["Kelompok Usia"]
        .value_counts()
        .reindex(age_order, fill_value=0)
        .reset_index()
    )
    age_c.columns = ["Kelompok Usia", "Peserta"]
    fig_age = px.bar(
        age_c, x="Kelompok Usia", y="Peserta",
        title="Distribusi Usia",
        color="Kelompok Usia", color_discrete_sequence=PALETTE, text="Peserta",
    )
    fig_age.update_traces(textposition="outside", marker_line_width=0)
    fig_age.update_layout(
        **CHART_LAYOUT, showlegend=False,
        xaxis=dict(categoryorder="array", categoryarray=age_order, title=""),
        yaxis=dict(title=""),
    )

    # ── Profesi ──────────────────────────────────────────────────────────
    prof = df_uniq["Kategori Profesi"].value_counts().reset_index()
    prof.columns = ["Profesi", "Peserta"]
    fig_prof = px.bar(
        prof, x="Peserta", y="Profesi", orientation="h",
        title="Profesi Peserta",
        color="Peserta", color_continuous_scale=WARM_SCALE, text="Peserta",
    )
    fig_prof.update_traces(textposition="outside", marker_line_width=0)
    fig_prof.update_layout(
        **CHART_LAYOUT, coloraxis_showscale=False,
        yaxis=dict(categoryorder="total ascending", title=""),
        xaxis=dict(title=""),
    )

    # ── Kota ─────────────────────────────────────────────────────────────
    kota = df_uniq["Kota"].value_counts().head(15).reset_index()
    kota.columns = ["Kota", "Peserta"]
    fig_kota = px.bar(
        kota, x="Peserta", y="Kota", orientation="h",
        title="Distribusi Kota Asal Peserta",
        color="Peserta", color_continuous_scale=BLUE_SCALE, text="Peserta",
    )
    fig_kota.update_traces(textposition="outside", marker_line_width=0)
    fig_kota.update_layout(
        **CHART_LAYOUT, coloraxis_showscale=False,
        yaxis=dict(categoryorder="total ascending", title=""),
        xaxis=dict(title=""),
    )

    # ── Harapan ──────────────────────────────────────────────────────────
    h_all = []
    for v in df_uniq["Topik Harapan"].dropna():
        h_all.extend(parse_topics(v, KNOWN_HARAPAN))
    h_cnt = Counter(h_all)
    h_cnt.pop("Tidak Ada Respons", None)
    h_df = pd.DataFrame(h_cnt.most_common(), columns=["Topik", "Peserta"])
    fig_har = px.bar(
        h_df, x="Peserta", y="Topik", orientation="h",
        title="Topik Harapan Peserta",
        color="Peserta",
        color_continuous_scale=["#D4F0FF", "#ADD3FA", "#7BBEF0"],
        text="Peserta",
    )
    fig_har.update_traces(textposition="outside", marker_line_width=0)
    fig_har.update_layout(
        **CHART_LAYOUT, coloraxis_showscale=False,
        yaxis=dict(categoryorder="total ascending", title=""),
        xaxis=dict(title=""),
    )

    # ── Keluhan ──────────────────────────────────────────────────────────
    k_all = []
    for v in df_uniq["Topik Keluhan"].dropna():
        k_all.extend(parse_topics(v, KNOWN_KELUHAN))
    k_cnt = Counter(k_all)
    for noise in ["Tidak Ada Respons", "Tidak Ada Keluhan"]:
        k_cnt.pop(noise, None)
    k_df = pd.DataFrame(k_cnt.most_common(), columns=["Topik", "Peserta"])

    if not k_df.empty:
        fig_kel = px.bar(
            k_df, x="Peserta", y="Topik", orientation="h",
            title="Topik Keluhan Peserta",
            color="Peserta", color_continuous_scale=PEACH_SCALE, text="Peserta",
        )
        fig_kel.update_traces(textposition="outside", marker_line_width=0)
        fig_kel.update_layout(
            **CHART_LAYOUT, coloraxis_showscale=False,
            yaxis=dict(categoryorder="total ascending", title=""),
            xaxis=dict(title=""),
        )
    else:
        fig_kel = go.Figure()
        fig_kel.update_layout(**CHART_LAYOUT, title="Topik Keluhan Peserta")
        fig_kel.add_annotation(text="Tidak ada keluhan tercatat",
                               x=0.5, y=0.5, showarrow=False,
                               font=dict(size=14, color="#aaa"))

    # ── Wilayah ──────────────────────────────────────────────────────────
    wil = (
        df_uniq["Wilayah"]
        .value_counts()
        .reindex(WILAYAH_ORDER, fill_value=0)
        .reset_index()
    )
    wil.columns = ["Wilayah", "Peserta"]
    wil = wil[wil["Peserta"] > 0]
    total_wil = wil["Peserta"].sum()

    fig_wil = go.Figure(go.Pie(
        labels=wil["Wilayah"], values=wil["Peserta"], hole=0.55,
        marker_colors=["#ADD3FA", "#FAEFC3", "#FAD4C8", "#B9EBFA"],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} peserta (%{percent})<extra></extra>",
        direction="clockwise", sort=False,
    ))
    fig_wil.update_layout(
        **CHART_LAYOUT, title="Distribusi Wilayah", showlegend=False,
        annotations=[dict(
            text=f"<b>{total_wil}</b><br>"
                 f"<span style='font-size:11px;color:#888'>Peserta</span>",
            x=0.5, y=0.5, font_size=16, showarrow=False,
        )],
    )

    # ── Frekuensi Kehadiran ───────────────────────────────────────────────
    freq_df = (
        df_uniq["Frekuensi Kehadiran"]
        .value_counts()
        .reindex(FREQ_ORDER, fill_value=0)
        .reset_index()
    )
    freq_df.columns = ["Frekuensi", "Peserta"]
    fig_freq = go.Figure(go.Bar(
        x=freq_df["Frekuensi"], y=freq_df["Peserta"],
        marker_color="#ADD3FA", text=freq_df["Peserta"], textposition="outside",
    ))
    fig_freq.update_layout(
        **CHART_LAYOUT, title="Frekuensi Kehadiran Peserta", showlegend=False,
        xaxis=dict(categoryorder="array", categoryarray=FREQ_ORDER, title=""),
        yaxis=dict(title=""),
    )

    # ── Table per event ──────────────────────────────────────────────────
    tbl = (
        df.groupby("Event Label", sort=False)
        .agg(
            Kategori=  ("Kategori", "first"),
            Peserta=   ("Nama",     "nunique"),
            Perempuan= ("Gender",   lambda x: (x == "Female").sum()),
            Laki_laki= ("Gender",   lambda x: (x == "Male").sum()),
            Rata_usia= ("Usia",     lambda x: round(x.mean(), 1)),
        )
        .reset_index()
        .sort_values("Peserta", ascending=False)
        .rename(columns={
            "Event Label": "Nama Event",
            "Laki_laki":   "Laki-laki",
            "Rata_usia":   "Rata-rata Usia",
        })
    )
    table = dash_table.DataTable(
        data=tbl.to_dict("records"),
        columns=[{"name": c, "id": c} for c in tbl.columns],
        sort_action="native", page_size=8,
        style_table={"borderRadius": "8px", "overflow": "hidden",
                     "boxShadow": "0 1px 4px rgba(0,0,0,0.06)"},
        style_header={"backgroundColor": "#ADD3FA", "fontWeight": "bold",
                      "border": "none", "padding": "10px 14px", "fontSize": "13px"},
        style_cell={"padding": "9px 14px", "fontFamily": "Segoe UI, sans-serif",
                    "fontSize": "13px", "border": "1px solid #eef2f7",
                    "textAlign": "left", "whiteSpace": "normal"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f5faff"},
            {"if": {"column_id": "Peserta"}, "fontWeight": "bold", "color": "#3a8fd9"},
        ],
    )

    # ── Rekap Kehadiran Peserta ─────────────────────────────────────────
    peserta_tbl = (
        df.groupby("Nama", sort=False)
        .agg(
            Domisili=           ("Kota",             "first"),
            Profesi=            ("Kategori Profesi", "first"),
            Kategori_Terbanyak= ("Kategori",         lambda x: x.value_counts().idxmax()),
            No_telp=            ("No WhatsApp",      "first"),
            Total_Kehadiran=    ("Nama",             "count"),
        )
        .reset_index()
        .sort_values("Total_Kehadiran", ascending=False)
        .rename(columns={
            "Nama":               "Nama Peserta",
            "Domisili":           "Kota Domisili",
            "Profesi":            "Kategori Profesi",
            "Kategori_Terbanyak": "Kategori Terbanyak",
            "No_telp":            "No WhatsApp",
            "Total_Kehadiran":    "Total Kehadiran",
        })
    )
    tbl_peserta = dash_table.DataTable(
        data=peserta_tbl.to_dict("records"),
        columns=[{"name": c, "id": c} for c in peserta_tbl.columns],
        sort_action="native", filter_action="native", page_size=6,
        style_table={"borderRadius": "8px", "overflow": "hidden",
                     "boxShadow": "0 1px 4px rgba(0,0,0,0.06)"},
        style_header={"backgroundColor": "#B9EBFA", "fontWeight": "bold",
                      "border": "none", "padding": "10px 14px", "fontSize": "13px"},
        style_cell={"padding": "9px 14px", "fontFamily": "Segoe UI, sans-serif",
                    "fontSize": "13px", "border": "1px solid #eef2f7",
                    "textAlign": "left", "whiteSpace": "normal"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f5faff"},
            {"if": {"column_id": "Total Kehadiran"}, "fontWeight": "bold",
             "color": "#3a8fd9"},
        ],
    )

    return (kpis, fig_loc, fig_gen, fig_age, fig_prof, fig_kota,
            fig_har, fig_kel, fig_wil, fig_freq, table, tbl_peserta,
            peserta_tbl.to_dict("records"))


@app.callback(
    Output("dd-search-peserta", "options"),
    Input("hadir-data-cache", "data"),
)
def update_search_peserta_options(hadir_json):
    if not hadir_json:
        return []
    df = pd.read_json(io.StringIO(hadir_json), orient="split")
    names = sorted(df["Nama"].dropna().unique())
    return [{"label": n, "value": n} for n in names]


@app.callback(
    Output("table-riwayat", "children"),
    Input("dd-search-peserta", "value"),
    State("hadir-data-cache", "data"),
)
def show_riwayat(nama, hadir_json):
    if not nama:
        return html.P("Pilih nama peserta untuk melihat riwayat kehadiran.",
                      className="text-muted small")
    if not hadir_json:
        return html.P("Data belum dimuat. Silakan tunggu sebentar.",
                      className="text-muted small")
    df = pd.read_json(io.StringIO(hadir_json), orient="split")
    rows = (
        df[df["Nama"] == nama][["Nama Event", "Lokasi Event", "Kategori"]]
        .copy()
        .rename(columns={"Lokasi Event": "Lokasi"})
    )
    return dash_table.DataTable(
        data=rows.to_dict("records"),
        columns=[{"name": c, "id": c} for c in rows.columns],
        style_table={"borderRadius": "8px", "overflow": "hidden"},
        style_header={"backgroundColor": "#ADD3FA", "fontWeight": "bold",
                      "border": "none", "padding": "10px 14px", "fontSize": "13px"},
        style_cell={"padding": "9px 14px", "fontFamily": "Segoe UI, sans-serif",
                    "fontSize": "13px", "border": "1px solid #eef2f7",
                    "textAlign": "left"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f5faff"},
        ],
    )


# ── Download Rekap Kehadiran Peserta ──────────────────────────────────────────
@app.callback(
    Output("download-rekap-peserta", "data"),
    Input("btn-download-rekap", "n_clicks"),
    State("store-rekap-peserta", "data"),
    prevent_initial_call=True,
)
def download_rekap_peserta(n_clicks, stored_data):
    if not stored_data:
        return None
    df_export = pd.DataFrame(stored_data)
    filename = f"Rekap_Peserta_Hadir_{date.today().strftime('%Y-%m-%d')}.xlsx"
    return dcc.send_data_frame(df_export.to_excel, filename, index=False)
