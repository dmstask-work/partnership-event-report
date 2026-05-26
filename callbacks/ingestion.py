"""
callbacks/ingestion.py
======================
Two callbacks that power the Data Ingestion tab.

  Callback 1 — Upload → ETL → DataTable preview
    Decodes the Base64 payload from dcc.Upload, runs the in-memory ETL
    transform for the selected data type, and populates the editable
    DataTable so the user can review / correct before syncing.

  Callback 2 — Sync button → Supabase (PostgreSQL)
    Reads the *current* (possibly user-edited) DataTable state, rebuilds
    a Pandas DataFrame, and appends it to the target table via SQLAlchemy.

Environment variable required:
    DATABASE_URL  — Supabase PostgreSQL connection string, e.g.:
                    postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
                    or the "postgres://" variant (auto-converted below).
"""

import base64
import io
import os
import time

import numpy  as np
import pandas as pd
from dash import Input, Output, State, html, no_update
import dash_bootstrap_components as dbc
from sqlalchemy import create_engine

from dash_instance import app
from config import KNOWN_HARAPAN, KNOWN_KELUHAN

# ══════════════════════════════════════════════════════════════════════════════
# TARGET-SCHEMA COLUMN MAPS  (raw Excel header → PostgreSQL snake_case column)
# ══════════════════════════════════════════════════════════════════════════════

HADIR_COLUMN_MAP: dict[str, str] = {
    "Email":                 "email",
    "Nama":                  "nama",
    "No WhatsApp":           "no_whatsapp",
    "Kota - Provinsi":       "kota_provinsi",
    "Tempat Kegiatan":       "tempat_kegiatan",
    "Tanggal":               "tanggal",
    "Sesi":                  "sesi",
    "Jumlah Sesi":           "jumlah_sesi",
    "Tahun":                 "tahun",
    "Bulan":                 "bulan",
    "Kategori":              "kategori",
    "Nama Event":            "nama_event",
    "Lokasi Event":          "lokasi_event",
    "Gender":                "gender",
    "Kota":                  "kota",
    "Provinsi":              "provinsi",
    "Usia":                  "usia",
    "Kelompok Usia":         "kelompok_usia",
    "Profesi (Asli)":        "profesi_asli",
    "Kategori Profesi":      "kategori_profesi",
    "Harapan (Asli)":        "harapan_asli",
    "Topik Harapan":         "topik_harapan",
    "Keluhan (Asli)":        "keluhan_asli",
    "Topik Keluhan":         "topik_keluhan",
    "Wilayah":               "wilayah",
    "Workshop yang Diikuti": "workshop_yang_diikuti",
}

WP_COLUMN_MAP: dict[str, str] = {
    "Email":           "email",
    "Nama":            "nama",
    "No WhatsApp":     "no_whatsapp",
    "Kota - Provinsi": "kota_provinsi",
    "Tempat Kegiatan": "tempat_kegiatan",
    "Tanggal":         "tanggal",
    "Sesi":            "sesi",
    "Jumlah Sesi":     "jumlah_sesi",
    "Tahun":           "tahun",
    "Bulan":           "bulan",
    "Kategori":        "kategori",
    "Nama Event":      "nama_event",
    "Lokasi Event":    "lokasi_event",
    "Gender":          "gender",
    "Kota":            "kota",
    "Provinsi":        "provinsi",
    "District":        "district",
    "Country":         "country",
}

# Sentinel strings treated as NULL / missing
_NULLISH = {"-", "", "n/a", "na", "null", "none"}

# Integer columns per table (coerced after ETL)
_HADIR_INT_COLS = ["tahun", "bulan", "usia", "jumlah_sesi"]
_WP_INT_COLS    = ["tahun", "bulan", "jumlah_sesi"]

# NOT NULL columns and their safe Postgres defaults
HADIR_NOT_NULL_DEFAULTS: dict[str, object] = {
    "nama":            "-",
    "no_whatsapp":     "-",
    "tempat_kegiatan": "-",
    "tanggal":         "1900-01-01",
    "sesi":            "-",
    "jumlah_sesi":     1,
    "tahun":           0,
    "bulan":           0,
    "kategori":        "-",
    "nama_event":      "-",
    "lokasi_event":    "-",
    "wilayah":         "-",
}

WP_NOT_NULL_DEFAULTS: dict[str, object] = {
    "nama": "-",
}

# ── Fuzzy alias maps (lower-stripped raw header → canonical Excel header) ──────
HADIR_ALIAS_MAP: dict[str, str] = {
    "e-mail":                  "Email",
    "email address":           "Email",
    "name":                    "Nama",
    "nama lengkap":            "Nama",
    "no. whatsapp":            "No WhatsApp",
    "no.whatsapp":             "No WhatsApp",
    "no hp":                   "No WhatsApp",
    "no. hp":                  "No WhatsApp",
    "phone":                   "No WhatsApp",
    "kota/provinsi":           "Kota - Provinsi",
    "kota provinsi":           "Kota - Provinsi",
    "kota - provinsi":         "Kota - Provinsi",
    "tempat":                  "Tempat Kegiatan",
    "date":                    "Tanggal",
    "tgl":                     "Tanggal",
    "session":                 "Sesi",
    "sesi ke":                 "Sesi",
    "total sesi":              "Jumlah Sesi",
    "year":                    "Tahun",
    "month":                   "Bulan",
    "kategori event":          "Kategori",
    "event":                   "Nama Event",
    "nama kegiatan":           "Nama Event",
    "venue":                   "Lokasi Event",
    "sex":                     "Gender",
    "jenis kelamin":           "Gender",
    "city":                    "Kota",
    "province":                "Provinsi",
    "age":                     "Usia",
    "umur":                    "Usia",
    "age group":               "Kelompok Usia",
    "kelompok umur":           "Kelompok Usia",
    "pekerjaan":               "Profesi (Asli)",
    "kategori profesi":        "Kategori Profesi",
    "harapan":                 "Harapan (Asli)",
    "keluhan":                 "Keluhan (Asli)",
    "topik harapan":           "Topik Harapan",
    "topik keluhan":           "Topik Keluhan",
    "region":                  "Wilayah",
    "area":                    "Wilayah",
    "workshop":                "Workshop yang Diikuti",
    "workshop diikuti":        "Workshop yang Diikuti",
}

