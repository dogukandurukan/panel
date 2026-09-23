# -*- coding: utf-8 -*-
"""
GÜNÜN İŞLERİ — İLAN FEED'İ (v2, 21 Eylül 2026)
===============================================
Her gün açık (anahtar gerektirmeyen) iş ilanı API'lerinden data/analytics
ilanlarını çeker, KESİN filtreden geçirir, ülkeye göre gruplar, açıklanabilir
bir uygunluk puanı verir ve kotalı bir seçimle jobs.json'a yazar.

Kotalar (en fazla 10 ilan):
  * Türkiye  3 — YALNIZCA KONUMU TÜRKİYE OLAN ilanlar (23 Eyl, kullanıcı kararı):
                 Türkiye remote > İstanbul hybrid > İstanbul onsite.
                 "Worldwide / Europe / EMEA remote" ilanlar TÜRKİYE SAYILMIYOR ve
                 hiçbir kovaya girmiyor — kullanıcı LinkedIn'deki gibi gerçek
                 Türkiye ilanları istiyor, dünya geneli remote listesi değil.
  * Almanya  3 — Berlin > diğer Almanya şehirleri > Almanya remote
  * Hollanda 3
  * UK       3
Bir ülkenin kotası dolmazsa BAŞKA ülkeyle doldurulmaz; eksik sayı ve sebebi
hem Actions loguna hem jobs.json'daki `stats`'a yazılır.

Kaynaklar — Jooble dışındakiler herkese açık, kimlik doğrulaması istemez:
  * Jooble      https://jooble.org/api/{key}                  (TÜRKİYE kaynağı;
    tek anahtar gerektiren kaynak. Anahtar SADECE GitHub Actions secret'ında
    (JOOBLE_API_KEY); repoya ve panele girmez. Anahtar yoksa sessizce atlanır.)
  * Arbeitnow   https://www.arbeitnow.com/api/job-board-api   (Almanya + UK ağırlıklı)
  * Remotive    https://remotive.com/api/remote-jobs          (yalnız remote)
  * Himalayas   https://himalayas.app/jobs/api                (remote; ilanın hangi
    ülkelerle sınırlı olduğunu `locationRestrictions` ile AÇIKÇA veriyor — TR
    uygunluğu tahmin edilmiyor). Sayfa başına 20 kayıt, cursor ile ilerleniyor;
    `search`/`category` parametreleri YOK SAYILIYOR (23 Eyl'de ölçüldü).
  * Remote OK   https://remoteok.com/api                      (remote; tek istek)
  * WeWorkRemotely https://weworkremotely.com/remote-jobs.rss (remote; tek istek,
    RSS. Kategori akışları 301 dönüyor, genel akış süzülüyor. `region` alanı
    "Anywhere in the World" / "Europe Only" gibi bölge veriyor.)
    API şartı: kaynak adı ve ilana giden bağlantı gösterilecek — panel ikisini
    de yapıyor ("Remote OK" etiketi + "İlana git").
    Remotive public API: günde tek koşu, koşu başına tek istek (public uç
    parametreleri yok sayıp ~18 ilan döndürüyor, bkz. from_remotive). İlanın gerçek Remotive URL'si korunur, kaynak panelde yazar.

TEKRAR POLİTİKASI (eski "son 300 URL bir daha asla" listesinin yerine)
  jobs.json'daki `history` her ilanın durumunu tutar:
    first_seen  ilk kez listeye (seçim ya da yedek) girdiği gün
    last_seen   kaynakta en son görüldüğü gün
    status      listed | expired
  * İlan kaynakta hâlâ duruyorsa ve ilk listelenişinden bu yana 14 gün
    geçmediyse yeniden gösterilebilir (kaybolmaz).
  * 14 gün dolunca `expired` olur, bir daha önerilmez.
  * Kaynakta artık görünmeyen ilan aday olamaz (kaldırılmış sayılır).
  * Eski `seen` listesindeki URL'ler `expired` olarak taşınır — eskiden de bir
    daha gösterilmiyorlardı, davranış korunur.
  * "Başvurdum", "Ret" ve "Uygun değil/gizle" bilgisi kullanıcının tarayıcısında
    (ve gizli gist'te) durur; bu repo herkese açık olduğu için feed onu okumaz.
    Bunun yerine her kova için YEDEK adaylar da yazılır, panel işaretlenenleri
    çıkarıp yedeklerden doldurur.

TASARIM NOTLARI
---------------
* LinkedIn KULLANILMIYOR (bireysel API yok, otomatik erişim sözleşmeye aykırı).
* Kişisel veri (CV, iletişim, başvurulan şirketler) BU DOSYADA VE REPODA TUTULMAZ.
* Test: `python3 -m unittest tests/test_jobs_feed.py` (ağ gerektirmez).
  Ağla deneme koşusu: `JOBS_OUT=/tmp/jobs.json python3 jobs_feed.py`
"""

import datetime as dt
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request

IST = dt.timezone(dt.timedelta(hours=3))
UA = "panel-jobs-feed/2.0 (+https://github.com/dogukandurukan/panel)"
TIMEOUT = 25
OUT = os.environ.get("JOBS_OUT", "jobs.json")
PREV = os.environ.get("JOBS_PREV", "jobs.json")

QUOTA = {"tr": 3, "de": 3, "nl": 3, "uk": 3}          # 23 Eyl: NL 5->3 istek üzerine, NL/UK 1 -> 3
# panel başvurulan/gizlenen ilanları çıkarınca bu yedeklerden doldurur
RESERVE = {"tr": 5, "de": 5, "nl": 3, "uk": 3}
BUCKET_ORDER = ["tr", "de", "nl", "uk"]
BUCKET_AD = {"tr": "Türkiye", "de": "Almanya", "nl": "Hollanda", "uk": "UK"}
COUNTRY_OF = {"de": "DE", "nl": "NL", "uk": "UK", "tr": "TR"}

MAX_LIST_DAYS = 14      # işlem yapılmamış ilan en fazla bu kadar gün listede kalır
MAX_POST_AGE = 45       # yayın tarihi bundan eskiyse aday değil
HISTORY_KEEP = 30       # kaynakta bu kadar gün görünmeyen geçmiş kaydı silinir
MIN_FIT = 35            # bunun altı "kalitesiz" — kotayı doldurmak için gösterilmez

