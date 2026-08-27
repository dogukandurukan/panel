# -*- coding: utf-8 -*-
"""
check_rejections.py — Gmail'de iş başvurusu RET mailini otomatik algılar ve
"Başvuru Takip" Google Sheet'indeki ilgili satırın "Durum" hücresini "Ret"
olarak günceller.

Hiçbir mail göndermez / silmez / okundu işaretlemez. Sadece:
  1) Sheet'ten şirket listesini ve mevcut durumlarını okur (Sheets API, read)
  2) Zaten "Ret" olmayan her şirket için Gmail'de o şirket adını VE bilinen
     ret-mail kalıplarını (TR/EN) birlikte içeren mail arar (Gmail search,
     geniş/kaba filtre)
  3) Adayları tek tek mail gövdesinden doğrular: eşleşen ifade "eğer/if/in
     case/should/unless" gibi KOŞULLU bir cümle içindeyse (ör. "Thank you for
     your application... If you are not selected for this position, keep an
     eye on our jobs page" gibi ret olmayan otomatik onay mailleri) o aday
     ELENIR — yanlış pozitifi önlemek için (2. katman doğrulama)
  4) Gerçek bir ret ifadesi bulunursa ilgili satırın Durum hücresini "Ret"
     yazar (Sheets API, write)
  5) İKİNCİ GEÇİŞ: Sheet'te hiç olmayan başvuruların reddi de görünsün diye
     gelen kutusunu şirket adı olmadan, yalnızca GÜÇLÜ ret kalıplarıyla
     tarar; göndereni şirkete çevirir. Sonuç repoya YAZILMAZ (depo herkese
     açık) — senkronun gizli gist'indeki panel-data.json / d:retler
     anahtarına yazılır, panel oradan okur.

Kimlik bilgileri ortam değişkenlerinden okunur (GitHub Actions secrets):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
  PANEL_GIST_TOKEN (2. geçişin sonucunu gist'e yazmak için; yoksa yalnızca
  log'a basılır, betik çökmez)
(refresh token hem gmail.readonly hem spreadsheets scope'una sahip olmalı)

Çalıştırma: python check_rejections.py
"""
import base64
import datetime as dt
import json
import os
import re
import time

import requests

import gist_io

SHEET_ID = "1Vw4pZMhnZqDWDQ8UqLvdX_3QadJ1aSZPna4aV2oNqkk"
SHEET_NAME = "Untitled"
DATA_RANGE = f"{SHEET_NAME}!A2:G1000"

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://www.googleapis.com/gmail/v1/users/me"
SHEETS_API = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"

CANDIDATES_PER_COMPANY = 5

# Şirket adıyla BİRLİKTE aranacak, ret mailine özgü kalıplar (TR + EN).
# "not selected for this position" gibi kabul mailinde koşullu ("If you are
# not selected...") geçebilen zayıf/genel ifadeler kasıtlı olarak dışarıda
# bırakıldı; bkz. STAGE 2 (koşullu cümle filtresi) ek güvenlik katmanı.
REJECTION_TERMS = [
    # Türkçe
    "maalesef",
    "başka adaylarla",
    "başka bir adayla",
    "olumsuz sonuçlanmıştır",
    "olumsuz olarak sonuçlanmıştır",
    "olumlu sonuçlanmamıştır",
    "değerlendirmeye almayacağ",
    "süreci olumsuz",
    "reddedilmiştir",
    "üzülerek bildiririz",
    "işe alım sürecini sonlandır",
    # İngilizce
    "unfortunately",
    "move forward with other candidates",
    "moving forward with other candidates",
    "will not be moving forward",
    "not moving forward with your application",
    "unable to offer you",
    "regret to inform you",
    "pursue other candidates",
    "position has been filled",
    "decided not to proceed with your application",
    "decided not to move forward",
    # Elle yazılmış retlerde çıkan, listede olmayan kalıplar
    "not be taking your application further",
    "not be proceeding with your application",
    "will not be proceeding",
    "not be progressing your application",
    "decided to proceed with other candidates",
    "proceed with other applicants",
    "move forward with other applicants",
    "not selected to move forward",
    "not be moving ahead",
    "decided to move ahead with other",
    "we have chosen another candidate",
    "gone with another candidate",
    "no longer under consideration",
    "your application was unsuccessful",
    "were not successful on this occasion",
    "başvurunuz olumsuz",
    "başvurunuz maalesef",
    "sürecinize devam etmeme kararı",
    "devam etmeme kararı aldık",
    "başka bir aday ile",
]