WP_ALIAS_MAP: dict[str, str] = {
    "e-mail":          "Email",
    "email address":   "Email",
    "name":            "Nama",
    "nama lengkap":    "Nama",
    "no. whatsapp":    "No WhatsApp",
    "no hp":           "No WhatsApp",
    "phone":           "No WhatsApp",
    "kota/provinsi":   "Kota - Provinsi",
    "kota provinsi":   "Kota - Provinsi",
    "date":            "Tanggal",
    "tgl":             "Tanggal",
    "session":         "Sesi",
    "total sesi":      "Jumlah Sesi",
    "year":            "Tahun",
    "month":           "Bulan",
    "kategori event":  "Kategori",
    "event":           "Nama Event",
    "nama kegiatan":   "Nama Event",
    "venue":           "Lokasi Event",
    "sex":             "Gender",
    "jenis kelamin":   "Gender",
    "city":            "Kota",
    "province":        "Provinsi",
    "district":        "District",
    "country":         "Country",
}


# ══════════════════════════════════════════════════════════════════════════════
# SQLAlchemy engine — lazily initialised and module-level cached
# ══════════════════════════════════════════════════════════════════════════════

_engine = None


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise EnvironmentError(
            "DATABASE_URL is not set. Add it to your .env file or "
            "the Render dashboard environment variables."
        )
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine


# ══════════════════════════════════════════════════════════════════════════════
# ETL HELPER FUNCTIONS  (ported 1-to-1 from transform.ipynb)
# ══════════════════════════════════════════════════════════════════════════════

# ── H1 · No WhatsApp normalisation ───────────────────────────────────────────
def _fmt_wa(s) -> str:
    """08x / +628x / 628x -> '628xxxxxxxxx'.  Returns '-' if blank."""
    if pd.isna(s) or str(s).strip() == "":
        return "-"
    s = str(s).strip().replace(" ", "").replace("-", "").replace("+", "")
    s = s.split(".")[0]
    if s.startswith("0"):
        return "62" + s[1:]
    return s if s.startswith("62") else "62" + s


# ── H2 · Age from DOB (DD/MM/YYYY) ──────────────────────────────────────────
_TODAY = pd.Timestamp.now()


def _calc_age(s) -> object:
    """Compute integer age from a DD/MM/YYYY birth-date string."""
    if pd.isna(s) or str(s).strip() == "":
        return pd.NA
    txt = str(s).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            dob = pd.to_datetime(txt, format=fmt)
            return int(
                _TODAY.year - dob.year
                - ((_TODAY.month, _TODAY.day) < (dob.month, dob.day))
            )
        except Exception:
            pass
    try:
        return int(float(txt))
    except Exception:
        return pd.NA