# ---------------------------------------------------------------- rol filtresi
# Kullanıcının deneyimine doğrudan uyan roller
ROLE_PRIMARY = re.compile(
    r"\b(data\s+engineer|analytics\s+engineer|"
    r"bi\s+(engineer|developer|analyst|consultant|specialist)|business\s+intelligence|\bbi\b|"
    r"data\s+analyst|reporting\s+analyst|analytics\s+analyst|"
    r"data\s+platform|etl\b|data\s+integration|azure\s+data|power\s?bi|"
    r"data\s+warehouse|dwh\b|analytics\s+consultant|data\s*(&|and)\s*analytics|"
    # Türkçe ilan başlıkları (Jooble gibi TR kaynakları için)
    r"veri\s+(analist|analiz|m[üu]hendis|ambar|taban)\w*|i[şs]\s+zekas\w*|"
    r"raporlama\s+(uzman|analist|m[üu]hendis)\w*|anali[tz]ik\s+m[üu]hendis\w*|"
    r"veri\s+platform\w*|veri\s+entegrasyon\w*)",
    re.I)
# Uygun olduğunda: ML / Data Science (daha düşük rol puanı)
ROLE_SECONDARY = re.compile(
    r"\b(data\s+scien(ce|tist)|machine\s+learning\s+engineer|ml\s+engineer|"
    r"mlops\s+engineer|ml\s+data\s+engineer|veri\s+bilimci\w*|makine\s+[öo][ğg]renmesi)", re.I)
# Başlıkta geçerse ilan elenir
TITLE_EXCLUDE = re.compile(
    r"\b(intern|internship|praktikum|praktikant\w*|werkstudent\w*|working\s+student|"
    r"student\w*|trainee|ausbildung|azubi|thesis|abschlussarbeit|"
    r"sales|vertrieb|business\s+development|account\s+(executive|manager)|"
    r"recruit\w*|talent\s+acquisition|marketing|"
    r"front[-\s]?end|back[-\s]?end|full[-\s]?stack|mobile|ios|android|"
    r"director|vice\s+president|vp|head\s+of|chief|cto|cdo|"
    r"product\s+(manager|owner|director)|legal|counsel|"
    r"teacher|nurse|driver|"
    # Türkçe elemeler
    r"staj\w*|sat[ıi][şs]\w*|pazarlama|m[üu][şs]teri\s+temsilcis\w*|"
    r"direkt[öo]r\w*|genel\s+m[üu]d[üu]r\w*|i[şs]e\s+al[ıi]m)\b", re.I)
# Yoğun ekip yönetimi — elemiyor, puan düşürüyor
PEOPLE_MGMT = re.compile(
    r"(people\s+management|line\s+management|direct\s+reports|manage\s+a\s+team\s+of|"
    r"build\s+and\s+lead\s+(a|the)\s+team|lead\s+a\s+team\s+of\s+\d+|"
    r"disziplinarische\s+führung|personalverantwortung)", re.I)

# ---------------------------------------------------------------- beceriler
# (etiket, desen). Her beceri ilanda kaç kez geçerse geçsin BİR kez sayılır.
SKILLS = [
    ("SQL", r"\bsql\b|t-sql|\btsql\b"),
    ("Python", r"\bpython\b"),
    ("Power BI", r"\bpower\s?bi\b"),
    ("Tableau", r"\btableau\b"),
    ("Azure", r"\bazure\b"),
    ("Microsoft Fabric", r"microsoft\s+fabric|\bms\s+fabric\b|\bfabric\s+(lakehouse|data\s+factory|warehouse|notebooks?)"),
    ("SSIS", r"\bssis\b"),
    ("ETL", r"\betl\b|\belt\b"),
    ("Airflow", r"\bairflow\b"),
    ("Databricks", r"\bdatabricks\b"),
    ("PySpark", r"\bpyspark\b|\bspark\b"),
    ("PostgreSQL", r"\bpostgres(ql)?\b"),
    ("DAX", r"\bdax\b"),
    ("Power Query", r"\bpower\s?query\b"),
    ("Snowflake", r"\bsnowflake\b"),
    ("dbt", r"\bdbt\b"),
]
SKILLS_RE = [(ad, re.compile(p, re.I)) for ad, p in SKILLS]

# ---------------------------------------------------------------- dil
DE_WORDS = re.compile(
    r"\b(und|oder|wir|uns|unsere|unser|deine|dein|ihre|dich|bei|für|mit|von|"
    r"dem|den|der|die|das|ein|eine|einen|einem|nicht|auch|sowie|aufgaben|"
    r"kenntnisse|erfahrung|erfahrungen|arbeiten|stelle|bewerbung|profil|"
    r"suchen|bieten|willkommen|standort|mitarbeiter|unternehmen|abgeschlossenes|"
    r"idealerweise|zusammen|weiter|werden|haben|sind|ist|wird|kannst|"
    r"gute|sehr|mehr|über|durch|schon|damit|dabei)\b", re.I)
EN_WORDS = re.compile(
    r"\b(the|and|you|your|our|we|with|for|from|will|are|is|have|has|this|that|"
    r"work|team|role|experience|skills|about|what|who|how|be|to|of|in|on|as|"
    r"looking|join|help|build|across|within|able|strong|good|more|than|"
    r"including|using|ensure|drive|support)\b", re.I)
TR_WORDS = re.compile(
    r"\b(ve|bir|için|ile|olarak|deneyim\w*|aranan|nitelik\w*|bu|en\s+az|olan|veya|"
    r"sahip|konusunda|bilgi\w*|çalışma|ekibimize|arıyoruz|yıl|iyi|tercih)\b", re.I)
# "ileri seviye Almanca ŞART" — plus/avantaj diyenler elenmez
DE_REQ = re.compile(
    r"((fluent|fließend\w*|verhandlungssicher\w*|native|muttersprach\w*|excellent|"
    r"very\s+good|sehr\s+gute?\w*|business[-\s]fluent|proficient|strong)\s+"
    r"(command\s+of\s+|knowledge\s+of\s+|skills\s+in\s+|in\s+)?(german|deutsch\w*)"
    r"|\b(german|deutsch\w*)\s*[(:\-–]?\s*(c1|c2|native|fluent|muttersprach\w*|verhandlungssicher\w*)"
    r"|deutschkenntnisse\s+(auf\s+)?(c1|c2|muttersprach\w*|verhandlungssicher\w*)"
    r"|german\s+(is|are)\s+(a\s+)?(must|required|mandatory))", re.I)
DE_REQ_YUMUSAK = re.compile(
    r"(plus|advantage|nice|bonus|beneficial|preferred|desirable|von\s+vorteil|"
    r"wünschenswert|optional|not\s+required|kein\s+muss)", re.I)

