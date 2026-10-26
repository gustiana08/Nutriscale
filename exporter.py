# exporter.py
"""
Modul ekspor laporan GiziKu — mendukung format Excel (.xlsx), Word (.docx), dan CSV.

Template mengikuti identitas Biru Institusi GiziKu (navy #0A2A5E /
biru #1C4FA0 / kertas #F4F6FA / aksen tint #E6ECF6). Angka di Word
ditulis format Indonesia (koma desimal); di Excel angka tetap numerik
dengan format tampilan satu desimal agar bisa diolah lagi.
"""

import io
from datetime import date

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor

NAVY = "0A2A5E"
BIRU = "1C4FA0"
TINT = "E6ECF6"
KERTAS = "F4F6FA"
GARIS = "DBE2EF"
ABU = "5A6C87"

_BULAN_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]
_BULAN_PENDEK = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul",
                 "Agu", "Sep", "Okt", "Nov", "Des"]

# Label manusiawi untuk kolom laporan.
LABEL_KOLOM = {
    "tanggal": "Tanggal",
    "siklus_hari": "Siklus Hari",
    "waktu_makan": "Porsi Makanan",
    "nama_menu": "Nama Menu",
    "bahan_pangan": "Bahan Pangan",
    "berat_kotor": "Berat Kotor (g)",
    "berat_bersih": "Berat Bersih (g)",
    "bdd": "BDD (%)",
    "energi_kcal": "Energi (kkal)",
    "protein_g": "Protein (g)",
    "lemak_g": "Lemak (g)",
    "karbo_g": "Karbohidrat (g)",
}

KOLOM_NUMERIK = ["berat_kotor", "berat_bersih", "energi_kcal",
                 "protein_g", "lemak_g", "karbo_g"]


def _parse_tanggal(v):
    """'2026-10-23' / Timestamp / date -> date (atau None)."""
    if v is None:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _tgl_panjang(v):
    d = _parse_tanggal(v)
    if d is None:
        return str(v)
    return f"{d.day} {_BULAN_ID[d.month - 1]} {d.year}"


def _tgl_pendek(v):
    d = _parse_tanggal(v)
    if d is None:
        return str(v)
    return f"{d.day} {_BULAN_PENDEK[d.month - 1]} {d.year}"


def _periode_teks(df):
    if df is None or df.empty or "tanggal" not in df.columns:
        return ""
    tgl = sorted({str(t)[:10] for t in df["tanggal"]})
    if len(tgl) == 1:
        return f"Periode: {_tgl_panjang(tgl[0])}"
    return f"Periode: {_tgl_panjang(tgl[0])} s/d {_tgl_panjang(tgl[-1])}"


def _fmt_id(x):
    """Format angka Indonesia satu desimal: 1234.5 -> '1.234,5'."""
    try:
        s = f"{float(x):,.1f}"
    except (TypeError, ValueError):
        return str(x)
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


# =========================================================
# EXCEL
# =========================================================