# ── H3 · City -> Province lookup ─────────────────────────────────────────────
_CITY_PROV: dict[str, str] = {
    # Jawa Timur
    "surabaya":"Jawa Timur","sidoarjo":"Jawa Timur","malang":"Jawa Timur",
    "gresik":"Jawa Timur","kediri":"Jawa Timur","madiun":"Jawa Timur",
    "blitar":"Jawa Timur","mojokerto":"Jawa Timur","jombang":"Jawa Timur",
    "lamongan":"Jawa Timur","pasuruan":"Jawa Timur","probolinggo":"Jawa Timur",
    "banyuwangi":"Jawa Timur","lumajang":"Jawa Timur","jember":"Jawa Timur",
    "tulungagung":"Jawa Timur","bojonegoro":"Jawa Timur","nganjuk":"Jawa Timur",
    "ponorogo":"Jawa Timur","pacitan":"Jawa Timur","magetan":"Jawa Timur",
    "ngawi":"Jawa Timur","tuban":"Jawa Timur","situbondo":"Jawa Timur",
    "bondowoso":"Jawa Timur","sumenep":"Jawa Timur","pamekasan":"Jawa Timur",
    "sampang":"Jawa Timur","bangkalan":"Jawa Timur","trenggalek":"Jawa Timur",
    # Jawa Tengah
    "semarang":"Jawa Tengah","solo":"Jawa Tengah","surakarta":"Jawa Tengah",
    "salatiga":"Jawa Tengah","pekalongan":"Jawa Tengah","magelang":"Jawa Tengah",
    "tegal":"Jawa Tengah","purwokerto":"Jawa Tengah","cilacap":"Jawa Tengah",
    "kebumen":"Jawa Tengah","klaten":"Jawa Tengah","wonogiri":"Jawa Tengah",
    "boyolali":"Jawa Tengah","purworejo":"Jawa Tengah","banyumas":"Jawa Tengah",
    "demak":"Jawa Tengah","kudus":"Jawa Tengah","jepara":"Jawa Tengah",
    "rembang":"Jawa Tengah","blora":"Jawa Tengah","grobogan":"Jawa Tengah",
    "sragen":"Jawa Tengah","karanganyar":"Jawa Tengah","brebes":"Jawa Tengah",
    "batang":"Jawa Tengah","kendal":"Jawa Tengah","temanggung":"Jawa Tengah",
    "wonosobo":"Jawa Tengah","banjarnegara":"Jawa Tengah","purbalingga":"Jawa Tengah",
    "pemalang":"Jawa Tengah",
    # DI Yogyakarta
    "yogyakarta":"DI Yogyakarta","jogja":"DI Yogyakarta","bantul":"DI Yogyakarta",
    "sleman":"DI Yogyakarta","gunungkidul":"DI Yogyakarta","kulonprogo":"DI Yogyakarta",
    # Jawa Barat
    "tasikmalaya":"Jawa Barat","bandung":"Jawa Barat","bogor":"Jawa Barat",
    "bekasi":"Jawa Barat","depok":"Jawa Barat","cimahi":"Jawa Barat",
    "cirebon":"Jawa Barat","sukabumi":"Jawa Barat","garut":"Jawa Barat",
    "karawang":"Jawa Barat","subang":"Jawa Barat","ciamis":"Jawa Barat",
    "sumedang":"Jawa Barat","majalengka":"Jawa Barat","kuningan":"Jawa Barat",
    "indramayu":"Jawa Barat","purwakarta":"Jawa Barat",
    # Jabodetabek
    "jakarta":"Jabodetabek","jakarta selatan":"Jabodetabek",
    "jakarta utara":"Jabodetabek","jakarta barat":"Jabodetabek",
    "jakarta timur":"Jabodetabek","jakarta pusat":"Jabodetabek",
    "tangerang":"Jabodetabek","tangerang selatan":"Jabodetabek",
    "serpong":"Jabodetabek","bsd":"Jabodetabek",
    # Bali
    "bali":"Bali","denpasar":"Bali","badung":"Bali","gianyar":"Bali",
    "tabanan":"Bali","buleleng":"Bali","karangasem":"Bali",
    "klungkung":"Bali","bangli":"Bali","jembrana":"Bali",
    "ubud":"Bali","seminyak":"Bali","canggu":"Bali","sanur":"Bali",
    # NTB
    "mataram":"Nusa Tenggara Barat","lombok":"Nusa Tenggara Barat",
    "sumbawa":"Nusa Tenggara Barat","bima":"Nusa Tenggara Barat",
    # Others
    "medan":"Sumatera Utara","palembang":"Sumatera Selatan",
    "padang":"Sumatera Barat","pekanbaru":"Riau","batam":"Kepulauan Riau",
    "bandar lampung":"Lampung","balikpapan":"Kalimantan Timur",
    "samarinda":"Kalimantan Timur","banjarmasin":"Kalimantan Selatan",
    "pontianak":"Kalimantan Barat","makassar":"Sulawesi Selatan",
    "manado":"Sulawesi Utara",
}

_TEMPAT_WILAYAH: dict[str, str] = {
    "surabaya":"Jawa Timur","sidoarjo":"Jawa Timur","malang":"Jawa Timur",
    "gresik":"Jawa Timur",
    "semarang":"Jawa Tengah","solo":"Jawa Tengah","surakarta":"Jawa Tengah",
    "jogja":"DI Yogyakarta","yogyakarta":"DI Yogyakarta",
    "jakarta":"Jabodetabek","jabodetabek":"Jabodetabek",
    "tangerang":"Jabodetabek","bekasi":"Jabodetabek","bogor":"Jabodetabek",
    "depok":"Jabodetabek","serpong":"Jabodetabek","bsd":"Jabodetabek",
    "bali":"Bali","denpasar":"Bali",
}


def _get_province(kota: str) -> str:
    if pd.isna(kota) or str(kota).strip() == "":
        return ""
    key = str(kota).strip().lower()
    if key in _CITY_PROV:
        return _CITY_PROV[key]
    for prefix in ("kota ", "kabupaten ", "kab. ", "kab "):
        if key.startswith(prefix):
            stripped = key[len(prefix):]
            if stripped in _CITY_PROV:
                return _CITY_PROV[stripped]
    for k, v in _CITY_PROV.items():
        if k in key:
            return v
    return ""


def _parse_domisili(val) -> tuple:
    """Parse raw Domisili cell -> (kota, provinsi, kota_provinsi)."""
    if pd.isna(val) or str(val).strip() == "":
        return ("", "", "")
    val = str(val).strip()
    if " - " in val:
        kota, hint = [p.strip() for p in val.split(" - ", 1)]
        prov = _get_province(kota) or hint
    elif "," in val:
        kota, hint = [p.strip() for p in val.split(",", 1)]
        prov = _get_province(kota) or hint
    else:
        kota = val
        prov = _get_province(kota)
    kota_prov = f"{kota}, {prov}" if prov else kota
    return (kota, prov, kota_prov)


