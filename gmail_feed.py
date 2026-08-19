# -*- coding: utf-8 -*-
"""
gmail_feed.py — Gmail'deki son günlerin okunmamış maillerinden gmail.json üretir.
MAIL GÖNDERMEZ, hiçbir maili değiştirmez/okundu işaretlemez (salt-okunur scope).

Sayım, Gmail'de kullanıcının fiilen baktığı PRIMARY sekmesiyle birebir aynı olsun diye
category:primary + in:inbox ile sınırlandırılmıştır. (Aksi halde Promotions/Updates
sekmelerindeki bülten ve LinkedIn iş ilanı bildirimleri de sayılıyor ve panel, Gmail'de
"hiç okunmamışım yok" görünürken 49 gibi kafa karıştırıcı bir sayı gösteriyordu.)
Eleme sırası:
  1) is:unread + in:inbox + category:primary + son WINDOW_DAYS gün ile pencere daraltılıyor
  2) Toplu/otomatik postalar (bülten, iş ilanı bildirimi, pazarlama vb.) List-Unsubscribe /
     List-Unsubscribe-Post / Precedence: bulk header'larına bakılarak eleniyor
  3) Header'da bu bilgi yoksa, bilinen toplu-mail gönderen domain/local-part
     kalıplarına göre ikinci bir eleme yapılıyor
Kalan mailler "önemli/kişisel, muhtemelen cevap bekleyen" olarak kabul edilip
tarihe göre sıralanıp panele en yeni 8 tanesi veriliyor.

Kimlik bilgileri ortam değişkenlerinden okunur (GitHub Actions secrets):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN

Çalıştırma: python gmail_feed.py
"""
import json
import os
import re
import datetime as dt
import urllib.parse

import requests

IST = dt.timezone(dt.timedelta(hours=3))
WINDOW_DAYS = 3       # hafta sonu boşluğunu (Cuma->Pazartesi) da kapsasın diye 3 gün
MAX_ITEMS = 8         # panelde gösterilecek en fazla mail sayısı
MAX_FETCH = 100        # header çekilecek üst sınır (API kotasını korumak için)

TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://www.googleapis.com/gmail/v1/users/me"

# Header'da List-Unsubscribe yoksa ikinci güvenlik ağı: bilinen toplu-mail kalıpları
BULK_LOCALPART_RE = re.compile(
    r"(noreply|no-reply|donotreply|do-not-reply|notification|bildirim|bulten|"
    r"kampanya|marketing|mailer|bounce|jobalerts|jobs-noreply|e-bulten|newsletter)",
    re.IGNORECASE,
)
BULK_DOMAIN_RE = re.compile(
    r"(linkedin\.com|indeed\.com|glassdoor\.com|greenhouse\.io|myworkday\.com|"
    r"successfactors\.com|coursera\.org|trendyol\.com|iyzico\.com|flypgs\.com|"
    r"turkishairlines\.com|garantibbva\.com\.tr|chess\.com|bolt\.eu|2k\.com|"
    r"zalando\.|mango\.com|eventbrite\.com|pinterest\.com)",
    re.IGNORECASE,
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


def list_unread_ids(headers, window_days):
    q = f"is:unread in:inbox category:primary newer_than:{window_days}d -in:chats"
    ids, page_token = [], None
    while True:
        params = {"q": q, "maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(f"{API_BASE}/messages", headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        ids.extend(m["id"] for m in data.get("messages", []))
        page_token = data.get("nextPageToken")
        if not page_token or len(ids) >= MAX_FETCH:
            break
    return ids[:MAX_FETCH]


def fetch_meta(headers, msg_id):
    params = {
        "format": "metadata",
        "metadataHeaders": ["List-Unsubscribe", "List-Unsubscribe-Post",
                             "Precedence", "From", "Subject", "Date"],
    }
    r = requests.get(f"{API_BASE}/messages/{msg_id}", headers=headers, params=params, timeout=20)
    r.raise_for_status()
    md = r.json()
    hdrs = {h["name"]: h["value"] for h in md.get("payload", {}).get("headers", [])}
    return hdrs, int(md.get("internalDate", "0"))


def is_bulk(hdrs):
    if "List-Unsubscribe" in hdrs or "List-Unsubscribe-Post" in hdrs:
        return True
    if hdrs.get("Precedence", "").lower() in ("bulk", "list", "junk"):
        return True
    sender = hdrs.get("From", "")
    if BULK_LOCALPART_RE.search(sender) or BULK_DOMAIN_RE.search(sender):
        return True
    return False


def parse_from(raw):
    # "Ad Soyad <mail@ornek.com>" ya da "mail@ornek.com"
    m = re.match(r'^\s*"?([^"<]*)"?\s*<([^>]+)>\s*$', raw or "")
    if m:
        name = m.group(1).strip() or m.group(2)
        return name, m.group(2)
    return raw, raw


def build():
    try:
        token = get_access_token()
    except Exception as e:
        return {
            "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
            "ok": False,
            "error": f"auth_failed: {e}",
            "total_unread": 0,
            "important_unread": 0,
            "items": [],
        }

    headers = {"Authorization": f"Bearer {token}"}

    try:
        ids = list_unread_ids(headers, WINDOW_DAYS)
    except Exception as e:
        return {
            "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
            "ok": False,
            "error": f"list_failed: {e}",
            "total_unread": 0,
            "important_unread": 0,
            "items": [],
        }

    important = []
    for mid in ids:
        try:
            hdrs, internal_date = fetch_meta(headers, mid)
        except Exception:
            continue
        if is_bulk(hdrs):
            continue
        name, email = parse_from(hdrs.get("From", ""))
        important.append({
            "from": name,
            "email": email,
            "subject": hdrs.get("Subject", "(konu yok)"),
            "date": hdrs.get("Date", ""),
            "ts": internal_date,
        })

    important.sort(key=lambda x: x["ts"], reverse=True)
    for it in important:
        del it["ts"]

    return {
        "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "ok": True,
        "window_days": WINDOW_DAYS,
        "total_unread": len(ids),
        "important_unread": len(important),
        "items": important[:MAX_ITEMS],
    }


if __name__ == "__main__":
    d = build()
    with open("gmail.json", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    if d.get("ok"):
        print(f"gmail.json: {d['total_unread']} okunmamış (son {d['window_days']} gün), "
              f"{d['important_unread']} önemli/kişisel")
    else:
        print(f"gmail.json: HATA - {d.get('error')}")
