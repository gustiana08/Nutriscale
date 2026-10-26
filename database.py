# database.py

import pandas as pd
import sqlite3
import os
import math

# Path absolut relatif terhadap lokasi file ini
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE_DIR, "nutriscale.db")
CSV_PATH = os.path.join(_BASE_DIR, "nutrition.csv")
DATASET_CSV_PATH = os.path.join(_BASE_DIR, "dataset", "nutrition.csv")

# ---------------------------------------------------------------
# Koneksi database aktif.
# Bila kredensial Turso tersedia (Streamlit Secrets atau environment
# TURSO_DATABASE_URL + TURSO_AUTH_TOKEN), aplikasi memakai database
# cloud Turso (libSQL) yang PERSISTEN — data tidak hilang saat app
# Streamlit Cloud restart/reboot. Tanpa kredensial, fallback ke
# SQLite lokal seperti semula (untuk pengembangan lokal).
# ---------------------------------------------------------------
def _turso_config():
    url = token = None
    try:
        import streamlit as st
        url = st.secrets.get("TURSO_DATABASE_URL")
        token = st.secrets.get("TURSO_AUTH_TOKEN")
    except Exception:
        pass
    url = url or os.environ.get("TURSO_DATABASE_URL")
    token = token or os.environ.get("TURSO_AUTH_TOKEN")
    return url, token

def buat_koneksi():
    """Membuka koneksi ke database aktif (Turso bila terkonfigurasi,
    selain itu SQLite lokal). Semua fungsi modul ini lewat sini."""
    url, token = _turso_config()
    if url:
        import libsql
        if token:
            return libsql.connect(database=url, auth_token=token)
        return libsql.connect(database=url)
    return sqlite3.connect(DB_PATH, timeout=30)

def _adalah_lokal():
    """True bila database aktif adalah SQLite lokal (bukan Turso)."""
    return _turso_config()[0] is None

def _mulai_tulis_langsung(cursor):
    """BEGIN IMMEDIATE (kunci tulis sejak awal). Pada driver yang
    mengelola transaksi sendiri (libsql remote) perintah ini bisa
    ditolak — abaikan: serialisasi tulis di sisi server tetap
    menjamin tidak ada seeding/pembaruan ganda bersamaan."""
    try:
        cursor.execute("BEGIN IMMEDIATE")
    except Exception:
        pass

def parse_float(val):
    """Mengonversi string bertanda koma Indonesia (misal: '435,00') menjadi float (435.0)"""
    if pd.isna(val) or val is None or str(val).strip() in ['', '-']:
        return 0.0
    try:
        # Ubah koma desimal Indonesia menjadi titik desimal Python
        clean_str = str(val).replace('.', '').replace(',', '.').strip()
        return float(clean_str)
    except ValueError:
        return 0.0