# ── H4 · Kategori Profesi keyword mapping ────────────────────────────────────
_KW_INSTRUKTUR = [
    "yoga","pilates","senam","instruktur","instructor","pelatih","trainer",
    "coach","teacher","pengajar","aerobic","barre","praktisi","olahraga",
    "olah raga","sport","gym","kebugaran","fitness",
]
_KW_NAKES = [
    "dokter","perawat","bidan","fisioterapis","apoteker","akupunkturis",
    "hidroterapis","hydroterapis","hipnoterapis","hypnoterapis","terapis",
    "nurse","therapist","medis","klinik",
]
_KW_IRT       = ["ibu rumah tangga","irt","homemaker","home maker"]
_KW_WIRAUSAHA = ["wiraswasta","wirausaha","pengusaha","bisnis","owner"]
_KW_PELAJAR   = ["mahasiswa","siswa","pelajar","student"]
_KW_PENDIDIK  = ["dosen"]
_KW_KARYAWAN  = [
    "karyawan","karyawati","asn","pns","pegawai","staff","staf","akuntan",
    "accounting","direktur","manager","swasta","freelancer","sekretaris",
]


def _map_kategori_profesi(s) -> str:
    if pd.isna(s) or str(s).strip() == "":
        return "Tidak Diketahui"
    sl = str(s).strip().lower()
    if any(k in sl for k in _KW_IRT) and not any(k in sl for k in _KW_INSTRUKTUR):
        return "Ibu Rumah Tangga"
    if any(k in sl for k in _KW_NAKES):
        return "Tenaga Kesehatan"
    if any(k in sl for k in _KW_INSTRUKTUR):
        return "Instruktur Kebugaran"
    if "guru" in sl or any(k in sl for k in _KW_PENDIDIK):
        return "Tenaga Pendidik"
    if any(k in sl for k in _KW_PELAJAR):
        return "Pelajar / Mahasiswa"
    if any(k in sl for k in _KW_WIRAUSAHA):
        return "Wirausaha"
    if any(k in sl for k in _KW_KARYAWAN):
        return "Karyawan / Pegawai"
    return "Tidak Diketahui"


# ── H5 · Topik Harapan keyword mapping ───────────────────────────────────────
_HARAPAN_TOPICS: dict[str, list] = {
    "Menambah Pengetahuan & Wawasan": [
        "pengetahuan","wawasan","belajar","memahami","ilmu","mengerti",
        "mengetahui","informasi","mengenal","paham",
    ],
    "Penanganan Cedera & Keluhan": [
        "terapi","therapy","hnp","saraf","nyeri","cedera","penanganan",
        "sembuh","mengobati","menterapi","lbp","keluhan","memperbaiki",
        "perbaiki","mengatasi","meredakan","pemulihan",
    ],
    "Anatomi, Gerak & Postur Tubuh": [
        "postur","gerakan","anatomi","gerak","tulang belakang","shoulder",
        "leher","lumbar","punggung","tubuh","bergerak","fisik",
    ],
    "Pengembangan Profesi & Berbagi Ilmu": [
        "kelas","peserta","mengajar","profesi","berbagi","instruktur",
        "penderita","membantu orang","klien","murid",
    ],
    "Penerapan untuk Diri Sendiri & Keluarga": [
        "mandiri","diri sendiri","keluarga","pribadi","sendiri","sesama",
    ],
}


def _map_topik_harapan(s) -> str:
    if pd.isna(s) or str(s).strip() == "":
        return "Tidak Ada Respons"
    sl = str(s).strip().lower()
    matched = [t for t, kws in _HARAPAN_TOPICS.items() if any(k in sl for k in kws)]
    return ", ".join(matched) if matched else "Lainnya"


# ── H6 · Topik Keluhan keyword mapping ───────────────────────────────────────
_NO_COMPLAINT = {"-","*","nan","tidak ada","tidak","tdk ada","no","none","n/a"}


def _map_topik_keluhan(s) -> str:
    if pd.isna(s) or str(s).strip() == "":
        return "Tidak Ada Respons"
    sl = str(s).strip().lower()
    if sl in _NO_COMPLAINT or "tidak ada" in sl or "tdk ada" in sl:
        return "Tidak Ada Keluhan"
    if "skoliosis" in sl:
        return "Skoliosis"
    if any(k in sl for k in [
        "hnp","saraf","kejepit","punggung","lumbar",
        "pinggang","hernia","tulang belakang","leher","cervical","lumbal",
    ]):
        return "Saraf Kejepit & Nyeri Punggung"
    if any(k in sl for k in [
        "nyeri","otot","sendi","bahu","shoulder","lelah","kaku","pegal","ngilu","encok",
    ]):
        return "Nyeri Sendi & Otot"
    if any(k in sl for k in ["diabetes","metabolik","kolesterol","hipertensi","asam urat"]):
        return "Penyakit Metabolik"
    if any(k in sl for k in ["sembuh","ingin sembuh"]):
        return "Ingin Sembuh / Terapi"
    return "Lainnya"


