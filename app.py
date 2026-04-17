import os
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

# ── Data ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data_clean", "data_merged.xlsx")

df_raw = pd.read_excel(DATA_PATH)

# Build a combined event label that distinguishes same-name events at different locations
df_raw["Event Label"] = df_raw.apply(
    lambda r: r["Nama Event"] + " - " + r["Lokasi Event"]
    if isinstance(r["Lokasi Event"], str) and r["Lokasi Event"].strip() not in ("", "-")
    else r["Nama Event"],
    axis=1,
)

# ── Frequency bucket per Nama (computed on full dataset — person property) ──
_freq_map = df_raw["Nama"].value_counts()
df_raw["_freq"] = df_raw["Nama"].map(_freq_map)
df_raw["Frekuensi Kehadiran"] = df_raw["_freq"].apply(
    lambda x: ">5 Kali" if x > 5 else (f"{x} Kali" if x >= 2 else "1 Kali")
)
df_raw = df_raw.drop(columns=["_freq"])

FREQ_ORDER    = ["1 Kali", "2 Kali", "3 Kali", "4 Kali", "5 Kali", ">5 Kali"]
WILAYAH_ORDER = ["Jabodetabek", "Jawa Tengah", "Jawa Timur", "Bali"]

# ── Palette ────────────────────────────────────────────────────────────────
PALETTE = [
    "#ADD3FA", "#B9EBFA", "#FAFAD5", "#FAEFC3", "#FADFAA", "#FAD4C8",
    "#C5E4FB", "#D4F5FB", "#FAFAEC", "#FAF2D8", "#FAE8BE", "#FAD9D0",
]
BLUE_SCALE  = ["#D4F0FF", "#ADD3FA", "#7AB8F0"]
WARM_SCALE  = ["#FAFAD5", "#FAEFC3", "#FAD4C8"]
PEACH_SCALE = ["#FAFAD5", "#FAD4C8", "#FADFAA"]

# ── Styles ─────────────────────────────────────────────────────────────────
CARD_STYLE = {"borderRadius": "10px", "boxShadow": "0 2px 8px rgba(0,0,0,0.07)"}
SECTION_STYLE = {"background": "white", "borderRadius": "10px",
                 "padding": "16px", "boxShadow": "0 2px 8px rgba(0,0,0,0.06)"}
CHART_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Segoe UI, sans-serif", size=12, color="#333"),
    margin=dict(t=48, b=32, l=8, r=24),
)

# ── Known topic labels (handles "Anatomi, Gerak & Postur Tubuh" with comma) ─
KNOWN_HARAPAN = [
    "Menambah Pengetahuan & Wawasan",
    "Penanganan Cedera & Keluhan",
    "Anatomi, Gerak & Postur Tubuh",
    "Pengembangan Profesi & Berbagi Ilmu",
    "Penerapan untuk Diri Sendiri & Keluarga",
    "Kesehatan Metabolik",
    "Skoliosis",
    "Kesehatan Anak & Postur Remaja",
    "Lainnya",
    "Tidak Ada Respons",
]
KNOWN_KELUHAN = [
    "Skoliosis",
    "Saraf Kejepit & Nyeri Punggung",
    "Nyeri Sendi & Otot",
    "Postur Tubuh Tidak Seimbang",
    "Penyakit Metabolik",
    "Ingin Sembuh / Terapi",
    "Tidak Ada Keluhan",
    "Tidak Ada Respons",
    "Lainnya",
]


def parse_topics(text, known):
    """Greedy match against known topic labels (handles commas inside labels)."""
    if not isinstance(text, str) or not text.strip():
        return []
    remaining = text.strip()
    found = []
    while remaining:
        matched = False
        for t in known:
            if remaining.startswith(t):
                found.append(t)
                remaining = remaining[len(t):].lstrip(", ")
                matched = True
                break
        if not matched:
            idx = remaining.find(", ")
            if idx == -1:
                found.append(remaining.strip())
                break
            found.append(remaining[:idx].strip())
            remaining = remaining[idx + 2:]
    return found


