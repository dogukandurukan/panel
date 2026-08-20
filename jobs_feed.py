# -*- coding: utf-8 -*-
"""
GÜNÜN 3 İŞİ — İLAN FEED'İ
=========================
Her gün açık (anahtar gerektirmeyen) iş ilanı API'lerinden data/analytics
ilanlarını çeker, hedef profile göre puanlar ve en iyi 3'ünü jobs.json'a yazar.

Kaynaklar — ikisi de herkese açık, kimlik doğrulaması istemez:
  * Arbeitnow   https://www.arbeitnow.com/api/job-board-api   (Almanya + UK ağırlıklı)
  * Remotive    https://remotive.com/api/remote-jobs          (uzaktan çalışma)

TASARIM NOTLARI
---------------
* LinkedIn KULLANILMIYOR. LinkedIn'in bireysel iş arama API'si yok ve
  otomatik erişim Kullanıcı Sözleşmesi'ne aykırı (hesap kısıtlama riski).
  Panel yalnızca ilana giden bir bağlantı gösterir; başvuruyu kullanıcı yapar.
* Kişisel veri (CV, iletişim) BU DOSYADA VE REPODA TUTULMAZ. Repo herkese
  açık. CV/profil yalnızca kullanıcının tarayıcısında (localStorage) durur.
* `seen` listesi sayesinde aynı ilan tekrar tekrar önerilmez.
"""

import datetime as dt
import html
import json
import os
import re
import urllib.parse
import urllib.request

IST = dt.timezone(dt.timedelta(hours=3))
UA = "panel-jobs-feed/1.0 (+https://github.com/dogukandurukan/panel)"
TIMEOUT = 25
OUT = "jobs.json"
PICK = 3            # günde kaç ilan gösterilecek
SEEN_KEEP = 300     # tekrar önlemek için hatırlanan ilan sayısı

# --- hedef profil (kişisel veri değil; yalnızca arama kriteri) ---
TITLE_RE = re.compile(
    r"\b(data\s+engineer|analytics\s+engineer|data\s+scientist|data\s+analyst|"
    r"business\s+intelligence|bi\s+(analyst|engineer|developer)|data\s+platform|"
    r"machine\s+learning|\bml\s+engineer|\bai\s+engineer|analytics\s+(analyst|lead|manager)|"
    r"data\s+architect|big\s+data|etl\s+(developer|engineer)|data\s+warehouse)\b",
    re.I,
)
# başlıkta geçerse ilanı ele (yönetici/satış/staj vb. hedef dışı)
EXCLUDE_RE = re.compile(
    r"\b(intern|internship|praktikum|werkstudent|ausbildung|sales|recruiter|"
    r"account\s+executive|teacher|nurse|driver|warehouse\s+(operative|worker))\b",
    re.I,
)
# kullanıcının güçlü olduğu teknolojiler — ilan metninde geçerse puan
SKILLS = [
    "python", "sql", "pyspark", "spark", "databricks", "azure", "airflow",
    "power bi", "powerbi", "tableau", "looker", "dbt", "snowflake", "etl",
    "data warehouse", "dax", "mssql", "ci/cd", "git", "a/b test", "llm",
]
# Almanca ilan tespiti (Almanca seviyesi orta -> kullanıcı bilmek istiyor)
DE_WORDS = re.compile(
    r"\b(und|oder|wir|unsere|deine|ihre|bei|für|mit|aufgaben|kenntnisse|"
    r"erfahrung|arbeiten|team|stelle|bewerbung|m/w/d|w/m/d)\b", re.I
)


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def clean(txt, limit=None):
    """HTML etiketlerini ve fazla boşlukları at.

    Sıra önemli: önce escape çözülür, SONRA etiket silinir. Ters sırada
    `&lt;div&gt;` etiket silindikten sonra gerçek etikete dönüşüp metinde kalıyordu.
    """
    t = html.unescape(txt or "")
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)              # &amp;lt; gibi çift escape'ler için
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit] if limit else t


def where(location, remote):
    """Konumu sınıflandır: (etiket, puan). Berlin en yüksek öncelik."""
    l = (location or "").lower()
    if "berlin" in l:
        return "Berlin", 50
    de = ("germany", "deutschland", "münchen", "munich", "hamburg", "frankfurt",
          "köln", "cologne", "stuttgart", "düsseldorf", "leipzig", "dresden",
          "nürnberg", "hannover", "bremen", "essen", "dortmund", "bonn",
          "mannheim", "karlsruhe", "freiburg", "münster", "aachen", "wolfsburg")
    if any(k in l for k in de):
        return "Almanya", 30
    nl = ("netherlands", "nederland", "amsterdam", "rotterdam", "utrecht",
          "eindhoven", "hague", "den haag")
    if any(k in l for k in nl):
        return "Hollanda", 35
    uk = ("united kingdom", "london", "manchester", "england", "birmingham",
          "edinburgh", "glasgow", "bristol", "leeds", "cambridge", "oxford")
    if any(k in l for k in uk):
        return "UK", 15
    if remote or "remote" in l or "anywhere" in l:
        return "Remote", 20
    return (location or "—")[:22], 0


