import os
import tempfile
import unittest

import database


def _bahan(nama_menu, bahan, energi=100.0, protein=10.0, lemak=5.0, karbo=20.0):
    return {
        "nama_menu": nama_menu,
        "bahan_pangan": bahan,
        "berat_kotor": 100.0,
        "berat_bersih": 100.0,
        "bdd": 100.0,
        "energi_kcal": energi,
        "protein_g": protein,
        "lemak_g": lemak,
        "karbo_g": karbo,
    }


class RencanaMingguanTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_paths = (database.DB_PATH, database.CSV_PATH, database.DATASET_CSV_PATH)
        database.DB_PATH = os.path.join(self.temp_dir.name, "test.db")
        database.CSV_PATH = os.path.join(self.temp_dir.name, "missing.csv")
        database.DATASET_CSV_PATH = os.path.join(self.temp_dir.name, "missing-dataset.csv")
        database.init_db()

    def tearDown(self):
        database.DB_PATH, database.CSV_PATH, database.DATASET_CSV_PATH = self.original_paths
        self.temp_dir.cleanup()

    def test_simpan_dan_ambil_rencana(self):
        database.simpan_rencana_hari("2026-10-26", "Senin", "Menu A",
                                     [_bahan("Menu A", "Nasi"), _bahan("Menu A", "Ayam", energi=200.0)])
        df = database.ambil_rencana_mingguan("2026-10-26")
        self.assertEqual(len(df), 2)
        self.assertEqual(df["energi_kcal"].sum(), 300.0)
        self.assertTrue((df["hari"] == "Senin").all())

    def test_simpan_ulang_menu_yang_sama_tidak_mengganda(self):
        database.simpan_rencana_hari("2026-10-26", "Senin", "Menu A", [_bahan("Menu A", "Nasi")])
        database.simpan_rencana_hari("2026-10-26", "Senin", "Menu A",
                                     [_bahan("Menu A", "Nasi"), _bahan("Menu A", "Ayam")])
        df = database.ambil_rencana_mingguan("2026-10-26")
        self.assertEqual(len(df), 2)

    def test_salin_hari_menggantikan_tujuan(self):
        database.simpan_rencana_hari("2026-10-26", "Senin", "Menu A", [_bahan("Menu A", "Nasi")])
        database.simpan_rencana_hari("2026-10-26", "Selasa", "Menu Lama", [_bahan("Menu Lama", "Tempe")])
        jumlah = database.salin_rencana_hari("2026-10-26", "Senin", "Selasa")
        self.assertEqual(jumlah, 1)
        df = database.ambil_rencana_mingguan("2026-10-26")
        selasa = df[df["hari"] == "Selasa"]
        self.assertEqual(len(selasa), 1)
        self.assertEqual(selasa.iloc[0]["nama_menu"], "Menu A")

    def test_hapus_menu_dan_hari_tidak_valid(self):
        database.simpan_rencana_hari("2026-10-26", "Senin", "Menu A", [_bahan("Menu A", "Nasi")])
        database.hapus_rencana_menu("2026-10-26", "Senin", "Menu A")
        self.assertTrue(database.ambil_rencana_mingguan("2026-10-26").empty)
        with self.assertRaises(ValueError):
            database.simpan_rencana_hari("2026-10-26", "Sabtu", "Menu A", [_bahan("Menu A", "Nasi")])

    def test_rencana_bisa_diterapkan_ke_log_harian(self):
        database.simpan_rencana_hari("2026-10-26", "Senin", "Menu A", [_bahan("Menu A", "Nasi")])
        df = database.ambil_rencana_mingguan("2026-10-26")
        database.simpan_menu_harian("2026-10-26", "Senin", "Standard / Biasa",
                                    df.to_dict("records"))
        laporan = database.ambil_laporan_harian("2026-10-26", "2026-10-26")
        self.assertEqual(len(laporan), 1)
        self.assertEqual(laporan.iloc[0]["nama_menu"], "Menu A")


if __name__ == "__main__":
    unittest.main()