def setup_database():
    lokal = _adalah_lokal()
    conn = buat_koneksi()
    cursor = conn.cursor()
    # Kunci tulis sejak awal (BEGIN IMMEDIATE) HANYA untuk SQLite lokal:
    # mencegah seeding ganda saat beberapa sesi membuka aplikasi bersamaan
    # pada database yang masih kosong — tanpa kunci ini tiap sesi melihat
    # tabel kosong dan sama-sama mengimpor seluruh CSV (pernah menghasilkan
    # 4x duplikasi baris seed). Pada Turso (remote) transaksi interaktif
    # yang menggantung selama parse CSV yang lambat akan di-rollback oleh
    # server karena stream menganggur ("interactive transaction was rolled
    # back because the stream was idle for too long", terlihat di log
    # Streamlit Cloud 2026-10-24) — di sana tiap pernyataan berjalan
    # autocommit yang cepat, dan langkah dedupe di bawah membersihkan
    # sisa duplikasi bila dua sesi sempat seeding bersamaan.
    if lokal:
        _mulai_tulis_langsung(cursor)
    
    # 1. Buat Tabel Bahan Pangan
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bahan_pangan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL,
        kalori REAL,
        protein REAL,
        lemak REAL,
        karbohidrat REAL,
        bdd REAL DEFAULT 100,
        gambar TEXT,
        is_custom INTEGER DEFAULT 0
    )
    ''')
    
    # 2. Buat Tabel Log Menu Harian
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS log_menu_harian (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal DATE NOT NULL,
        siklus_hari VARCHAR(50),
        waktu_makan VARCHAR(50),
        nama_menu VARCHAR(100),
        bahan_pangan VARCHAR(100),
        berat_kotor REAL,
        berat_bersih REAL,
        bdd REAL,
        energi_kcal REAL,
        protein_g REAL,
        lemak_g REAL,
        karbo_g REAL
    )
    ''')

    # 2c. Buat Tabel Rencana Mingguan (Senin-Jumat). Strukturnya
    # mengikuti log_menu_harian agar baris rencana bisa diterapkan ke
    # menu harian apa adanya; minggu_mulai selalu hari Senin.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rencana_mingguan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        minggu_mulai DATE NOT NULL,
        hari VARCHAR(20) NOT NULL,
        nama_menu VARCHAR(100),
        bahan_pangan VARCHAR(100),
        berat_kotor REAL,
        berat_bersih REAL,
        bdd REAL,
        energi_kcal REAL,
        protein_g REAL,
        lemak_g REAL,
        karbo_g REAL
    )
    ''')

    # 2b/2c. Perbaikan data HANYA dijalankan bila pemeriksaan menemukan
    # masalahnya. Pada kondisi normal (database sudah terisi dan bersih)
    # setup hanya MEMBACA — penting untuk database remote: sesi-sesi yang
    # mulai bersamaan tidak lagi berebut kunci tulis. Sebelumnya DELETE
    # dan UPDATE berjalan tanpa syarat di setiap startup; di Turso sesi
    # yang kalah menunggu sampai transaksinya di-rollback server
    # ("stream idle") dan pengguna melihat error pada muatan pertama
    # setelah reboot (kejadian 2026-10-24).
    cursor.execute('''
    SELECT COUNT(*) FROM (
        SELECT 1 FROM bahan_pangan WHERE is_custom = 0
        GROUP BY nama HAVING COUNT(*) > 1 LIMIT 1
    )
    ''')
    if cursor.fetchone()[0]:
        # Bersihkan duplikat baris seed — sisakan satu baris per nama
        # (id terkecil). Baris custom pengguna tidak disentuh.
        cursor.execute('''
        DELETE FROM bahan_pangan
        WHERE is_custom = 0 AND id NOT IN (
            SELECT MIN(id) FROM bahan_pangan WHERE is_custom = 0 GROUP BY nama
        )
        ''')
    cursor.execute("SELECT COUNT(*) FROM bahan_pangan WHERE is_custom = 0 AND (bdd > 100 OR bdd <= 0)")
    if cursor.fetchone()[0]:
        # Perbaiki BDD baris seed di luar rentang sah (0, 100] pada
        # database lama — di CSV sumber ada makanan olahan tercatat BDD
        # 110-400%, yang menggelembungkan hitungan gizi.
        cursor.execute("UPDATE bahan_pangan SET bdd = 100 WHERE is_custom = 0 AND (bdd > 100 OR bdd <= 0)")
    
    # Impor data jika tabel bahan_pangan masih kosong
    cursor.execute("SELECT COUNT(*) FROM bahan_pangan")
    if cursor.fetchone()[0] == 0:
        actual_csv = CSV_PATH if os.path.exists(CSV_PATH) else (DATASET_CSV_PATH if os.path.exists(DATASET_CSV_PATH) else None)
        
        if actual_csv:
            try:
                # Membaca CSV dengan separator ';' dan melewati 4 baris header pertama
                df = pd.read_csv(actual_csv, sep=';', skiprows=4, header=None, encoding='utf-8')
                
                data_to_insert = []
                for _, row in df.iterrows():
                    # Ambil data berdasarkan indeks kolom file TKPI
                    nama = row[2] if len(row) > 2 else None
                    bdd_val = parse_float(row[5]) if len(row) > 5 else 100.0
                    kalori = parse_float(row[8]) if len(row) > 8 else 0.0
                    protein = parse_float(row[9]) if len(row) > 9 else 0.0
                    lemak = parse_float(row[10]) if len(row) > 10 else 0.0
                    karbo = parse_float(row[11]) if len(row) > 11 else 0.0
                    
                    if pd.notna(nama) and str(nama).strip() != '' and str(nama).strip().lower() != 'nan':
                        data_to_insert.append((
                            str(nama).strip(),
                            kalori,
                            protein,
                            lemak,
                            karbo,
                            bdd_val if 0 < bdd_val <= 100 else 100.0,
                            '',
                            0
                        ))
                
                if not lokal:
                    # Segarkan koneksi sebelum impor besar: koneksi lama
                    # mungkin sudah menganggur selama parse CSV di atas.
                    conn.close()
                    conn = buat_koneksi()
                    cursor = conn.cursor()
                cursor.executemany('''
                INSERT INTO bahan_pangan (nama, kalori, protein, lemak, karbohidrat, bdd, gambar, is_custom)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', data_to_insert)
                print(f"✅ Berhasil mengimpor {len(data_to_insert)} bahan pangan dari Tabel Komposisi Pangan Indonesia!")
            except Exception as e:
                print(f"⚠️ Gagal membaca file nutrition.csv: {e}")
            
    conn.commit()
    conn.close()

