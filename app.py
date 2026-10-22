import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
from database import (
    init_db, 
    simpan_menu_harian, 
    ambil_laporan_harian, 
    cari_bahan_pangan, 
    tambah_bahan_custom, 
    update_bahan_pangan,
    hapus_bahan_pangan,
    hapus_log_menu,
    ambil_log_dengan_id,
    DB_PATH
)
from calculator import konversi_berat, hitung_nutrisi_bahan, perbarui_keranjang
from exporter import export_to_excel, export_to_csv, export_to_word
import altair as alt

# Inisialisasi Database
init_db()

st.set_page_config(page_title="GiziKu — Perencanaan & Pencatatan Gizi SPPG", page_icon="🥗", layout="wide")

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
# HEADER BANNER APLIKASI
# ---------------------------------------------------------
st.markdown("""
<div class="app-header">
    <div class="app-header-mark">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 19C5 10.5 11.5 4.5 20 4.5c0 8.5-6 14.5-15 14.5Z"/>
            <path d="M5 19c3-5.5 7-9.5 12-12"/>
        </svg>
    </div>
    <div>
        <h1>GiziKu</h1>
        <p>Perencanaan menu, pencatatan sajian harian, dan pengelolaan bahan pangan untuk Satuan Pelayanan Pemenuhan Gizi (SPPG).</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# TIGA TAB UTAMA APLIKASI
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "Input Menu Harian", 
    "Laporan & Rekapitulasi Gizi", 
    "Database & Kelola Bahan"
])

# =========================================================
# TAB 1: INPUT MENU HARIAN
# =========================================================
with tab1:
    st.subheader("Pencatatan Menu Sajian Harian")

    if 'flash_tab1' in st.session_state:
        st.success(st.session_state.pop('flash_tab1'))
    
    col_tgl, col_siklus, col_porsi = st.columns(3)
    with col_tgl:
        tgl_saji = st.date_input("Tanggal Penyajian", datetime.now())
    with col_siklus:
        siklus = st.selectbox("Siklus Hari", ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"])
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
    
    data_hasil_search = cari_bahan_pangan(keyword_cari.strip()) if keyword_cari.strip() else []
    
    col_pilih, col_kotor, col_btn = st.columns([4, 2, 1])
    
    with col_pilih:
        if data_hasil_search:
            opsi_dict = {f"{b['nama']} (BDD: {b['bdd']}%)": b for b in data_hasil_search}
            pilihan_label = st.selectbox("Pilih Bahan dari List Hasil Pencarian:", list(opsi_dict.keys()))
            bahan_terpilih = opsi_dict[pilihan_label]
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
with tab2:
    st.subheader("Filter Laporan Gizi Harian SPPG")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tgl_mulai = st.date_input("Dari Tanggal", datetime.now())
    with col_f2:
        tgl_selesai = st.date_input("Sampai Tanggal", datetime.now())
        
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
        
        st.markdown("### Grafik Asupan Energi Harian (kcal)")
        # Pakai Altair eksplisit dengan sumbu Y selalu mulai dari 0.
        # st.line_chart dengan data 1 hari menghasilkan domain sumbu yang
        # degenerate sehingga label sumbunya kacau / muncul angka negatif.
        data_grafik = rekap_harian.copy()
        data_grafik["tanggal"] = pd.to_datetime(data_grafik["tanggal"])
        grafik = (
            alt.Chart(data_grafik)
            .mark_line(point=True, color="#e8a33d")
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
            excel_data = export_to_excel(df_laporan)
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
with tab3:
    st.subheader("Database Bahan Pangan")

    if 'flash_tab3' in st.session_state:
        st.success(st.session_state.pop('flash_tab3'))
    
    sub_tab1, sub_tab2 = st.tabs(["List & Edit Bahan", "Tambah Bahan Baru"])
    
    # --- SUB-TAB 1: LIST & EDIT BAHAN ---
    with sub_tab1:
        search_kw = st.text_input("Cari Nama Bahan Makanan:", "", placeholder="Contoh: Ayam, Nasi, Tempe...").strip()
        
        conn = sqlite3.connect(DB_PATH)
        if search_kw:
            query = "SELECT id, nama, kalori, protein, lemak, karbohidrat, bdd FROM bahan_pangan WHERE nama LIKE ?"
            df_db = pd.read_sql_query(query, conn, params=(f"%{search_kw}%",))
        else:
            query = "SELECT id, nama, kalori, protein, lemak, karbohidrat, bdd FROM bahan_pangan"
            df_db = pd.read_sql_query(query, conn)
        conn.close()
        
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
                for _, row in edited_df_db.iterrows():
                    # Lewati baris yang ada sel kosongnya (NaN) — jangan sampai
                    # merusak data atau bikin proses simpan gagal di tengah jalan.
                    if pd.isna(row["nama"]) or any(pd.isna(row[k]) for k in ["kalori", "protein", "lemak", "karbohidrat", "bdd"]):
                        terlewat += 1
                        continue
                    update_bahan_pangan(
                        int(row["id"]), 
                        row["nama"], 
                        float(row["kalori"]), 
                        float(row["protein"]), 
                        float(row["lemak"]), 
                        float(row["karbohidrat"]),
                        float(row["bdd"])
                    )
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