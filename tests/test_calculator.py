import unittest

from calculator import (
    hitung_nutrisi_bahan,
    konversi_berat,
    perbarui_keranjang,
)


class CalculatorTests(unittest.TestCase):
    def test_konversi_berat_kotor_dan_bersih(self):
        self.assertEqual(konversi_berat(100, 80, "kotor"), (100, 80.0))
        self.assertEqual(konversi_berat(80, 80, "bersih"), (100.0, 80))

    def test_tipe_input_tidak_valid_ditolak(self):
        with self.assertRaises(ValueError):
            konversi_berat(80, 80, "salah")

    def test_perbarui_keranjang_tidak_memutasi_data_lama(self):
        keranjang = [{"Berat Kotor (g)": 100, "nama": "Ayam"}]
        hasil, berubah = perbarui_keranjang(keranjang, [(0, 125.54)])
        self.assertTrue(berubah)
        self.assertEqual(hasil[0]["Berat Kotor (g)"], 125.5)
        self.assertEqual(keranjang[0]["Berat Kotor (g)"], 100)

    def test_hitung_nutrisi(self):
        self.assertEqual(
            hitung_nutrisi_bahan(80, 100, 10, 5, 20),
            {"kalori": 80.0, "protein": 8.0, "lemak": 4.0, "karbohidrat": 16.0},
        )


if __name__ == "__main__":
    unittest.main()
