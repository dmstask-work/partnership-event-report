import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# ── DB engine (lazy singleton) ─────────────────────────────────────────────
_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        url = os.environ["DATABASE_URL"]
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine

# ── Column rename maps (DB snake_case → dashboard display names) ───────────
_HADIR_REVERSE = {
    "email": "Email", "nama": "Nama", "no_whatsapp": "No WhatsApp",
    "kota_provinsi": "Kota - Provinsi", "tempat_kegiatan": "Tempat Kegiatan",
    "tanggal": "Tanggal", "sesi": "Sesi", "jumlah_sesi": "Jumlah Sesi",
    "tahun": "Tahun", "bulan": "Bulan", "kategori": "Kategori",
    "nama_event": "Nama Event", "lokasi_event": "Lokasi Event",
    "gender": "Gender", "kota": "Kota", "provinsi": "Provinsi",
    "usia": "Usia", "kelompok_usia": "Kelompok Usia",
    "profesi_asli": "Profesi (Asli)", "kategori_profesi": "Kategori Profesi",
    "harapan_asli": "Harapan (Asli)", "topik_harapan": "Topik Harapan",
    "keluhan_asli": "Keluhan (Asli)", "topik_keluhan": "Topik Keluhan",
    "wilayah": "Wilayah", "workshop_yang_diikuti": "Workshop yang Diikuti",
}

_WP_REVERSE = {
    "email": "Email", "nama": "Nama", "no_whatsapp": "No WhatsApp",
    "kota_provinsi": "Kota - Provinsi", "tempat_kegiatan": "Tempat Kegiatan",
    "tanggal": "Tanggal", "sesi": "Sesi", "jumlah_sesi": "Jumlah Sesi",
    "tahun": "Tahun", "bulan": "Bulan", "kategori": "Kategori",
    "nama_event": "Nama Event", "lokasi_event": "Lokasi Event",
    "gender": "Gender", "kota": "Kota", "provinsi": "Provinsi",
    "district": "District", "country": "Country",
}

# ── Load data from Supabase ────────────────────────────────────────────────
_HADIR_DISPLAY_COLS = list(_HADIR_REVERSE.values())
_WP_DISPLAY_COLS    = list(_WP_REVERSE.values())

try:
    _eng = _get_engine()
    df_raw = pd.read_sql(
        "SELECT email, nama, no_whatsapp, kota_provinsi, tempat_kegiatan, "
        "tanggal, sesi, jumlah_sesi, tahun, bulan, kategori, nama_event, "
        "lokasi_event, gender, kota, provinsi, usia, kelompok_usia, "
        "profesi_asli, kategori_profesi, harapan_asli, topik_harapan, "
        "keluhan_asli, topik_keluhan, wilayah, workshop_yang_diikuti "
        "FROM hadir_data",
        _eng,
    ).rename(columns=_HADIR_REVERSE)

    df_wp_raw = pd.read_sql(
        "SELECT email, nama, no_whatsapp, kota_provinsi, tempat_kegiatan, "
        "tanggal, sesi, jumlah_sesi, tahun, bulan, kategori, nama_event, "
        "lokasi_event, gender, kota, provinsi, district, country "
        "FROM wp_data",
        _eng,
    ).rename(columns=_WP_REVERSE)

except Exception as exc:
    import warnings
    warnings.warn(f"[data.py] Could not load from Supabase: {exc}. Using empty DataFrames.")
    df_raw    = pd.DataFrame(columns=_HADIR_DISPLAY_COLS)
    df_wp_raw = pd.DataFrame(columns=_WP_DISPLAY_COLS)

# ── Build a combined event label (distinguishes same-name events at different locations)
if not df_raw.empty:
    df_raw["Event Label"] = df_raw.apply(
        lambda r: r["Nama Event"] + " - " + r["Lokasi Event"]
        if isinstance(r["Lokasi Event"], str) and r["Lokasi Event"].strip() not in ("", "-")
        else r["Nama Event"],
        axis=1,
    )

    # ── Frequency bucket per Nama (computed on full dataset — person property)
    _freq_map = df_raw["Nama"].value_counts()
    df_raw["_freq"] = df_raw["Nama"].map(_freq_map)
    df_raw["Frekuensi Kehadiran"] = df_raw["_freq"].apply(
        lambda x: ">5 Kali" if x > 5 else (f"{x} Kali" if x >= 2 else "1 Kali")
    )
    df_raw = df_raw.drop(columns=["_freq"])

