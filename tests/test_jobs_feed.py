# -*- coding: utf-8 -*-
"""jobs_feed seçim kuralları — ağ gerektirmez.

    python3 -m unittest tests/test_jobs_feed.py -v

Kayıtlar kaynakların gerçek biçiminde (Arbeitnow / Remotive JSON) yazılır ve
feed'in kendi normalize fonksiyonlarından geçirilir.
"""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import jobs_feed as F  # noqa: E402

BUGUN = dt.date(2026, 9, 21)
TS = int(dt.datetime(2026, 9, 20, 12, tzinfo=F.IST).timestamp())
EN = ("We are looking for someone to join our team and help us build reliable data "
      "products. You will work with stakeholders across the company. Experience with "
      "SQL, Python, Power BI and Azure is required. You will own pipelines and reporting.")


def an(title, location, company="Acme", remote=False, body=EN, created=TS, url=None):
    return F.arbeitnow_kaydi({
        "title": title, "company_name": company, "location": location, "remote": remote,
        "url": url or ("https://www.arbeitnow.com/jobs/" + company + "/" + title).replace(" ", "-"),
        "description": body, "tags": [], "created_at": created,
    })


def hi(title, kis, company="Himco", body=EN, pub=None):
    return F.himalayas_kaydi({
        "title": title, "companyName": company, "locationRestrictions": kis,
        "description": body, "pubDate": str(int(dt.datetime(2026, 9, 20, 9, tzinfo=F.IST).timestamp()) if pub is None else pub),
        "applicationLink": "https://himalayas.app/companies/" + company + "/jobs/" + title.replace(" ", "-"),
    })


def ro(title, loc, company="ROco", body=EN, date="2026-09-20T08:00:00"):
    return F.remoteok_kaydi({
        "position": title, "company": company, "location": loc, "description": body,
        "date": date, "url": "https://remoteok.com/remote-jobs/" + title.replace(" ", "-"), "tags": [],
    })


def rm(title, cand, company="Remoco", body=EN, date="2026-09-20T10:00:00", url=None):
    return F.remotive_kaydi({
        "id": hash(title + company), "title": title, "company_name": company,
        "candidate_required_location": cand, "url": url or "https://remotive.com/remote-jobs/data/" + title.replace(" ", "-"),
        "description": body, "tags": [], "publication_date": date,
    })


def sec(adaylar, prev=None):
    return F.sec(adaylar, prev or {}, BUGUN, log=lambda *_: None)


def kovalar(items):
    out = {}
    for j in items:
        out.setdefault(j["bucket"], []).append(j)
    return out