def _gaya_sheet(ws, df_tampil, kolom, judul, periode, lebar_kolom,
                label_numerik, label_tanggal, ada_total=False,
                kolom_persen=frozenset()):
    """Tata satu sheet: judul, periode, header biru, lebar kolom, angka."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    tipis = Side(style="thin", color=GARIS)
    border = Border(left=tipis, right=tipis, top=tipis, bottom=tipis)

    nkol = len(kolom)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=nkol)
    c = ws.cell(row=1, column=1, value=judul)
    c.font = Font(name="Calibri", size=14, bold=True, color=NAVY)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=nkol)
    c = ws.cell(row=2, column=1, value=periode)
    c.font = Font(name="Calibri", size=10, color=ABU)

    baris_header = 4
    fill_header = PatternFill("solid", fgColor=BIRU)
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    for j, kol in enumerate(kolom, start=1):
        cell = ws.cell(row=baris_header, column=j)
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
    ws.row_dimensions[baris_header].height = 28

    fill_seling = PatternFill("solid", fgColor=KERTAS)
    baris_terakhir = baris_header
    for i, (_, row) in enumerate(df_tampil.iterrows()):
        r = baris_header + 1 + i
        baris_terakhir = r
        for j, kol in enumerate(kolom, start=1):
            cell = ws.cell(row=r, column=j)
            cell.border = border
            cell.font = Font(name="Calibri", size=10)
            if i % 2 == 1:
                cell.fill = fill_seling
            if kol in label_numerik:
                cell.number_format = '#,##0.0"%"' if kol in kolom_persen else '#,##0.0'
                cell.alignment = Alignment(horizontal="right")
            elif kol == label_tanggal:
                cell.number_format = 'DD/MM/YYYY'
                cell.alignment = Alignment(horizontal="center")

    if ada_total and not df_tampil.empty:
        r = baris_terakhir + 1
        fill_total = PatternFill("solid", fgColor=TINT)
        for j, kol in enumerate(kolom, start=1):
            cell = ws.cell(row=r, column=j)
            cell.fill = fill_total
            cell.border = border
            cell.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
            if j == 1:
                cell.value = "TOTAL"
            elif kol in label_numerik:
                cell.value = round(float(df_tampil[kol].sum()), 1)
                cell.number_format = '#,##0.0'
                cell.alignment = Alignment(horizontal="right")
        baris_terakhir = r

    for nama, lebar in lebar_kolom.items():
        if nama in kolom:
            ws.column_dimensions[get_column_letter(kolom.index(nama) + 1)].width = lebar
    ws.freeze_panes = ws.cell(row=baris_header + 1, column=1)
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.orientation = "landscape"
    ws.print_title_rows = f"{baris_header}:{baris_header}"
    return ws


def export_to_excel(df_laporan: pd.DataFrame, judul: str = "Laporan Gizi SPPG",
                    akg=None) -> io.BytesIO:
    """
    Menghasilkan file Excel (.xlsx) dari DataFrame laporan harian,
    dengan template Biru Institusi: judul + periode, header biru,
    label kolom manusiawi, lebar kolom tertata, dan baris TOTAL
    pada sheet Rekap Harian.

    Args:
        akg: opsional, tuple (label_kelompok, df_akg) dengan df_akg
            berk kolom tanggal, energi_pct, protein_pct, lemak_pct,
            karbo_pct, penilaian. Bila diisi, sheet ketiga
            "Kecukupan AKG" ikut dibuat; sheet lain tidak berubah.
    """
    output = io.BytesIO()
    judul_besar = "Laporan Gizi Harian SPPG"
    periode = _periode_teks(df_laporan)

    if df_laporan.empty and len(df_laporan.columns) == 0:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame({"Keterangan": ["Tidak ada data"]}).to_excel(
                writer, sheet_name='Rincian Lengkap', index=False)
        output.seek(0)
        return output

    kolom_rincian = ["tanggal", "siklus_hari", "waktu_makan", "nama_menu",
                     "bahan_pangan", "berat_kotor", "berat_bersih", "bdd",
                     "energi_kcal", "protein_g", "lemak_g", "karbo_g"]
    kolom_rincian = [k for k in kolom_rincian if k in df_laporan.columns]
    lebar_rincian = {"tanggal": 13, "siklus_hari": 12, "waktu_makan": 17,
                     "nama_menu": 26, "bahan_pangan": 34, "berat_kotor": 13,
                     "berat_bersih": 13, "bdd": 9, "energi_kcal": 12,
                     "protein_g": 11, "lemak_g": 11, "karbo_g": 14}

    df_r = df_laporan.copy()
    if "tanggal" in df_r.columns:
        df_r["tanggal"] = [_parse_tanggal(v) for v in df_r["tanggal"]]
    df_r = df_r.rename(columns=LABEL_KOLOM)
    label_rincian = [LABEL_KOLOM[k] for k in kolom_rincian]
    df_r = df_r[label_rincian] if label_rincian else df_r

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_r.to_excel(writer, sheet_name='Rincian Lengkap', index=False, startrow=3)
        ws = writer.sheets['Rincian Lengkap']
        kolom_internal = [LABEL_KOLOM[k] for k in kolom_rincian]
        # Pemetaan ulang nama internal untuk pewarnaan/format:
        df_internal = df_laporan.copy()
        if "tanggal" in df_internal.columns:
            df_internal["tanggal"] = [_parse_tanggal(v) for v in df_internal["tanggal"]]
        df_internal = df_internal.rename(columns=LABEL_KOLOM)
        _gaya_sheet(ws, df_internal, label_rincian, judul_besar, periode,
                    {LABEL_KOLOM[k]: v for k, v in lebar_rincian.items()
                     if k in LABEL_KOLOM},
                    {LABEL_KOLOM[k] for k in KOLOM_NUMERIK} | {LABEL_KOLOM["bdd"]},
                    LABEL_KOLOM["tanggal"])

        # Sheet 2: Rekap Harian (agregasi per tanggal) + TOTAL
        if not df_laporan.empty and 'tanggal' in df_laporan.columns:
            kolom_ada = [k for k in KOLOM_NUMERIK if k in df_laporan.columns]
            if kolom_ada:
                rekap = df_laporan.groupby('tanggal')[kolom_ada].sum().reset_index().round(1)
                kolom_rekap = ["tanggal"] + kolom_ada
                df_k = rekap.copy()
                df_k["tanggal"] = [_parse_tanggal(v) for v in df_k["tanggal"]]
                df_k = df_k.rename(columns=LABEL_KOLOM)
                label_rekap = [LABEL_KOLOM[k] for k in kolom_rekap]
                df_k.to_excel(writer, sheet_name='Rekap Harian', index=False, startrow=3)
                ws2 = writer.sheets['Rekap Harian']
                lebar_rekap = {LABEL_KOLOM["tanggal"]: 14}
                for k in kolom_ada:
                    lebar_rekap[LABEL_KOLOM[k]] = 15
                _gaya_sheet(ws2, df_k, label_rekap, judul_besar, periode,
                            lebar_rekap,
                            {LABEL_KOLOM[k] for k in kolom_ada},
                            LABEL_KOLOM["tanggal"], ada_total=True)

        # Sheet 3 (opsional): Kecukupan AKG per hari.
        if akg is not None:
            label_kelompok, df_akg = akg
            if df_akg is not None and not df_akg.empty:
                label_akg = {
                    "tanggal": "Tanggal",
                    "energi_pct": "Energi (% AKG)",
                    "protein_pct": "Protein (% AKG)",
                    "lemak_pct": "Lemak (% AKG)",
                    "karbo_pct": "Karbohidrat (% AKG)",
                    "penilaian": "Penilaian",
                }
                kolom_akg = [k for k in label_akg if k in df_akg.columns]
                df_a = df_akg[kolom_akg].copy()
                df_a["tanggal"] = [_parse_tanggal(v) for v in df_a["tanggal"]]
                df_a = df_a.rename(columns=label_akg)
                label_tampil = [label_akg[k] for k in kolom_akg]
                df_a.to_excel(writer, sheet_name='Kecukupan AKG', index=False, startrow=3)
                ws3 = writer.sheets['Kecukupan AKG']
                _gaya_sheet(
                    ws3, df_a, label_tampil,
                    "Kecukupan Gizi (AKG 2019)",
                    f"Kelompok umur: {label_kelompok}",
                    {"Tanggal": 14, "Energi (% AKG)": 15, "Protein (% AKG)": 15,
                     "Lemak (% AKG)": 15, "Karbohidrat (% AKG)": 17, "Penilaian": 15},
                    {label_akg[k] for k in
                     ("energi_pct", "protein_pct", "lemak_pct", "karbo_pct")
                     if k in kolom_akg},
                    "Tanggal",
                    kolom_persen={label_akg[k] for k in
                                  ("energi_pct", "protein_pct", "lemak_pct", "karbo_pct")
                                  if k in kolom_akg},
                )

    output.seek(0)
    return output


def export_to_csv(df_laporan: pd.DataFrame) -> bytes:
    """
    Menghasilkan file CSV dari DataFrame laporan.
    CSV memang format mentah untuk olah data lanjutan — tanpa styling.
    """
    return df_laporan.to_csv(index=False).encode('utf-8')


# =========================================================
# WORD
# =========================================================

def _shade(cell, hexcolor):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:fill'), hexcolor)
    tc_pr.append(shd)


def _isi_sel(cell, teks, bold=False, size=9, warna=None, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run(str(teks))
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = "Calibri"
    if warna:
        run.font.color.rgb = RGBColor.from_string(warna)
    return run


def _judul_seksi(doc, teks):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(teks)
    run.bold = True
    run.font.size = Pt(12)
    run.font.name = "Calibri"
    run.font.color.rgb = RGBColor.from_string(NAVY)
    return p


def export_to_word(df_laporan: pd.DataFrame, tanggal_awal: str, tanggal_akhir: str) -> io.BytesIO:
    """
    Menghasilkan dokumen laporan Word (.docx) dengan template
    Biru Institusi: kop GiziKu, judul, periode format Indonesia,
    tabel berkepala biru dengan angka format koma, baris TOTAL
    pada rekap, dan blok tanda tangan petugas.
    """
    doc = Document()

    # Halaman A4, margin ramping agar tabel rincian muat.
    section = doc.sections[0]
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(1.7)
    section.right_margin = Cm(1.7)

    normal = doc.styles['Normal']
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    # --- Kop dokumen ---
    kop = doc.add_paragraph()
    kop.paragraph_format.space_after = Pt(0)
    run = kop.add_run("GiziKu")
    run.bold = True
    run.font.size = Pt(15)
    run.font.name = "Calibri"
    run.font.color.rgb = RGBColor.from_string(NAVY)
    sub = doc.add_paragraph()
    sub.paragraph_format.space_after = Pt(4)
    run = sub.add_run("Satuan Pelayanan Pemenuhan Gizi (SPPG) · Sistem Pencatatan Gizi Harian")
    run.font.size = Pt(9)
    run.font.name = "Calibri"
    run.font.color.rgb = RGBColor.from_string(ABU)
    # Garis bawah kop (biru institusi).
    pPr = sub._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '12')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), BIRU)
    pBdr.append(bottom)
    pPr.append(pBdr)

    # --- Judul + periode ---
    judul = doc.add_paragraph()
    judul.alignment = WD_ALIGN_PARAGRAPH.CENTER
    judul.paragraph_format.space_before = Pt(10)
    judul.paragraph_format.space_after = Pt(2)
    run = judul.add_run("LAPORAN GIZI HARIAN SPPG")
    run.bold = True
    run.font.size = Pt(16)
    run.font.name = "Calibri"
    run.font.color.rgb = RGBColor.from_string(NAVY)

    if _parse_tanggal(tanggal_awal) and tanggal_awal == tanggal_akhir:
        teks_periode = f"Periode: {_tgl_panjang(tanggal_awal)}"
    else:
        teks_periode = (f"Periode: {_tgl_panjang(tanggal_awal)} "
                        f"s/d {_tgl_panjang(tanggal_akhir)}")
    per = doc.add_paragraph()
    per.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = per.add_run(teks_periode)
    run.font.size = Pt(10)
    run.font.name = "Calibri"
    run.font.color.rgb = RGBColor.from_string(ABU)

    kosong = not df_laporan.empty

    # --- 1. Rekapitulasi per hari + TOTAL ---
    _judul_seksi(doc, "1. Rekapitulasi Gizi Per Hari")
    kolom_ada = [k for k in KOLOM_NUMERIK if k in df_laporan.columns]
    if kosong and kolom_ada:
        rekap = df_laporan.groupby('tanggal')[kolom_ada].sum().reset_index().round(1)
        header = ["Tanggal"] + [LABEL_KOLOM[k] for k in kolom_ada]
        tabel = doc.add_table(rows=1, cols=len(header))
        tabel.style = 'Table Grid'
        for i, label in enumerate(header):
            _isi_sel(tabel.rows[0].cells[i], label, bold=True, size=9, warna="FFFFFF")
            _shade(tabel.rows[0].cells[i], BIRU)
        for _, row in rekap.iterrows():
            sel = tabel.add_row().cells
            _isi_sel(sel[0], _tgl_pendek(row['tanggal']), size=9)
            for j, kol in enumerate(kolom_ada):
                _isi_sel(sel[j + 1], _fmt_id(row[kol]), size=9,
                         align=WD_ALIGN_PARAGRAPH.RIGHT)
        sel = tabel.add_row().cells
        _isi_sel(sel[0], "TOTAL", bold=True, size=9, warna=NAVY)
        _shade(sel[0], TINT)
        for j, kol in enumerate(kolom_ada):
            _isi_sel(sel[j + 1], _fmt_id(rekap[kol].sum()), bold=True, size=9,
                     warna=NAVY, align=WD_ALIGN_PARAGRAPH.RIGHT)
            _shade(sel[j + 1], TINT)
    else:
        doc.add_paragraph("Tidak ada data pada periode ini.")

    # --- 2. Rincian bahan & menu ---
    _judul_seksi(doc, "2. Rincian Bahan & Menu")
    kolom_rincian = ['tanggal', 'nama_menu', 'bahan_pangan', 'berat_kotor',
                     'berat_bersih', 'energi_kcal', 'protein_g', 'lemak_g',
                     'karbo_g']
    kolom_tampil = [k for k in kolom_rincian if k in df_laporan.columns]
    if kosong and kolom_tampil:
        tabel = doc.add_table(rows=1, cols=len(kolom_tampil))
        tabel.style = 'Table Grid'
        for i, kol in enumerate(kolom_tampil):
            _isi_sel(tabel.rows[0].cells[i], LABEL_KOLOM[kol], bold=True,
                     size=8.5, warna="FFFFFF")
            _shade(tabel.rows[0].cells[i], BIRU)
        for _, row in df_laporan[kolom_tampil].iterrows():
            sel = tabel.add_row().cells
            for j, kol in enumerate(kolom_tampil):
                if kol == 'tanggal':
                    _isi_sel(sel[j], _tgl_pendek(row[kol]), size=8.5)
                elif kol in KOLOM_NUMERIK:
                    _isi_sel(sel[j], _fmt_id(row[kol]), size=8.5,
                             align=WD_ALIGN_PARAGRAPH.RIGHT)
                else:
                    _isi_sel(sel[j], row[kol], size=8.5)
    else:
        doc.add_paragraph("Tidak ada data pada periode ini.")

    # --- Blok tanda tangan ---
    doc.add_paragraph("")
    ttd = doc.add_table(rows=1, cols=2)
    kiri, kanan = ttd.rows[0].cells
    _isi_sel(kiri, "Mengetahui,\nPenanggung Jawab SPPG\n\n\n\n( .................................... )",
             size=10)
    _isi_sel(kanan, f"{_tgl_panjang(tanggal_akhir)}\nPetugas Gizi SPPG\n\n\n\n( .................................... )",
             size=10)
    for cell in (kiri, kanan):
        tcPr = cell._tc.get_or_add_tcPr()
        borders = OxmlElement('w:tcBorders')
        for sisi in ('top', 'left', 'bottom', 'right'):
            el = OxmlElement(f'w:{sisi}')
            el.set(qn('w:val'), 'nil')
            borders.append(el)
        tcPr.append(borders)

    # --- Footer ---
    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_p.add_run("GiziKu · Sistem Pencatatan Gizi SPPG")
    run.font.size = Pt(8)
    run.font.name = "Calibri"
    run.font.color.rgb = RGBColor.from_string(ABU)

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output
