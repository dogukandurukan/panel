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
        self.assertEqual({b: len(v) for b, v in k.items()}, {"tr": 5, "de": 3, "nl": 1, "uk": 1})
        self.assertEqual(stats["missing"], {})
        self.assertEqual(len(items), 10)

    # 2
    def test_istanbul_tr_remote_once(self):
        items, *_ = sec([rm("Data Engineer", "Turkey", company="R"), an("Data Engineer", "Istanbul", company="I")])
        tr = kovalar(items)["tr"]
        self.assertEqual([j["label"] for j in tr], ["İstanbul", "Türkiye Remote"])

    # 3
    def test_berlin_oncelikli(self):
        items, *_ = sec([an("Data Engineer", "München", company="M"), an("Data Engineer", "Frankfurt", company="F"),
                         an("Data Engineer", "Berlin", company="B"), an("Data Engineer", "Germany", company="G", remote=True)])
        de = kovalar(items)["de"]
        self.assertEqual(de[0]["company"], "B")
        self.assertEqual(len(de), 3)

    # 4
    def test_tr_bolge_yedegi(self):
        items, _, stats, _ = sec([an("Data Engineer", "Istanbul", company="I"),
                                  rm("Data Engineer", "Worldwide", company="W"),
                                  rm("BI Analyst", "EMEA", company="E"),
                                  rm("Analytics Engineer", "Europe", company="U")])
        tr = kovalar(items)["tr"]
        self.assertEqual(tr[0]["label"], "İstanbul")
        self.assertEqual(sorted(j["label"] for j in tr[1:]), ["EMEA Remote", "Europe Remote", "Worldwide Remote"])
        self.assertEqual(stats["missing"]["tr"]["eksik"], 1)

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
    def test_suresi_dolan_ve_eski_seen_tekrar_onerilmez(self):
        eski = an("Data Engineer", "Berlin", company="Eski", url="https://x/eski")
        yeni = an("Data Engineer", "Berlin", company="Yeni")
        on4 = an("Data Engineer", "Berlin", company="Ondort")
        prev = {"seen": ["https://x/eski"],
                "history": {on4["id"]: {"first_seen": "2026-09-06", "last_seen": "2026-09-20", "status": "listed"}}}
        items, res, stats, hist = sec([eski, yeni, on4], prev)
        self.assertEqual([j["company"] for j in items + res], ["Yeni"])
        self.assertEqual(hist[on4["id"]]["status"], "expired")
        self.assertIn("url:https://x/eski", hist)

    def test_onceki_gunden_kalan_aktif_ilan_kaybolmaz(self):
        dun = an("Data Engineer", "Berlin", company="Dun")
        prev = {"history": {dun["id"]: {"first_seen": "2026-09-18", "last_seen": "2026-09-20", "status": "listed"}}}
        items, *_ = sec([dun, an("Data Engineer", "Hamburg", company="Bugun")], prev)
        de = kovalar(items)["de"]
        self.assertEqual([j["company"] for j in de], ["Bugun", "Dun"])   # yeni önce, eski hâlâ listede
        self.assertFalse(de[1]["is_new"])

    # 11
    def test_kota_yanlis_ulkeyle_doldurulmaz(self):
        items, _, stats, _ = sec([an("Data Engineer", "Berlin", company="B%d" % i) for i in range(8)])
        k = kovalar(items)
        self.assertEqual(len(k["de"]), 3)
        self.assertNotIn("nl", k); self.assertNotIn("uk", k); self.assertNotIn("tr", k)
        self.assertEqual(stats["missing"]["nl"]["eksik"], 1)
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