# ŞİRKET LİSTESİ OLMADAN tarama için: yalnızca rette geçen, güçlü kalıplar.
# "unfortunately"/"maalesef" gibi tek başına her yerde geçen sözcükler burada
# YOK — şirket adı çapası olmadan yanlış pozitif üretirlerdi.
GUCLU_TERIMLER = [
    "regret to inform",
    "not moving forward with your application",
    "will not be moving forward",
    "decided not to proceed with your application",
    "decided not to move forward",
    "move forward with other candidates",
    "moving forward with other candidates",
    "proceed with other applicants",
    "move forward with other applicants",
    "not be taking your application further",
    "not be proceeding with your application",
    "not selected to move forward",
    "your application was unsuccessful",
    "were not successful on this occasion",
    "no longer under consideration",
    "unable to offer you",
    "position has been filled",
    "olumsuz sonuçlanmıştır",
    "olumlu sonuçlanmamıştır",
    "başvurunuz olumsuz",
    "başka adaylarla",
    "başka bir adayla",
    "üzülerek bildiririz",
    "devam etmeme kararı",
]

# Ret olduğu kadar İŞ BAŞVURUSU olduğu da doğrulanmalı: bir mağaza da
# "we regret to inform" yazabiliyor.
IS_BAGLAMI = ("application", "position", "role", "candidate", "interview",
              "recruit", "hiring", "vacancy", "cv", "resume",
              "başvuru", "pozisyon", "aday", "mülakat", "işe alım", "özgeçmiş")

# Şirket adı bu alan adlarından çıkarılamaz — hepsi işe alım yazılımı.
ATS_ALANLARI = {
    "greenhouse.io", "us.greenhouse.io", "eu.greenhouse.io", "lever.co",
    "hire.lever.co", "myworkday.com", "workday.com", "workdaysuite.com",
    "smartrecruiters.com", "personio.de", "personio.com", "successfactors.com",
    "icims.com", "ashbyhq.com", "recruitee.com", "teamtailor.com", "jobvite.com",
    "bamboohr.com", "join.com", "softgarden.io", "workable.com", "breezy.hr",
    "hibob.com", "pinpointhq.com", "gmail.com", "googlemail.com", "outlook.com",
    "hotmail.com", "linkedin.com", "indeed.com", "email.indeed.com",
}
# Gönderen adı bunlardan ibaretse şirket adı sayılmaz
JENERIK_AD = ("no-reply", "noreply", "no reply", "recruiting", "recruitment",
              "talent", "talent acquisition", "hr", "human resources", "careers",
              "career", "jobs", "hiring", "people team", "notification",
              "team", "info", "kariyer", "ik", "insan kaynakları")

# Eşleşen ifade bu kalıplardan biriyle AYNI CÜMLEDE geçiyorsa muhtemelen
# koşullu/varsayımsal bir cümledir (ör. "if you are not selected...") ve
# gerçek bir ret bildirimi SAYILMAZ.
CONDITIONAL_CUES = [
    "if you", "if not", "if we", "in case", "should you", "should we",
    "unless", "in the event", "eğer", "aksi takdirde",
]

SENTENCE_SPLIT_RE = re.compile(r"[.!?\n]+")

# Durum sütununda "zaten reddedilmiş" sayılan yazımlar. Panel ile aynı mantık:
# "Reddedildi" kelimesi "ret" harf dizisini içermediği için ayrı kalıp şart.
ALREADY_REJECTED_RE = re.compile(
    r"(^|\s)ret(\b|$)|reddedil|olumsuz|rejected|declined", re.IGNORECASE
)