# ---------------------------------------------------------------- konum
DE_YER = ("berlin", "germany", "deutschland", "(deu)", "münchen", "munich", "muenchen",
          "hamburg", "frankfurt", "köln", "koeln", "cologne", "stuttgart", "düsseldorf",
          "duesseldorf", "leipzig", "dresden", "nürnberg", "nuremberg", "hannover",
          "hanover", "bremen", "essen", "dortmund", "bonn", "mannheim", "karlsruhe",
          "freiburg", "münster", "aachen", "wolfsburg", "heidelberg", "potsdam",
          "garching", "augsburg", "regensburg", "ingolstadt", "darmstadt", "wiesbaden",
          "mainz", "kiel", "lübeck", "rostock", "erlangen", "würzburg", "ulm",
          "bielefeld", "bochum", "duisburg", "wuppertal", "langenfeld", "bayern",
          "bavaria", "hessen", "nrw", "nordrhein", "baden", "sachsen", "brandenburg",
          "niedersachsen", "schleswig")
NL_YER = ("netherlands", "nederland", "amsterdam", "rotterdam", "utrecht", "eindhoven",
          "the hague", "den haag", "groningen", "leiden", "haarlem", "delft", "tilburg",
          "arnhem", "nijmegen", "breda")
UK_YER = ("united kingdom", "london", "manchester", "england", "birmingham", "edinburgh",
          "glasgow", "bristol", "leeds", "cambridge", "oxford", "scotland", "wales",
          "belfast", "liverpool", "newcastle", "sheffield", "nottingham", "reading")
TR_YER = ("istanbul", "i̇stanbul", "türkiye", "turkey", "turkiye", "ankara", "izmir",
          "i̇zmir", "bursa", "antalya", "kocaeli")
# Remotive candidate_required_location jetonları
REGION_TOK = {
    "worldwide": "worldwide", "anywhere": "worldwide", "global": "worldwide",
    "anywhere in the world": "worldwide", "anywhere in world": "worldwide",
    "europe": "europe", "european": "europe", "cet": "europe", "cet timezone": "europe",
    "emea": "emea",
}
COUNTRY_TOK = {
    "turkey": "TR", "türkiye": "TR", "turkiye": "TR",
    "germany": "DE", "deutschland": "DE",
    "netherlands": "NL", "the netherlands": "NL", "holland": "NL",
    "uk": "UK", "united kingdom": "UK", "england": "UK", "great britain": "UK", "gb": "UK",
}
# Türkiye'den başvuruyu engelleyen açıklama kalıpları (Worldwide/Europe/EMEA
# etiketi tek başına güvence değil).
TR_ENGEL = [
    (r"\b(us|u\.s\.|usa|united\s+states|canada|uk|eu|latam|americas|north\s+america)[-\s](only|based)\b", "ülke kısıtı"),
    (r"\bonly\s+(open\s+to\s+|accept\w*\s+|consider\w*\s+|hiring\s+)?(candidates|applicants|people|residents)?\s*"
     r"(from|in|based\s+in|located\s+in|residing\s+in)\s+(the\s+)?(us|u\.s\.|usa|united\s+states|canada|uk|"
     r"united\s+kingdom|eu|european\s+union|germany|spain|portugal|poland|latam|americas|north\s+america)\b", "ülke kısıtı"),
    (r"\bmust\s+(be\s+)?(located|based|reside|residing|live|living)\s+in\s+(the\s+)?(us|u\.s\.|usa|united\s+states|"
     r"canada|uk|united\s+kingdom|eu|european\s+union|germany|spain|portugal|poland|latam|americas|north\s+america)\b", "ikamet şartı"),
    (r"\b(eu|european\s+union|us|u\.s\.|uk|canadian|american)\s+(work|working)\s+(authori[sz]ation|permit|visa|rights?)", "çalışma izni şartı"),
    (r"\bright\s+to\s+work\s+in\s+(the\s+)?(uk|us|eu|european\s+union|germany|netherlands|united\s+kingdom|united\s+states)", "çalışma izni şartı"),
    (r"\b(authori[sz]ed|eligible|legally\s+allowed)\s+to\s+work\s+in\s+(the\s+)?(us|u\.s\.|usa|united\s+states|canada|"
     r"uk|united\s+kingdom|eu|european\s+union)", "çalışma izni şartı"),
    (r"\b(eu|us|u\.s\.)\s+citizen(s|ship)?\b", "vatandaşlık şartı"),
    (r"\b(us|u\.s\.|usa|north\s+american)\s+time\s?zones?\s+only\b", "saat dilimi kısıtı"),
    (r"\bwe\s+(are\s+)?(not\s+able|unable)\s+to\s+(hire|sponsor)\b.{0,60}\boutside\s+(of\s+)?(the\s+)?(us|eu|uk|europe)", "ülke kısıtı"),
]
TR_ENGEL_RE = [(re.compile(p, re.I), neden) for p, neden in TR_ENGEL]


# ================================================================ yardımcılar
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


def kucult(t):
    """Türkçe güvenli küçültme: 'İ'.lower() -> i + U+0307 tuzağı (DEVAM.md §5.10)."""
    return (t or "").replace("İ", "i").lower().replace("i̇", "i")


def age_days(iso, bugun=None):
    if not iso:
        return None
    ref = bugun or dt.datetime.now(IST).date()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = dt.datetime.strptime(str(iso)[:19], fmt).date()
            return max((ref - d).days, 0)
        except ValueError:
            continue
    return None


def dil(text, title=""):
    """'de' | 'tr' | 'en' — işlev kelimesi yoğunluğu KIYASLANIR (mutlak eşik
    yetmiyordu: Almanca sloganla başlayıp İngilizce devam eden ilanlar var)."""
    sample = (text or "")[:2500]
    de = len(DE_WORDS.findall(sample))
    en = len(EN_WORDS.findall(sample))
    tr = len(TR_WORDS.findall(sample))
    if de + en + tr < 8:                   # metin çok kısa -> başlığa bak
        if re.search(r"\b(und|für|mit|wir|deine)\b", title or "", re.I):
            return "de"
        if re.search(r"\b(ve|için|uzman\w*|mühendis\w*)\b", title or "", re.I):
            return "tr"
        return "en"
    enc = max(de, en, tr)
    return "de" if enc == de and de > en else ("tr" if enc == tr and tr > en else "en")


def almanca_sart(text):
    """İlan ileri seviye / ana dil Almanca ŞART koşuyor mu? 'plus' diyorsa hayır."""
    for m in DE_REQ.finditer(text or ""):
        pencere = (text or "")[m.end(): m.end() + 60]
        once = (text or "")[max(0, m.start() - 25): m.start()]
        if DE_REQ_YUMUSAK.search(pencere) or DE_REQ_YUMUSAK.search(once):
            continue
        return m.group(0)
    return ""


