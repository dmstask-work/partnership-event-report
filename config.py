import os

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data_clean", "data_merged.xlsx")
WP_PATH   = os.path.join(BASE_DIR, "data_clean", "output_wp.xlsx")

# ── Ordering ───────────────────────────────────────────────────────────────
FREQ_ORDER    = ["1 Kali", "2 Kali", "3 Kali", "4 Kali", "5 Kali", ">5 Kali"]
WILAYAH_ORDER = ["Jabodetabek", "Jawa Tengah", "Jawa Timur", "Bali"]

# ── Colour palettes ────────────────────────────────────────────────────────
PALETTE = [
    "#ADD3FA", "#B9EBFA", "#FAFAD5", "#FAEFC3", "#FADFAA", "#FAD4C8",
    "#C5E4FB", "#D4F5FB", "#FAFAEC", "#FAF2D8", "#FAE8BE", "#FAD9D0",
]
BLUE_SCALE  = ["#D4F0FF", "#ADD3FA", "#7AB8F0"]
WARM_SCALE  = ["#FAFAD5", "#FAEFC3", "#FAD4C8"]
PEACH_SCALE = ["#FAFAD5", "#FAD4C8", "#FADFAA"]

# ── Reusable component styles ──────────────────────────────────────────────
CARD_STYLE = {"borderRadius": "10px", "boxShadow": "0 2px 8px rgba(0,0,0,0.07)"}
SECTION_STYLE = {
    "background": "white",
    "borderRadius": "10px",
    "padding": "16px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.06)",
}
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