# ── App ────────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Partnership & Event Report",
)
server = app.server

app.layout = dbc.Container([

    # ── Header ──────────────────────────────────────────────────────────────
    dbc.Row(dbc.Col(
        html.Div([
            html.H3("📊 Dashboard Report Partnership & Event", className="mb-0 fw-bold"),
            html.P("Summary data partnership & event",
                   className="mb-0 text-black-50 small"),
        ], className="py-3 px-4"),
    ), style={"background": "linear-gradient(135deg, #ADD3FA 0%, #B9EBFA 100%)",
              "borderRadius": "0 0 16px 16px", "marginBottom": "2.5rem"}),

    # ── Filters ─────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            html.Label("Kategori", className="fw-semibold small text-muted mb-1"),
            dcc.Dropdown(
                id="dd-kategori",
                options=[{"label": "✦ Semua Kategori", "value": "ALL"}] + [
                    {"label": k, "value": k}
                    for k in sorted(df_raw["Kategori"].dropna().unique())
                ],
                value="ALL",
                clearable=False,
                style={"borderRadius": "8px"},
            ),
        ], md=3),
        dbc.Col([
            html.Label("Nama Event", className="fw-semibold small text-muted mb-1"),
            dcc.Dropdown(
                id="dd-event",
                options=[{"label": "✦ Semua Event", "value": "ALL"}] + [
                    {"label": e, "value": e}
                    for e in sorted(df_raw["Event Label"].dropna().unique())
                ],
                value="ALL",
                clearable=False,
                style={"borderRadius": "8px"},
            ),
        ], md=5),
        dbc.Col([
            html.Label("Wilayah", className="fw-semibold small text-muted mb-1"),
            dcc.Dropdown(
                id="dd-wilayah",
                options=[{"label": "✦ Semua Wilayah", "value": "ALL"}] + [
                    {"label": w, "value": w} for w in WILAYAH_ORDER
                ],
                value="ALL",
                clearable=False,
                style={"borderRadius": "8px"},
            ),
        ], md=2),
        dbc.Col([
            html.Label("Frekuensi Kehadiran", className="fw-semibold small text-muted mb-1"),
            dcc.Dropdown(
                id="dd-frekuensi",
                options=[{"label": "✦ Semua", "value": "ALL"}] + [
                    {"label": f, "value": f} for f in FREQ_ORDER
                ],
                value="ALL",
                clearable=False,
                style={"borderRadius": "8px"},
            ),
        ], md=2),
    ], className="mb-4 p-3 g-3",
       style={"background": "#f7fafd", "borderRadius": "10px",
              "boxShadow": "0 1px 4px rgba(0,0,0,0.05)"}),

    # ── KPI Cards ────────────────────────────────────────────────────────────
    dbc.Row(id="kpi-row", className="mb-4 g-3"),

    # ── Row 1 : Location + Gender ────────────────────────────────────────────
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="chart-location", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=8,
        ),
        dbc.Col(
            html.Div(dcc.Graph(id="chart-gender", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=4,
        ),
    ], className="mb-4 g-3"),

    # ── Row 1.5 : Kota ─────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="chart-kota", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=12,
        ),
    ], className="mb-4 g-3"),

    # ── Row 1.7 : Wilayah + Frekuensi Kehadiran ────────────────────────────────
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="chart-wilayah", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=5,
        ),
        dbc.Col(
            html.Div(dcc.Graph(id="chart-frekuensi", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=7,
        ),
    ], className="mb-4 g-3"),

    # ── Row 2 : Age + Profession ─────────────────────────────────────────────
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="chart-age", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=6,
        ),
        dbc.Col(
            html.Div(dcc.Graph(id="chart-profesi", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=6,
        ),
    ], className="mb-4 g-3"),

    # ── Row 3 : Harapan + Keluhan ─────────────────────────────────────────────
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="chart-harapan", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=6,
        ),
        dbc.Col(
            html.Div(dcc.Graph(id="chart-keluhan", config={"displayModeBar": False}),
                     style=SECTION_STYLE),
            md=6,
        ),
    ], className="mb-4 g-3"),

    # ── Table ─────────────────────────────────────────────────────────────────
    dbc.Row(dbc.Col(
        html.Div([
            html.H6("Ringkasan per Event", className="fw-bold mb-3 text-secondary"),
            html.Div(id="table-summary"),
        ], style=SECTION_STYLE),
    ), className="mb-4"),

    # ── Peserta Activity Table ─────────────────────────────────────────────
    dbc.Row(dbc.Col(
        html.Div([
            html.H6("Rekap Kehadiran Peserta", className="fw-bold mb-3 text-secondary"),
            html.Div(id="table-peserta"),
        ], style=SECTION_STYLE),
    ), className="mb-4"),

    # ── Riwayat Kehadiran per Peserta ─────────────────────────────────────────
    dbc.Row(dbc.Col(
        html.Div([
            html.H6("Riwayat Kehadiran per Peserta", className="fw-bold mb-3 text-secondary"),
            dcc.Dropdown(
                id="dd-search-peserta",
                options=[{"label": n, "value": n} for n in sorted(df_raw["Nama"].dropna().unique())],
                placeholder="Cari nama peserta...",
                clearable=True,
                style={"borderRadius": "8px", "marginBottom": "12px"},
            ),
            # html.Datalist(
            #     id="peserta-datalist",
            #     children=[html.Option(value=n) for n in sorted(df_raw["Nama"].dropna().unique())]
            # ),
            # dcc.Input(
            #     id="dd-search-peserta",
            #     type="text",
            #     placeholder="Cari nama peserta...",
            #     debounce=True,
            #     list="peserta-datalist",
            #     style={"borderRadius": "4px", "marginBottom": "12px", "width": "100%", "padding": "0px 12px"},
            # ),
            html.Div(id="table-riwayat"),
        ], style=SECTION_STYLE),
    ), className="mb-5"),

], fluid=True, style={"fontFamily": "Segoe UI, sans-serif",
                       "padding": "0 20px 5px 20px", "backgroundColor": "#f0f6fd"})


