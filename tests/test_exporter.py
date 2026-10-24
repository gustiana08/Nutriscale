import unittest

import pandas as pd

from exporter import export_to_csv, export_to_excel, export_to_word


class ExporterTests(unittest.TestCase):
    def test_export_data_kosong_tanpa_kolom(self):
        hasil = export_to_excel(pd.DataFrame())
        self.assertGreater(hasil.getbuffer().nbytes, 0)

    def test_semua_format_export(self):
        data = pd.DataFrame([
            {
                "tanggal": "2026-10-24",
                "nama_menu": "Menu Uji",
                "energi_kcal": 100.0,
                "protein_g": 10.0,
            }
        ])
        self.assertTrue(export_to_csv(data).startswith(b"tanggal"))
        self.assertGreater(export_to_excel(data).getbuffer().nbytes, 0)
        self.assertGreater(
            export_to_word(data, "2026-10-24", "2026-10-24").getbuffer().nbytes,
            0,
        )


if __name__ == "__main__":
    unittest.main()