def tr_engeli(text):
    """Worldwide/Europe/EMEA ilanında Türkiye'den başvuruyu engelleyen kısıt."""
    for rx, neden in TR_ENGEL_RE:
        m = rx.search(text or "")
        if m:
            return neden + ": \"" + m.group(0)[:60] + "\""
    return ""


def eslesen_beceriler(text):
    return [ad for ad, rx in SKILLS_RE if rx.search(text or "")]


def kidem(title, body):
    t = title.lower()
    if re.search(r"\b(junior|jr\.?|graduate|entry[-\s]level|berufseinsteiger)\b", t):
        return "junior"
    if re.search(r"\b(lead|principal|staff|team\s*lead|teamleiter\w*)\b", t):
        return "lead"
    if re.search(r"\bmanager\b", t):
        return "manager"
    if re.search(r"\b(senior|sr\.?)\b", t):
        return "senior"
    return "mid"


# ---- focus: cover letter hangi deneyim bloğunu öne çıkaracak
# "ai" / "model" gibi her yerde geçen kelimeler TEK BAŞINA ML seçtirmez;
# başlık 3 kat ağırlıkta, her terim en fazla 3 kez sayılır.
FOCUS_TERMS = {
    "ml": [r"machine\s+learning", r"deep\s+learning", r"\bmlops\b", r"\bml\b", r"model\s+(training|deployment|serving)",
           r"predictive\s+model", r"\bnlp\b", r"computer\s+vision", r"data\s+scien(ce|tist)", r"recommend(ation|er)\s+system",
           r"(train|fine[-\s]?tun)\w*\s+(models?|llms?)"],
    "bi": [r"\bpower\s?bi\b", r"\btableau\b", r"\blooker\b", r"dashboards?", r"\breporting\b", r"business\s+intelligence",
           r"\bbi\b", r"\bdax\b", r"\bkpis?\b", r"visuali[sz]ation", r"semantic\s+model", r"self[-\s]service",
           r"\bpower\s?query\b", r"\bssrs\b"],
    "pipeline": [r"pipelines?", r"\betl\b", r"\belt\b", r"ingestion", r"\bairflow\b", r"\bdbt\b", r"\bspark\b", r"pyspark",
                 r"databricks", r"data\s+warehous\w*", r"lakehouse", r"streaming", r"\bkafka\b", r"orchestrat\w*",
                 r"data\s+platform", r"data\s+integration", r"\bssis\b"],
    "business": [r"stakeholders?", r"business\s+impact", r"commercial", r"strateg\w+", r"cross[-\s]functional",
                 r"\bgrowth\b", r"insights?", r"decision[-\s]making", r"product\s+analytics", r"a/b\s+test"],
}
FOCUS_RE = {k: [re.compile(p, re.I) for p in v] for k, v in FOCUS_TERMS.items()}
FOCUS_TITLE = [
    ("bi", re.compile(r"\b(bi|business\s+intelligence|power\s?bi|reporting|dashboard)\b", re.I)),
    ("pipeline", re.compile(r"\b(data\s+engineer|analytics\s+engineer|etl|data\s+platform|data\s+integration|dwh|data\s+warehouse)\b", re.I)),
    ("ml", re.compile(r"\b(data\s+scien\w*|machine\s+learning|ml|mlops)\b", re.I)),
    ("business", re.compile(r"\b(data\s+analyst|analytics\s+consultant|analyst)\b", re.I)),
]


def focus_of(title, body):
    puan = {k: 0 for k in FOCUS_RE}
    for k, rxs in FOCUS_RE.items():
        for rx in rxs:
            puan[k] += 3 * min(len(rx.findall(title or "")), 1) + min(len(rx.findall(body or "")), 3)
    for k, rx in FOCUS_TITLE:
        if rx.search(title or ""):
            puan[k] += 8
            break                                # başlıktaki en belirgin rol yeter
    sira = ["bi", "pipeline", "ml", "business"]  # eşitlikte daha dar olan kazanır
    return max(sira, key=lambda k: (puan[k], -sira.index(k))), puan


KEY_RE = re.compile(
    r"\b(stakeholder|dashboard|pipeline|forecast|automation|governance|"
    r"optimi[sz]ation|migration|real[- ]?time|self[- ]?service|data quality|"
    r"cost|scalab|experimentation|a/b|root cause|anomaly|retail|energy|"
    r"finance|supply chain|e-?commerce|saas|startup|enterprise)\w*", re.I)


def keywords_of(body):
    out = []
    for m in KEY_RE.findall(body or ""):
        k = m.lower()
        if k not in out:
            out.append(k)
    return out[:12]


def baslik_temiz(title):
    t = re.sub(r"_[A-Za-z0-9]+\s*$", "", clean(title, 140)).strip()   # "... (f/m/d)_metrify"
    return t


def anahtar(company, title):
    """Kaynaklar arası tekrar anahtarı: şirket + cinsiyet/konum ekleri atılmış başlık."""
    t = kucult(title)
    t = re.sub(r"\((m|w|f|d|x|all\s*genders?|gn\*?|w/m/d|m/w/d|f/m/d|d/f/m|m/f/d|m/f/x|f/m/x)[^)]*\)", " ", t)
    t = re.sub(r"[^a-z0-9ğüşöçı]+", "", t)[:60]
    c = re.sub(r"\b(gmbh|ag|se|ltd|limited|inc|bv|b\.v\.|llc|a\.ş\.|as)\b", "", kucult(company))
    c = re.sub(r"[^a-z0-9ğüşöçı]+", "", c)
    return c + "|" + t


def ilan_id(company, title):
    return hashlib.sha1(anahtar(company, title).encode("utf-8")).hexdigest()[:12]


# ================================================================ konum
def _var(l, liste):
    return any(k in l for k in liste)


def konum_arbeitnow(location, remote, title, body):
    """Arbeitnow: serbest metin konum + remote bayrağı."""
    l = kucult(location)
    hib = bool(re.search(r"\bhybrid\b|hybrides?\s+arbeiten", kucult(location + " " + title + " " + body[:1500])))
    wp = "remote" if remote else ("hybrid" if hib else ("onsite" if l else "unknown"))
    if _var(l, TR_YER):
        ulke, sehir = "TR", ("İstanbul" if "istanbul" in l else location.split(",")[0].strip())
    elif _var(l, NL_YER):
        ulke, sehir = "NL", location.split(",")[0].strip()
    elif _var(l, UK_YER):
        ulke, sehir = "UK", location.split(",")[0].strip()
    elif _var(l, DE_YER):
        ulke, sehir = "DE", ("Berlin" if "berlin" in l else location.split(",")[0].strip())
    else:
        return {"country": None, "city": location[:40], "workplace_type": wp, "regions": [],
                "location_reason": "ülke belirlenemedi: '" + location[:40] + "'"}
    if ulke != "TR" and remote and not sehir:
        sehir = ""
    return {"country": ulke, "city": sehir, "workplace_type": wp, "regions": [],
            "location_reason": "Arbeitnow konumu '" + location[:40] + "'" + (" · remote" if remote else "")}