def init_db():
    """Inisialisasi database — cukup dipanggil sekali saat startup aplikasi.

    Kegagalan sementara (mis. database remote sedang sibuk sesaat)
    dicoba ulang sampai 3 kali. Bila tetap gagal, aplikasi tetap dimuat
    alih-alih crash total — kesalahan akan muncul pada operasi data
    yang benar-benar membutuhkannya, dan setup berjalan lagi pada
    muatan berikutnya.
    """
    import time
    for percobaan in range(3):
        try:
            setup_database()
            return
        except Exception as e:
            if percobaan == 2:
                print(f"⚠️ setup_database gagal setelah 3 percobaan: {e}")
            else:
                time.sleep(1.5)

def cari_bahan_pangan(keyword: str, limit: int = 50):
    """Mencari bahan pangan berdasarkan kata kunci nama.

    Karakter khusus LIKE (%, _, \\) pada kata kunci diperlakukan sebagai teks
    biasa, bukan wildcard. Hasil diurutkan nama dan dibatasi `limit` baris —
    panggil dengan limit+1 untuk tahu apakah masih ada kecocokan lain.
    """
    kata_aman = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    conn = buat_koneksi()
    cursor = conn.cursor()
    query = "SELECT id, nama, kalori, protein, lemak, karbohidrat, bdd, is_custom FROM bahan_pangan WHERE nama LIKE ? ESCAPE '\\' ORDER BY nama LIMIT ?"
    cursor.execute(query, (f"%{kata_aman}%", int(limit)))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": r[0], "nama": r[1], "kalori": r[2], 
        "protein": r[3], "lemak": r[4], "karbohidrat": r[5], "bdd": r[6], "is_custom": r[7]
    } for r in rows]

def _bdd_valid(bdd) -> float:
    """BDD yang sah: 0 < bdd <= 100. Nilai di luar rentang dijepit masuk."""
    try:
        bdd = float(bdd)
    except (TypeError, ValueError):
        return 100.0
    if not math.isfinite(bdd):
        return 100.0
    return min(max(bdd, 1.0), 100.0)