class Secim(unittest.TestCase):
    def tam_set(self):
        return [
            an("Data Engineer", "Istanbul, Türkiye", company="T1"),
            an("BI Developer", "İstanbul", company="T2"),
            rm("Data Analyst", "Turkey", company="T3"),
            rm("Analytics Engineer", "Türkiye", company="T4"),
            rm("Senior Data Engineer", "Worldwide", company="T5"),
            an("Data Engineer", "Berlin", company="D1"),
            an("Analytics Engineer", "München", company="D2"),
            an("BI Engineer", "Hamburg", company="D3"),
            an("Data Engineer", "Amsterdam, Netherlands", company="N1"),
            an("Data Analyst", "London, United Kingdom", company="U1"),
        ]

    # 1
    def test_tam_gruplama(self):
        items, res, stats, _ = sec(self.tam_set())
        k = kovalar(items)
        self.assertEqual({b: len(v) for b, v in k.items()}, {"tr": 3, "de": 3, "nl": 1, "uk": 1})
        self.assertEqual(stats["missing"].keys(), {"nl", "uk"})   # kota 3, elde 1 aday
        self.assertEqual(len(items), 8)

    # 2 — 23 Eyl: kullanıcı isteğiyle TR'de REMOTE önce, İstanbul hibrit/onsite sonra
    def test_tr_remote_once_istanbul_sonra(self):
        items, *_ = sec([
            an("Data Engineer", "Istanbul", company="ONSITE"),
            an("BI Developer", "Istanbul", company="HIBRIT", body=EN + " This is a hybrid role in our Istanbul office."),
            rm("Analytics Engineer", "Turkey", company="TRREMOTE"),
        ])
        tr = kovalar(items)["tr"]
        self.assertEqual([j["label"] for j in tr], ["Türkiye Remote", "İstanbul Hibrit", "İstanbul"])

    # 3
    def test_berlin_oncelikli(self):
        items, *_ = sec([an("Data Engineer", "München", company="M"), an("Data Engineer", "Frankfurt", company="F"),
                         an("Data Engineer", "Berlin", company="B"), an("Data Engineer", "Germany", company="G", remote=True)])
        de = kovalar(items)["de"]
        self.assertEqual(de[0]["company"], "B")
        self.assertEqual(len(de), 3)

    # 4 — bölge remote'ları TR kovasını doldurur, İstanbul onsite en sonda kalır
    def test_tr_bolge_remote_doldurur(self):
        items, *_ = sec([an("Data Engineer", "Istanbul", company="I"),
                         rm("Data Engineer", "Worldwide", company="W"),
                         rm("BI Analyst", "EMEA", company="E"),
                         rm("Analytics Engineer", "Europe", company="U")])
        tr = kovalar(items)["tr"]
        self.assertEqual(len(tr), 3)
        self.assertTrue(all(j["workplace_type"] == "remote" for j in tr))
        self.assertNotIn("I", [j["company"] for j in tr])

    # 5
    def test_us_only_tr_listesine_girmez(self):
        items, *_ = sec([
            rm("Data Engineer", "USA", company="A"),
            rm("Data Engineer", "Worldwide", company="B", body=EN + " This role is US-only; candidates must be located in the United States."),
            rm("Data Engineer", "Europe", company="C", body=EN + " Applicants need EU work authorization."),
            rm("Data Engineer", "Worldwide", company="D", body=EN + " You must have the right to work in the UK."),
        ])
        self.assertEqual(kovalar(items).get("tr", []), [])

    # 6 + 7
    def test_almanca_sart_ve_ingilizce_ilan(self):
        zorunlu = an("Data Engineer", "Berlin", company="Z",
                     body=EN + " Fluent German (C1) and English are required for this position.")
        artı = an("Data Engineer", "Berlin", company="P", body=EN + " German is a plus but not required.")
        almanca = an("Data Engineer", "Berlin", company="A", body=(
            "Wir suchen dich für unser Team. Du arbeitest mit uns an der Datenplattform und bist "
            "für die Pipelines verantwortlich. Wir bieten dir flexible Arbeitszeiten und ein tolles "
            "Team. Deine Aufgaben sind vielfältig und wir freuen uns auf deine Bewerbung mit SQL und Python."))
        items, res, stats, _ = sec([zorunlu, artı, almanca])
        sirketler = [j["company"] for j in items + res]
        self.assertEqual(sirketler, ["P"])
        self.assertEqual(stats["eliminated"].get("ileri seviye Almanca şartı"), 1)
        self.assertEqual(stats["eliminated"].get("Almanca ilan"), 1)

    # 8
    def test_ayni_ilan_iki_kovaya_girmez(self):
        items, res, *_ = sec(self.tam_set() + [rm("Data Engineer", "Germany, Turkey", company="Cift")])
        idler = [j["id"] for j in items + res]
        self.assertEqual(len(idler), len(set(idler)))
        self.assertEqual([j["bucket"] for j in items + res if j["company"] == "Cift"], ["tr"])

    # 9
    def test_kaynaklar_arasi_tekrar(self):
        a = an("Senior Data Engineer (m/w/d)", "Germany", company="Acme GmbH", remote=True)
        r = rm("Senior Data Engineer", "Germany", company="Acme")
        items, res, stats, _ = sec([a, r])
        self.assertEqual(len(items + res), 1)
        self.assertEqual(stats["eliminated"].get("tekrar (farklı kaynak)"), 1)
        self.assertTrue((items + res)[0]["also_on"])

    # 10 — başvuru/ret/gizle panelde; feed tarafı: 14 gün ve eski 'seen' listesi
    def test_suresi_dolan_ilan_tekrar_onerilmez(self):
        eski = an("Data Engineer", "Berlin", company="Eski", url="https://x/eski")
        yeni = an("Data Engineer", "Berlin", company="Yeni")
        on4 = an("Data Engineer", "Berlin", company="Ondort")
        prev = {"history": {eski["id"]: {"first_seen": "2026-09-01", "last_seen": "2026-09-20", "status": "expired"},
                            on4["id"]: {"first_seen": "2026-09-06", "last_seen": "2026-09-20", "status": "listed"}}}
        items, res, stats, hist = sec([eski, yeni, on4], prev)
        self.assertEqual([j["company"] for j in items + res], ["Yeni"])
        self.assertEqual(hist[on4["id"]]["status"], "expired")

    def test_onceki_gunden_kalan_aktif_ilan_kaybolmaz(self):
        dun = an("Data Engineer", "Berlin", company="Dun")
        prev = {"history": {dun["id"]: {"first_seen": "2026-09-18", "last_seen": "2026-09-20", "status": "listed"}}}
        items, *_ = sec([dun, an("Data Engineer", "Hamburg", company="Bugun")], prev)
        de = kovalar(items)["de"]
        self.assertEqual([j["company"] for j in de], ["Bugun", "Dun"])   # yeni önce, eski hâlâ listede
        self.assertFalse(de[1]["is_new"])

    def test_nl_uk_kotasi_uce_cikti(self):
        s = [an("Data Engineer", "Amsterdam", company="N%d" % i) for i in range(4)] + \
            [an("Data Analyst", "London", company="U%d" % i) for i in range(4)]
        items, *_ = sec(s)
        k = kovalar(items)
        self.assertEqual(len(k["nl"]), 3)
        self.assertEqual(len(k["uk"]), 3)

    def test_yeni_kaynaklar(self):
        """Himalayas locationRestrictions ve Remote OK location alanları kovaya çevrilir."""
        items, res, stats, _ = sec([
            hi("Data Engineer", ["Worldwide"], company="H1"),
            hi("Analytics Engineer", "['Germany']", company="H2"),
            hi("BI Analyst", ["United States"], company="H3"),        # TR'ye uygun değil
            ro("Data Analyst", "Worldwide", company="R1"),
            ro("Data Engineer", "Netherlands", company="R2"),
        ])
        esle = {j["company"]: (j["bucket"], j["label"], j["source"]) for j in items + res}
        self.assertEqual(esle["H1"], ("tr", "Worldwide Remote", "Himalayas"))
        self.assertEqual(esle["H2"][0], "de")
        self.assertNotIn("H3", esle)
        self.assertEqual(esle["R1"], ("tr", "Worldwide Remote", "Remote OK"))
        self.assertEqual(esle["R2"][0], "nl")

    def test_wwr_kaydi(self):
        import xml.etree.ElementTree as ET
        rss = ("<rss><channel><item><title>Toptal: Senior Data Engineer</title>"
               "<region>Anywhere in the World</region><category>Data</category>"
               "<pubDate>Tue, 22 Sep 2026 07:31:13 +0000</pubDate>"
               "<link>https://weworkremotely.com/remote-jobs/toptal-sde</link>"
               "<description>" + EN + "</description></item></channel></rss>")
        j = F.wwr_kaydi(ET.fromstring(rss).find(".//item"))
        self.assertEqual((j["company"], j["title"], j["source"]), ("Toptal", "Senior Data Engineer", "WeWorkRemotely"))
        self.assertEqual(j["publication_date"], "2026-09-22")
        items, *_ = sec([j])
        self.assertEqual((items[0]["bucket"], items[0]["label"]), ("tr", "Worldwide Remote"))

    def test_eski_seen_14_gun_hakki_alir(self):
        """23 Eyl düzeltmesi: eski `seen` kalıcı eleme DEĞİL."""
        j = an("Data Engineer", "Berlin", company="Eski", url="https://x/eski")
        items, res, _, hist = sec([j], {"seen": ["https://x/eski"]})
        self.assertEqual([x["company"] for x in items], ["Eski"])
        self.assertEqual(hist["url:https://x/eski"]["status"], "listed")

    # 11
    def test_kota_yanlis_ulkeyle_doldurulmaz(self):
        items, _, stats, _ = sec([an("Data Engineer", "Berlin", company="B%d" % i) for i in range(8)])
        k = kovalar(items)
        self.assertEqual(len(k["de"]), 3)
        self.assertNotIn("nl", k); self.assertNotIn("uk", k); self.assertNotIn("tr", k)
        self.assertEqual(stats["missing"]["nl"]["eksik"], 3)
        self.assertEqual(stats["missing"]["uk"]["sebep"], "uygun aday yok")

    # 13
    def test_bi_ilani_bi_odakli(self):
        body = ("Build dashboards in Power BI, own reporting and KPIs for the business. You will work "
                "with our AI team and help them understand model outputs. Strong SQL and DAX.")
        for baslik in ["Senior Business Intelligence Lead", "BI Developer", "Power BI Developer", "BI Analyst"]:
            self.assertEqual(F.focus_of(baslik, body)[0], "bi", baslik)
        self.assertEqual(F.focus_of("Data Engineer", "We build pipelines with Airflow, dbt and Spark. AI is everywhere.")[0], "pipeline")
        self.assertEqual(F.focus_of("Senior Data Scientist", "Machine learning models, forecasting, experimentation.")[0], "ml")

    def test_rol_filtresi(self):
        items, res, stats, _ = sec([an(t, "Berlin", company=t) for t in [
            "Data Engineer Intern", "Werkstudent Data Analytics", "Sales Data Analyst", "Marketing Data Analyst",
            "Senior Frontend Developer", "Director of Data Engineering", "Head of BI", "Data Engineer"]])
        self.assertEqual([j["title"] for j in items + res], ["Data Engineer"])

    def test_beceri_bir_kez_sayilir(self):
        j = an("Data Engineer", "Berlin", body=EN + " SQL SQL SQL sql T-SQL Python python.")
        self.assertEqual(j["matched_skills"].count("SQL"), 1)
        self.assertEqual(j["matched_skills"].count("Python"), 1)

    def test_aciklanabilir_alanlar(self):
        items, *_ = sec([an("Data Engineer", "Berlin")])
        o = F.cikti(items[0], "2026-09-21 08:00")
        for alan in ["id", "title", "company", "location", "country", "market", "workplace_type", "source",
                     "source_url", "publication_date", "fit_score", "matched_skills", "focus", "language",
                     "generated_at", "location_reason", "seniority", "url", "skills", "score"]:
            self.assertIn(alan, o)
        self.assertEqual(o["market"], "international")
        self.assertEqual(o["country"], "DE")


if __name__ == "__main__":
    unittest.main()
