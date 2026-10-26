import unittest

from calculator import TARGET_AKG, hitung_pemenuhan_akg, status_pemenuhan


class AkgTests(unittest.TestCase):
    def test_target_sesuai_permenkes_28_2019(self):
        # Nilai disalin dari Lampiran I Tabel 1 Permenkes No. 28/2019.
        self.assertEqual(
            TARGET_AKG["7-9 tahun"],
            {"energi": 1650, "protein": 40, "lemak": 55, "karbohidrat": 250},
        )
        self.assertEqual(
            TARGET_AKG["10-12 tahun (Laki-laki)"],
            {"energi": 2000, "protein": 50, "lemak": 65, "karbohidrat": 300},
        )
        self.assertEqual(
            TARGET_AKG["10-12 tahun (Perempuan)"],
            {"energi": 1900, "protein": 55, "lemak": 65, "karbohidrat": 280},
        )
        self.assertEqual(
            TARGET_AKG["13-15 tahun (Laki-laki)"],
            {"energi": 2400, "protein": 70, "lemak": 80, "karbohidrat": 350},
        )
        self.assertEqual(
            TARGET_AKG["13-15 tahun (Perempuan)"],
            {"energi": 2050, "protein": 65, "lemak": 70, "karbohidrat": 300},
        )
        self.assertEqual(
            TARGET_AKG["16-18 tahun (Laki-laki)"],
            {"energi": 2650, "protein": 75, "lemak": 85, "karbohidrat": 400},
        )
        self.assertEqual(
            TARGET_AKG["16-18 tahun (Perempuan)"],
            {"energi": 2100, "protein": 65, "lemak": 70, "karbohidrat": 300},
        )

    def test_persen_dan_status_pemenuhan(self):
        hasil = hitung_pemenuhan_akg(
            {"energi": 1650, "protein": 20, "lemak": 55, "karbohidrat": 100},
            "7-9 tahun",
        )
        self.assertEqual(hasil["energi"]["persen"], 100.0)
        self.assertEqual(hasil["energi"]["status"], "Terpenuhi")
        self.assertEqual(hasil["protein"]["persen"], 50.0)
        self.assertEqual(hasil["protein"]["status"], "Sangat kurang")
        self.assertEqual(hasil["lemak"]["persen"], 100.0)
        self.assertEqual(hasil["karbohidrat"]["persen"], 40.0)

    def test_band_status(self):
        self.assertEqual(status_pemenuhan(100.0), "Terpenuhi")
        self.assertEqual(status_pemenuhan(120.5), "Terpenuhi")
        self.assertEqual(status_pemenuhan(90.0), "Kurang")
        self.assertEqual(status_pemenuhan(80.0), "Kurang")
        self.assertEqual(status_pemenuhan(79.9), "Sangat kurang")
        self.assertEqual(status_pemenuhan(0.0), "Sangat kurang")

    def test_kelompok_tidak_dikenal_ditolak(self):
        with self.assertRaises(ValueError):
            hitung_pemenuhan_akg({"energi": 100}, "20-30 tahun")

    def test_total_kosong_tidak_crash(self):
        hasil = hitung_pemenuhan_akg({}, "7-9 tahun")
        self.assertEqual(hasil["energi"]["persen"], 0.0)
        self.assertEqual(hasil["energi"]["status"], "Sangat kurang")


if __name__ == "__main__":
    unittest.main()