def _validasi_bahan(nama, kalori, protein, lemak, karbohidrat):
    """Memvalidasi identitas dan angka gizi sebelum disimpan."""
    if not isinstance(nama, str) or not nama.strip():
        raise ValueError("Nama bahan pangan wajib diisi")

    nilai = []
    for label, angka in (
        ("kalori", kalori),
        ("protein", protein),
        ("lemak", lemak),
        ("karbohidrat", karbohidrat),
    ):
        try:
            angka = float(angka)
        except (TypeError, ValueError):
            raise ValueError(f"{label} harus berupa angka") from None
        if not math.isfinite(angka) or angka < 0:
            raise ValueError(f"{label} harus berupa angka nol atau lebih")
        nilai.append(angka)
    return nama.strip(), *nilai

def tambah_bahan_custom(nama: str, kalori: float, protein: float, lemak: float, karbohidrat: float, bdd: float = 100.0):
    """Menambahkan bahan pangan baru (kustom) ke database."""
    nama, kalori, protein, lemak, karbohidrat = _validasi_bahan(
        nama, kalori, protein, lemak, karbohidrat)
    conn = buat_koneksi()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bahan_pangan (nama, kalori, protein, lemak, karbohidrat, bdd, is_custom) VALUES (?, ?, ?, ?, ?, ?, 1)",
        (nama, kalori, protein, lemak, karbohidrat, _bdd_valid(bdd))
    )
    conn.commit()
    conn.close()
    return True

def update_bahan_pangan(id_bahan: int, nama: str, kalori: float, protein: float, lemak: float, karbohidrat: float, bdd: float = 100.0):
    """Memperbarui data bahan pangan berdasarkan ID."""
    nama, kalori, protein, lemak, karbohidrat = _validasi_bahan(
        nama, kalori, protein, lemak, karbohidrat)
    conn = buat_koneksi()
    cursor = conn.cursor()
    query = """
    UPDATE bahan_pangan 
    SET nama = ?, kalori = ?, protein = ?, lemak = ?, karbohidrat = ?, bdd = ?
    WHERE id = ?
    """
    cursor.execute(query, (nama, kalori, protein, lemak, karbohidrat, _bdd_valid(bdd), id_bahan))
    conn.commit()
    conn.close()
    return True

def update_bahan_massal(baris: list):
    """Memperbarui banyak bahan sekaligus dalam SATU transaksi (atomik).

    Args:
        baris: list tuple (id, nama, kalori, protein, lemak, karbohidrat, bdd).
    Semua baris tersimpan, atau tidak sama sekali bila terjadi kesalahan —
    menggantikan pola lama satu koneksi + commit per baris.
    """
    baris_valid = []
    for id_bahan, nama, kalori, protein, lemak, karbohidrat, bdd in baris:
        nama, kalori, protein, lemak, karbohidrat = _validasi_bahan(
            nama, kalori, protein, lemak, karbohidrat)
        baris_valid.append((
            int(id_bahan), nama, kalori, protein, lemak, karbohidrat, _bdd_valid(bdd)
        ))

    conn = buat_koneksi()
    cursor = conn.cursor()
    # BEGIN IMMEDIATE hanya lokal; di remote, executemany terkirim sebagai
    # satu batch sehingga tetap atomik tanpa transaksi interaktif.
    if _adalah_lokal():
        _mulai_tulis_langsung(cursor)
    cursor.executemany(
        "UPDATE bahan_pangan SET nama = ?, kalori = ?, protein = ?, lemak = ?, karbohidrat = ?, bdd = ? WHERE id = ?",
        [(nama, kalori, protein, lemak, karbohidrat, bdd, id_bahan)
         for (id_bahan, nama, kalori, protein, lemak, karbohidrat, bdd) in baris_valid],
    )
    conn.commit()
    conn.close()
    return len(baris)