def score(job):
    """İlanı hedef profile göre puanla. Yalnızca ilan verisine bakar."""
    s = job["loc_score"]
    if job["remote"]:
        s += 20
    t = job["title"].lower()
    if re.search(r"\b(senior|sr\.?|lead)\b", t):
        s += 12          # 5+ yıl deneyim
    if re.search(r"\b(junior|jr\.?|graduate|entry)\b", t):
        s -= 18
    s += min(len(job["skills"]), 6) * 6      # eşleşen teknoloji başına puan
    d = job.get("days")
    if d is not None:
        s += 14 if d <= 1 else 9 if d <= 3 else 4 if d <= 7 else 0
    return s


def age_days(iso):
    if not iso:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = dt.datetime.strptime(str(iso)[:19], fmt)
            return max((dt.datetime.now() - d).days, 0)
        except ValueError:
            continue
    return None


def norm(*, title, company, location, remote, url, text, posted, source, tags):
    body = clean(text, 4000)
    hay = (title + " " + body + " " + " ".join(tags)).lower()
    found = []
    for sk in SKILLS:
        if sk in hay and sk not in found:
            found.append(sk)
    label, lscore = where(location, remote)
    # bazı kaynaklar başlığa iç referans ekliyor: "... (f/m/d)_metrify" -> temizle
    t_clean = re.sub(r"_[A-Za-z0-9]+\s*$", "", clean(title, 110)).strip()
    j = {
        "title": t_clean,
        "company": clean(company, 60),
        "location": label,
        "loc_raw": clean(location, 60),
        "loc_score": lscore,
        "remote": bool(remote),
        "url": url,
        "source": source,
        "posted": posted,
        "days": age_days(posted),
        "skills": found[:6],
        # ilan Almanca mı — kullanıcının Almancası orta seviye, bilmek işine yarıyor
        "german": len(DE_WORDS.findall(body[:1500])) >= 6,
        "summary": body[:260],
    }
    j["score"] = score(j)
    return j


def from_arbeitnow(pages=4):
    out = []
    for p in range(1, pages + 1):
        try:
            d = get_json(f"https://www.arbeitnow.com/api/job-board-api?page={p}")
        except Exception as e:
            print(f"  arbeitnow sayfa {p} atlandi: {e}")
            break
        rows = d.get("data") or []
        if not rows:
            break
        for r in rows:
            t = r.get("title") or ""
            if not TITLE_RE.search(t) or EXCLUDE_RE.search(t):
                continue
            created = r.get("created_at")
            posted = None
            if created:
                try:
                    posted = dt.datetime.fromtimestamp(int(created)).strftime("%Y-%m-%d")
                except (ValueError, TypeError, OSError):
                    posted = None
            out.append(norm(
                title=t, company=r.get("company_name") or "—",
                location=r.get("location") or "", remote=r.get("remote"),
                url=r.get("url") or "", text=r.get("description") or "",
                posted=posted, source="Arbeitnow", tags=r.get("tags") or [],
            ))
    return out


def from_remotive():
    out = []
    for term in ("data engineer", "analytics engineer", "data scientist", "business intelligence"):
        try:
            d = get_json("https://remotive.com/api/remote-jobs?limit=40&search="
                         + urllib.parse.quote(term))
        except Exception as e:
            print(f"  remotive '{term}' atlandi: {e}")
            continue
        for r in d.get("jobs") or []:
            t = r.get("title") or ""
            if not TITLE_RE.search(t) or EXCLUDE_RE.search(t):
                continue
            out.append(norm(
                title=t, company=r.get("company_name") or "—",
                location=r.get("candidate_required_location") or "Remote", remote=True,
                url=r.get("url") or "", text=r.get("description") or "",
                posted=r.get("publication_date"), source="Remotive",
                tags=r.get("tags") or [],
            ))
    return out


def build():
    prev = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                prev = json.load(f)
        except (ValueError, OSError):
            prev = {}
    seen = list(prev.get("seen") or [])

    jobs = []
    print("Arbeitnow...")
    jobs += from_arbeitnow()
    print(f"  {len(jobs)} uygun ilan")
    n = len(jobs)
    print("Remotive...")
    jobs += from_remotive()
    print(f"  {len(jobs) - n} uygun ilan")

    # aynı ilanı iki kez gösterme (url + şirket/başlık ikilisi)
    uniq, keys = [], set()
    for j in jobs:
        k = (j["company"].lower(), re.sub(r"\W+", "", j["title"].lower())[:40])
        if not j["url"] or j["url"] in seen or k in keys:
            continue
        keys.add(k)
        uniq.append(j)

    uniq.sort(key=lambda x: -x["score"])
    pick = uniq[:PICK]
    for j in pick:
        j.pop("loc_score", None)

    seen = ([j["url"] for j in pick] + seen)[:SEEN_KEEP]
    return {
        "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "ok": len(pick) > 0,
        "count": len(pick),
        "pool": len(uniq),
        "items": pick,
        "seen": seen,
        # panel bu notu gösterebilir; kişisel veri içermez
        "note": "Kaynak: Arbeitnow + Remotive. Basvuruyu kullanici kendisi yapar.",
    }


if __name__ == "__main__":
    data = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"\n{OUT}: {data['count']} ilan yazildi (havuz {data['pool']})")
    for j in data["items"]:
        flag = " [DE]" if j["german"] else ""
        print(f"  {j['score']:>3}p  {j['title'][:46]:46} | {j['company'][:20]:20} | "
              f"{j['location']:9}{flag}")
