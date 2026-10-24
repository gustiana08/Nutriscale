# GiziKu - Platform Perencanaan & Pencatatan Gizi SPPG

**GiziKu** adalah aplikasi web interaktif berbasis **Python dan Streamlit** yang dikembangkan untuk membantu proses perencanaan, perhitungan, pencatatan, dan analisis gizi pada lingkungan **Satuan Pelayanan Pemenuhan Gizi (SPPG)**.

Aplikasi ini mengintegrasikan **database lebih dari 1.200 bahan pangan Indonesia** berdasarkan data **Tabel Komposisi Pangan Indonesia (TKPI)**, kalkulasi berat bahan, nilai gizi makro, pencatatan menu harian, serta visualisasi dan ekspor laporan.

**Tujuan:** Digitalisasi proses perhitungan dan pencatatan gizi agar lebih terstruktur, konsisten, dan efisien.

### Tentang Repo Ini

Repo ini adalah salinan dari proyek terbuka [NutriScale](https://github.com/rayrachman/nutriscale) oleh rayrachman yang di-rebrand menjadi **GiziKu** dengan tampilan baru. Demo versi asli tersedia di https://nutriscale.streamlit.app

---

## Fitur Utama

### Perencanaan Menu dan Perhitungan Bahan

* **Pencarian bahan pangan** berdasarkan database TKPI.
* **Perhitungan berat kotor dan bersih** berdasarkan % BDD (Bagian yang Dapat Dimakan).
* **Penyesuaian porsi interaktif** melalui tabel sajian.
* **Perhitungan nilai gizi otomatis** berdasarkan berat bahan yang digunakan.

### Analisis Gizi dan Laporan Harian

* Filter laporan berdasarkan tanggal penyajian.
* Rekapitulasi energi, protein, lemak, dan karbohidrat harian.
* Visualisasi tren asupan energi.
* Ekspor data ke **CSV, Excel, dan Word**.

### Pengelolaan Database Bahan Pangan

NutriScale menyediakan database bahan pangan yang dapat dikelola secara langsung.

* Lebih dari 1.200 data bahan pangan Indonesia.
* Penambahan dan penghapusan bahan pangan.
* Penyuntingan nilai gizi per 100 gram.
* Pengelolaan % BDD.
* Penyimpanan menggunakan SQLite atau Turso.

### Dukungan Perangkat

NutriScale dirancang agar dapat digunakan pada berbagai perangkat:

* Desktop dan laptop.
* Perangkat Android dan iOS.
* Browser modern.

---

## Alur Perhitungan dan Data

Secara umum, proses pengolahan data pada NutriScale mengikuti alur:

```text
Food Database (TKPI)
        ->
Ingredient Selection
        ->
Gross Weight Input
        ->
BDD Calculation
        ->
Net Weight
        ->
Nutrition Calculation
        ->
Daily Nutrition Summary
        ->
Visualization & Reporting
```

Konsep dasar perhitungan berat bersih:

```text
Berat Bersih = Berat Kotor x (% BDD / 100)
```

Nilai gizi kemudian dihitung berdasarkan berat bersih bahan yang digunakan.

---

## Teknologi

### Programming Language

* Python 3.10+

### Framework

* Streamlit

### Data Processing

* Pandas
* OpenPyXL
* python-docx

### Database

* SQLite3
* Turso/libSQL (opsional)

### Deployment

* Streamlit Community Cloud

---

## Struktur Proyek

```text
nutriscale/
- app.py              # Aplikasi utama Streamlit
- calculator.py       # Logika perhitungan berat dan gizi
- database.py         # Inisialisasi dan pengelolaan database
- exporter.py         # Ekspor laporan CSV, Excel, dan Word
- style.css           # Gaya visual aplikasi
- dataset/            # Dataset bahan pangan
- tests/              # Automated tests
- requirements.txt    # Dependency Python
- README.md           # Dokumentasi proyek
```

---

## Menjalankan Secara Lokal

### 1. Clone Repository

```bash
git clone https://github.com/gustiana08/Nutriscale.git
cd Nutriscale
```

### 2. Create Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python database.py
```

### 5. Run Application

```bash
python -m streamlit run app.py
```

The application will be available at:

```text
http://localhost:8501
```

### Menjalankan Test

```bash
python -m unittest discover -s tests -v
```

## Deployment dengan Turso

Secara default aplikasi menggunakan SQLite lokal. Untuk penyimpanan persisten
di Streamlit Community Cloud, isi dua secret berikut pada pengaturan aplikasi:

```toml
TURSO_DATABASE_URL = "libsql://nama-database.turso.io"
TURSO_AUTH_TOKEN = "token-turso"
```

Untuk pengembangan lokal, nilai yang sama dapat diberikan sebagai environment
variable `TURSO_DATABASE_URL` dan `TURSO_AUTH_TOKEN`. Jangan menyimpan token di
repository.

---

## Dependency

```text
streamlit
pandas
openpyxl
python-docx
libsql
```

---

## Ringkasan Implementasi

| Area                  | Implementation            |
| --------------------- | ------------------------- |
| Data Processing       | Pandas                    |
| Database Management   | SQLite                    |
| Nutrition Calculation | Python                    |
| Data Visualization    | Streamlit                 |
| Data Export           | CSV, Excel, dan Word      |
| Web Application       | Streamlit                 |
| Deployment            | Streamlit Community Cloud |
| Responsive UI         | Desktop & Mobile          |

---

## Pengembang

**Moch Rayhan Aulia Rachman**

Information Technology -> Data Science & Machine Learning

GitHub: [@rayrachman](https://github.com/rayrachman)

---

## Disclaimer

NutriScale is a software project intended to support data management, calculation, and reporting workflows.

The application does not replace professional judgment from qualified nutritionists or other healthcare professionals.

---

## Catatan Perbaikan Audit (Oktober 2026)

Perbaikan bug mayor hasil audit aplikasi live:

* Edit berat bahan di tabel sajian sekarang menghitung ulang berat bersih & nilai gizi secara langsung.
* Laporan lama dibersihkan otomatis saat filter baru menghasilkan data kosong / rentang tanggal tidak valid.
* Grafik energi harian memakai sumbu Y yang selalu mulai dari 0.
* Berat desimal tampil utuh di tabel (mis. 12,5 g tidak lagi tampil sebagai 12).
* Ditambahkan fitur hapus entri laporan (Tab Laporan) dan hapus bahan pangan (Tab Database), masing-masing dengan konfirmasi.
* Pesan keberhasilan simpan/tambah data kini tampil konsisten setelah halaman dimuat ulang.
