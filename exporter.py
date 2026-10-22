# exporter.py
"""
Modul ekspor laporan GiziKu — mendukung format Excel (.xlsx), Word (.docx), dan CSV.
"""

import io
import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


def export_to_excel(df_laporan: pd.DataFrame, judul: str = "Laporan Gizi SPPG") -> io.BytesIO:
    """
    Menghasilkan file Excel (.xlsx) dari DataFrame laporan harian.
    
    Args:
        df_laporan: DataFrame berisi data laporan (dari ambil_laporan_harian).
        judul: Judul untuk sheet Excel.
    
    Returns:
        BytesIO buffer berisi file .xlsx (siap di-download di Streamlit).
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Rincian Lengkap
        df_laporan.to_excel(writer, sheet_name='Rincian Lengkap', index=False)
        
        # Sheet 2: Rekap Harian (agregasi per tanggal)
        if not df_laporan.empty and 'tanggal' in df_laporan.columns:
            kolom_numerik = ['berat_kotor', 'berat_bersih', 'energi_kcal', 'protein_g', 'lemak_g', 'karbo_g']
            kolom_ada = [k for k in kolom_numerik if k in df_laporan.columns]
            
            if kolom_ada:
                rekap = df_laporan.groupby('tanggal')[kolom_ada].sum().reset_index().round(1)
                rekap.to_excel(writer, sheet_name='Rekap Harian', index=False)
    
    output.seek(0)
    return output


def export_to_csv(df_laporan: pd.DataFrame) -> bytes:
    """
    Menghasilkan file CSV dari DataFrame laporan.
    
    Args:
        df_laporan: DataFrame berisi data laporan.
    
    Returns:
        Bytes berisi konten CSV (UTF-8 encoded).
    """
    return df_laporan.to_csv(index=False).encode('utf-8')


def export_to_word(df_laporan: pd.DataFrame, tanggal_awal: str, tanggal_akhir: str) -> io.BytesIO:
    """
    Menghasilkan dokumen laporan Word (.docx) dari DataFrame laporan.
    
    Args:
        df_laporan: DataFrame berisi data laporan.
        tanggal_awal: Tanggal awal periode laporan.
        tanggal_akhir: Tanggal akhir periode laporan.
    
    Returns:
        BytesIO buffer berisi file .docx (siap di-download di Streamlit).
    """
    doc = Document()
    
    # Judul Laporan
    title = doc.add_heading('LAPORAN GIZI HARIAN SPPG', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Info Periode
    doc.add_paragraph(f"Periode: {tanggal_awal} s/d {tanggal_akhir}")
    doc.add_paragraph("")
    
    # Section 1: Rekap Harian
    doc.add_heading('1. Rekapitulasi Gizi Per Hari', level=1)
    
    kolom_numerik = ['berat_kotor', 'berat_bersih', 'energi_kcal', 'protein_g', 'lemak_g', 'karbo_g']
    kolom_ada = [k for k in kolom_numerik if k in df_laporan.columns]
    
    if kolom_ada and not df_laporan.empty:
        rekap = df_laporan.groupby('tanggal')[kolom_ada].sum().reset_index().round(1)
        
        # Buat tabel rekap
        table_rekap = doc.add_table(rows=1, cols=len(['Tanggal'] + kolom_ada))
        table_rekap.style = 'Table Grid'
        
        header_cells = table_rekap.rows[0].cells
        header_labels = ['Tanggal'] + [k.replace('_', ' ').title() for k in kolom_ada]
        for i, label in enumerate(header_labels):
            header_cells[i].text = label
            for run in header_cells[i].paragraphs[0].runs:
                run.font.bold = True
                run.font.size = Pt(9)
        
        for _, row in rekap.iterrows():
            row_cells = table_rekap.add_row().cells
            row_cells[0].text = str(row['tanggal'])
            for j, col in enumerate(kolom_ada):
                row_cells[j + 1].text = str(row[col])
    
    # Section 2: Rincian Lengkap
    doc.add_heading('2. Rincian Bahan & Menu', level=1)
    
    kolom_rincian = ['tanggal', 'nama_menu', 'bahan_pangan', 'berat_kotor', 'berat_bersih', 
                     'energi_kcal', 'protein_g', 'lemak_g', 'karbo_g']
    kolom_tampil = [k for k in kolom_rincian if k in df_laporan.columns]
    
    if kolom_tampil and not df_laporan.empty:
        table_detail = doc.add_table(rows=1, cols=len(kolom_tampil))
        table_detail.style = 'Table Grid'
        
        header_cells = table_detail.rows[0].cells
        for i, col in enumerate(kolom_tampil):
            header_cells[i].text = col.replace('_', ' ').title()
            for run in header_cells[i].paragraphs[0].runs:
                run.font.bold = True
                run.font.size = Pt(8)
        
        for _, row in df_laporan[kolom_tampil].iterrows():
            row_cells = table_detail.add_row().cells
            for j, col in enumerate(kolom_tampil):
                row_cells[j].text = str(row[col])
                for paragraph in row_cells[j].paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(8)
    
    # Output Buffer
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output