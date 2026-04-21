import os
import pandas as pd
from config import DATA_PATH, WP_PATH

# ── Load raw data ──────────────────────────────────────────────────────────
df_raw = pd.read_excel(DATA_PATH)
df_wp_raw = (
    pd.read_excel(WP_PATH)
    if os.path.exists(WP_PATH)
    else pd.DataFrame(columns=[
        "Email", "Nama", "No WhatsApp", "Kota - Provinsi", "Tempat Kegiatan",
        "Tanggal", "Sesi", "Jumlah Sesi", "Tahun", "Bulan", "Kategori",
        "Nama Event", "Lokasi Event", "Gender", "Kota", "Provinsi",
        "District", "Country",
    ])
)

# ── Build a combined event label (distinguishes same-name events at different locations)
df_raw["Event Label"] = df_raw.apply(
    lambda r: r["Nama Event"] + " - " + r["Lokasi Event"]
    if isinstance(r["Lokasi Event"], str) and r["Lokasi Event"].strip() not in ("", "-")
    else r["Nama Event"],
    axis=1,
)

# ── Frequency bucket per Nama (computed on full dataset — person property) ─
_freq_map = df_raw["Nama"].value_counts()
df_raw["_freq"] = df_raw["Nama"].map(_freq_map)
df_raw["Frekuensi Kehadiran"] = df_raw["_freq"].apply(
    lambda x: ">5 Kali" if x > 5 else (f"{x} Kali" if x >= 2 else "1 Kali")
)
df_raw = df_raw.drop(columns=["_freq"])
