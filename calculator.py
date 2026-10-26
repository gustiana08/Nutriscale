# calculator.py
"""
Modul kalkulasi gizi GiziKu — konversi berat kotor/bersih dan analisis makronutrisi.
"""


def konversi_berat(berat_input: float, bdd: float, tipe_input: str = "kotor"):
    """
    Mengonversi antara berat kotor dan berat bersih berdasarkan % BDD.
    
    Args:
        berat_input: Berat dalam gram.
        bdd: Persentase Bagian Dapat Dimakan (1-100).
        tipe_input: 'kotor' (konversi ke bersih) atau 'bersih' (konversi ke kotor).
    
    Returns:
        Tuple (berat_kotor, berat_bersih) dalam gram, dibulatkan 1 desimal.
    """
    if bdd <= 0:
        bdd = 100.0
        
    if tipe_input not in ("kotor", "bersih"):
        raise ValueError("tipe_input harus berupa 'kotor' atau 'bersih'")

    if tipe_input == "kotor":
        berat_kotor = berat_input
        berat_bersih = berat_input * (bdd / 100.0)
    else:
        berat_bersih = berat_input
        berat_kotor = berat_input / (bdd / 100.0)
        
    return round(berat_kotor, 1), round(berat_bersih, 1)


def hitung_nutrisi_bahan(berat_bersih: float, kalori_per100: float, protein_per100: float, 
                          lemak_per100: float, karbo_per100: float):
    """
    Menghitung nilai gizi berdasarkan berat bersih dan kandungan per 100g.
    
    Args:
        berat_bersih: Berat bersih bahan (gram).
        kalori_per100: Kalori per 100g bahan.
        protein_per100: Protein per 100g bahan.
        lemak_per100: Lemak per 100g bahan.
        karbo_per100: Karbohidrat per 100g bahan.
    
    Returns:
        Dict dengan kunci: kalori, protein, lemak, karbohidrat (sudah dibulatkan).
    """
    faktor = berat_bersih / 100.0
    return {
        "kalori": round(kalori_per100 * faktor, 1),
        "protein": round(protein_per100 * faktor, 1),
        "lemak": round(lemak_per100 * faktor, 1),
        "karbohidrat": round(karbo_per100 * faktor, 1),
    }


def perbarui_keranjang(keranjang_lama: list, baris_editor: list):
    """
    Menyinkronkan keranjang menu dengan hasil edit tabel data_editor.

    Args:
        keranjang_lama: List dict item keranjang saat ini (tidak dimutasi).
        baris_editor: List tuple (index, berat_kotor) dari DataFrame hasil editor.

    Returns:
        Tuple (keranjang_baru, berubah):
        - Baris yang hilang dari editor dianggap dihapus pengguna.
        - Index di luar rentang (baris tambahan kosong bawaan editor) diabaikan
          dan ditandai berubah agar dibersihkan lewat rerun.
        - Berat NaN / <= 0 dianggap tidak valid dan kembali ke berat lama.
        - Berat dibulatkan 1 desimal (sesuai presisi tampilan tabel).
    """
    import math

    berubah = False
    keranjang_baru = []
    for index, berat in baris_editor:
        if index is None or index < 0 or index >= len(keranjang_lama):
            berubah = True
            continue
        item = dict(keranjang_lama[index])
        berat_lama = float(item["Berat Kotor (g)"])
        try:
            berat_baru = float(berat)
        except (TypeError, ValueError):
            berat_baru = berat_lama
        if math.isnan(berat_baru) or berat_baru <= 0:
            berat_baru = berat_lama
        berat_baru = round(berat_baru, 1)
        if berat_baru != berat_lama:
            berubah = True
        item["Berat Kotor (g)"] = berat_baru
        keranjang_baru.append(item)
    if len(keranjang_baru) != len(keranjang_lama):
        berubah = True
    return keranjang_baru, berubah


# ---------------------------------------------------------------
# Target AKG 2019 (Permenkes No. 28 Tahun 2019, Lampiran I Tabel 1:
# Angka Kecukupan Energi, Protein, Lemak, Karbohidrat per orang per
# hari). Kelompok 7-9 tahun tidak dibedakan jenis kelamin dalam
# peraturan; kelompok 10 tahun ke atas dibedakan laki-laki/perempuan.
# Nilai di bawah ini disalin dari teks peraturan (Berita Negara
# Republik Indonesia Tahun 2019 Nomor 956).
# ---------------------------------------------------------------
TARGET_AKG = {
    "7-9 tahun": {"energi": 1650, "protein": 40, "lemak": 55, "karbohidrat": 250},
    "10-12 tahun (Laki-laki)": {"energi": 2000, "protein": 50, "lemak": 65, "karbohidrat": 300},
    "10-12 tahun (Perempuan)": {"energi": 1900, "protein": 55, "lemak": 65, "karbohidrat": 280},
    "13-15 tahun (Laki-laki)": {"energi": 2400, "protein": 70, "lemak": 80, "karbohidrat": 350},
    "13-15 tahun (Perempuan)": {"energi": 2050, "protein": 65, "lemak": 70, "karbohidrat": 300},
    "16-18 tahun (Laki-laki)": {"energi": 2650, "protein": 75, "lemak": 85, "karbohidrat": 400},
    "16-18 tahun (Perempuan)": {"energi": 2100, "protein": 65, "lemak": 70, "karbohidrat": 300},
}

