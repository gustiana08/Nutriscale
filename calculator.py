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