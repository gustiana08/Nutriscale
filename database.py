# database.py

import pandas as pd
import sqlite3
import os

# Path absolut relatif terhadap lokasi file ini
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE_DIR, "nutriscale.db")
CSV_PATH = os.path.join(_BASE_DIR, "nutrition.csv")
DATASET_CSV_PATH = os.path.join(_BASE_DIR, "dataset", "nutrition.csv")

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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    conn.commit()
    
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
                            bdd_val if bdd_val > 0 else 100.0,
                            '',
                            0
                        ))
                
                cursor.executemany('''
                INSERT INTO bahan_pangan (nama, kalori, protein, lemak, karbohidrat, bdd, gambar, is_custom)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', data_to_insert)
                conn.commit()
                print(f"✅ Berhasil mengimpor {len(data_to_insert)} bahan pangan dari Tabel Komposisi Pangan Indonesia!")
            except Exception as e:
                print(f"⚠️ Gagal membaca file nutrition.csv: {e}")
            
    conn.close()

def init_db():
    """Inisialisasi database — cukup dipanggil sekali saat startup aplikasi."""
    setup_database()

def cari_bahan_pangan(keyword: str):
    """Mencari bahan pangan berdasarkan kata kunci nama."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT id, nama, kalori, protein, lemak, karbohidrat, bdd, is_custom FROM bahan_pangan WHERE nama LIKE ? LIMIT 20"
    cursor.execute(query, (f"%{keyword}%",))
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": r[0], "nama": r[1], "kalori": r[2], 
        "protein": r[3], "lemak": r[4], "karbohidrat": r[5], "bdd": r[6], "is_custom": r[7]
    } for r in rows]

def tambah_bahan_custom(nama: str, kalori: float, protein: float, lemak: float, karbohidrat: float, bdd: float = 100.0):
    """Menambahkan bahan pangan baru (kustom) ke database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bahan_pangan (nama, kalori, protein, lemak, karbohidrat, bdd, is_custom) VALUES (?, ?, ?, ?, ?, ?, 1)",
        (nama, kalori, protein, lemak, karbohidrat, bdd)
    )
    conn.commit()
    conn.close()
    return True

def update_bahan_pangan(id_bahan: int, nama: str, kalori: float, protein: float, lemak: float, karbohidrat: float, bdd: float = 100.0):
    """Memperbarui data bahan pangan berdasarkan ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
    UPDATE bahan_pangan 
    SET nama = ?, kalori = ?, protein = ?, lemak = ?, karbohidrat = ?, bdd = ?
    WHERE id = ?
    """
    cursor.execute(query, (nama, kalori, protein, lemak, karbohidrat, bdd, id_bahan))
    conn.commit()
    conn.close()
    return True

def simpan_menu_harian(tanggal, siklus_hari, waktu_makan, daftar_bahan):
    """Menyimpan log menu harian ke database."""
    conn = sqlite3.connect(DB_PATH)
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

def hapus_log_menu(log_id: int):
    """Menghapus satu entri log menu harian berdasarkan ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM log_menu_harian WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return True

def ambil_laporan_harian(tanggal_awal, tanggal_akhir):
    """Mengambil data laporan harian berdasarkan rentang tanggal."""
    conn = sqlite3.connect(DB_PATH)
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