# Band status pemenuhan (hanya penanda tampilan, bukan standar klinis):
# >= 100% terpenuhi, 80-99% kurang, < 80% sangat kurang.
BAND_AKG = ((100.0, "Terpenuhi"), (80.0, "Kurang"))


def status_pemenuhan(persen: float) -> str:
    """Status tampilan untuk satu persen pemenuhan AKG."""
    for batas, label in BAND_AKG:
        if persen >= batas:
            return label
    return "Sangat kurang"


def hitung_pemenuhan_akg(total: dict, kelompok_umur: str) -> dict:
    """
    Membandingkan total gizi sehari dengan target AKG 2019.

    Args:
        total: dict dengan kunci energi, protein, lemak, karbohidrat
            (satuan: kkal untuk energi, gram untuk sisanya).
        kelompok_umur: salah satu kunci TARGET_AKG.

    Returns:
        Dict per zat gizi: {"aktual", "target", "persen", "status"},
        plus kunci "kelompok" berisi label kelompok yang dipakai.

    Raises:
        ValueError: bila kelompok_umur tidak dikenal.
    """
    if kelompok_umur not in TARGET_AKG:
        raise ValueError(f"Kelompok umur AKG tidak dikenal: {kelompok_umur}")
    target = TARGET_AKG[kelompok_umur]
    hasil = {"kelompok": kelompok_umur}
    for zat in ("energi", "protein", "lemak", "karbohidrat"):
        aktual = float(total.get(zat, 0.0) or 0.0)
        tgt = float(target[zat])
        persen = round((aktual / tgt) * 100, 1) if tgt > 0 else 0.0
        hasil[zat] = {
            "aktual": round(aktual, 1),
            "target": tgt,
            "persen": persen,
            "status": status_pemenuhan(persen),
        }
    return hasil


def analisis_menu(daftar_bahan_terpilih: list, target_kebutuhan: dict = None):
    """
    Menganalisis keseluruhan menu dan membandingkan dengan target AKG.
    
    Args:
        daftar_bahan_terpilih: List dict bahan (nama, kalori, protein, lemak, karbohidrat, bdd, berat_gram, tipe_input).
        target_kebutuhan: Dict opsional (target_kalori, target_protein, target_lemak, target_karbo).
    
    Returns:
        Dict dengan rincian_menu, total_asupan, dan persentase_akg.
    """
    total_kalori = 0.0
    total_protein = 0.0
    total_lemak = 0.0
    total_karbo = 0.0
    
    rincian_menu = []
    
    for item in daftar_bahan_terpilih:
        bdd = item.get('bdd', 100.0)
        tipe_input = item.get('tipe_input', 'kotor')
        berat_val = item.get('berat_gram', 100.0)
        
        berat_kotor, berat_bersih = konversi_berat(berat_val, bdd, tipe_input)
        
        # Kandungan gizi selalu dihitung dari BERAT BERSIH
        nutrisi = hitung_nutrisi_bahan(
            berat_bersih, 
            item['kalori'], item['protein'], item['lemak'], item['karbohidrat']
        )
        
        total_kalori += nutrisi['kalori']
        total_protein += nutrisi['protein']
        total_lemak += nutrisi['lemak']
        total_karbo += nutrisi['karbohidrat']
        
        rincian_menu.append({
            "nama": item['nama'],
            "bdd_pct": bdd,
            "berat_kotor_g": berat_kotor,
            "berat_bersih_g": berat_bersih,
            "kalori": nutrisi['kalori'],
            "protein": nutrisi['protein'],
            "lemak": nutrisi['lemak'],
            "karbo": nutrisi['karbohidrat']
        })
    
    # Hitung persentase AKG jika target tersedia
    persentase_akg = {}
    if target_kebutuhan:
        pct_kalori = (total_kalori / target_kebutuhan['target_kalori']) * 100 if target_kebutuhan.get('target_kalori', 0) > 0 else 0
        pct_protein = (total_protein / target_kebutuhan['target_protein']) * 100 if target_kebutuhan.get('target_protein', 0) > 0 else 0
        pct_lemak = (total_lemak / target_kebutuhan['target_lemak']) * 100 if target_kebutuhan.get('target_lemak', 0) > 0 else 0
        pct_karbo = (total_karbo / target_kebutuhan['target_karbo']) * 100 if target_kebutuhan.get('target_karbo', 0) > 0 else 0
        persentase_akg = {
            "kalori_pct": round(pct_kalori, 1),
            "protein_pct": round(pct_protein, 1),
            "lemak_pct": round(pct_lemak, 1),
            "karbo_pct": round(pct_karbo, 1)
        }
    
    return {
        "rincian_menu": rincian_menu,
        "total_asupan": {
            "kalori": round(total_kalori, 1),
            "protein": round(total_protein, 1),
            "lemak": round(total_lemak, 1),
            "karbo": round(total_karbo, 1)
        },
        "persentase_akg": persentase_akg
    }