def simpan_menu_harian(tanggal, siklus_hari, waktu_makan, daftar_bahan):
    """Menyimpan log menu harian ke database."""
    conn = buat_koneksi()
    cursor = conn.cursor()
    for item in daftar_bahan:
        cursor.execute("""
            INSERT INTO log_menu_harian 
            (tanggal, siklus_hari, waktu_makan, nama_menu, bahan_pangan, berat_kotor, berat_bersih, bdd, energi_kcal, protein_g, lemak_g, karbo_g)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tanggal, siklus_hari, waktu_makan,
            item['nama_menu'], item['bahan_pangan'], 
            item['berat_kotor'], item['berat_bersih'], item['bdd'],
            item['energi_kcal'], item['protein_g'], item['lemak_g'], item['karbo_g']
        ))
    conn.commit()
    conn.close()

# ---------------------------------------------------------------
# Rencana menu mingguan (Senin-Jumat). Satu minggu dikenali dari
# tanggal Senin-nya (minggu_mulai). Simpan bersifat ganti-per-menu:
# menyimpan menu yang sama pada hari yang sama menimpa susunan lama
# menu itu, jadi menyimpan ulang hasil edit tidak menggandakan baris.
# Semua tulis rencana memakai satu koneksi + satu commit (atomik).
# ---------------------------------------------------------------
HARI_SEKOLAH = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]


def _validasi_hari_sekolah(hari: str):
    if hari not in HARI_SEKOLAH:
        raise ValueError(f"Hari rencana harus salah satu dari {HARI_SEKOLAH}")
    return hari


def simpan_rencana_hari(minggu_mulai, hari, nama_menu, daftar_bahan):
    """Menyimpan satu menu ke rencana hari tertentu (ganti bila menu
    yang sama sudah ada pada hari itu). daftar_bahan memakai format
    yang sama dengan simpan_menu_harian."""
    _validasi_hari_sekolah(hari)
    conn = buat_koneksi()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM rencana_mingguan WHERE minggu_mulai = ? AND hari = ? AND nama_menu = ?",
        (minggu_mulai, hari, nama_menu),
    )
    for item in daftar_bahan:
        cursor.execute("""
            INSERT INTO rencana_mingguan
            (minggu_mulai, hari, nama_menu, bahan_pangan, berat_kotor, berat_bersih, bdd, energi_kcal, protein_g, lemak_g, karbo_g)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            minggu_mulai, hari,
            item['nama_menu'], item['bahan_pangan'],
            item['berat_kotor'], item['berat_bersih'], item['bdd'],
            item['energi_kcal'], item['protein_g'], item['lemak_g'], item['karbo_g']
        ))
    conn.commit()
    conn.close()
    return len(daftar_bahan)


def ambil_rencana_mingguan(minggu_mulai):
    """Seluruh baris rencana satu minggu, terurut Senin-Jumat lalu id."""
    conn = buat_koneksi()
    urutan = "CASE hari " + " ".join(
        f"WHEN '{h}' THEN {i}" for i, h in enumerate(HARI_SEKOLAH)
    ) + " ELSE 99 END"
    df = pd.read_sql_query(
        f"""SELECT id, minggu_mulai, hari, nama_menu, bahan_pangan,
                   berat_kotor, berat_bersih, bdd, energi_kcal, protein_g, lemak_g, karbo_g
            FROM rencana_mingguan
            WHERE minggu_mulai = ?
            ORDER BY {urutan}, id ASC""",
        conn, params=(minggu_mulai,))
    conn.close()
    return df


def hapus_rencana_menu(minggu_mulai, hari, nama_menu):
    """Menghapus satu menu dari rencana hari tertentu."""
    conn = buat_koneksi()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM rencana_mingguan WHERE minggu_mulai = ? AND hari = ? AND nama_menu = ?",
        (minggu_mulai, hari, nama_menu),
    )
    conn.commit()
    conn.close()
    return True


