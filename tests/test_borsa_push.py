# -*- coding: utf-8 -*-
"""borsa_push bildirim metni — ağ gerektirmez.

    python3 -m unittest tests/test_borsa_push.py -v
(pywebpush kurulu değilse atlanır; Actions'ta kurulu.)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    import borsa_push as BP  # noqa: E402
except ImportError:          # pywebpush yok
    BP = None


def sinyal(code, durum, kisa):
    return {"code": code, "durum": durum, "price": "10.00", "kisa": kisa, "trend": "yatay"}


@unittest.skipIf(BP is None, "pywebpush kurulu değil")
class OzetTest(unittest.TestCase):
    def test_sinyal_yok(self):
        b, g = BP.ozet_metni({"updated": "2026-11-11 09:00", "sinyaller": [],
                              "sinyalTarama": {"bist": 36, "abd": 5}})
        self.assertEqual(b, "Borsa · 09:00")
        self.assertIn("41 kağıt", g)
        self.assertIn("tavsiye değil", g)

    def test_sayac_ve_sinir(self):
        s = [sinyal(f"K{i}", "olasi_alim" if i % 2 else "olasi_satis", ["zirve kırılımı"])
             for i in range(6)]
        b, g = BP.ozet_metni({"updated": "2026-11-11 14:00", "sinyaller": s})
        self.assertEqual(b, "Borsa · 14:00 · 3 olası alım, 3 olası satış")
        self.assertIn("+2 kağıt panelde", g)
        self.assertEqual(g.count("▲") + g.count("▼"), BP.EN_FAZLA)
        self.assertTrue(g.endswith("tavsiye değil"))


if __name__ == "__main__":
    unittest.main()
