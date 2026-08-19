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

Kimlik bilgileri ortam değişkenlerinden okunur (GitHub Actions secrets):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
(refresh token hem gmail.readonly hem spreadsheets scope'una sahip olmalı)

Çalıştırma: python check_rejections.py
"""
import base64
import datetime as dt
import os
import re

import requests

SHEET_ID = "1dUImQztxAZlKERjtkVAqQ92EgrvwzO7iUfAr4lz6AsY"
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
]

# Eşleşen ifade bu kalıplardan biriyle AYNI CÜMLEDE geçiyorsa muhtemelen
# koşullu/varsayımsal bir cümledir (ör. "if you are not selected...") ve
# gerçek bir ret bildirimi SAYILMAZ.
CONDITIONAL_CUES = [
    "if you", "if not", "if we", "in case", "should you", "should we",
    "unless", "in the event", "eğer", "aksi takdirde",
]

SENTENCE_SPLIT_RE = re.compile(r"[.!?\n]+")


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


def is_genuine_rejection(body_text):
    """Ret ifadesi geçen cümleyi bulur; koşullu/varsayımsal cümleleri eler."""
    sentences = SENTENCE_SPLIT_RE.split(body_text.lower())
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
        if "ret" in durum.lower():
            continue  # zaten ret olarak işaretli

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


if __name__ == "__main__":
    main()