# ── H7 · Gender prediction — vectorized name heuristic ───────────────────────
_FEMALE_NAMES = {
    "shinta","velia","heny","leny","yuli","ayda","silvia","lidya","elisa",
    "erna","fortunata","anisyah","fatima","siti","nur","dewi","rini","maya",
    "widya","indah","desi","novi","lilis","nita","linda","mira","dian","nina",
    "sinta","retno","endah","laras","wulan","ratna","niken","eni","nanik",
    "ira","laila","suci","anis","iis","irma","nani","rosi","windi","cici",
    "fifi","tuti","chandrawati","artika","jillian","lusiyani","yulita",
    "evi","tika","anna","diana","sonya","anisa","agnes","grace","helen",
    "irene","jessica","karen","lily","mia","natalia","olivia","patricia",
    "rachel","rebecca","sarah","sandra","tina","vera","vivian","wendy",
    "yulia","zara","lestari","astuti","wahyuni","setyawati","handayani",
    "kusuma","amelia","aisyah","hasanah","rahmawati","fitriani","nurul",
    "rohma","halimah","khadijah","latifah","maryam","nurdiana","susanti",
    "kurniawati","lies","theresia","stefania","katarina","maria","monika",
    "risma","yuliani","utami","setiawati","murniati","rahayu","sulistyowati",
    "hidayati","anggraeni","apriyani","oktaviani","ningsih","sri","ayu",
    "lia","putri","ani","yani","ning","tari","sari","wati",
    "ratu","kezia","erlina","ika","nisa","citra","safira","bella",
    "bunga","melati","mawar","anggun","cantika","intan","mutiara","permata",
    "andini","sekar","serly","sella","della","wella","nella","lina","rina",
    "dina","mina","vina","gina","hana","ana","ina","yuna","luna",
    "nana","rara","lala","dara","fara","para",
}
_MALE_NAMES = {
    "andi","budi","heri","agus","bambang","dedi","herman","hari","rudi",
    "joko","wahyu","rizal","arief","fajar","yusuf","ridwan","bayu","gilang",
    "faisal","hendra","irwan","iqbal","teguh","sugeng","suryo","susanto",
    "wawan","yanto","eko","lukman","mulyono","mulyadi","toni","doni","roni",
    "adam","alan","alex","aris","erwin","iwan","rian","fahri","farhan",
    "gunawan","guntur","hendri","imam","kurniawan","mahfud","marsudi",
    "mustafa","nandang","nugroho","pandu","panji","prasetyo","prayoga",
    "purwanto","rahmat","rangga","rasyid","reza","rifki","rizky","rokhim",
    "saiful","sakti","salim","santoso","setiawan","sudirman","sudrajat",
    "sugiarto","suharto","suyanto","syaiful","usman","wibowo","widodo",
    "yahya","yoga","yogi","yusron","andika","bagas","candra","dadan",
    "daffa","damar","devan","dimas","elang","evan","ferry","firman","galih",
    "gerry","hafid","hanif","hasan","hasbi","helmi","hidayat","ilham",
    "irham","tomi","soni","aryo","tri","udin","zaenuddin","zainul",
    "wahyudi","satria","putra","prayogo",
}
_FEM_RE  = (
    r"wati$|yani$|tari$|sari$|ningsih$|ningrum$|tika$|nia$|lia$|via$"
    r"|ayu$|putri$|dewi$|ning$|yah$|iah$|rahayu$|utami$|lestari$"
    r"|indah$|anggraeni$|fitriani$|oktaviani$|apriyani$"
)
_MALE_RE = (
    r"anto$|iman$|iwan$|seto$|putra$|yanto$|nanto$|aryo$|prayogo$"
    r"|utomo$|santoso$|purnomo$|agung$|saputro$|nugroho$"
)


def _predict_gender(name_series: pd.Series) -> pd.Series:
    """Vectorized gender prediction. Priority: dict Male > dict Female > suffix."""
    first     = name_series.fillna("").astype(str).str.strip().str.split().str[0].str.lower()
    fem_dict  = first.isin(_FEMALE_NAMES)
    male_dict = first.isin(_MALE_NAMES)
    fem_suf   = first.str.contains(_FEM_RE,  regex=True, na=False)
    male_suf  = first.str.contains(_MALE_RE, regex=True, na=False)
    gender = pd.Series(
        np.select(
            [male_dict, fem_dict, male_suf & ~fem_dict, fem_suf],
            ["Male",    "Female", "Male",               "Female"],
            default="Female",
        ),
        index=name_series.index,
    )
    empty = name_series.isna() | (name_series.astype(str).str.strip() == "")
    gender[empty] = np.nan
    return gender


# ── H8 · Kelompok Usia bucketing ─────────────────────────────────────────────
def _bucket_kelompok_usia(usia_series: pd.Series) -> pd.Series:
    num = pd.to_numeric(usia_series, errors="coerce")
    buckets = pd.cut(
        num,
        bins=  [0,  12,  17,  25,  35,  45,  55,  65, 120],
        labels=["<13","13-17","18-25","26-35","36-45","46-55","56-65","66+"],
        right=True,
    ).astype(object)
    return buckets.where(num.notna(), other="-").fillna("-")


# ── H9 · Nama Event split + kategori derivation ──────────────────────────────
def _split_and_categorise_event(raw_event_series: pd.Series) -> pd.DataFrame:
    """
    Split raw 'Nama Event' (full Google-Forms string) into:
      tempat_kegiatan  — last word (venue city)
      nama_event       — everything except last word
      lokasi_event     — same as tempat_kegiatan
      sesi             — full original string
      kategori         — keyword-based event category
      wilayah          — tempat -> region map
    """
    s     = raw_event_series.fillna("").astype(str).str.strip()
    split = s.str.rsplit(" ", n=1)
    tempat   = split.str[-1]
    nm_ev    = split.str[0]
    sl = s.str.lower()
    kat_conds = [
        sl.str.contains("private",                                     na=False),
        sl.str.contains("special class",                               na=False),
        sl.str.contains(r"training course|ttc",       regex=True,      na=False),
        sl.str.contains(
            r"workshop|terapi|therapy|saraf|scoliosis|metabolic|anatomy|biomechanics",
            regex=True, na=False,
        ),
        sl.str.contains("yoga",   regex=False, na=False),
        sl.str.contains("pilates",regex=False, na=False),
    ]
    kat_choices = [
        "Private Therapy","Special Class","Training Course",
        "Therapy Workshop","Yoga","Pilates",
    ]
    kategori = pd.Series(
        np.select(kat_conds, kat_choices, default="Workshop"),
        index=raw_event_series.index,
    )
    wilayah = tempat.str.lower().map(_TEMPAT_WILAYAH).fillna("-")
    return pd.DataFrame({
        "tempat_kegiatan": tempat,
        "nama_event":      nm_ev,
        "lokasi_event":    tempat,
        "sesi":            s,
        "kategori":        kategori,
        "wilayah":         wilayah,
    }, index=raw_event_series.index)


