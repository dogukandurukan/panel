# -*- coding: utf-8 -*-
"""linkedin_feed ayrıştırıcısı — ağ gerektirmez.

    python3 -m unittest tests/test_linkedin_feed.py -v

Örnek gövde, LinkedIn iş uyarısı mailinin yapısına göre yazıldı: ilan başlığı
/jobs/view/<id> bağlantısı, hemen ardından şirket · konum · tarih metni.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import linkedin_feed as L  # noqa: E402

MAIL = """
<html><body>
  <table><tr><td>
    <a href="https://www.linkedin.com/comm/jobs/view/4123456789/?trackingId=abc">Data Analyst</a>
    <p>HiredBuddy &middot; Istanbul, T&uuml;rkiye (Remote) &middot; 17 saat &ouml;nce</p>
    <a href="https://www.linkedin.com/comm/jobs/view/4123456789/?apply=1">Şimdi başvur</a>
  </td></tr><tr><td>
    <a href="https://www.linkedin.com/comm/jobs/view/4987654321/?trackingId=def">Senior BI Developer</a>
    <p>Sovos &middot; &#304;stanbul, T&uuml;rkiye (Hybrid) &middot; 1 g&uuml;n &ouml;nce</p>
  </td></tr><tr><td>
    <a href="https://www.linkedin.com/comm/jobs/view/4555555555/">Veri M&uuml;hendisi</a>
    <p>FunnelFox &middot; T&uuml;rkiye (Remote)</p>
  </td></tr></table>
  <a href="https://www.linkedin.com/comm/jobs/search/?keywords=data">T&uuml;m ilanlar&#305; g&ouml;r</a>
</body></html>
"""


class Ayikla(unittest.TestCase):
    def setUp(self):
        self.isler = L.ilanlari_ayikla(MAIL, "23 yeni iş: Data Analyst")

    def test_ilan_sayisi(self):
        # "Şimdi başvur" ve arama bağlantısı ilan sayılmaz; aynı ilan bir kez alınır
        self.assertEqual(len(self.isler), 3)

    def test_alanlar(self):
        j = self.isler[0]
        self.assertEqual(j["id"], "li-4123456789")
        self.assertEqual(j["title"], "Data Analyst")
        self.assertEqual(j["company"], "HiredBuddy")
        self.assertIn("Istanbul", j["location"])
        self.assertIn("Remote", j["location"])
        self.assertEqual(j["url"], "https://www.linkedin.com/comm/jobs/view/4123456789/")
        self.assertEqual(j["alert"], "23 yeni iş: Data Analyst")

    def test_turkce_karakter_ve_hibrit(self):
        j = self.isler[1]
        self.assertEqual((j["company"], j["title"]), ("Sovos", "Senior BI Developer"))
        self.assertIn("Hybrid", j["location"])
        self.assertEqual(self.isler[2]["title"], "Veri Mühendisi")

    def test_bos_govde(self):
        self.assertEqual(L.ilanlari_ayikla("", ""), [])
        self.assertEqual(L.ilanlari_ayikla("<p>ilan yok</p>", ""), [])

    def test_sirket_konum_ayristirma(self):
        self.assertEqual(L.sirket_konum("Acme · Istanbul, Türkiye (Remote) · 2 gün önce"),
                         ("Acme", "Istanbul, Türkiye (Remote)"))
        # ayraçsız, iki boşlukla ayrılmış şablon
        self.assertEqual(L.sirket_konum("Beta Corp   Berlin, Germany   3 gün önce")[0], "Beta Corp")
        self.assertEqual(L.sirket_konum(""), ("", ""))

    def test_sorgu_gonderenleri_kapsiyor(self):
        q = L.SORGU.format(gun=L.WINDOW_DAYS)
        self.assertIn("jobalerts-noreply@linkedin.com", q)
        self.assertIn("newer_than:4d", q)


if __name__ == "__main__":
    unittest.main()