# ── Helpers ────────────────────────────────────────────────────────────────
def filter_df(kategori, event, wilayah="ALL", frekuensi="ALL"):
    df = df_raw.copy()
    if kategori != "ALL":
        df = df[df["Kategori"] == kategori]
    if event != "ALL":
        df = df[df["Event Label"] == event]
    if wilayah != "ALL":
        df = df[df["Wilayah"] == wilayah]
    if frekuensi != "ALL":
        df = df[df["Frekuensi Kehadiran"] == frekuensi]
    return df


def kpi_card(label, value, accent):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.P(label, className="text-muted small mb-1",
                       style={"fontSize": "0.75rem", "fontWeight": "600"}),
                html.H4(value, className="fw-bold mb-0", style={"color": "#333"}),
            ]),
            style={**CARD_STYLE, "borderLeft": f"5px solid {accent}",
                   "borderTop": "none", "borderRight": "none", "borderBottom": "none"},
        ),
        md=True,
    )


# ── Cascading filter ───────────────────────────────────────────────────────
@app.callback(
    Output("dd-event", "options"),
    Input("dd-kategori", "value"),
    Input("dd-wilayah", "value"),
    Input("dd-frekuensi", "value"),
)
def cascade_event(kategori, wilayah, frekuensi):
    df = df_raw.copy()
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