def get_access_token():
    client_id = os.environ["GMAIL_CLIENT_ID"]
    client_secret = os.environ["GMAIL_CLIENT_SECRET"]
    refresh_token = os.environ["GMAIL_REFRESH_TOKEN"]
    r = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def read_sheet_rows(headers):
    r = requests.get(f"{SHEETS_API}/values/{DATA_RANGE}", headers=headers, timeout=20)
    r.raise_for_status()
    return r.json().get("values", [])


def window_days_for(basvuru_tarihi):
    """Başvuru tarihinden bugüne kaç gün geçmiş + tampon süre; makul sınırlar içinde."""
    try:
        d = dt.datetime.strptime(basvuru_tarihi.strip(), "%Y-%m-%d").date()
        delta = (dt.date.today() - d).days + 7
        return max(14, min(delta, 180))
    except Exception:
        return 60


def build_query(company, days):
    keyword_group = " OR ".join(
        f'"{t}"' if " " in t else t for t in REJECTION_TERMS
    )
    return f'"{company}" ({keyword_group}) in:inbox -in:chats newer_than:{days}d'


def search_candidates(headers, company, days):
    q = build_query(company, days)
    r = requests.get(f"{GMAIL_API}/messages", headers=headers,
                      params={"q": q, "maxResults": CANDIDATES_PER_COMPANY}, timeout=20)
    r.raise_for_status()
    return [m["id"] for m in r.json().get("messages", [])]


def _extract_body(payload):
    if payload.get("body", {}).get("data"):
        try:
            return base64.urlsafe_b64decode(payload["body"]["data"] + "===").decode("utf-8", "ignore")
        except Exception:
            return ""
    for part in payload.get("parts", []) or []:
        b = _extract_body(part)
        if b:
            return b
    return ""


def fetch_message(headers, msg_id):
    r = requests.get(f"{GMAIL_API}/messages/{msg_id}", headers=headers,
                      params={"format": "full"}, timeout=20)
    r.raise_for_status()
    md = r.json()
    hdrs = {h["name"]: h["value"] for h in md.get("payload", {}).get("headers", [])}
    raw = _extract_body(md.get("payload", {}))
    text = re.sub(r"<[^>]+>", " ", raw)
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    subject = hdrs.get("Subject", "(konu yok)")
    sender = hdrs.get("From", "")
    return subject, sender, text


# "won't be taking your application further" kalıp listesindeki
# "not be taking..." ile eşleşmiyordu: elle yazılmış retler kısaltma kullanıyor.
KISALTMA = [
    ("won't", "will not"), ("wouldn't", "would not"), ("can't", "can not"),
    ("cannot", "can not"), ("don't", "do not"), ("doesn't", "does not"),
    ("didn't", "did not"), ("haven't", "have not"), ("hasn't", "has not"),
    ("isn't", "is not"), ("aren't", "are not"), ("weren't", "were not"),
    ("we're", "we are"), ("we've", "we have"), ("we'll", "we will"),
    ("you're", "you are"), ("it's", "it is"),
]


def _ac(metin):
    d = (metin or "").lower().replace("\u2019", "'")
    for k, v in KISALTMA:
        d = d.replace(k, v)
    return d


def is_genuine_rejection(body_text):
    """Ret ifadesi geçen cümleyi bulur; koşullu/varsayımsal cümleleri eler."""
    sentences = SENTENCE_SPLIT_RE.split(_ac(body_text))
    for sentence in sentences:
        for term in REJECTION_TERMS:
            if term.lower() in sentence:
                if any(cue in sentence for cue in CONDITIONAL_CUES):
                    continue  # koşullu cümle -> sayma, başka terim/cümleye bak
                return True, term
    return False, None


def mark_as_ret(headers, row_number):
    rng = f"{SHEET_NAME}!E{row_number}"
    r = requests.put(
        f"{SHEETS_API}/values/{rng}",
        headers=headers,
        params={"valueInputOption": "RAW"},
        json={"values": [["Ret"]]},
        timeout=20,
    )
    r.raise_for_status()