def salin_rencana_hari(minggu_mulai, hari_asal, hari_tujuan):
    """Menyalin seluruh menu hari asal ke hari tujuan (menggantikan
    isi hari tujuan). Mengembalikan jumlah baris yang disalin."""
    _validasi_hari_sekolah(hari_asal)
    _validasi_hari_sekolah(hari_tujuan)
    conn = buat_koneksi()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nama_menu, bahan_pangan, berat_kotor, berat_bersih, bdd, energi_kcal, protein_g, lemak_g, karbo_g "
        "FROM rencana_mingguan WHERE minggu_mulai = ? AND hari = ? ORDER BY id ASC",
        (minggu_mulai, hari_asal),
    )
    baris = cursor.fetchall()
    cursor.execute(
        "DELETE FROM rencana_mingguan WHERE minggu_mulai = ? AND hari = ?",
        (minggu_mulai, hari_tujuan),
    )
    cursor.executemany(
        """INSERT INTO rencana_mingguan
           (minggu_mulai, hari, nama_menu, bahan_pangan, berat_kotor, berat_bersih, bdd, energi_kcal, protein_g, lemak_g, karbo_g)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(minggu_mulai, hari_tujuan, *r) for r in baris],
    )
    conn.commit()
    conn.close()
    return len(baris)


def hapus_bahan_pangan(id_bahan: int):
    """Menghapus satu bahan pangan berdasarkan ID."""
    conn = buat_koneksi()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bahan_pangan WHERE id = ?", (id_bahan,))
    conn.commit()
    conn.close()
    return True

def ambil_log_dengan_id(tanggal_awal, tanggal_akhir):
    """Mengambil log menu harian termasuk kolom id (untuk keperluan hapus entri)."""
    conn = buat_koneksi()
    query = """
        SELECT id, tanggal, siklus_hari, waktu_makan, nama_menu, bahan_pangan,
               berat_kotor, berat_bersih, bdd, energi_kcal, protein_g, lemak_g, karbo_g
        FROM log_menu_harian
        WHERE tanggal BETWEEN ? AND ?
        ORDER BY tanggal ASC, id ASC
    """
    df = pd.read_sql_query(query, conn, params=(tanggal_awal, tanggal_akhir))
    conn.close()
    return df

def hapus_log_menu(log_id: int):
    """Menghapus satu entri log menu harian berdasarkan ID."""
    conn = buat_koneksi()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM log_menu_harian WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return True

def ambil_bahan_editor(keyword: str = ""):
    """Daftar bahan untuk editor Tab 3: semua bahan, atau yang namanya
    mengandung keyword (LIKE). Menggantikan query sqlite3 langsung
    yang dulu ditulis inline di app.py."""
    conn = buat_koneksi()
    if keyword:
        kata_aman = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        df = pd.read_sql_query(
            "SELECT id, nama, kalori, protein, lemak, karbohidrat, bdd FROM bahan_pangan WHERE nama LIKE ? ESCAPE '\\'",
            conn, params=(f"%{kata_aman}%",))
    else:
        df = pd.read_sql_query(
            "SELECT id, nama, kalori, protein, lemak, karbohidrat, bdd FROM bahan_pangan",
            conn)
    conn.close()
    return df

def ambil_laporan_harian(tanggal_awal, tanggal_akhir):
    """Mengambil data laporan harian berdasarkan rentang tanggal."""
    conn = buat_koneksi()
    query = """
        SELECT tanggal, siklus_hari, waktu_makan, nama_menu, bahan_pangan, 
               berat_kotor, berat_bersih, bdd, energi_kcal, protein_g, lemak_g, karbo_g
        FROM log_menu_harian
        WHERE tanggal BETWEEN ? AND ?
        ORDER BY tanggal ASC, waktu_makan ASC
    """
    df = pd.read_sql_query(query, conn, params=(tanggal_awal, tanggal_akhir))
    conn.close()
    return df

if __name__ == "__main__":
    setup_database()