# GiziKu — Platform Perencanaan & Pencatatan Gizi SPPG

**GiziKu** adalah aplikasi web interaktif berbasis **Python dan Streamlit** yang dikembangkan untuk membantu proses perencanaan, perhitungan, pencatatan, dan analisis gizi pada lingkungan **Satuan Pelayanan Pemenuhan Gizi (SPPG)**.

Aplikasi ini mengintegrasikan **database lebih dari 1.200 bahan pangan Indonesia** berdasarkan data **Tabel Komposisi Pangan Indonesia (TKPI)**, kalkulasi berat bahan, nilai gizi makro, pencatatan menu harian, serta visualisasi dan ekspor laporan.

> 🎯 **Goal:** Digitalisasi proses perhitungan dan pencatatan gizi agar lebih terstruktur, konsisten, dan efisien.

### Tentang Repo Ini

Repo ini adalah salinan dari proyek terbuka [NutriScale](https://github.com/rayrachman/nutriscale) oleh rayrachman yang di-rebrand menjadi **GiziKu** dengan tampilan baru. Demo versi asli tersedia di https://nutriscale.streamlit.app

---

## ✨ Key Features

### 📝 Menu Planning & Ingredient Calculation

* 🔎 **Smart Ingredient Search** — pencarian bahan pangan berdasarkan database TKPI.
* ⚖️ **Gross & Net Weight Calculation** — perhitungan berat kotor dan berat bersih berdasarkan % BDD (Bagian yang Dapat Dimakan).
* ✏️ **Interactive Portion Adjustment** — perubahan berat bahan secara langsung untuk menyesuaikan kebutuhan porsi.
* 🧮 **Automatic Nutrition Calculation** — perhitungan nilai gizi berdasarkan berat bahan yang digunakan.

### 📊 Nutrition Analysis & Daily Reporting

* 📅 Filter laporan berdasarkan tanggal penyajian.
* ⚡ Rekapitulasi energi harian.
* 💪 Perhitungan protein.
* 🥑 Perhitungan lemak.
* 🍚 Perhitungan karbohidrat.
* 📈 Visualisasi tren asupan energi.
* 📤 Ekspor data ke **CSV dan Excel**.

### 📚 Food Database Management

NutriScale menyediakan database bahan pangan yang dapat dikelola secara langsung.

* 🗃️ 1.200+ data bahan pangan Indonesia.
* ➕ Penambahan bahan pangan baru.
* ✏️ Editing nilai gizi.
* 📊 Pengelolaan nilai gizi per 100 gram.
* ⚖️ Pengelolaan % BDD.
* 💾 Penyimpanan menggunakan SQLite.

### 📱 Responsive & PWA-Ready

NutriScale dirancang agar dapat digunakan pada berbagai perangkat:

* 💻 Desktop / Laptop
* 📱 Android
* 🍎 iOS
* 🌐 Browser modern

---

## 🧠 Data & Calculation Workflow

Secara umum, proses pengolahan data pada NutriScale mengikuti alur:

```text
Food Database (TKPI)
        ↓
Ingredient Selection
        ↓
Gross Weight Input
        ↓
BDD Calculation
        ↓
Net Weight
        ↓
Nutrition Calculation
        ↓
Daily Nutrition Summary
        ↓
Visualization & Reporting
```

Konsep dasar perhitungan berat bersih:

```text
Berat Bersih = Berat Kotor × (%BDD / 100)
```

Nilai gizi kemudian dihitung berdasarkan berat bersih bahan yang digunakan.

---

## 🛠️ Technology Stack

### Programming Language

* Python 3.10+

### Framework

* Streamlit

### Data Processing

* Pandas
* OpenPyXL

### Database

* SQLite3

### Deployment

* Streamlit Community Cloud

---

## 📁 Project Structure

```text
nutriscale/
│
├── app.py              # Main Streamlit application
├── database.py         # SQLite database initialization & management
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

---

## 🚀 Run Locally

### 1. Clone Repository

```bash
git clone https://github.com/rayrachman/nutriscale.git
cd nutriscale
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
streamlit run app.py
```

The application will be available at:

```text
http://localhost:8501
```

---

## 📦 Dependencies

```text
streamlit
pandas
openpyxl
```

---

## 🎯 Project Highlights

| Area                  | Implementation            |
| --------------------- | ------------------------- |
| Data Processing       | Pandas                    |
| Database Management   | SQLite                    |
| Nutrition Calculation | Python                    |
| Data Visualization    | Streamlit                 |
| Data Export           | CSV & Excel               |
| Web Application       | Streamlit                 |
| Deployment            | Streamlit Community Cloud |
| Responsive UI         | Desktop & Mobile          |

---

## 👨‍💻 Developer

**Moch Rayhan Aulia Rachman**

Information Technology → Data Science & Machine Learning

GitHub: [@rayrachman](https://github.com/rayrachman)

---

## 📌 Disclaimer

NutriScale is a software project intended to support data management, calculation, and reporting workflows.

The application does not replace professional judgment from qualified nutritionists or other healthcare professionals.

---

## 🔧 Catatan Perbaikan (Audit — Oktober 2026)

Perbaikan bug mayor hasil audit aplikasi live:

* Edit berat bahan di tabel sajian sekarang menghitung ulang berat bersih & nilai gizi secara langsung.
* Laporan lama dibersihkan otomatis saat filter baru menghasilkan data kosong / rentang tanggal tidak valid.
* Grafik energi harian memakai sumbu Y yang selalu mulai dari 0.
* Berat desimal tampil utuh di tabel (mis. 12,5 g tidak lagi tampil sebagai 12).
* Ditambahkan fitur hapus entri laporan (Tab Laporan) dan hapus bahan pangan (Tab Database), masing-masing dengan konfirmasi.
* Pesan keberhasilan simpan/tambah data kini tampil konsisten setelah halaman dimuat ulang.