# ---------------------------------------------------------------------------
# ŞİRKET LİSTESİ OLMADAN TARAMA
# Sheet'e girilmemiş başvurunun reddi hiç görülmüyordu (Enpal böyle kaçtı):
# eski akış YALNIZCA Sheet'teki şirket adlarını Gmail'de arıyor. Bu geçiş
# gelen kutusunu ret kalıbıyla tarayıp göndereni şirkete çeviriyor.
#
# NEREYE YAZILIYOR: bu depo herkese açık (CLAUDE.md 1. kural), başvuru verisi
# kişiseldir. Sonuç repoya değil, senkronun kullandığı GİZLİ gist'e
# (panel-data.json / d:retler) yazılıyor; panel zaten oradan okuyor.
# ---------------------------------------------------------------------------
RET_ANAHTAR = "d:retler"
SERBEST_GUN = 60
SERBEST_MAX = 25


def _ad_temizle(ham):
    """From başlığındaki görünen ad -> şirket adı. Çıkarılamazsa None."""
    ad = re.sub(r"<[^>]*>", "", ham or "").strip().strip('"').strip()
    ad = re.sub(r"\s+", " ", ad)
    if not ad or "@" in ad:
        return None
    # "Enpal Recruiting Team" -> "Enpal"
    for jen in ("recruiting team", "recruitment team", "talent acquisition",
                "talent team", "hiring team", "people team", "careers",
                "recruiting", "recruitment", "talent", "hiring", "hr", "jobs",
                "kariyer", "insan kaynakları", "ik ekibi"):
        ad = re.sub(r"(?i)\b" + re.escape(jen) + r"\b", " ", ad)
    ad = re.sub(r"(?i)\b(team|ekibi|ekip|no[- ]?reply|via .*)$", " ", ad)
    ad = re.sub(r"[|·•]+", " ", ad)
    ad = re.sub(r"\s+", " ", ad).strip(" -–—,.")
    if len(ad) < 2 or ad.lower() in JENERIK_AD:
        return None
    return ad


SIRKET_EKI = ("gmbh", "inc", "inc.", "ltd", "ltd.", "ag", "b.v.", "bv", "se",
              "a.ş.", "as", "llc", "co", "corp", "group", "labs", "tech")


def _kisi_adi_mi(ad):
    """İki kelimelik, şirket eki olmayan Büyük Harfli ad -> muhtemelen insan.
    Retler çoğu zaman bir insandan geliyor; kartta "Julia Braun" değil şirket
    adı görünmeli."""
    p = ad.split()
    if len(p) != 2 or len(ad) > 30:
        return False
    if any(x.lower().strip(".,") in SIRKET_EKI for x in p):
        return False
    return all(x[:1].isupper() and x[1:].islower() for x in p)


def sirket_cikar(from_header):
    """Görünen ad; kişi adıysa ya da yoksa alan adı. ATS alanları sayılmaz."""
    ad = _ad_temizle(from_header)
    m = re.search(r"@([A-Za-z0-9.\-]+)", from_header or "")
    if ad and not (_kisi_adi_mi(ad) and m):
        return ad
    if not m:
        return ad
    alan = m.group(1).lower().strip(".")
    if alan in ATS_ALANLARI:
        return ad          # ATS'ten geliyorsa elde kalan tek şey görünen ad
    kok = alan.split(".")
    # careers.enpal.de -> enpal ; mail.hellofresh.com -> hellofresh
    parca = [p for p in kok if p not in
             ("mail", "email", "e", "careers", "career", "jobs", "recruiting",
              "notifications", "no-reply", "reply", "smtp", "mailer", "www")]
    if len(parca) >= 2:
        return parca[-2].capitalize()
    return (parca[0] if parca else kok[0]).capitalize()


def is_basvurusu_mu(body_text):
    d = body_text.lower()
    return any(k in d for k in IS_BAGLAMI)


