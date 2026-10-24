import math
import os
import tempfile
import unittest

import database


class DatabaseTests(unittest.TestCase):
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

    def test_bahan_valid_dapat_disimpan_dan_dicari(self):
        database.tambah_bahan_custom("Ayam 100%", 100, 10, 5, 0, 80)
        database.tambah_bahan_custom("Nasi Putih", 130, 2, 1, 28, 100)
        self.assertEqual(len(database.cari_bahan_pangan("%")), 1)
        self.assertEqual(len(database.ambil_bahan_editor("%")), 1)

    def test_input_bahan_tidak_valid_ditolak(self):
        invalid_values = [("", 100, 10, 5, 0), ("Ayam", math.nan, 10, 5, 0), ("Ayam", 100, -1, 5, 0)]
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    database.tambah_bahan_custom(*values)

    def test_bdd_nan_menggunakan_default(self):
        self.assertEqual(database._bdd_valid(math.nan), 100.0)


if __name__ == "__main__":
    unittest.main()