def konum_remotive(cand):
    """Remotive `candidate_required_location`: jetonlara ayır, ülke/bölge çıkar."""
    raw = (cand or "").strip()
    jetonlar = [kucult(x).strip() for x in re.split(r"[,;/|]|\band\b", raw) if x.strip()]
    ulkeler, bolgeler, diger = [], [], []
    for j in jetonlar:
        j2 = re.sub(r"\s*(only|timezones?|time\s+zones?)$", "", j).strip()
        if j2 in COUNTRY_TOK:
            ulkeler.append(COUNTRY_TOK[j2])
        elif j2 in REGION_TOK:
            bolgeler.append(REGION_TOK[j2])
        elif j2:
            diger.append(j2)
    if not raw:
        bolgeler.append("worldwide")
    if "TR" in ulkeler:
        ulke = "TR"
    elif ulkeler:
        ulke = ulkeler[0]
    else:
        ulke = None
    return {"country": ulke, "city": "", "workplace_type": "remote",
            "regions": sorted(set(bolgeler)), "countries_listed": ulkeler, "other_listed": diger,
            "location_reason": "Remotive candidate_required_location '" + raw[:60] + "'"}


# ================================================================ normalize
def normalize(*, title, company, location, remote, url, text, posted, source, tags, cand=None):
    body = clean(text, 6000)
    t = baslik_temiz(title)
    hay = t + " " + body + " " + " ".join(tags or [])
    if cand is not None:                    # remote kaynaklar: Remotive / Himalayas / Remote OK
        yer = konum_remotive(cand)
        yer_metin = cand or "Remote"
    else:
        yer = konum_arbeitnow(location or "", remote, t, body)
        yer_metin = clean(location, 60)
    f, fpuan = focus_of(t, body)
    return {
        "id": ilan_id(company, t),
        "key": anahtar(company, t),
        "title": t,
        "company": clean(company, 60),
        "location": yer_metin or "—",
        "source": source,
        "source_url": url or "",
        "publication_date": posted,
        "body": body,
        "tags": tags or [],
        "matched_skills": eslesen_beceriler(hay),
        "language": dil(body, t),
        "de_req": almanca_sart(body),
        "focus": f,
        "focus_scores": fpuan,
        "seniority": kidem(t, body),
        "people_mgmt": bool(PEOPLE_MGMT.search(body)),
        **yer,
    }


def arbeitnow_kaydi(r):
    created = r.get("created_at")
    posted = None
    if created:
        try:
            posted = dt.datetime.fromtimestamp(int(created), IST).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            posted = None
    return normalize(
        title=r.get("title") or "", company=r.get("company_name") or "—",
        location=r.get("location") or "", remote=bool(r.get("remote")),
        url=r.get("url") or "", text=r.get("description") or "",
        posted=posted, source="Arbeitnow", tags=r.get("tags") or [],
    )


def remotive_kaydi(r):
    return normalize(
        title=r.get("title") or "", company=r.get("company_name") or "—",
        location=None, remote=True, url=r.get("url") or "",
        text=r.get("description") or "", posted=(r.get("publication_date") or "")[:10] or None,
        source="Remotive", tags=r.get("tags") or [],
        cand=r.get("candidate_required_location") or "",
    )


def himalayas_kaydi(r):
    kis = r.get("locationRestrictions")
    if isinstance(kis, str):
        kis = [x.strip(" '\"[]") for x in kis.strip("[]").split(",") if x.strip(" '\"[]")]
    kis = kis or []
    posted = None
    try:
        posted = dt.datetime.fromtimestamp(int(r.get("pubDate") or 0), IST).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        posted = None
    return normalize(
        title=r.get("title") or "", company=r.get("companyName") or "—",
        location=None, remote=True,
        url=r.get("applicationLink") or r.get("guid") or "",
        text=r.get("description") or r.get("excerpt") or "", posted=posted,
        source="Himalayas", tags=[], cand=", ".join(kis) or "Worldwide",
    )


def remoteok_kaydi(r):
    return normalize(
        title=r.get("position") or r.get("title") or "", company=r.get("company") or "—",
        location=None, remote=True, url=r.get("url") or "",
        text=r.get("description") or "", posted=(r.get("date") or "")[:10] or None,
        source="Remote OK", tags=r.get("tags") or [],
        cand=r.get("location") or "Worldwide",
    )


def from_himalayas(pages=12):
    """Sayfa başına 20 kayıt; `search`/`category` çalışmıyor, bu yüzden son ~400
    ilan gezilip veri rolleri süzülüyor. İstekler arası 1 sn."""
    out, cur = [], None
    for _ in range(pages):
        u = "https://himalayas.app/jobs/api?limit=100" + (("&cursor=" + urllib.parse.quote(cur)) if cur else "")
        try:
            d = get_json(u)
        except Exception as e:
            print(f"  himalayas atlandi: {e}")
            break
        out += [himalayas_kaydi(r) for r in (d.get("jobs") or [])]
        cur = d.get("nextCursor")
        if not cur:
            break
        time.sleep(1)
    return out


def from_remoteok():
    try:
        d = get_json("https://remoteok.com/api")
    except Exception as e:
        print(f"  remoteok atlandi: {e}")
        return []
    # ilk kayıt API şartlarını taşıyan meta satırı
    return [remoteok_kaydi(r) for r in (d or [])[1:] if r.get("position")]


WWR_BOLGE = {"anywhere in the world": "Worldwide", "europe only": "Europe", "emea only": "EMEA",
             "north america only": "North America", "usa only": "USA", "latin america only": "LATAM",
             "asia only": "Asia", "africa only": "Africa", "oceania only": "Oceania"}


def wwr_kaydi(item):
    """WeWorkRemotely RSS öğesi. Başlık 'Şirket: Pozisyon' biçiminde."""
    ham = (item.findtext("title") or "").strip()
    sirket, _, poz = ham.partition(":")
    if not poz:
        sirket, poz = "—", ham
    bolge = (item.findtext("region") or "").strip()
    posted = None
    pd = item.findtext("pubDate")
    if pd:
        try:
            posted = dt.datetime.strptime(pd[:25].strip(), "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d")
        except ValueError:
            posted = None
    return normalize(
        title=poz.strip(), company=sirket.strip(), location=None, remote=True,
        url=(item.findtext("link") or item.findtext("guid") or "").strip(),
        text=item.findtext("description") or "", posted=posted, source="WeWorkRemotely",
        tags=[x for x in [(item.findtext("category") or "").strip()] if x],
        cand=WWR_BOLGE.get(kucult(bolge), bolge or "Worldwide"),
    )