# ── Main callback ─────────────────────────────────────────────────────────
@app.callback(
    Output("kpi-row", "children"),
    Output("chart-location", "figure"),
    Output("chart-gender", "figure"),
    Output("chart-age", "figure"),
    Output("chart-profesi", "figure"),
    Output("chart-kota", "figure"),
    Output("chart-harapan", "figure"),
    Output("chart-keluhan", "figure"),
    Output("chart-wilayah", "figure"),
    Output("chart-frekuensi", "figure"),
    Output("table-summary", "children"),
    Output("table-peserta", "children"),
    Input("dd-kategori", "value"),
    Input("dd-event", "value"),
    Input("dd-wilayah", "value"),
    Input("dd-frekuensi", "value"),    
)
def update_all(kategori, event, wilayah, frekuensi):
    df = filter_df(kategori, event, wilayah, frekuensi)
    df_uniq = df.drop_duplicates(subset="Nama", keep="first")
    n = df_uniq.shape[0]

    # ── KPI ──────────────────────────────────────────────────────────────
    avg_age = df_uniq["Usia"].mean() if n else 0
    pct_f = (df_uniq["Gender"] == "Female").sum() / n * 100 if n else 0
    top_prov = df_uniq["Wilayah"].value_counts().idxmax() if n else "-"
    n_events = df["Event Label"].nunique()

    kpis = [
        kpi_card("Peserta",        str(n),              "#ADD3FA"),
        kpi_card("Jumlah Event",        str(n_events),       "#B9EBFA"),
        kpi_card("Rata-rata Usia",      f"{avg_age:.1f} th", "#FAFAD5"),
        kpi_card("Proporsi Perempuan",  f"{pct_f:.0f}%",     "#FADFAA"),
        kpi_card("Wilayah Terbanyak",   top_prov,            "#FAD4C8"),
    ]

    # ── Location ─────────────────────────────────────────────────────────
    prov = df_uniq["Provinsi"].value_counts().reset_index()
    prov.columns = ["Provinsi", "Peserta"]
    fig_loc = px.bar(
        prov, x="Peserta", y="Provinsi", orientation="h",
        title="Lokasi Peserta per Provinsi",
        color="Peserta", color_continuous_scale=BLUE_SCALE,
        text="Peserta",
    )
    fig_loc.update_traces(textposition="outside", marker_line_width=0)
    fig_loc.update_layout(
        **CHART_LAYOUT,
        coloraxis_showscale=False,
        yaxis=dict(categoryorder="total ascending", title=""),
        xaxis=dict(title=""),
    )

    # ── Gender ───────────────────────────────────────────────────────────
    gen = df_uniq["Gender"].value_counts()
    label_map = {"Female": "Perempuan", "Male": "Laki-laki"}
    gen.index = [label_map.get(i, i) for i in gen.index]
    fig_gen = go.Figure(go.Pie(
        labels=gen.index,
        values=gen.values,
        hole=0.58,
        marker_colors=["#ADD3FA", "#FADFAA"],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} peserta<extra></extra>",
        direction="clockwise",
        sort=False,
    ))
    fig_gen.update_layout(
        **CHART_LAYOUT,
        title="Komposisi Gender",
        showlegend=False,
        annotations=[dict(
            text=f"<b>{n}</b><br><span style='font-size:11px;color:#888'>Peserta</span>",
            x=0.5, y=0.5, font_size=16, showarrow=False,
        )],
    )

    # ── Age ──────────────────────────────────────────────────────────────
    age_order = ["≤12", "13-17", "18-25", "26-35", "36-45", "46-55", "56-65", "66+"]
    age_c = (df_uniq["Kelompok Usia"]
             .value_counts()
             .reindex(age_order, fill_value=0)
             .reset_index())
    age_c.columns = ["Kelompok Usia", "Peserta"]
    fig_age = px.bar(
        age_c, x="Kelompok Usia", y="Peserta",
        title="Distribusi Usia",
        color="Kelompok Usia",
        color_discrete_sequence=PALETTE,
        text="Peserta",
    )
    fig_age.update_traces(textposition="outside", marker_line_width=0)
    fig_age.update_layout(
        **CHART_LAYOUT,
        showlegend=False,
        xaxis=dict(categoryorder="array", categoryarray=age_order, title=""),
        yaxis=dict(title=""),
    )

    # ── Profesi ──────────────────────────────────────────────────────────
    prof = df_uniq["Kategori Profesi"].value_counts().reset_index()
    prof.columns = ["Profesi", "Peserta"]
    fig_prof = px.bar(
        prof, x="Peserta", y="Profesi", orientation="h",
        title="Profesi Peserta",
        color="Peserta", color_continuous_scale=WARM_SCALE,
        text="Peserta",
    )
    fig_prof.update_traces(textposition="outside", marker_line_width=0)
    fig_prof.update_layout(
        **CHART_LAYOUT,
        coloraxis_showscale=False,
        yaxis=dict(categoryorder="total ascending", title=""),
        xaxis=dict(title=""),
    )

    # ── Kota ─────────────────────────────────────────────────────────────
    kota = df_uniq["Kota"].value_counts().head(15).reset_index()
    kota.columns = ["Kota", "Peserta"]
    fig_kota = px.bar(
        kota, x="Peserta", y="Kota", orientation="h",
        title="Top 15 Kota Asal Peserta",
        color="Peserta", color_continuous_scale=BLUE_SCALE,
        text="Peserta",
    )
    fig_kota.update_traces(textposition="outside", marker_line_width=0)
    fig_kota.update_layout(
        **CHART_LAYOUT,
        coloraxis_showscale=False,
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
        color="Peserta", color_continuous_scale=["#D4F0FF", "#ADD3FA", "#7BBEF0"],
        text="Peserta",
    )
    fig_har.update_traces(textposition="outside", marker_line_width=0)
    fig_har.update_layout(
        **CHART_LAYOUT,
        coloraxis_showscale=False,
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
            color="Peserta", color_continuous_scale=PEACH_SCALE,
            text="Peserta",
        )
        fig_kel.update_traces(textposition="outside", marker_line_width=0)
        fig_kel.update_layout(
            **CHART_LAYOUT,
            coloraxis_showscale=False,
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
        labels=wil["Wilayah"],
        values=wil["Peserta"],
        hole=0.55,
        marker_colors=["#ADD3FA", "#FAEFC3", "#FAD4C8", "#B9EBFA"],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} peserta (%{percent})<extra></extra>",
        direction="clockwise",
        sort=False,
    ))
    fig_wil.update_layout(
        **CHART_LAYOUT,
        title="Distribusi Wilayah",
        showlegend=False,
        annotations=[dict(
            text=f"<b>{total_wil}</b><br><span style='font-size:11px;color:#888'>Peserta</span>",
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
        x=freq_df["Frekuensi"],
        y=freq_df["Peserta"],
        marker_color="#ADD3FA",
        text=freq_df["Peserta"],
        textposition="outside",
    ))
    fig_freq.update_layout(
        **CHART_LAYOUT,
        title="Frekuensi Kehadiran Peserta",
        showlegend=False,
        xaxis=dict(categoryorder="array", categoryarray=FREQ_ORDER, title=""),
        yaxis=dict(title=""),
    )

    # ── Table per event ──────────────────────────────────────────────────
    tbl = (
        df.groupby("Event Label", sort=False)
        .agg(
            Kategori=("Kategori", "first"),
            Peserta=("Nama", "nunique"),
            Perempuan=("Gender", lambda x: (x == "Female").sum()),
            Laki_laki=("Gender", lambda x: (x == "Male").sum()),
            Rata_usia=("Usia", lambda x: round(x.mean(), 1)),
        )
        .reset_index()
        .sort_values("Peserta", ascending=False)
        .rename(columns={
            "Event Label": "Nama Event",
            "Laki_laki": "Laki-laki",
            "Rata_usia": "Rata-rata Usia",
        })
    )

    table = dash_table.DataTable(
        data=tbl.to_dict("records"),
        columns=[{"name": c, "id": c} for c in tbl.columns],
        sort_action="native",
        page_size=8,
        style_table={"borderRadius": "8px", "overflow": "hidden",
                     "boxShadow": "0 1px 4px rgba(0,0,0,0.06)"},
        style_header={
            "backgroundColor": "#ADD3FA",
            "fontWeight": "bold",
            "border": "none",
            "padding": "10px 14px",
            "fontSize": "13px",
        },
        style_cell={
            "padding": "9px 14px",
            "fontFamily": "Segoe UI, sans-serif",
            "fontSize": "13px",
            "border": "1px solid #eef2f7",
            "textAlign": "left",
            "whiteSpace": "normal",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f5faff"},
            {"if": {"column_id": "Peserta"}, "fontWeight": "bold", "color": "#3a8fd9"},
        ],
    )

    # ── Rekap Kehadiran Peserta ─────────────────────────────────────────
    peserta_tbl = (
        df.groupby("Nama", sort=False)
        .agg(
            Domisili=("Kota", 'first'),
            Profesi=("Kategori Profesi", 'first'),
            Kategori_Terbanyak=("Kategori",   lambda x: x.value_counts().idxmax()),
            No_telp=("No WhatsApp", 'first'),
            Total_Kehadiran=("Nama",           "count"),
        )
        .reset_index()
        .sort_values("Total_Kehadiran", ascending=False)
        .rename(columns={
            "Nama":              "Nama Peserta",
            "Domisili":          "Kota Domisili",
            "Profesi":           "Kategori Profesi",
            "Kategori_Terbanyak": "Kategori Terbanyak",
            "No_telp":           "No WhatsApp",
            "Total_Kehadiran":   "Total Kehadiran",
        })
    )

    tbl_peserta = dash_table.DataTable(
        data=peserta_tbl.to_dict("records"),
        columns=[{"name": c, "id": c} for c in peserta_tbl.columns],
        sort_action="native",
        filter_action="native",
        page_size=6,
        style_table={"borderRadius": "8px", "overflow": "hidden",
                     "boxShadow": "0 1px 4px rgba(0,0,0,0.06)"},
        style_header={
            "backgroundColor": "#B9EBFA",
            "fontWeight": "bold",
            "border": "none",
            "padding": "10px 14px",
            "fontSize": "13px",
        },
        style_cell={
            "padding": "9px 14px",
            "fontFamily": "Segoe UI, sans-serif",
            "fontSize": "13px",
            "border": "1px solid #eef2f7",
            "textAlign": "left",
            "whiteSpace": "normal",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f5faff"},
            {"if": {"column_id": "Total Kehadiran"}, "fontWeight": "bold", "color": "#3a8fd9"},
        ],
    )

    return kpis, fig_loc, fig_gen, fig_age, fig_prof, fig_kota, fig_har, fig_kel, fig_wil, fig_freq, table, tbl_peserta

# ── Riwayat Kehadiran per Peserta ─────────────────────────────────────────
@app.callback(
    Output("table-riwayat", "children"),
    Input("dd-search-peserta", "value"),
)
def show_riwayat(nama):
    if not nama:
        return html.P("Pilih nama peserta untuk melihat riwayat kehadiran.",
                      className="text-muted small")
    rows = df_raw[df_raw["Nama"] == nama][["Nama Event", "Lokasi Event", "Kategori"]].copy()
    # rows = df_raw[df_raw["Nama"].str.contains(nama, case=False, na=False)][["Nama Event", "Lokasi Event", "Kategori"]].copy()
    rows = rows.rename(columns={"Lokasi Event": "Lokasi"})
    return dash_table.DataTable(
        data=rows.to_dict("records"),
        columns=[{"name": c, "id": c} for c in rows.columns],
        style_table={"borderRadius": "8px", "overflow": "hidden"},
        style_header={"backgroundColor": "#ADD3FA", "fontWeight": "bold",
                      "border": "none", "padding": "10px 14px", "fontSize": "13px"},
        style_cell={"padding": "9px 14px", "fontFamily": "Segoe UI, sans-serif",
                    "fontSize": "13px", "border": "1px solid #eef2f7", "textAlign": "left"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f5faff"},
        ],
    )

if __name__ == "__main__":
    app.run(debug=True)