# ══════════════════════════════════════════════════════════════════════════════
# SHARED UTILITY
# ══════════════════════════════════════════════════════════════════════════════

def _apply_not_null_defaults(
    df: pd.DataFrame,
    not_null_def: dict,
    int_cols: list,
) -> pd.DataFrame:
    """Fill NaN / empty in every NOT NULL column with its safe default."""
    for pg_col, default in not_null_def.items():
        if pg_col not in df.columns:
            continue
        if pg_col in int_cols:
            df[pg_col] = (
                pd.to_numeric(df[pg_col], errors="coerce")
                .fillna(default)
                .astype("Int64")
            )
        else:
            mask = df[pg_col].isna() | (df[pg_col].astype(str).str.strip() == "")
            df.loc[mask, pg_col] = default
    return df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ETL PIPELINE — transform_raw_to_merged()
# ══════════════════════════════════════════════════════════════════════════════

_RAW_FORM_HADIR_COLS = {
    "timestamp", "nomor whatsapp", "domisili",
    "harapan mengikuti workshop", "sesi yang diambil",
}


def _is_raw_hadir_form(df: pd.DataFrame) -> bool:
    """True when the file looks like a raw Google-Forms export."""
    lower_cols = {c.lower().strip() for c in df.columns}
    return bool(lower_cols & _RAW_FORM_HADIR_COLS)