def serbest_tarama(headers, sheet_sirketleri):
    """Gelen kutusunda güçlü ret kalıbı arar; Sheet'te olmayanları döndürür."""
    grup = " OR ".join(f'"{t}"' for t in GUCLU_TERIMLER)
    q = f'({grup}) in:inbox -in:chats newer_than:{SERBEST_GUN}d'
    try:
        r = requests.get(f"{GMAIL_API}/messages", headers=headers,
                         params={"q": q, "maxResults": SERBEST_MAX}, timeout=25)
        r.raise_for_status()
        ids = [m["id"] for m in r.json().get("messages", [])]
    except Exception as e:
        print(f"serbest tarama: arama hatası: {e}")
        return []

    bilinen = [s.lower() for s in sheet_sirketleri if s]
    bulunan, atlanan_sheet, atlanan_kosullu, atlanan_isdisi = [], 0, 0, 0
    for mid in ids:
        try:
            subject, sender, body = fetch_message(headers, mid)
        except Exception:
            continue
        gercek, terim = is_genuine_rejection(body)
        if gercek and not any(t in _ac(body) for t in GUCLU_TERIMLER):
            # 1. geçişin zayıf kalıpları (yalnız "unfortunately" gibi) şirket
            # çapası olmadan yeterli değil.
            gercek = False
        if not gercek:
            atlanan_kosullu += 1
            continue
        if not is_basvurusu_mu(body + " " + subject):
            atlanan_isdisi += 1
            continue
        sirket = sirket_cikar(sender)
        # Sheet'te varsa 1. geçiş zaten ilgileniyor
        ad_k = (sirket or "").lower()
        if ad_k and any(ad_k in b or b in ad_k for b in bilinen):
            atlanan_sheet += 1
            continue
        bulunan.append({
            "sirket": sirket or "(gönderen çözülemedi)",
            "konu": subject[:120],
            "kimden": re.sub(r"\s+", " ", sender)[:90],
            "terim": terim,
        })
    print(f"serbest tarama: {len(ids)} aday · {len(bulunan)} yeni ret · "
          f"{atlanan_sheet} Sheet'te var · {atlanan_kosullu} koşullu/ret değil · "
          f"{atlanan_isdisi} iş başvurusu değil")
    return bulunan


def main():
    try:
        token = get_access_token()
    except Exception as e:
        print(f"check_rejections.py: HATA - auth_failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    json_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        rows = read_sheet_rows(json_headers)
    except Exception as e:
        print(f"check_rejections.py: HATA - sheet_read_failed: {e}")
        return

    checked = 0
    updated = 0
    for i, row in enumerate(rows):
        row_number = i + 2  # A2'den başlıyor
        company = (row[0] if len(row) > 0 else "").strip()
        durum = (row[4] if len(row) > 4 else "").strip()
        basvuru_tarihi = row[3] if len(row) > 3 else ""

        if not company:
            continue
        if ALREADY_REJECTED_RE.search(durum):
            continue  # zaten ret olarak işaretli (elle "Reddedildi" yazılmış olabilir)

        checked += 1
        days = window_days_for(basvuru_tarihi)
        try:
            candidate_ids = search_candidates(headers, company, days)
        except Exception as e:
            print(f"  [{company}] arama hatası: {e}")
            continue

        confirmed = None
        for mid in candidate_ids:
            try:
                subject, sender, body = fetch_message(headers, mid)
            except Exception as e:
                print(f"  [{company}] mail okuma hatası: {e}")
                continue
            genuine, term = is_genuine_rejection(body)
            if genuine:
                confirmed = (subject, sender, term)
                break

        if confirmed:
            subject, sender, term = confirmed
            try:
                mark_as_ret(json_headers, row_number)
                updated += 1
                print(f"  [{company}] RET olarak işaretlendi -> '{subject}' ({sender}) [\"{term}\"]")
            except Exception as e:
                print(f"  [{company}] sheet güncelleme hatası: {e}")
        elif candidate_ids:
            print(f"  [{company}] {len(candidate_ids)} aday mail bulundu ama hepsi koşullu/belirsiz görüldü, ret sayılmadı")
        else:
            print(f"  [{company}] ret maili bulunamadı (son {days} gün)")

    print(f"check_rejections.py: {checked} şirket kontrol edildi, {updated} tanesi Ret olarak işaretlendi")

    # 2. geçiş: Sheet'te HİÇ olmayan başvuruların retleri
    sheet_sirketleri = [(row[0] if row else "").strip() for row in rows]
    retler = serbest_tarama(headers, sheet_sirketleri)
    print(gist_io.yaz(RET_ANAHTAR, json.dumps(retler, ensure_ascii=False)))


if __name__ == "__main__":
    main()
