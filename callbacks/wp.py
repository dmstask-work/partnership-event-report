import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dash_table, html

from dash_instance import app
from config import BLUE_SCALE, WARM_SCALE, CHART_LAYOUT
from utils import filter_wp, kpi_card


@app.callback(
    Output("wp-kpi-row",         "children"),
    Output("wp-chart-sesi",      "figure"),
    Output("wp-chart-gender",    "figure"),
    Output("wp-chart-provinsi",  "figure"),
    Output("wp-chart-country",   "figure"),
    Output("wp-chart-district",  "figure"),
    Output("wp-chart-frekuensi", "figure"),
    Output("wp-table-summary",   "children"),
    Output("wp-table-peserta",   "children"),
    Input("wp-dd-sesi",     "value"),
    Input("wp-dd-provinsi", "value"),
    Input("wp-dd-country",  "value"),
)
def update_wp(sesi, provinsi, country):
    df = filter_wp(sesi, provinsi, country)

    def _empty(title=""):
        fig = go.Figure()
        fig.update_layout(**CHART_LAYOUT, title=title)
        fig.add_annotation(text="Data tidak tersedia", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=14, color="#aaa"))
        return fig

    if df.empty:
        empty_tbl = html.P("Data tidak tersedia.", className="text-muted small")
        return ([], _empty("Top Sesi"), _empty("Gender"),
                _empty("Provinsi"), _empty("Negara"),
                _empty("Distrik"), _empty("Frekuensi Kehadiran Peserta"),
                empty_tbl, empty_tbl)

    n_entries = len(df)
    n_peserta = df["Nama"].nunique()
    pct_f     = (df["Gender"] == "Female").sum() / n_entries * 100 if n_entries else 0
    top_raw   = (df[df["Nama Event"] != "-"]["Nama Event"].value_counts().idxmax()
                 if (df["Nama Event"] != "-").any() else "-")
    top_lbl   = (top_raw[:22] + "\u2026") if len(top_raw) > 22 else top_raw
    n_ctry    = df[df["Country"] != "-"]["Country"].nunique()

    kpis = [
        kpi_card("Total Peserta",      str(n_peserta),  "#ADD3FA"),
        kpi_card("Total Sesi",         str(n_entries),  "#B9EBFA"),
        kpi_card("Proporsi Perempuan", f"{pct_f:.0f}%", "#FAFAD5"),
        kpi_card("Sesi Terpopuler",    top_lbl,         "#FADFAA"),
        kpi_card("Negara",             str(n_ctry),     "#FAD4C8"),
    ]

    # ── Top Sesi ─────────────────────────────────────────────────────────
    sesi_df = (df[df["Nama Event"] != "-"]["Nama Event"]
               .value_counts().head(15).reset_index())
    sesi_df.columns = ["Sesi", "Entri"]
    fig_sesi = px.bar(
        sesi_df, x="Entri", y="Sesi", orientation="h",
        title="Distribusi Event",
        color="Entri", color_continuous_scale=BLUE_SCALE, text="Entri",
    )
    fig_sesi.update_traces(textposition="outside", marker_line_width=0)
    fig_sesi.update_layout(**CHART_LAYOUT, coloraxis_showscale=False,
                           yaxis=dict(categoryorder="total ascending", title=""),
                           xaxis=dict(title=""))

    # ── Gender ───────────────────────────────────────────────────────────
    gen     = df.drop_duplicates(subset="Nama")["Gender"].value_counts()
    lbl_map = {"Female": "Perempuan", "Male": "Laki-laki"}
    gen.index = [lbl_map.get(i, i) for i in gen.index]
    n_uniq  = int(gen.sum())
    fig_gen = go.Figure(go.Pie(
        labels=gen.index, values=gen.values, hole=0.58,
        marker_colors=["#ADD3FA", "#FADFAA"],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} peserta<extra></extra>",
        direction="clockwise", sort=False,
    ))
    fig_gen.update_layout(
        **CHART_LAYOUT, title="Distribusi Gender", showlegend=False,
        annotations=[dict(
            text=f"<b>{n_uniq}</b><br>"
                 f"<span style='font-size:11px;color:#888'>Peserta</span>",
            x=0.5, y=0.5, font_size=16, showarrow=False,
        )],
    )

    # ── Provinsi ─────────────────────────────────────────────────────────
    prov_s  = df[df["Provinsi"].apply(
        lambda x: isinstance(x, str) and x not in ("-", "nan")
    )]["Provinsi"]
    prov_df = prov_s.value_counts().reset_index()
    prov_df.columns = ["Provinsi", "Entri"]
    fig_prov = px.bar(
        prov_df, x="Entri", y="Provinsi", orientation="h",
        title="Distribusi Provinsi",
        color="Entri", color_continuous_scale=BLUE_SCALE, text="Entri",
    )
    fig_prov.update_traces(textposition="outside", marker_line_width=0)
    fig_prov.update_layout(**CHART_LAYOUT, coloraxis_showscale=False,
                           yaxis=dict(categoryorder="total ascending", title=""),
                           xaxis=dict(title=""))

    # ── Country ──────────────────────────────────────────────────────────
    ctry_s  = df[df["Country"].apply(
        lambda x: isinstance(x, str) and x not in ("-", "nan")
    )]["Country"]
    ctry_df = ctry_s.value_counts().reset_index()
    ctry_df.columns = ["Country", "Entri"]
    fig_ctry = px.bar(
        ctry_df, x="Entri", y="Country", orientation="h",
        title="Distribusi Negara",
        color="Entri", color_continuous_scale=WARM_SCALE, text="Entri",
    )
    fig_ctry.update_traces(textposition="outside", marker_line_width=0)
    fig_ctry.update_layout(**CHART_LAYOUT, coloraxis_showscale=False,
                           yaxis=dict(categoryorder="total ascending", title=""),
                           xaxis=dict(title=""))

    # ── District (top 6 + Lainnya donut) ─────────────────────────────────
    dist_s     = df.drop_duplicates(subset="Nama")[df.drop_duplicates(subset="Nama")["District"].apply(
        lambda x: isinstance(x, str) and x not in ("-", "nan")
    )]["District"]
    dist_counts = dist_s.value_counts()
    dist_top    = dist_counts.head(6)
    lainnya     = dist_counts.iloc[6:].sum()
    if lainnya > 0:
        import pandas as pd
        dist_top = pd.concat([dist_top, pd.Series({"Lainnya": lainnya})])
    dist_colors = ["#ADD3FA", "#B9EBFA", "#FAFAD5",
                   "#FAEFC3", "#FADFAA", "#FAD4C8", "#d0d8e4"]
    fig_dist    = go.Figure(go.Pie(
        labels=dist_top.index, values=dist_top.values, hole=0.58,
        marker_colors=dist_colors[:len(dist_top)],
        textinfo="percent",
        textposition="inside",
        insidetextorientation="radial",
        hovertemplate="%{label}: %{value} peserta (%{percent})<extra></extra>",
        direction="clockwise", sort=True,
        domain=dict(x=[0, 0.7], y=[0, 1]),
    ))
    fig_dist.update_layout(
        **CHART_LAYOUT, title="Distribusi Kota / Distrik", showlegend=True,
        legend=dict(
            orientation="v",
            x=0.75, y=0.5,
            xanchor="left", yanchor="middle",
            font=dict(size=11, color="#555"),
            itemwidth=30,
        ),
        annotations=[dict(
            text=f"<b>{n_peserta}</b><br>"
                 f"<span style='font-size:11px;color:#888'>Peserta</span>",
            x=0.35, y=0.5, font_size=16, showarrow=False,
        )],
    )
    fig_dist.update_layout(margin=dict(t=48, b=32, l=8, r=120))

    # ── Frekuensi Kehadiran Peserta ─────────────────────────────────────
    freq_counts = df["Nama"].value_counts()
    freq_buckets = freq_counts.apply(
        lambda x: ">5 Kali" if x > 5 else (f"{x} Kali" if x >= 2 else "1 Kali")
    )
    freq_order_wp = ["1 Kali", "2 Kali", "3 Kali", "4 Kali", "5 Kali", ">5 Kali"]
    freq_df_wp = (
        freq_buckets.value_counts()
        .reindex(freq_order_wp, fill_value=0)
        .rename_axis("Frekuensi")
        .reset_index(name="Peserta")
    )
    fig_freq_wp = go.Figure(go.Bar(
        x=freq_df_wp["Frekuensi"], y=freq_df_wp["Peserta"],
        marker_color="#ADD3FA", text=freq_df_wp["Peserta"], textposition="outside",
    ))
    fig_freq_wp.update_layout(
        **CHART_LAYOUT, title="Frekuensi Kehadiran Peserta", showlegend=False,
        xaxis=dict(categoryorder="array", categoryarray=freq_order_wp, title=""),
        yaxis=dict(title=""),
    )

    # ── Ringkasan per Event ───────────────────────────────────────────────
    tbl_event = (
        df.groupby("Nama Event", sort=False)
        .agg(
            Peserta=  ("Nama",   "nunique"),
            Perempuan=("Gender", lambda x: (x == "Female").sum()),
            Laki_laki=("Gender", lambda x: (x == "Male").sum()),
        )
        .reset_index()
        .sort_values("Peserta", ascending=False)
        .rename(columns={"Laki_laki": "Laki-laki"})
    )
    summary_table = dash_table.DataTable(
        data=tbl_event.to_dict("records"),
        columns=[{"name": c, "id": c} for c in tbl_event.columns],
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
            {"if": {"column_id": "Peserta"}, "fontWeight": "bold",
             "color": "#3a8fd9"},
        ],
    )

    # ── Rekap Peserta WP ─────────────────────────────────────────────────
    tbl_wp = (
        df.groupby("Nama", sort=False)
        .agg(
            No_WA=     ("No WhatsApp", "first"),
            Provinsi=  ("Provinsi",    "first"),
            Country=   ("Country",     "first"),
            Total_Sesi=("Nama Event",  "count"),
        )
        .reset_index()
        .sort_values("Total_Sesi", ascending=False)
        .rename(columns={
            "Nama":       "Nama Peserta",
            "No_WA":      "No WhatsApp",
            "Total_Sesi": "Total Sesi",
        })
    )
    wp_table = dash_table.DataTable(
        data=tbl_wp.to_dict("records"),
        columns=[{"name": c, "id": c} for c in tbl_wp.columns],
        sort_action="native", filter_action="native", page_size=10,
        style_table={"borderRadius": "8px", "overflow": "hidden",
                     "boxShadow": "0 1px 4px rgba(0,0,0,0.06)"},
        style_header={"backgroundColor": "#ADD3FA", "fontWeight": "bold",
                      "border": "none", "padding": "10px 14px", "fontSize": "13px"},
        style_cell={"padding": "9px 14px", "fontFamily": "Segoe UI, sans-serif",
                    "fontSize": "13px", "border": "1px solid #eef2f7",
                    "textAlign": "left", "whiteSpace": "normal",
                    "maxWidth": "220px", "overflow": "hidden",
                    "textOverflow": "ellipsis"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f5faff"},
            {"if": {"column_id": "Total Sesi"}, "fontWeight": "bold",
             "color": "#3a8fd9"},
        ],
    )
    return (kpis, fig_sesi, fig_gen, fig_prov, fig_ctry, fig_dist,
            fig_freq_wp, summary_table, wp_table)


@app.callback(
    Output("wp-table-riwayat", "children"),
    Input("wp-dd-search-peserta", "value"),
)
def wp_show_riwayat(nama):
    from data import df_wp_raw
    if not nama:
        return html.P("Pilih nama peserta untuk melihat riwayat kehadiran.",
                      className="text-muted small")
    cols = [c for c in ["Nama Event", "Lokasi Event", "Tanggal", "Sesi"]
            if c in df_wp_raw.columns]
    rows = df_wp_raw[df_wp_raw["Nama"] == nama][cols].copy()
    if rows.empty:
        return html.P("Tidak ada data untuk peserta ini.", className="text-muted small")
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