def transform_raw_to_merged(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Raw Google-Forms CSV -> hadir_data PostgreSQL schema.
    Replicates transform.ipynb logic with full defensive column checking.

    Source columns handled:
      Timestamp               -> tanggal, tahun, bulan
      Nomor WhatsApp          -> no_whatsapp  (fmt_wa normalisation)
      Nama Event              -> tempat_kegiatan, nama_event, lokasi_event,
                                  sesi, kategori, wilayah
      Domisili                -> kota, provinsi, kota_provinsi
      Usia (DOB DD/MM/YYYY)   -> usia, kelompok_usia
      Nama                    -> nama, gender
      Profesi                 -> profesi_asli, kategori_profesi
      Harapan Mengikuti ...   -> harapan_asli, topik_harapan
      Keluhan                 -> keluhan_asli, topik_keluhan
      Sesi yang diambil       -> jumlah_sesi
      Workshop yang Diikuti   -> workshop_yang_diikuti
      Email                   -> email
    """
    raw  = df_raw.copy()
    _col = {c.lower().strip(): c for c in raw.columns}

    def _get(key: str, default="-") -> pd.Series:
        orig = _col.get(key.lower().strip())
        if orig is not None:
            return raw[orig]
        return pd.Series(default, index=raw.index, dtype="object")

    out = pd.DataFrame(index=raw.index)

    out["email"] = _get("email", "-")
    out["nama"]  = _get("nama",  "-")

    out["no_whatsapp"] = _get("nomor whatsapp").apply(_fmt_wa)

    ev_split = _split_and_categorise_event(_get("nama event", ""))
    for col in ev_split.columns:
        out[col] = ev_split[col]

    out["jumlah_sesi"] = (
        pd.to_numeric(_get("sesi yang diambil"), errors="coerce")
        .fillna(1).astype("Int64")
    )

    ts = pd.to_datetime(_get("timestamp"), format="%m/%d/%Y", errors="coerce")
    out["tanggal"] = ts.dt.strftime("%Y-%m-%d").fillna("1900-01-01")
    out["tahun"]   = ts.dt.year.astype("Int64")
    out["bulan"]   = ts.dt.month.astype("Int64")

    out["gender"] = _predict_gender(_get("nama", ""))

    dom = _get("domisili").apply(_parse_domisili)
    out["kota"]          = dom.apply(lambda x: x[0]).replace("", "-")
    out["provinsi"]      = dom.apply(lambda x: x[1]).replace("", "-")
    out["kota_provinsi"] = dom.apply(lambda x: x[2]).replace("", "-")

    out["usia"]          = _get("usia").apply(_calc_age)
    out["kelompok_usia"] = _bucket_kelompok_usia(out["usia"])

    profesi_raw             = _get("profesi", "-")
    out["profesi_asli"]     = profesi_raw
    out["kategori_profesi"] = profesi_raw.apply(_map_kategori_profesi)

    harapan_raw          = _get("harapan mengikuti workshop", "")
    out["harapan_asli"]  = harapan_raw
    out["topik_harapan"] = harapan_raw.apply(_map_topik_harapan)

    keluhan_raw          = _get("keluhan", "")
    out["keluhan_asli"]  = keluhan_raw
    out["topik_keluhan"] = keluhan_raw.apply(_map_topik_keluhan)

    out["workshop_yang_diikuti"] = _get("workshop yang diikuti", "-")

    out = _apply_not_null_defaults(out, HADIR_NOT_NULL_DEFAULTS, _HADIR_INT_COLS)

    target_cols = list(HADIR_COLUMN_MAP.values())
    for col in target_cols:
        if col not in out.columns:
            out[col] = HADIR_NOT_NULL_DEFAULTS.get(col, "-")
    return out[[c for c in target_cols if c in out.columns]]


# ══════════════════════════════════════════════════════════════════════════════
# CORE SCHEMA MAPPER — clean_and_map_dataframe()
# Used for already-processed files (e.g. data_merged.xlsx re-upload)
# ══════════════════════════════════════════════════════════════════════════════

def clean_and_map_dataframe(
    df_raw: pd.DataFrame,
    target_type: str,
) -> pd.DataFrame:
    """
    Maps an already-processed (canonical-header) file to the exact PG schema.

    Steps:
      A — fuzzy column rename (case-insensitive + alias map)
      B — date parse, integer coerce, string strip
      C — inject missing columns
      D — fill NaN in NOT NULL columns
      E — select and reorder to target schema
    """
    if target_type == "hadir":
        col_map      = HADIR_COLUMN_MAP
        alias_map    = HADIR_ALIAS_MAP
        int_cols     = _HADIR_INT_COLS
        not_null_def = HADIR_NOT_NULL_DEFAULTS
    else:
        col_map      = WP_COLUMN_MAP
        alias_map    = WP_ALIAS_MAP
        int_cols     = _WP_INT_COLS
        not_null_def = WP_NOT_NULL_DEFAULTS

    df = df_raw.copy()

    canonical_lower = {k.lower().strip(): k for k in col_map}
    alias_lower     = {k.lower().strip(): v for k, v in alias_map.items()}

    rename_map: dict[str, str] = {}
    for raw_col in df.columns:
        key = raw_col.lower().strip()
        if key in canonical_lower:
            rename_map[raw_col] = col_map[canonical_lower[key]]
        elif key in alias_lower:
            excel_name = alias_lower[key]
            if excel_name in col_map:
                rename_map[raw_col] = col_map[excel_name]

    df = df.rename(columns=rename_map)
    df = df.replace({s: pd.NA for s in _NULLISH})

    if "tanggal" in df.columns:
        df["tanggal"] = (
            pd.to_datetime(df["tanggal"], errors="coerce").dt.strftime("%Y-%m-%d")
        )

    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(
        lambda s: s.str.strip() if hasattr(s, "str") else s
    )

    for pg_col in col_map.values():
        if pg_col not in df.columns:
            df[pg_col] = not_null_def.get(pg_col, pd.NA)

    df = _apply_not_null_defaults(df, not_null_def, int_cols)
    target_cols = list(col_map.values())
    return df[[c for c in target_cols if c in df.columns]]


# ══════════════════════════════════════════════════════════════════════════════
# TRANSFORM WRAPPERS
# ══════════════════════════════════════════════════════════════════════════════

def _transform_hadir(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Routes to transform_raw_to_merged() for raw Google-Forms files,
    or clean_and_map_dataframe() for already-processed files.
    """
    if _is_raw_hadir_form(df_raw):
        return transform_raw_to_merged(df_raw)
    return clean_and_map_dataframe(df_raw, target_type="hadir")


def _transform_wp(df_raw: pd.DataFrame) -> pd.DataFrame:
    """wp_data ETL: schema map + phone normalisation."""
    df = clean_and_map_dataframe(df_raw, target_type="wp")
    if "no_whatsapp" in df.columns:
        df["no_whatsapp"] = df["no_whatsapp"].apply(_fmt_wa)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK 1 — Upload -> ETL -> DataTable preview
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("ingestion-preview-table",     "data"),
    Output("ingestion-preview-table",     "columns"),
    Output("ingestion-table-wrapper",     "style"),
    Output("ingestion-table-placeholder", "style"),
    Output("ingestion-sync-btn",          "disabled"),
    Output("ingestion-row-count",         "children"),
    Output("ingestion-filename-display",  "children"),
    Output("ingestion-alert-container",   "children"),
    Input("ingestion-upload",             "contents"),
    State("ingestion-upload",             "filename"),
    State("ingestion-data-type",          "value"),
    prevent_initial_call=True,
)
def preview_uploaded_file(contents, filename, data_type):
    _SHOW = {"display": "block"}
    _HIDE = {"display": "none"}

    if contents is None:
        return [], [], _HIDE, {}, True, "", "", no_update

    try:
        _header, b64_data = contents.split(",", 1)
        decoded  = base64.b64decode(b64_data)
        file_buf = io.BytesIO(decoded)

        fname_lower = (filename or "").lower()
        if fname_lower.endswith(".csv"):
            df_uploaded = pd.read_csv(file_buf, dtype=str)
        elif fname_lower.endswith((".xlsx", ".xls")):
            df_uploaded = pd.read_excel(file_buf, dtype=str)
        else:
            return (
                [], [], _HIDE, {}, True, "", filename or "",
                dbc.Alert(
                    [html.Strong("Format tidak didukung. "),
                     "Harap upload file .xlsx, .xls, atau .csv."],
                    color="warning", dismissable=True,
                ),
            )

        df_transformed = (
            _transform_hadir(df_uploaded)
            if data_type == "hadir"
            else _transform_wp(df_uploaded)
        )

        if df_transformed.empty:
            return (
                [], [], _HIDE, {}, True, "", filename or "",
                dbc.Alert(
                    "File berhasil dibaca namun DataFrame kosong setelah transformasi. "
                    "Periksa apakah header kolom sesuai dengan template.",
                    color="warning", dismissable=True,
                ),
            )

        # Serialise Int64 / NaT -> Python native (JSON-safe)
        df_json = df_transformed.astype(object).where(df_transformed.notna(), other=None)

        columns = [
            {"name": col, "id": col, "deletable": False, "renamable": False}
            for col in df_json.columns
        ]

        # Inject hidden "_rid" per row: Dash uses this to reconcile DOM rows
        # without remounting the whole table, preventing the cursor-jump bug.
        records = df_json.to_dict("records")
        data    = [{"_rid": str(i), **row} for i, row in enumerate(records)]

        n_rows = len(data)
        n_cols = len(columns)

        return (
            data, columns,
            _SHOW, _HIDE,
            False,
            f"{n_rows:,} baris  x  {n_cols:,} kolom",
            [
                html.Span("OK ", style={"color": "#198754"}),
                html.Strong(filename, className="me-1"),
                html.Span(f"- {n_rows:,} baris dimuat", className="text-muted"),
            ],
            "",
        )

    except Exception as exc:
        return (
            [], [], _HIDE, {}, True, "",
            filename or "",
            dbc.Alert(
                [html.Strong("Error saat memproses file: "), str(exc)],
                color="danger", dismissable=True,
            ),
        )


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK 2 — Sync DataTable -> Supabase via SQLAlchemy
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("ingestion-alert-container", "children",  allow_duplicate=True),
    Output("ingestion-sync-btn",        "disabled",  allow_duplicate=True),
    Output("data-refresh-ts",           "data",      allow_duplicate=True),
    Input("ingestion-sync-btn",         "n_clicks"),
    State("ingestion-preview-table",    "data"),
    State("ingestion-preview-table",    "columns"),
    State("ingestion-data-type",        "value"),
    prevent_initial_call=True,
)
def sync_to_supabase(n_clicks, table_data, table_columns, data_type):
    """
    Read current DataTable state, re-coerce types, re-apply NOT NULL defaults,
    then append to the target PostgreSQL table via to_sql().

    Sync strategy: if_exists='append' — rows are ADDED. Never truncates.
    The entire operation runs inside a single transaction; any error triggers
    an automatic rollback so no partial data is committed.
    """
    if not n_clicks or not table_data:
        return no_update, no_update, no_update

    target_table = "hadir_data" if data_type == "hadir" else "wp_data"
    int_cols     = _HADIR_INT_COLS if data_type == "hadir" else _WP_INT_COLS
    not_null_def = HADIR_NOT_NULL_DEFAULTS if data_type == "hadir" else WP_NOT_NULL_DEFAULTS

    try:
        col_ids    = [c["id"] for c in (table_columns or []) if c["id"] != "_rid"]
        df_to_sync = pd.DataFrame(
            [{k: v for k, v in row.items() if k != "_rid"} for row in table_data],
            columns=col_ids or None,
        )

        if df_to_sync.empty:
            return (
                dbc.Alert("Tidak ada data untuk disinkronisasi.", color="warning", dismissable=True),
                False,
                no_update,
            )

        # Re-coerce: DataTable serialises everything to str after user edits
        for col in int_cols:
            if col in df_to_sync.columns:
                df_to_sync[col] = (
                    pd.to_numeric(df_to_sync[col], errors="coerce").astype("Int64")
                )

        if "tanggal" in df_to_sync.columns:
            df_to_sync["tanggal"] = (
                pd.to_datetime(df_to_sync["tanggal"], errors="coerce")
                .dt.strftime("%Y-%m-%d")
            )

        df_to_sync = _apply_not_null_defaults(df_to_sync, not_null_def, int_cols)

        # Replace remaining pd.NA / NaN -> None (SQL NULL, safe for nullable cols)
        df_to_sync = df_to_sync.where(df_to_sync.notna(), other=None)

        with _get_engine().begin() as conn:
            df_to_sync.to_sql(
                name      = target_table,
                con       = conn,
                if_exists = "append",
                index     = False,
                method    = "multi",
                chunksize = 500,
            )

        n_rows = len(df_to_sync)
        return (
            dbc.Alert(
                [
                    html.Span("OK ", style={"color": "#198754", "fontSize": "1.1rem"}),
                    html.Strong(f"{n_rows:,} baris "),
                    "berhasil disinkronisasi ke tabel ",
                    html.Code(target_table),
                    " di Supabase.",
                ],
                color="success",
                dismissable=True,
                duration=10_000,
            ),
            True,
            time.time(),
        )

    except EnvironmentError as env_err:
        return (
            dbc.Alert(
                [html.Strong("Konfigurasi Error: "), str(env_err)],
                color="danger", dismissable=True,
            ),
            False,
            no_update,
        )

    except Exception as exc:
        return (
            dbc.Alert(
                [
                    html.Strong("Sync gagal: "),
                    str(exc),
                    html.Br(),
                    html.Small(
                        "Tidak ada baris yang tersimpan (transaksi di-rollback otomatis).",
                        className="text-muted",
                    ),
                ],
                color="danger", dismissable=True,
            ),
            False,
            no_update,
        )
