import streamlit as st
import pandas as pd
import hmac
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))

def tanggal_hari_ini():
    """Tanggal hari ini menurut WIB (server Streamlit berjalan di UTC,
    jadi datetime.now() polos bisa mundur sehari pada pagi hari WIB)."""
    return datetime.now(WIB).date()
from database import (
    init_db,
    simpan_menu_harian,
    ambil_laporan_harian,
    cari_bahan_pangan,
    tambah_bahan_custom,
    update_bahan_pangan,
    update_bahan_massal,
    hapus_bahan_pangan,
    hapus_log_menu,
    ambil_log_dengan_id,
    ambil_bahan_editor,
    HARI_SEKOLAH,
    simpan_rencana_hari,
    ambil_rencana_mingguan,
    hapus_rencana_menu,
    salin_rencana_hari,
)
from calculator import (
    konversi_berat,
    hitung_nutrisi_bahan,
    perbarui_keranjang,
    TARGET_AKG,
    hitung_pemenuhan_akg,
)
from exporter import export_to_excel, export_to_csv, export_to_word
import altair as alt

# Inisialisasi Database
init_db()

st.set_page_config(page_title="GiziKu — Perencanaan & Pencatatan Gizi SPPG", page_icon="🥗", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------
# GERBANG LOGIN (opsional, via Streamlit Secrets)
# ---------------------------------------------------------
# Bila secret GIZIKU_PASSWORD disetel, seluruh aplikasi terkunci di
# balik satu kata sandi bersama (satu akun bersama untuk petugas
# SPPG, bukan akun per pengguna). Bila secret tidak disetel — atau
# secrets tidak tersedia (mis. jalan lokal tanpa secrets.toml) —
# aplikasi tetap berjalan TERBUKA seperti semula, tanpa pesan apa
# pun yang membocorkan ada/tidaknya kata sandi. Kata sandi tidak
# pernah ditulis di repository; yang tersimpan di sini hanya cara
# membacanya dari Secrets.
def _sandi_aplikasi():
    try:
        sandi = st.secrets.get("GIZIKU_PASSWORD")
    except Exception:
        return None
    if isinstance(sandi, str) and sandi.strip():
        return sandi
    return None


def _gerbang_login():
    sandi = _sandi_aplikasi()
    if sandi is None:
        return
    if st.session_state.get("giziku_login"):
        return
    st.markdown("## GiziKu")
    st.caption("Masuk dengan kata sandi petugas untuk membuka aplikasi.")
    with st.form("form_login_giziku"):
        masukan = st.text_input("Kata sandi", type="password")
        tombol = st.form_submit_button("Masuk", type="primary")
    if tombol:
        if isinstance(masukan, str) and hmac.compare_digest(masukan, sandi):
            st.session_state["giziku_login"] = True
            st.rerun()
        else:
            st.error("Kata sandi salah. Coba lagi.")
    st.stop()


_gerbang_login()

# =========================================================
# TEMA VISUAL — style.css + .streamlit/config.toml
# =========================================================

# Muat CSS eksternal jika ada
import os
_CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
if os.path.exists(_CSS_PATH):
    with open(_CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Seluruh tema visual tinggal di style.css dan .streamlit/config.toml

# ---------------------------------------------------------
# SIDEBAR — identitas, navigasi halaman, ringkasan hari ini
# ---------------------------------------------------------
_HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
_BULAN_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]

def _fmt_angka(x):
    """Format angka gaya Indonesia: 1.166,5."""
    s = f"{float(x):,.1f}"
    return s.replace(",", " ").replace(".", ",").replace(" ", ".")

def _fmt_tanggal_id(tgl):
    return f"{_HARI_ID[tgl.weekday()]}, {tgl.day} {_BULAN_ID[tgl.month - 1]} {tgl.year}"

def _tabel_gizi_keranjang(keranjang):
    """Menghitung berat bersih + gizi untuk tiap item keranjang (format
    item sama dengan keranjang Input Menu Harian). Dipakai halaman
    Perencanaan Mingguan; halaman Input memakai loop inline-nya sendiri
    yang sudah terverifikasi dan tidak diubah."""
    baris = []
    for item in keranjang:
        _, berat_bersih = konversi_berat(item["Berat Kotor (g)"], item["% BDD"], "kotor")
        nutrisi = hitung_nutrisi_bahan(berat_bersih, item["kal_100"], item["prot_100"], item["lem_100"], item["karb_100"])
        baris.append({
            "Komposisi Makanan": item["Komposisi Makanan"],
            "% BDD": item["% BDD"],
            "Berat Kotor (g)": round(float(item["Berat Kotor (g)"]), 1),
            "Berat Bersih (g)": round(berat_bersih, 1),
            "Energi (kcal)": nutrisi["kalori"],
            "Protein (g)": nutrisi["protein"],
            "Lemak (g)": nutrisi["lemak"],
            "Karbohidrat (g)": nutrisi["karbohidrat"],
        })
    return pd.DataFrame(baris)

with st.sidebar:
    st.markdown("""
    <div class="side-brand">
        <div class="side-brand-mark">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 19C5 10.5 11.5 4.5 20 4.5c0 8.5-6 14.5-15 14.5Z"/>
                <path d="M5 19c3-5.5 7-9.5 12-12"/>
            </svg>
        </div>
        <div>
            <div class="side-brand-name">GiziKu</div>
            <div class="side-brand-sub">SPPG &middot; Dapur Pusat</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="side-label">Menu</div>', unsafe_allow_html=True)
    halaman = st.radio(
        "Navigasi halaman",
        ["Input Menu Harian", "Laporan & Rekapitulasi Gizi", "Database & Kelola Bahan", "Perencanaan Mingguan"],
        key="nav_halaman",
        label_visibility="collapsed",
    )
    # Kartu ringkasan hari ini — data asli dari log menu tersimpan.
    _hari_ini = tanggal_hari_ini()
    _df_ini = ambil_laporan_harian(_hari_ini.strftime("%Y-%m-%d"), _hari_ini.strftime("%Y-%m-%d"))
    if not _df_ini.empty:
        _energi_ini = _fmt_angka(_df_ini["energi_kcal"].sum())
        _menu_ini = int(_df_ini["nama_menu"].nunique())
        _isi_ini = (f'<div class="side-today-val">{_energi_ini} <span>kkal</span></div>'
                    f'<div class="side-today-sub">{_menu_ini} menu tercatat</div>')
    else:
        _isi_ini = '<div class="side-today-sub">Belum ada menu tercatat hari ini.</div>'
    st.markdown('<div class="side-label">Hari Ini</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="side-today"><div class="side-today-lab">Energi tersaji &middot; {_fmt_tanggal_id(_hari_ini)}</div>{_isi_ini}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="side-note">Perencanaan menu, pencatatan sajian harian, dan pengelolaan bahan pangan untuk Satuan Pelayanan Pemenuhan Gizi (SPPG).</div>',
        unsafe_allow_html=True,
    )
    # Tombol keluar hanya muncul bila gerbang login aktif (kata sandi
    # disetel). Pada mode terbuka tidak ada tombol ini sama sekali.
    if _sandi_aplikasi() is not None and st.session_state.get("giziku_login"):
        if st.button("Keluar", key="tombol_keluar"):
            st.session_state.pop("giziku_login", None)
            st.rerun()

# Kepala halaman utama: judul halaman aktif + tanggal hari ini (WIB).
st.markdown(f"""
<div class="page-head">
    <h1>{halaman}</h1>
    <span>{_fmt_tanggal_id(tanggal_hari_ini())}</span>
</div>
""", unsafe_allow_html=True)

# =========================================================
# HALAMAN 1: INPUT MENU HARIAN
# =========================================================
if halaman == "Input Menu Harian":
    st.subheader("Pencatatan Menu Sajian Harian")

    if 'flash_tab1' in st.session_state:
        st.success(st.session_state.pop('flash_tab1'))

    # Ringkasan hari ini — total menu tersimpan hari ini + porsi energi
    # dari tiap makronutrien (protein x4, lemak x9, karbohidrat x4 kkal).
    # Kartu memakai flex-wrap agar tetap terbaca di layar HP.
    _df_hari_ini = ambil_laporan_harian(_hari_ini.strftime("%Y-%m-%d"), _hari_ini.strftime("%Y-%m-%d"))
    if not _df_hari_ini.empty:
        _e = float(_df_hari_ini["energi_kcal"].sum())
        _p = float(_df_hari_ini["protein_g"].sum())
        _l = float(_df_hari_ini["lemak_g"].sum())
        _k = float(_df_hari_ini["karbo_g"].sum())
        _e_prot, _e_lem, _e_karb = _p * 4, _l * 9, _k * 4
        _e_makro = _e_prot + _e_lem + _e_karb
        if _e_makro > 0:
            _bagi = (f"Protein {_e_prot / _e_makro * 100:.0f}% &middot; "
                     f"Lemak {_e_lem / _e_makro * 100:.0f}% &middot; "
                     f"Karbohidrat {_e_karb / _e_makro * 100:.0f}% dari energi makro")
        else:
            _bagi = "Belum ada kandungan makro tercatat."
        _n_menu_ini = int(_df_hari_ini["nama_menu"].nunique())
        st.markdown(
            f'<div class="today-sum">'
            f'<div class="today-stat"><div class="today-stat-lab">Energi</div><div class="today-stat-val">{_fmt_angka(_e)} <span>kkal</span></div></div>'
            f'<div class="today-stat"><div class="today-stat-lab">Protein</div><div class="today-stat-val">{_fmt_angka(_p)} <span>g</span></div></div>'
            f'<div class="today-stat"><div class="today-stat-lab">Lemak</div><div class="today-stat-val">{_fmt_angka(_l)} <span>g</span></div></div>'
            f'<div class="today-stat"><div class="today-stat-lab">Karbohidrat</div><div class="today-stat-val">{_fmt_angka(_k)} <span>g</span></div></div>'
            f'</div>'
            f'<div class="today-sum-sub">{_n_menu_ini} menu tercatat hari ini &middot; {_bagi}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("Belum ada menu tersimpan untuk hari ini — ringkasan muncul setelah menu pertama disimpan.")
    
    col_tgl, col_siklus, col_porsi = st.columns(3)
    with col_tgl:
        tgl_saji = st.date_input("Tanggal Penyajian", tanggal_hari_ini())
    with col_siklus:
        # Siklus Hari mengikuti nama hari dari tanggal yang dipilih. Pilihan
        # manual pengguna tetap dihormati selama tanggalnya tidak berubah.
        HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        if st.session_state.get("_tgl_untuk_siklus") != tgl_saji:
            st.session_state["pilih_siklus"] = HARI_ID[tgl_saji.weekday()]
            st.session_state["_tgl_untuk_siklus"] = tgl_saji
        siklus = st.selectbox("Siklus Hari", HARI_ID, key="pilih_siklus")
    with col_porsi:
        porsi_makan = st.selectbox("Porsi Makanan", ["Standard / Biasa", "Kecil", "Besar"])

    nama_menu = st.text_input("Nama Menu / Hidangan", placeholder="Contoh: Ayam Goreng Mentega + Nasi Putih")
    
    st.markdown("---")
    st.markdown("### Cari & Tambah Bahan Makanan")
    st.caption("Ketik kata kunci bahan, pilih yang cocok, lalu tentukan berat kotor awal.")

    # Inisialisasi Keranjang Menu Harian di Session State
    if 'keranjang_sppg' not in st.session_state:
        st.session_state.keranjang_sppg = []

    # 1. FORM INPUT PENCARIAN & PENAMBAHAN BAHAN
    keyword_cari = st.text_input("Ketik Kata Kunci Bahan (misal: Ayam, Nasi, Telur, Daging):", "", key="input_cari_bahan")
    
    data_hasil_search = cari_bahan_pangan(keyword_cari.strip(), limit=51) if keyword_cari.strip() else []
    hasil_dibatasi = len(data_hasil_search) > 50
    if hasil_dibatasi:
        data_hasil_search = data_hasil_search[:50]
    
    col_pilih, col_kotor, col_btn = st.columns([4, 2, 1])
    
    with col_pilih:
        if data_hasil_search:
            opsi_dict = {f"{b['nama']} (BDD: {b['bdd']}%)": b for b in data_hasil_search}
            pilihan_label = st.selectbox("Pilih Bahan dari List Hasil Pencarian:", list(opsi_dict.keys()))
            bahan_terpilih = opsi_dict[pilihan_label]
            if hasil_dibatasi:
                st.caption("Menampilkan 50 hasil pertama — persempit kata kunci untuk melihat bahan lainnya.")
        else:
            if keyword_cari.strip():
                st.warning("Tidak ada bahan makanan yang cocok dengan kata kunci tersebut.")
            bahan_terpilih = None

    with col_kotor:
        berat_kotor_input = st.number_input("Berat Kotor Awal (Gram):", min_value=1.0, value=100.0, step=10.0)

    with col_btn:
        st.write("")
        st.write("")
        if st.button("Tambah", type="primary", width="stretch"):
            if bahan_terpilih:
                bdd = float(bahan_terpilih['bdd']) if bahan_terpilih['bdd'] > 0 else 100.0
                
                # Simpan data mentah gizi per 100g untuk keperluan perhitungan ulang dinamis
                st.session_state.keranjang_sppg.append({
                    "Komposisi Makanan": bahan_terpilih['nama'],
                    "% BDD": bdd,
                    "Berat Kotor (g)": float(berat_kotor_input),
                    "kal_100": float(bahan_terpilih['kalori']),
                    "prot_100": float(bahan_terpilih['protein']),
                    "lem_100": float(bahan_terpilih['lemak']),
                    "karb_100": float(bahan_terpilih['karbohidrat'])
                })
                st.toast(f"{bahan_terpilih['nama']} ditambahkan ke menu.")
            else:
                st.error("Silakan pilih bahan makanan terlebih dahulu.")

    # 2. TABEL SAJIAN INTERAKTIF (BERAT KOTOR BISA DIEDIT LANGSUNG)
    st.markdown("---")
    st.markdown("##### Tabel Sajian Menu & Kalkulasi Gizi")
    st.caption("Tips: ubah angka pada kolom **Berat Kotor (g)** langsung di tabel — nilai gizi menyesuaikan otomatis.")

    if st.session_state.keranjang_sppg:
        df_cart = pd.DataFrame(st.session_state.keranjang_sppg)

        # Hitung Nilai Turunan menggunakan modul calculator
        berat_bersih_list = []
        energi_list = []
        protein_list = []
        lemak_list = []
        karbo_list = []

        for _, row in df_cart.iterrows():
            _, berat_bersih = konversi_berat(row["Berat Kotor (g)"], row["% BDD"], "kotor")
            nutrisi = hitung_nutrisi_bahan(berat_bersih, row["kal_100"], row["prot_100"], row["lem_100"], row["karb_100"])
            
            berat_bersih_list.append(round(berat_bersih, 1))
            energi_list.append(nutrisi["kalori"])
            protein_list.append(nutrisi["protein"])
            lemak_list.append(nutrisi["lemak"])
            karbo_list.append(nutrisi["karbohidrat"])

        df_cart["Berat Bersih (g)"] = berat_bersih_list
        df_cart["Energi (kcal)"] = energi_list
        df_cart["Protein (g)"] = protein_list
        df_cart["Lemak (g)"] = lemak_list
        df_cart["Karbohidrat (g)"] = karbo_list
        df_cart["Berat Kotor (g)"] = df_cart["Berat Kotor (g)"].round(1)

        # Tampilkan Tabel Data Editor yang Hanya Mengizinkan Edit "Berat Kotor (g)"
        edited_cart = st.data_editor(
            df_cart[["Komposisi Makanan", "% BDD", "Berat Kotor (g)", "Berat Bersih (g)", "Energi (kcal)", "Protein (g)", "Lemak (g)", "Karbohidrat (g)"]],
            width="stretch",
            num_rows="dynamic", # Memungkinkan hapus baris langsung di tabel
            key="tabel_menu_interaktif",
            disabled=["Komposisi Makanan", "% BDD", "Berat Bersih (g)", "Energi (kcal)", "Protein (g)", "Lemak (g)", "Karbohidrat (g)"],
            column_config={
                "Berat Kotor (g)": st.column_config.NumberColumn("Berat Kotor (g)", min_value=1.0, step=1.0, required=True, format="%.1f"),
                "% BDD": st.column_config.NumberColumn("% BDD", format="%.1f%%"),
                "Berat Bersih (g)": st.column_config.NumberColumn("Berat Bersih (g)", format="%.1f"),
                "Energi (kcal)": st.column_config.NumberColumn("Energi (kcal)", format="%.1f"),
                "Protein (g)": st.column_config.NumberColumn("Protein (g)", format="%.1f"),
                "Lemak (g)": st.column_config.NumberColumn("Lemak (g)", format="%.1f"),
                "Karbohidrat (g)": st.column_config.NumberColumn("Karbohidrat (g)", format="%.1f"),
            }
        )

        # Sinkronkan keranjang dengan hasil edit tabel (berat diubah / baris dihapus).
        # perbarui_keranjang tidak memutasi item lama sebelum perbandingan, jadi
        # perubahan berat benar-benar terdeteksi dan memicu rerun — nilai turunan
        # (berat bersih & gizi) lalu dihitung ulang dari berat yang baru.
        baris_editor = [(index, row["Berat Kotor (g)"]) for index, row in edited_cart.iterrows()]
        keranjang_baru, ada_perubahan = perbarui_keranjang(st.session_state.keranjang_sppg, baris_editor)
        if ada_perubahan:
            st.session_state.keranjang_sppg = keranjang_baru
            st.rerun()

        # Hitung Total Akumulasi Nutrisi
        total_kotor = edited_cart["Berat Kotor (g)"].sum()
        total_bersih = edited_cart["Berat Bersih (g)"].sum()
        total_energi = edited_cart["Energi (kcal)"].sum()
        total_protein = edited_cart["Protein (g)"].sum()
        total_lemak = edited_cart["Lemak (g)"].sum()
        total_karbo = edited_cart["Karbohidrat (g)"].sum()

        st.info(
            f"**Akumulasi Total Sajian Menu Ini:**\n\n"
            f"• **Gramasi:** Berat Kotor = **{total_kotor:.1f} g** | Berat Bersih = **{total_bersih:.1f} g**\n"
            f"• **Kandungan Gizi:** Energi = **{total_energi:.1f} kcal** | Protein = **{total_protein:.1f} g** | Lemak = **{total_lemak:.1f} g** | Karbohidrat = **{total_karbo:.1f} g**"
        )

        col_kosong, col_simpan = st.columns([1, 2])
        with col_kosong:
            if st.button("Kosongkan Tabel"):
                st.session_state.keranjang_sppg = []
                st.rerun()

        with col_simpan:
            if st.button("Simpan Menu Hari Ini", type="primary", width="stretch"):
                # Validasi: nama menu wajib diisi
                if not nama_menu.strip():
                    st.error("**Nama Menu / Hidangan** wajib diisi sebelum menyimpan.")
                else:
                    daftar_bahan = []
                    for _, row in edited_cart.iterrows():
                        daftar_bahan.append({
                            "nama_menu": nama_menu.strip(),
                            "bahan_pangan": row["Komposisi Makanan"],
                            "berat_kotor": row["Berat Kotor (g)"],
                            "berat_bersih": row["Berat Bersih (g)"],
                            "bdd": row["% BDD"],
                            "energi_kcal": row["Energi (kcal)"],
                            "protein_g": row["Protein (g)"],
                            "lemak_g": row["Lemak (g)"],
                            "karbo_g": row["Karbohidrat (g)"]
                        })
                    
                    simpan_menu_harian(tgl_saji.strftime("%Y-%m-%d"), siklus, porsi_makan, daftar_bahan)
                    st.session_state.keranjang_sppg = []
                    st.session_state['flash_tab1'] = "Data menu harian berhasil disimpan."
                    st.rerun()
    else:
        st.caption("Belum ada bahan makanan yang ditambahkan. Gunakan pencarian di atas untuk memasukkan bahan baku.")

# =========================================================
# TAB 2: LAPORAN & REKAPITULASI
# =========================================================
elif halaman == "Laporan & Rekapitulasi Gizi":
    st.subheader("Filter Laporan Gizi Harian SPPG")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tgl_mulai = st.date_input("Dari Tanggal", tanggal_hari_ini())
    with col_f2:
        tgl_selesai = st.date_input("Sampai Tanggal", tanggal_hari_ini())
        
    if 'flash_tab2' in st.session_state:
        st.success(st.session_state.pop('flash_tab2'))

    if st.button("Tampilkan Laporan", type="primary"):
        if tgl_mulai > tgl_selesai:
            # Rentang tidak valid: bersihkan laporan lama agar tidak menyesatkan
            st.session_state.pop('laporan_data', None)
            st.error("Tanggal 'Dari' tidak boleh setelah tanggal 'Sampai'. Periksa lagi rentangnya.")
        else:
            df_laporan = ambil_laporan_harian(tgl_mulai.strftime("%Y-%m-%d"), tgl_selesai.strftime("%Y-%m-%d"))
            
            if df_laporan.empty:
                # Filter baru hasilnya kosong: laporan lama WAJIB dibersihkan,
                # kalau tidak laporan basi tetap tampil dan bisa terunduh.
                st.session_state.pop('laporan_data', None)
                st.warning("Belum ada data menu yang tersimpan pada rentang tanggal tersebut.")
            else:
                # Simpan ke session state agar bisa digunakan oleh tombol download
                st.session_state['laporan_data'] = df_laporan
                st.session_state['laporan_tgl_mulai'] = tgl_mulai.strftime("%Y-%m-%d")
                st.session_state['laporan_tgl_selesai'] = tgl_selesai.strftime("%Y-%m-%d")

    # Tampilkan laporan jika ada di session state
    if 'laporan_data' in st.session_state and not st.session_state['laporan_data'].empty:
        df_laporan = st.session_state['laporan_data']
        tgl_mulai_str = st.session_state['laporan_tgl_mulai']
        tgl_selesai_str = st.session_state['laporan_tgl_selesai']
        
        st.markdown("### Ringkasan Konsumsi Gizi Per Hari")
        
        rekap_harian = df_laporan.groupby("tanggal").agg({
            "berat_kotor": "sum",
            "berat_bersih": "sum",
            "energi_kcal": "sum",
            "protein_g": "sum",
            "lemak_g": "sum",
            "karbo_g": "sum"
        }).reset_index()
        
        st.dataframe(rekap_harian.round(1), width="stretch")

        # --- Kecukupan gizi vs AKG 2019 ---
        st.markdown("### Kecukupan Gizi (AKG 2019)")
        _daftar_akg = list(TARGET_AKG.keys())
        kelompok_akg = st.selectbox(
            "Kelompok umur AKG",
            _daftar_akg,
            index=_daftar_akg.index("10-12 tahun (Laki-laki)"),
            key="pilih_akg",
        )
        _baris_akg = []
        for _, _r in rekap_harian.iterrows():
            _cek = hitung_pemenuhan_akg({
                "energi": float(_r["energi_kcal"]),
                "protein": float(_r["protein_g"]),
                "lemak": float(_r["lemak_g"]),
                "karbohidrat": float(_r["karbo_g"]),
            }, kelompok_akg)
            _persen = [_cek[z]["persen"] for z in ("energi", "protein", "lemak", "karbohidrat")]
            _status = [_cek[z]["status"] for z in ("energi", "protein", "lemak", "karbohidrat")]
            _baris_akg.append({
                "tanggal": _r["tanggal"],
                "energi_pct": _cek["energi"]["persen"],
                "protein_pct": _cek["protein"]["persen"],
                "lemak_pct": _cek["lemak"]["persen"],
                "karbo_pct": _cek["karbohidrat"]["persen"],
                # Penilaian hari memakai persen terendah dari keempat zat gizi.
                "penilaian": _status[_persen.index(min(_persen))],
            })
        df_akg = pd.DataFrame(_baris_akg)
        st.dataframe(
            df_akg,
            width="stretch",
            column_config={
                "tanggal": st.column_config.TextColumn("Tanggal"),
                "energi_pct": st.column_config.NumberColumn("Energi (% AKG)", format="%.1f%%"),
                "protein_pct": st.column_config.NumberColumn("Protein (% AKG)", format="%.1f%%"),
                "lemak_pct": st.column_config.NumberColumn("Lemak (% AKG)", format="%.1f%%"),
                "karbo_pct": st.column_config.NumberColumn("Karbohidrat (% AKG)", format="%.1f%%"),
                "penilaian": st.column_config.TextColumn("Penilaian"),
            },
        )
        st.caption(
            "Target AKG 2019 (Permenkes No. 28 Tahun 2019). Penilaian: Terpenuhi bila "
            ">= 100%, Kurang bila 80-99%, Sangat kurang bila < 80%; penilaian satu hari "
            "memakai persen terendah dari keempat zat gizi. Lembar Kecukupan AKG ikut "
            "terunduh pada file Excel di bawah."
        )

        st.markdown("### Grafik Asupan Energi Harian (kcal)")
        # Pakai Altair eksplisit dengan sumbu Y selalu mulai dari 0.
        # st.line_chart dengan data 1 hari menghasilkan domain sumbu yang
        # degenerate sehingga label sumbunya kacau / muncul angka negatif.
        data_grafik = rekap_harian.copy()
        data_grafik["tanggal"] = pd.to_datetime(data_grafik["tanggal"])
        grafik = (
            alt.Chart(data_grafik)
            .mark_line(point=True, color="#1c4fa0")
            .encode(
                x=alt.X("tanggal:T", title="Tanggal"),
                y=alt.Y("energi_kcal:Q", title="Energi (kcal)", scale=alt.Scale(zero=True, nice=True)),
                tooltip=[
                    alt.Tooltip("tanggal:T", title="Tanggal"),
                    alt.Tooltip("energi_kcal:Q", title="Energi (kcal)", format=".1f"),
                ],
            )
        )
        st.altair_chart(grafik, width="stretch")
        
        st.markdown("### Rincian Lengkap Bahan & Menu (Laporan SPPG)")
        st.dataframe(df_laporan, width="stretch")
        
        # Tombol Ekspor — CSV, Excel, dan Word
        st.markdown("### Unduh Laporan")
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        with col_dl1:
            csv_data = export_to_csv(df_laporan)
            st.download_button(
                label="Unduh CSV",
                data=csv_data,
                file_name=f"Laporan_Gizi_SPPG_{tgl_mulai_str}_sd_{tgl_selesai_str}.csv",
                mime="text/csv",
                width="stretch",
            )
        
        with col_dl2:
            excel_data = export_to_excel(df_laporan, akg=(kelompok_akg, df_akg))
            st.download_button(
                label="Unduh Excel",
                data=excel_data,
                file_name=f"Laporan_Gizi_SPPG_{tgl_mulai_str}_sd_{tgl_selesai_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        
        with col_dl3:
            word_data = export_to_word(df_laporan, tgl_mulai_str, tgl_selesai_str)
            st.download_button(
                label="Unduh Word",
                data=word_data,
                file_name=f"Laporan_Gizi_SPPG_{tgl_mulai_str}_sd_{tgl_selesai_str}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
            )

        # --- Hapus entri laporan (per baris log) ---
        st.markdown("### Hapus Entri Laporan")
        st.caption("Salah simpan? Pilih entri log pada rentang laporan ini yang mau dihapus permanen.")
        df_log = ambil_log_dengan_id(tgl_mulai_str, tgl_selesai_str)
        if not df_log.empty:
            opsi_hapus_log = {
                f"{r['tanggal']} — {r['nama_menu']} — {r['bahan_pangan']} ({float(r['berat_kotor']):.1f} g)": int(r['id'])
                for _, r in df_log.iterrows()
            }
            pilihan_hapus_log = st.multiselect("Entri yang akan dihapus:", list(opsi_hapus_log.keys()), key="hapus_log_pilihan")
            konfirmasi_hapus_log = st.checkbox("Saya yakin mau menghapus entri terpilih secara permanen.", key="hapus_log_konfirmasi")
            if st.button("Hapus Entri Terpilih", disabled=not (pilihan_hapus_log and konfirmasi_hapus_log)):
                for label in pilihan_hapus_log:
                    hapus_log_menu(opsi_hapus_log[label])
                df_baru = ambil_laporan_harian(tgl_mulai_str, tgl_selesai_str)
                if df_baru.empty:
                    st.session_state.pop('laporan_data', None)
                else:
                    st.session_state['laporan_data'] = df_baru
                st.session_state['flash_tab2'] = f"{len(pilihan_hapus_log)} entri laporan berhasil dihapus."
                st.rerun()

# =========================================================
# TAB 3: DATABASE & KELOLA BAHAN PANGAN
# =========================================================
elif halaman == "Database & Kelola Bahan":
    st.subheader("Database Bahan Pangan")

    if 'flash_tab3' in st.session_state:
        st.success(st.session_state.pop('flash_tab3'))
    
    sub_tab1, sub_tab2 = st.tabs(["List & Edit Bahan", "Tambah Bahan Baru"])
    
    # --- SUB-TAB 1: LIST & EDIT BAHAN ---
    with sub_tab1:
        search_kw = st.text_input("Cari Nama Bahan Makanan:", "", placeholder="Contoh: Ayam, Nasi, Tempe...").strip()
        
        df_db = ambil_bahan_editor(search_kw)
        
        st.caption(f"Menampilkan {len(df_db)} bahan pangan.")
        
        if not df_db.empty:
            st.info("**Petunjuk:** ubah angka nutrisi / BDD langsung di dalam tabel, lalu klik **Simpan Perubahan Data**.")
            
            edited_df_db = st.data_editor(
                df_db,
                key="db_editor_tab3",
                width="stretch",
                disabled=["id"],
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "nama": st.column_config.TextColumn("Nama Bahan", required=True),
                    "kalori": st.column_config.NumberColumn("Kalori (kcal/100g)", min_value=0.0, max_value=1000.0, format="%.1f"),
                    "protein": st.column_config.NumberColumn("Protein (g/100g)", min_value=0.0, max_value=100.0, format="%.2f"),
                    "lemak": st.column_config.NumberColumn("Lemak (g/100g)", min_value=0.0, max_value=100.0, format="%.2f"),
                    "karbohidrat": st.column_config.NumberColumn("Karbohidrat (g/100g)", min_value=0.0, max_value=100.0, format="%.2f"),
                    "bdd": st.column_config.NumberColumn("% BDD", min_value=1.0, max_value=100.0, format="%.1f")
                }
            )
            
            if st.button("Simpan Perubahan Data", type="primary"):
                terlewat = 0
                baris_valid = []
                for _, row in edited_df_db.iterrows():
                    # Lewati baris yang ada sel kosongnya (NaN) — jangan sampai
                    # merusak data atau bikin proses simpan gagal di tengah jalan.
                    if pd.isna(row["nama"]) or any(pd.isna(row[k]) for k in ["kalori", "protein", "lemak", "karbohidrat", "bdd"]):
                        terlewat += 1
                        continue
                    baris_valid.append((
                        int(row["id"]),
                        row["nama"],
                        float(row["kalori"]),
                        float(row["protein"]),
                        float(row["lemak"]),
                        float(row["karbohidrat"]),
                        float(row["bdd"])
                    ))
                # Satu transaksi untuk semua baris: tersimpan semua atau
                # tidak sama sekali (atomik).
                update_bahan_massal(baris_valid)
                pesan_simpan = "Perubahan data bahan pangan berhasil disimpan."
                if terlewat:
                    pesan_simpan += f" {terlewat} baris dilewati karena ada sel yang kosong."
                st.session_state['flash_tab3'] = pesan_simpan
                st.rerun()

            st.markdown("##### Hapus Bahan Pangan")
            st.caption("Hapus bahan yang salah input atau tidak dipakai lagi (pakai pencarian di atas buat menyaring daftar). Penghapusan bersifat permanen.")
            opsi_hapus_bahan = {f"{r['nama']} (ID {int(r['id'])})": int(r['id']) for _, r in df_db.iterrows()}
            pilihan_hapus_bahan = st.multiselect("Bahan yang akan dihapus:", list(opsi_hapus_bahan.keys()), key="hapus_bahan_pilihan")
            konfirmasi_hapus_bahan = st.checkbox("Saya yakin mau menghapus bahan terpilih secara permanen.", key="hapus_bahan_konfirmasi")
            if st.button("Hapus Bahan Terpilih", disabled=not (pilihan_hapus_bahan and konfirmasi_hapus_bahan)):
                for label in pilihan_hapus_bahan:
                    hapus_bahan_pangan(opsi_hapus_bahan[label])
                st.session_state['flash_tab3'] = f"{len(pilihan_hapus_bahan)} bahan berhasil dihapus."
                st.rerun()
        else:
            st.warning("Bahan makanan tidak ditemukan di database.")

    # --- SUB-TAB 2: TAMBAH BAHAN BARU ---
    with sub_tab2:
        st.markdown("##### Form Tambah Bahan Pangan Baru ke Database")
        with st.form("form_tambah_tab3", clear_on_submit=True):
            tb_nama = st.text_input("Nama Bahan Makanan Baru *", placeholder="Misal: Daging Sapi Wagyu")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                tb_kal = st.number_input("Kalori (kcal/100g)", min_value=0.0, max_value=1000.0, step=1.0)
                tb_prot = st.number_input("Protein (g/100g)", min_value=0.0, max_value=100.0, step=0.1)
            with col_b:
                tb_lemak = st.number_input("Lemak (g/100g)", min_value=0.0, max_value=100.0, step=0.1)
                tb_karbo = st.number_input("Karbohidrat (g/100g)", min_value=0.0, max_value=100.0, step=0.1)
            with col_c:
                tb_bdd = st.number_input("% BDD (Bagian Dapat Dimakan)", min_value=1.0, max_value=100.0, value=100.0, step=1.0)
                
            submitted_tab3 = st.form_submit_button("Simpan Bahan Baru", type="primary")
            
            if submitted_tab3:
                if not tb_nama.strip():
                    st.warning("Nama bahan makanan wajib diisi.")
                else:
                    tambah_bahan_custom(tb_nama.strip(), tb_kal, tb_prot, tb_lemak, tb_karbo, tb_bdd)
                    st.session_state['flash_tab3'] = f"**{tb_nama.strip()}** berhasil ditambahkan ke database."
                    st.rerun()

# =========================================================
# HALAMAN 4: PERENCANAAN MINGGUAN (Senin-Jumat)
# =========================================================
elif halaman == "Perencanaan Mingguan":
    st.subheader("Perencanaan Menu Mingguan")

    if 'flash_rencana' in st.session_state:
        st.success(st.session_state.pop('flash_rencana'))

    _senin_ini = tanggal_hari_ini() - timedelta(days=tanggal_hari_ini().weekday())
    tgl_minggu = st.date_input("Minggu mulai (pilih tanggal apa pun dalam minggu itu)", _senin_ini, key="rencana_minggu")
    senin = tgl_minggu - timedelta(days=tgl_minggu.weekday())
    senin_str = senin.strftime("%Y-%m-%d")
    jumat = senin + timedelta(days=4)
    st.caption(f"Rencana minggu {_fmt_tanggal_id(senin)} s/d {_fmt_tanggal_id(jumat)}.")

    # --- 1. Susun rencana satu hari dari bahan ---
    st.markdown("### Susun Rencana Hari")
    col_rh, col_rn = st.columns(2)
    with col_rh:
        hari_rencana = st.selectbox("Hari", HARI_SEKOLAH, key="rencana_hari")
    with col_rn:
        nama_menu_rencana = st.text_input("Nama Menu / Hidangan", placeholder="Contoh: Nasi + Ayam Kecap + Tumis Buncis", key="rencana_nama_menu")

    if 'keranjang_rencana' not in st.session_state:
        st.session_state.keranjang_rencana = []

    keyword_rencana = st.text_input("Ketik Kata Kunci Bahan:", "", key="rencana_cari")
    hasil_rencana = cari_bahan_pangan(keyword_rencana.strip(), limit=51) if keyword_rencana.strip() else []
    if len(hasil_rencana) > 50:
        hasil_rencana = hasil_rencana[:50]

    col_rp, col_rk, col_rb = st.columns([4, 2, 1])
    with col_rp:
        if hasil_rencana:
            opsi_rencana = {f"{b['nama']} (BDD: {b['bdd']}%)": b for b in hasil_rencana}
            label_rencana = st.selectbox("Pilih Bahan:", list(opsi_rencana.keys()), key="rencana_pilih")
            bahan_rencana = opsi_rencana[label_rencana]
        else:
            if keyword_rencana.strip():
                st.warning("Tidak ada bahan makanan yang cocok dengan kata kunci tersebut.")
            bahan_rencana = None
    with col_rk:
        berat_rencana = st.number_input("Berat Kotor (g):", min_value=1.0, value=100.0, step=10.0, key="rencana_kotor")
    with col_rb:
        st.write("")
        st.write("")
        if st.button("Tambah", type="primary", width="stretch", key="rencana_tambah"):
            if bahan_rencana:
                bdd_r = float(bahan_rencana['bdd']) if bahan_rencana['bdd'] > 0 else 100.0
                st.session_state.keranjang_rencana.append({
                    "Komposisi Makanan": bahan_rencana['nama'],
                    "% BDD": bdd_r,
                    "Berat Kotor (g)": float(berat_rencana),
                    "kal_100": float(bahan_rencana['kalori']),
                    "prot_100": float(bahan_rencana['protein']),
                    "lem_100": float(bahan_rencana['lemak']),
                    "karb_100": float(bahan_rencana['karbohidrat'])
                })
                st.toast(f"{bahan_rencana['nama']} ditambahkan ke rencana.")
                st.rerun()
            else:
                st.error("Silakan pilih bahan makanan terlebih dahulu.")

    if st.session_state.keranjang_rencana:
        df_rencana_cart = _tabel_gizi_keranjang(st.session_state.keranjang_rencana)
        st.dataframe(df_rencana_cart, width="stretch")
        st.info(
            f"**Total rencana {hari_rencana}:** Energi = **{df_rencana_cart['Energi (kcal)'].sum():.1f} kcal** | "
            f"Protein = **{df_rencana_cart['Protein (g)'].sum():.1f} g** | "
            f"Lemak = **{df_rencana_cart['Lemak (g)'].sum():.1f} g** | "
            f"Karbohidrat = **{df_rencana_cart['Karbohidrat (g)'].sum():.1f} g**"
        )
        col_rhps, col_rsv = st.columns(2)
        with col_rhps:
            hapus_cart = st.multiselect("Hapus bahan dari daftar:", df_rencana_cart["Komposisi Makanan"].tolist(), key="rencana_hapus_cart")
            if st.button("Hapus Bahan Terpilih", disabled=not hapus_cart):
                st.session_state.keranjang_rencana = [
                    it for it in st.session_state.keranjang_rencana
                    if it["Komposisi Makanan"] not in hapus_cart
                ]
                st.rerun()
        with col_rsv:
            if st.button("Simpan Rencana Hari Ini", type="primary", width="stretch"):
                if not nama_menu_rencana.strip():
                    st.error("**Nama Menu / Hidangan** wajib diisi sebelum menyimpan rencana.")
                else:
                    daftar_rencana = [{
                        "nama_menu": nama_menu_rencana.strip(),
                        "bahan_pangan": row["Komposisi Makanan"],
                        "berat_kotor": row["Berat Kotor (g)"],
                        "berat_bersih": row["Berat Bersih (g)"],
                        "bdd": row["% BDD"],
                        "energi_kcal": row["Energi (kcal)"],
                        "protein_g": row["Protein (g)"],
                        "lemak_g": row["Lemak (g)"],
                        "karbo_g": row["Karbohidrat (g)"]
                    } for _, row in df_rencana_cart.iterrows()]
                    simpan_rencana_hari(senin_str, hari_rencana, nama_menu_rencana.strip(), daftar_rencana)
                    st.session_state.keranjang_rencana = []
                    st.session_state['flash_rencana'] = f"Rencana {hari_rencana} ({nama_menu_rencana.strip()}) berhasil disimpan."
                    st.rerun()
    else:
        st.caption("Belum ada bahan pada daftar rencana hari ini.")

    # --- 2. Salin dari menu harian yang sudah tersimpan ---
    st.markdown("---")
    st.markdown("### Salin dari Menu Tersimpan")
    st.caption("Punya menu harian yang sudah jadi? Salin susunannya ke rencana minggu ini tanpa mengetik ulang.")
    tgl_salin = st.date_input("Tanggal menu tersimpan", tanggal_hari_ini(), key="rencana_tgl_salin")
    df_salin = ambil_laporan_harian(tgl_salin.strftime("%Y-%m-%d"), tgl_salin.strftime("%Y-%m-%d"))
    if df_salin.empty:
        st.caption("Tidak ada menu tersimpan pada tanggal tersebut.")
    else:
        menu_tersedia = sorted(df_salin["nama_menu"].unique().tolist())
        col_sm, col_sh, col_sb = st.columns([3, 2, 1])
        with col_sm:
            menu_salin = st.selectbox("Menu yang disalin:", menu_tersedia, key="rencana_menu_salin")
        with col_sh:
            hari_salin = st.selectbox("Ke hari:", HARI_SEKOLAH, key="rencana_hari_salin")
        with col_sb:
            st.write("")
            st.write("")
            if st.button("Salin", type="primary", width="stretch", key="rencana_tombol_salin"):
                baris_salin = df_salin[df_salin["nama_menu"] == menu_salin].to_dict("records")
                simpan_rencana_hari(senin_str, hari_salin, menu_salin, baris_salin)
                st.session_state['flash_rencana'] = f"Menu {menu_salin} disalin ke rencana {hari_salin}."
                st.rerun()

    # --- 3. Rekap minggu + aksi per hari ---
    st.markdown("---")
    st.markdown("### Rekap Minggu Ini")
    df_minggu = ambil_rencana_mingguan(senin_str)
    if df_minggu.empty:
        st.caption("Belum ada rencana pada minggu ini.")
    else:
        rekap_minggu = []
        for h in HARI_SEKOLAH:
            sub = df_minggu[df_minggu["hari"] == h]
            if sub.empty:
                continue
            rekap_minggu.append({
                "Hari": h,
                "Menu": ", ".join(sorted(sub["nama_menu"].unique().tolist())),
                "Energi (kcal)": round(float(sub["energi_kcal"].sum()), 1),
                "Protein (g)": round(float(sub["protein_g"].sum()), 1),
                "Lemak (g)": round(float(sub["lemak_g"].sum()), 1),
                "Karbohidrat (g)": round(float(sub["karbo_g"].sum()), 1),
            })
        st.dataframe(pd.DataFrame(rekap_minggu), width="stretch")
        st.info(
            f"**Total seminggu:** Energi = **{df_minggu['energi_kcal'].sum():.1f} kcal** | "
            f"Protein = **{df_minggu['protein_g'].sum():.1f} g** | "
            f"Lemak = **{df_minggu['lemak_g'].sum():.1f} g** | "
            f"Karbohidrat = **{df_minggu['karbo_g'].sum():.1f} g**"
        )
        with st.expander("Rincian bahan rencana minggu ini"):
            st.dataframe(df_minggu[["hari", "nama_menu", "bahan_pangan", "berat_kotor", "berat_bersih", "energi_kcal", "protein_g", "lemak_g", "karbo_g"]], width="stretch")

        st.markdown("#### Aksi Rencana")
        col_sa, col_sb2, col_sc = st.columns(3)
        with col_sa:
            st.caption("Salin satu hari ke hari lain")
            hari_asal = st.selectbox("Dari hari:", HARI_SEKOLAH, key="rencana_salin_dari")
            hari_tujuan = st.selectbox("Ke hari:", HARI_SEKOLAH, key="rencana_salin_ke")
            if st.button("Salin Hari", width="stretch"):
                jumlah = salin_rencana_hari(senin_str, hari_asal, hari_tujuan)
                st.session_state['flash_rencana'] = f"{jumlah} baris disalin dari {hari_asal} ke {hari_tujuan}."
                st.rerun()
        with col_sb2:
            st.caption("Hapus menu dari rencana")
            opsi_hapus_rencana = {
                f"{r['hari']} — {r['nama_menu']}": (r['hari'], r['nama_menu'])
                for _, r in df_minggu.drop_duplicates(subset=["hari", "nama_menu"]).iterrows()
            }
            pilihan_hapus_rencana = st.multiselect("Menu yang dihapus:", list(opsi_hapus_rencana.keys()), key="rencana_hapus_menu")
            if st.button("Hapus Menu Terpilih", disabled=not pilihan_hapus_rencana, width="stretch"):
                for label in pilihan_hapus_rencana:
                    h_hapus, m_hapus = opsi_hapus_rencana[label]
                    hapus_rencana_menu(senin_str, h_hapus, m_hapus)
                st.session_state['flash_rencana'] = f"{len(pilihan_hapus_rencana)} menu dihapus dari rencana."
                st.rerun()
        with col_sc:
            st.caption("Terapkan hari rencana ke menu harian")
            hari_terap = st.selectbox("Hari rencana:", HARI_SEKOLAH, key="rencana_terap_hari")
            tgl_terap = st.date_input("Tanggal penyajian:", tanggal_hari_ini(), key="rencana_terap_tgl")
            if st.button("Terapkan ke Menu Harian", type="primary", width="stretch"):
                sub_terap = df_minggu[df_minggu["hari"] == hari_terap]
                if sub_terap.empty:
                    st.error(f"Belum ada rencana untuk hari {hari_terap}.")
                else:
                    simpan_menu_harian(
                        tgl_terap.strftime("%Y-%m-%d"),
                        _HARI_ID[tgl_terap.weekday()],
                        "Standard / Biasa",
                        sub_terap.to_dict("records"),
                    )
                    st.session_state['flash_rencana'] = f"Rencana {hari_terap} diterapkan ke menu tanggal {tgl_terap.strftime('%Y-%m-%d')}."
                    st.rerun()

# ---------------------------------------------------------
# FOOTER KREDIT GITHUB
# ---------------------------------------------------------
st.markdown("---")
st.markdown("""
<div class="app-footer">
    GiziKu — platform pencatatan gizi untuk SPPG.<br>
    <span>Berdasarkan proyek terbuka <a href="https://github.com/rayrachman/nutriscale" target="_blank">NutriScale</a> oleh @rayrachman.</span>
</div>
""", unsafe_allow_html=True)