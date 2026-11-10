# -*- coding: utf-8 -*-
"""teknik.py kuralları — ağ gerektirmez, sentetik seriler.

    python3 -m unittest tests/test_teknik.py -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import teknik as T  # noqa: E402


def dalgali(n, baslangic, adim, genlik=0.4):
    """Düz trend + küçük zikzak (RSI'ın 0/100'e yapışmaması için)."""
    return [baslangic + adim * i + (genlik if i % 2 else -genlik) for i in range(n)]


class TeknikTest(unittest.TestCase):
    def test_yetersiz_veri(self):
        self.assertIsNone(T.analiz([10.0] * 40))

    def test_yatay_seri_notr(self):
        a = T.analiz(dalgali(80, 100, 0))
        self.assertEqual(a["trend"], "yatay")
        self.assertEqual(a["durum"], "notr")
        self.assertEqual(a["olaylar"], [])

    def test_yukselis_trendi_puan(self):
        a = T.analiz(dalgali(80, 50, 0.5, genlik=1.5))
        self.assertEqual(a["trend"], "yükseliş")
        self.assertGreaterEqual(a["puan"], 1)

    def test_dusus_ve_asiri_satim(self):
        a = T.analiz([200 - 2 * i for i in range(80)])
        self.assertEqual(a["trend"], "düşüş")
        self.assertEqual(a["durum"], "olasi_satis")
        self.assertTrue(any("aşağı kırıldı" in o for o in a["olaylar"]))

    def test_hacimli_kirilim_olasi_alim(self):
        k = dalgali(79, 100, 0, genlik=1) + [110.0]
        h = [1000.0] * 79 + [3000.0]
        a = T.analiz(k, h)
        self.assertTrue(any("zirvesi" in o and "katı" in o for o in a["olaylar"]))
        self.assertEqual(a["durum"], "olasi_alim")
        # kırılan zirve yeni destek olur
        self.assertAlmostEqual(a["destek"], 101.0)

    def test_hacimsiz_kirilim_zayif(self):
        k = dalgali(79, 100, 0, genlik=1) + [110.0]
        h = [1000.0] * 80
        a = T.analiz(k, h)
        self.assertTrue(any("hacim teyidi yok" in o for o in a["olaylar"]))

    def test_altin_kesisim(self):
        # uzun düşüş, sonra sert dönüş: 20g ort 50g'yi son günlerde yukarı keser
        k = [100 - 0.5 * i for i in range(60)] + [70 + 2.2 * i for i in range(20)]
        olaylar = None
        for son in range(60, 81):
            a = T.analiz(k[:son])
            if a and any("yukarı kesti" in o for o in a["olaylar"]):
                olaylar = a["olaylar"]
                break
        self.assertIsNotNone(olaylar, "kesişim hiç yakalanmadı")

    def test_destek_direncin_altinda(self):
        a = T.analiz(dalgali(80, 100, 0.1))
        self.assertLessEqual(a["destek"], a["direnc"])

    def test_nan_atlanir(self):
        k = dalgali(80, 100, 0)
        k[10] = float("nan")
        self.assertIsNotNone(T.analiz(k))


if __name__ == "__main__":
    unittest.main()