def from_wwr():
    """Tek istek, RSS (stdlib xml.etree). Kategori akışları 301 dönüyor; genel
    akış kullanılıp veri rolleri kendi filtremizle süzülüyor (23 Eyl ölçümü)."""
    import xml.etree.ElementTree as ET
    try:
        req = urllib.request.Request("https://weworkremotely.com/remote-jobs.rss", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            kok = ET.fromstring(r.read())
    except Exception as e:
        print(f"  weworkremotely atlandi: {e}")
        return []
    return [wwr_kaydi(x) for x in kok.findall(".//item")]


# ---------------------------------------------------------------- Jooble (TR)
# Türkiye ilanları için TEK gerçekçi kaynak: Arbeitnow/Remotive/Himalayas/
# RemoteOK/WWR'de Türkiye ilanı yok (23 Eyl ölçümü: 1741 ilanda 2 tanesi
# Türkiye'yi anıyor, ikisi de veri rolü değil).
# ANAHTAR: yalnızca GitHub Actions secret'ı JOOBLE_API_KEY. Repoya girmez,
# panele inmez. Anahtar yoksa kaynak sessizce atlanır — feed çalışmaya devam
# eder, yalnızca Türkiye kovası boş kalır.
JOOBLE_SORGULAR = ["data engineer", "data analyst", "business intelligence",
                   "veri analisti", "veri mühendisi", "power bi"]
JOOBLE_KONUM = "Türkiye"


def jooble_kaydi(r):
    metin = clean(r.get("snippet") or "", 2000)
    yer = clean(r.get("location") or "", 60)
    hay = kucult((r.get("title") or "") + " " + metin + " " + yer)
    uzak = bool(re.search(r"\bremote\b|uzaktan|home\s*office|evden", hay))
    hibrit = bool(re.search(r"\bhybrid\b|hibrit|karma\s+[çc]al[ıi][şs]ma", hay))
    posted = (r.get("updated") or "")[:10] or None
    j = normalize(
        title=r.get("title") or "", company=r.get("company") or "—",
        location=yer, remote=uzak, url=r.get("link") or "",
        text=metin, posted=posted, source="Jooble", tags=[],
    )
    # Arbeitnow kalıbı "hybrid" kelimesini gövdede arıyor; Jooble'da gövde
    # yalnızca kısa bir özet, o yüzden burada açıkça işaretliyoruz.
    if not uzak and hibrit:
        j["workplace_type"] = "hybrid"
    return j


def from_jooble():
    anahtar = (os.environ.get("JOOBLE_API_KEY") or "").strip()
    if not anahtar:
        print("  JOOBLE_API_KEY yok — Jooble atlandı (Türkiye kovası boş kalabilir)")
        return []
    out, gorulen = [], set()
    for i, sorgu in enumerate(JOOBLE_SORGULAR):
        if i:
            time.sleep(2)
        try:
            govde = json.dumps({"keywords": sorgu, "location": JOOBLE_KONUM}).encode("utf-8")
            req = urllib.request.Request(
                "https://jooble.org/api/" + urllib.parse.quote(anahtar), data=govde,
                headers={"Content-Type": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            # Anahtar hatalıysa da feed çökmesin; sebebi logla (anahtar BASILMAZ)
            print(f"  jooble '{sorgu}' atlandi: {type(e).__name__}")
            continue
        for r in d.get("jobs") or []:
            k = (r.get("link") or "") + (r.get("title") or "")
            if k in gorulen:
                continue
            gorulen.add(k)
            out.append(jooble_kaydi(r))
    return out


def from_arbeitnow(pages=10):
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
        out += [arbeitnow_kaydi(r) for r in rows]
        time.sleep(1)                      # kibar ol
    return out


def from_remotive():
    """Koşu başına TEK istek. 21 Eyl 2026'da ölçüldü: public API `category` ve
    `search` parametrelerini yok sayıp her istekte aynı ~18 güncel ilanı
    döndürüyor; ek istekler hiçbir ilan eklemiyor, yalnızca rate limit yiyordu.
    Parametre yine gönderiliyor (API ileride dikkate alırsa işe yarar)."""
    out, gorulen = [], set()
    istekler = ["category=data"]
    for i, q in enumerate(istekler):
        if i:
            time.sleep(3)
        try:
            d = get_json("https://remotive.com/api/remote-jobs?" + q)
        except Exception as e:
            print(f"  remotive '{q}' atlandi: {e}")
            continue
        for r in d.get("jobs") or []:
            if r.get("id") in gorulen:
                continue
            gorulen.add(r.get("id"))
            out.append(remotive_kaydi(r))
    return out


# ================================================================ değerlendirme
def rol(title):
    if ROLE_PRIMARY.search(title):
        return "primary"
    if ROLE_SECONDARY.search(title):
        return "secondary"
    return None


def kova(j):
    """(kova, kademe, konum_puanı, etiket) ya da (None, sebep). Kademe küçük = öncelikli."""
    u, wp = j.get("country"), j.get("workplace_type")
    if u == "TR":
        sehir = kucult(j.get("city"))
        if wp == "remote":
            # "Turkey" listelenmiş ama metin başka ülkeye izin/ikamet şartı
            # koyuyorsa (ör. "right to work in the UK") gerçek bir TR ilanı değil
            engel = tr_engeli(j.get("body", ""))
            if engel:
                return (None, "TR listelenmiş ama " + engel)
            return ("tr", 1, 15, "Türkiye Remote")
        if "istanbul" in sehir and wp == "hybrid":
            return ("tr", 2, 12, "İstanbul Hibrit")
        if "istanbul" in sehir:
            return ("tr", 3, 10, "İstanbul")
        return (None, "Türkiye'de İstanbul dışı onsite: " + (j.get("city") or "?"))
    if u in ("DE", "NL", "UK"):
        b = u.lower()
        sehirli = bool(j.get("city"))
        if b == "de":
            if "berlin" in kucult(j.get("city")):
                return ("de", 1, 15, "DE")
            return ("de", 2 if sehirli else 3, 10 if sehirli else 9, "DE")
        return (b, 1 if sehirli else 2, 12 if sehirli else 9, u)
    # Worldwide / Europe / EMEA remote: 23 Eyl'de kullanıcı kararıyla TAMAMEN
    # çıkarıldı. Türkiye kovası yalnızca konumu Türkiye olan ilanları alır.
    if j.get("regions"):
        return (None, "dünya geneli remote (Türkiye ilanı değil)")
    if j.get("country"):
        return (None, "hedef dışı ülke: " + j["country"])
    return (None, j.get("location_reason") or "konum belirsiz")


def fit_score(j, konum_puani, bugun):
    s, neden = 0, []
    r = rol(j["title"])
    rp = 30 if r == "primary" else 18
    s += rp; neden.append(f"rol {r} +{rp}")
    s += konum_puani; neden.append(f"konum +{konum_puani}")
    wp = {"hybrid": 5, "remote": 4, "onsite": 2}.get(j.get("workplace_type"), 0)
    s += wp
    bp = min(len(j["matched_skills"]), 6) * 5
    s += bp; neden.append(f"beceri {len(j['matched_skills'])}×5 +{bp}")
    kp = {"mid": 5, "senior": 5, "junior": -15, "lead": -6, "manager": -8}.get(j["seniority"], 0)
    if j.get("people_mgmt"):
        kp -= 10
    s += kp; neden.append(f"kıdem {j['seniority']} {kp:+d}")
    d = age_days(j.get("publication_date"), bugun)
    tp = 0 if d is None else (10 if d <= 1 else 7 if d <= 3 else 4 if d <= 7 else 2 if d <= 14 else 0)
    s += tp; neden.append(f"tazelik +{tp}")
    lp = 5 if j["language"] in ("en",) or (j["language"] == "tr" and j.get("country") == "TR") else 0
    s += lp
    return s, "; ".join(neden), d


def degerlendir(j, bugun):
    """Kesin filtre → kova → puan. Dönüş: (ilan|None, elenme_sebebi)."""
    t = j["title"]
    if TITLE_EXCLUDE.search(t):
        return None, "rol dışı (başlık)"
    r = rol(t)
    if not r:
        return None, "rol dışı (hedef rol yok)"
    if j["language"] == "de":
        return None, "Almanca ilan"
    if j["de_req"]:
        return None, "ileri seviye Almanca şartı"
    if j["language"] == "tr" and j.get("country") not in ("TR",):
        return None, "Türkçe ilan ama Türkiye dışı"
    d = age_days(j.get("publication_date"), bugun)
    if d is not None and d > MAX_POST_AGE:
        return None, "yayın tarihi eski"
    k = kova(j)
    if k[0] is None:
        return None, k[1]
    b, kademe, kpuan, etiket = k
    # ML / Data Science "uygun olduğunda": kullanıcının araçları ilanda geçmeli.
    # Türkiye kovasında eşik 1 — o kovanın arzı çok dar (23 Eyl ölçümü).
    if r == "secondary" and len(j["matched_skills"]) < (1 if b == "tr" else 2):
        return None, "ML/DS rolü, beceri örtüşmesi zayıf"
    fit, neden, d = fit_score(j, kpuan, bugun)
    if fit < MIN_FIT:
        return None, "düşük uygunluk"
    j = dict(j)
    j.update({"bucket": b, "tier": kademe, "label": etiket, "fit_score": fit, "fit_reason": neden,
              "days": d, "market": "turkey" if b == "tr" else "international"})
    return j, ""


# ================================================================ seçim
def gecmis_tasi(prev, bugun_s):
    """Eski `seen` (URL listesi) -> history kaydı.

    23 Eyl: bunlar önce `expired` yazılıyordu, yani eski sistemde bir kez
    gösterilmiş her ilan SONSUZA DEK eleniyordu. Türkiye kovasına uyan tek tük
    ilan da tam bunların arasından çıktığı için kova günlerce boş kaldı. Artık
    göç günü `first_seen` sayılıyor: normal 14 günlük pencere işliyor,
    başvurulan/gizlenen ilanları zaten panel süzüyor."""
    h = dict(prev.get("history") or {})
    for u in prev.get("seen") or []:
        h.setdefault("url:" + u, {"first_seen": bugun_s, "last_seen": bugun_s, "status": "listed", "legacy": True})
    for k, v in h.items():
        if v.get("legacy") and v.get("status") == "expired" and not v.get("first_seen"):
            v["first_seen"] = bugun_s
            v["status"] = "listed"
    return h


def sec(adaylar, prev, bugun=None, log=print):
    bugun = bugun or dt.datetime.now(IST).date()
    bugun_s = bugun.isoformat()
    history = gecmis_tasi(prev or {}, bugun_s)

    # 1) değerlendir, kaynaklar arası tekrarı birleştir
    elenen, uygun = {}, {}
    for j in adaylar:
        ok, neden = degerlendir(j, bugun)
        if not ok:
            elenen[neden.split(":")[0].split(" — ")[0]] = elenen.get(neden.split(":")[0].split(" — ")[0], 0) + 1
            continue
        onceki = uygun.get(ok["id"])
        if onceki:
            # aynı ilan iki kaynakta: daha yüksek puanlı kalır, diğer kaynak not edilir
            kalan, giden = (ok, onceki) if ok["fit_score"] > onceki["fit_score"] else (onceki, ok)
            kalan = dict(kalan); kalan["also_on"] = sorted(set(kalan.get("also_on", []) + [giden["source"]]))
            uygun[ok["id"]] = kalan
            elenen["tekrar (farklı kaynak)"] = elenen.get("tekrar (farklı kaynak)", 0) + 1
        else:
            uygun[ok["id"]] = ok

    # 2) geçmişle karşılaştır: süresi dolan / eski listede olanlar çıkar
    aktif = []
    for j in uygun.values():
        h = history.get(j["id"]) or history.get("url:" + j["source_url"])
        if h:
            h["last_seen"] = bugun_s
            if h.get("status") == "expired":
                elenen["süresi doldu (daha önce gösterildi)"] = elenen.get("süresi doldu (daha önce gösterildi)", 0) + 1
                continue
            ilk = dt.date.fromisoformat(h["first_seen"]) if h.get("first_seen") else bugun
            if (bugun - ilk).days >= MAX_LIST_DAYS:
                h["status"] = "expired"
                elenen["süresi doldu (14 gün)"] = elenen.get("süresi doldu (14 gün)", 0) + 1
                continue
        j["is_new"] = not h or h.get("first_seen") in (None, bugun_s)
        j["first_seen"] = (h or {}).get("first_seen") or bugun_s
        aktif.append(j)

    # 3) kovalara ayır ve sırala. Sıra: yeni > önceki günlerden kalan; TR'de
    #    bölge remote (kademe 3) en sonda yedek.
    kovalar = {b: [] for b in BUCKET_ORDER}
    for j in aktif:
        kovalar[j["bucket"]].append(j)
    for b, liste in kovalar.items():
        # TR dahil hepsi: yeni > önceki günlerden kalan, sonra kademe, sonra puan.
        # TR kademeleri remote önceliğini taşıyor (bkz. kova()).
        liste.sort(key=lambda j: (not j["is_new"], j["tier"], -j["fit_score"]))

    items, reserve, stats = [], [], {"candidates": {}, "selected": {}, "missing": {}, "eliminated": elenen}
    for b in BUCKET_ORDER:
        liste = kovalar[b]
        q = QUOTA[b]
        secilen = liste[:q]
        yedek = liste[q:q + RESERVE[b]]
        for rank, j in enumerate(secilen + yedek):
            j["rank"] = rank
            j["reserve"] = rank >= q
        items += secilen
        reserve += yedek
        if b == "tr":
            # kademeler: 1 TR remote · 2 İstanbul hibrit · 3 İstanbul onsite
            stats["candidates"]["tr"] = {"tr_remote": sum(j["tier"] == 1 for j in liste),
                                         "istanbul_hibrit": sum(j["tier"] == 2 for j in liste),
                                         "istanbul_onsite": sum(j["tier"] == 3 for j in liste)}
        else:
            stats["candidates"][b] = len(liste)
        stats["selected"][b] = len(secilen)
        if len(secilen) < q:
            stats["missing"][b] = {"eksik": q - len(secilen),
                                   "sebep": "uygun aday yok" if not liste else f"yalnızca {len(liste)} uygun aday"}

    # 4) geçmişi güncelle (listeye giren her ilan: seçilen + yedek)
    for j in items + reserve:
        h = history.setdefault(j["id"], {"first_seen": bugun_s, "status": "listed"})
        h["last_seen"] = bugun_s
    sinir = (bugun - dt.timedelta(days=HISTORY_KEEP)).isoformat()
    history = {k: v for k, v in history.items() if (v.get("last_seen") or bugun_s) >= sinir}

    # 5) log — Actions logu herkese açık; yalnızca sayı ve ilan bilgisi, kişisel veri yok
    c = stats["candidates"]
    log(f"Turkey candidates found: {sum(c['tr'].values())} "
        f"(TR remote {c['tr']['tr_remote']}, İstanbul hibrit {c['tr']['istanbul_hibrit']}, "
        f"İstanbul onsite {c['tr']['istanbul_onsite']})")
    log(f"Germany candidates found: {c['de']}")
    log(f"Netherlands candidates found: {c['nl']}")
    log(f"UK candidates found: {c['uk']}")
    log("Final selected count by bucket: " + ", ".join(f"{BUCKET_AD[b]} {stats['selected'][b]}/{QUOTA[b]}" for b in BUCKET_ORDER))
    if stats["missing"]:
        for b, m in stats["missing"].items():
            log(f"Missing quota reason: {BUCKET_AD[b]} {m['eksik']} eksik — {m['sebep']}")
    else:
        log("Missing quota reason: yok, bütün kotalar doldu")
    log("Elenenler: " + ", ".join(f"{k} {v}" for k, v in sorted(elenen.items(), key=lambda x: -x[1])))
    return items, reserve, stats, history


def cikti(j, simdi):
    """jobs.json'daki ilan kaydı. Eski alanlar (url, skills, score, posted,
    remote, german, summary) geriye uyumluluk için duruyor."""
    return {
        "id": j["id"],
        "title": j["title"],
        "company": j["company"],
        "location": j["location"],
        "country": j.get("country") or j["label"],     # TR / DE / NL / UK ya da "EMEA Remote" gibi bölge
        "market": j["market"],
        "bucket": j["bucket"],
        "label": j["label"],
        "tier": j["tier"],
        "rank": j["rank"],
        "reserve": j["reserve"],
        "is_new": j["is_new"],
        "first_seen": j["first_seen"],
        "workplace_type": j["workplace_type"],
        "source": j["source"],
        "also_on": j.get("also_on", []),
        "source_url": j["source_url"],
        "publication_date": j["publication_date"],
        "fit_score": j["fit_score"],
        "fit_reason": j["fit_reason"],
        "matched_skills": j["matched_skills"],
        "location_reason": j["location_reason"],
        "seniority": j["seniority"],
        "focus": j["focus"],
        "focus_scores": j["focus_scores"],
        "language": j["language"],
        "generated_at": simdi,
        "summary": j["body"][:260],
        "keywords": keywords_of(j["body"]),
        # --- eski panel alanları (v1) ---
        "url": j["source_url"],
        "skills": [s.lower() for s in j["matched_skills"]],
        "score": j["fit_score"],
        "posted": j["publication_date"],
        "days": j["days"],
        "remote": j["workplace_type"] == "remote",
        "german": False,
    }


def build():
    prev = {}
    if os.path.exists(PREV):
        try:
            with open(PREV, encoding="utf-8") as f:
                prev = json.load(f)
        except (ValueError, OSError):
            prev = {}
    print("Arbeitnow...")
    jobs = from_arbeitnow()
    print(f"  {len(jobs)} ilan okundu")
    for ad, fn in (("Jooble (TR)", from_jooble), ("Remotive", from_remotive),
                   ("Himalayas", from_himalayas), ("Remote OK", from_remoteok),
                   ("WeWorkRemotely", from_wwr)):
        print(ad + "...")
        yeni = fn()
        print(f"  {len(yeni)} ilan okundu")
        jobs += yeni
    items, reserve, stats, history = sec(jobs, prev)
    simdi = dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    return {
        "version": 2,
        "updated": simdi,
        "ok": len(items) > 0,
        "count": len(items),
        "pool": len(items) + len(reserve),
        "quota": QUOTA,
        "items": [cikti(j, simdi) for j in items],
        "reserve": [cikti(j, simdi) for j in reserve],
        "stats": stats,
        "history": history,
        "note": "Kaynak: Arbeitnow + Remotive. Basvuruyu kullanici kendisi yapar.",
    }


if __name__ == "__main__":
    data = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"\n{OUT}: {data['count']} ilan seçildi, {len(data['reserve'])} yedek")
    for j in data["items"] + data["reserve"]:
        print(f"  [{j['bucket']}{'*' if j['reserve'] else ' '}] {j['fit_score']:>3}p  {j['title'][:44]:44} | "
              f"{j['company'][:18]:18} | {j['label']:16} | {j['focus']:8} | {j['source']} | {j['fit_reason']}")
