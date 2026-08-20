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
import base64
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

MAX_DRAFTS = 5        # tur başına en fazla kaç maile taslak yazılsın (maliyet sınırı)
MAX_THREAD_MSGS = 6   # konuşmanın son kaç mesajı modele verilsin
MAX_BODY_CHARS = 1500 # mesaj başına gövde sınırı

TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://www.googleapis.com/gmail/v1/users/me"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"
ANTHROPIC_VERSION = "2023-06-01"

# Header'da List-Unsubscribe yoksa ikinci güvenlik ağı: bilinen toplu-mail kalıpları
BULK_LOCALPART_RE = re.compile(
    r"(noreply|no-reply|donotreply|do-not-reply|notification|bildirim|bulten|"
    r"kampanya|marketing|mailer|bounce|jobalerts|jobs-noreply|e-bulten|newsletter)",
    re.IGNORECASE,
)
# Toplu/pazarlama gönderim altyapılarının bıraktığı başlık adları.
# X-Mailer KASITEN yok: Apple Mail gibi gerçek istemciler de onu koyuyor,
# eklenirse kişisel mailler yanlışlıkla elenir.
BULK_HEADER_RE = re.compile(
    r"^(X-)?Feedback-ID$"
    r"|^X-(Mailgun|Mailjet|MJ|SMTPAPI|SG|Sendgrid|Campaign|UTM|CSA|EmailType)"
    r"|^X-(Report-Abuse|Complaints|Marketing|Bulk|Newsletter)"
    r"|^(Auto-Submitted|Bounces-To|Errors-To|X-Auto-Response-Suppress)$",
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
    # metadataHeaders ile SINIRLAMA YOK: toplu-posta parmak izi (Feedback-ID,
    # X-Mailgun-*, X-SMTPAPI ...) hangi başlıkta geleceği önceden bilinmediği için
    # tüm başlıklar çekilip is_bulk() içinde taranıyor.
    params = {"format": "metadata"}
    r = requests.get(f"{API_BASE}/messages/{msg_id}", headers=headers, params=params, timeout=20)
    r.raise_for_status()
    md = r.json()
    hdrs = {h["name"]: h["value"] for h in md.get("payload", {}).get("headers", [])}
    hdrs["__thread_id"] = md.get("threadId", "")   # konuşma geçmişini çekmek için
    return hdrs, int(md.get("internalDate", "0"))


def is_bulk(hdrs):
    if "List-Unsubscribe" in hdrs or "List-Unsubscribe-Post" in hdrs:
        return True
    if hdrs.get("Precedence", "").lower() in ("bulk", "list", "junk"):
        return True
    # Toplu gönderim altyapısı parmak izi. Etsy / Alibaba / Cursor gibi bazı
    # pazarlama gönderenleri List-Unsubscribe KOYMUYOR ve eskiden bu yüzden
    # "kişisel" sanılıyorlardı. Feedback-ID (Google FBL) ve ESP'ye özgü X-
    # başlıkları gerçek bir insanın yazdığı mailde bulunmaz.
    for name in hdrs:
        if BULK_HEADER_RE.match(name):
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


# ---------------------------------------------------------------------------
# Konuşma geçmişi (thread) — cevap taslağı için
# ---------------------------------------------------------------------------

def get_my_address(headers):
    r = requests.get(f"{API_BASE}/profile", headers=headers, timeout=20)
    r.raise_for_status()
    return (r.json().get("emailAddress") or "").lower()


def _decode(data):
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "===").decode("utf-8", "ignore")
    except Exception:
        return ""


def _plain_body(payload):
    """text/plain'i tercih et; yoksa text/html'i sadeleştir."""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        return _decode(payload.get("body", {}).get("data"))
    if mime == "text/html":
        html = _decode(payload.get("body", {}).get("data"))
        return re.sub(r"<[^>]+>", " ", html)
    for part in payload.get("parts", []) or []:
        b = _plain_body(part)
        if b.strip():
            return b
    return _decode(payload.get("body", {}).get("data"))


def strip_quoted(text):
    """Alıntılanan önceki maili ve imzayı at — taslak için gürültü."""
    lines = []
    for ln in (text or "").split("\n"):
        s = ln.strip()
        if s.startswith(">"):
            continue
        if re.match(r"^-{2,}\s*$", s) or s in ("--", "__"):
            break                                   # imza ayracı
        if re.match(r"^On .+ wrote:$", s) or re.match(r"^\d{1,2}\s.+ tarihinde .+ yazdı:$", s):
            break                                   # alıntı başlangıcı
        lines.append(ln)
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return re.sub(r"[ \t]+", " ", out).strip()


def fetch_thread(headers, thread_id, my_address):
    """Konuşmadaki tüm mesajları sırayla döndür (senin yazdıkların dahil)."""
    r = requests.get(f"{API_BASE}/threads/{thread_id}", headers=headers,
                     params={"format": "full"}, timeout=25)
    r.raise_for_status()
    msgs = []
    for m in r.json().get("messages", []):
        h = {x["name"]: x["value"] for x in m.get("payload", {}).get("headers", [])}
        _, sender_mail = parse_from(h.get("From", ""))
        body = strip_quoted(_plain_body(m.get("payload", {})))
        msgs.append({
            "from": h.get("From", ""),
            "date": h.get("Date", ""),
            "is_me": my_address in (sender_mail or "").lower(),
            "body": body[:MAX_BODY_CHARS],
        })
    return msgs


def build_transcript(msgs):
    parts = []
    for m in msgs[-MAX_THREAD_MSGS:]:
        who = "BEN" if m["is_me"] else f"KARŞI TARAF ({m['from']})"
        parts.append(f"--- {who} | {m['date']} ---\n{m['body']}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Cevap taslağı (Claude API)
# GİZLİLİK: bu bölüm çalıştığında mail konuşmasının metni Anthropic API'sine gider.
# ANTHROPIC_API_KEY tanımlı değilse hiçbir istek atılmaz; panel taslaksız çalışır.
# ---------------------------------------------------------------------------

DRAFT_SYSTEM = """Sen, Dogukan'ın Türkçe e-posta asistanısın.
Sana bir e-posta konuşmasının dökümü verilecek. "BEN" etiketli mesajlar Dogukan'ın
kendi yazdıklarıdır; "KARŞI TARAF" etiketliler ona gelenlerdir.

Görevin, Dogukan'ın AĞZINDAN, karşı tarafa gönderilebilecek bir cevap taslağı yazmak.

Kurallar:
- Konuşmanın dilini kullan (mail İngilizceyse taslak İngilizce, Türkçeyse Türkçe olsun).
- Kısa ve profesyonel ol; 120 kelimeyi geçme.
- Konuşmada geçen somut ayrıntılara (pozisyon adı, tarih, isim) atıf yap.
- ASLA bilgi uydurma. Dogukan'ın doldurması gereken bir yer varsa [köşeli parantez] kullan.
- Selamlama ve kapanış ekle, imza atma.
- Cevap gerektirmeyen bir mailse (sadece bilgilendirme, otomatik onay, ret bildirimi)
  draft'ı boş string bırak ve needs_reply'ı false yap.

SADECE şu JSON'u döndür, başka hiçbir şey yazma:
{"summary": "<mailin 1 cümlelik Türkçe özeti>", "needs_reply": true/false, "draft": "<taslak metin>"}"""


def pick_model(api_key):
    """Model kimliklerini sabitlemek yerine hesapta hangisi varsa onu seç."""
    env = os.environ.get("ANTHROPIC_MODEL")
    if env:
        return env
    r = requests.get(ANTHROPIC_MODELS_URL, timeout=20, headers={
        "x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION,
    })
    r.raise_for_status()
    ids = [m["id"] for m in r.json().get("data", [])]
    if not ids:
        raise RuntimeError("model listesi bos")
    for pref in ("haiku", "sonnet"):          # ucuzdan pahalıya
        for mid in ids:
            if pref in mid.lower():
                return mid
    return ids[0]


def generate_draft(api_key, model, subject, transcript):
    payload = {
        "model": model,
        "max_tokens": 700,
        "system": DRAFT_SYSTEM,
        "messages": [{"role": "user", "content":
                      f"Konu: {subject}\n\nKONUŞMA DÖKÜMÜ:\n{transcript}"}],
    }
    r = requests.post(ANTHROPIC_URL, timeout=60, json=payload, headers={
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    })
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json().get("content", [])).strip()
    m = re.search(r"\{.*\}", text, re.S)       # model bazen JSON'u metne sarar
    if not m:
        return None
    d = json.loads(m.group(0))
    return {
        "summary": (d.get("summary") or "").strip(),
        "needs_reply": bool(d.get("needs_reply")),
        "draft": (d.get("draft") or "").strip(),
    }


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
            "id": mid,
            "thread_id": hdrs.get("__thread_id", ""),
            "from": name,
            "email": email,
            "subject": hdrs.get("Subject", "(konu yok)"),
            "date": hdrs.get("Date", ""),
            "ts": internal_date,
        })

    important.sort(key=lambda x: x["ts"], reverse=True)
    for it in important:
        del it["ts"]
    important = important[:MAX_ITEMS]

    # --- konuşma geçmişi + cevap taslağı ---
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    draft_note = None
    model = None
    if api_key:
        try:
            model = pick_model(api_key)
        except Exception as e:
            draft_note = f"model_secilemedi: {e}"
    else:
        draft_note = "ANTHROPIC_API_KEY yok - taslak uretilmedi"

    try:
        my_address = get_my_address(headers)
    except Exception:
        my_address = ""

    drafted = 0
    for it in important:
        tid = it.get("thread_id")
        if not tid:
            continue
        try:
            msgs = fetch_thread(headers, tid, my_address)
        except Exception:
            continue
        it["thread_len"] = len(msgs)
        # Son mesaj senden ise zaten cevap vermişsin -> öneri gösterme
        it["awaiting_reply"] = bool(msgs) and not msgs[-1]["is_me"]
        it["i_replied_before"] = any(m["is_me"] for m in msgs)

        if not it["awaiting_reply"] or not model or drafted >= MAX_DRAFTS:
            continue
        try:
            res = generate_draft(api_key, model, it["subject"], build_transcript(msgs))
        except Exception as e:
            if not draft_note:
                draft_note = f"taslak_hatasi: {e}"
            continue
        if res:
            drafted += 1
            it["summary"] = res["summary"]
            it["needs_reply"] = res["needs_reply"]
            it["draft"] = res["draft"] if res["needs_reply"] else ""

    out = {
        "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "ok": True,
        "window_days": WINDOW_DAYS,
        "total_unread": len(ids),
        "important_unread": len(important),
        "drafts": drafted,
        "model": model or "",
        "items": important,
    }
    if draft_note:
        out["draft_note"] = draft_note
    return out


if __name__ == "__main__":
    d = build()
    with open("gmail.json", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    if d.get("ok"):
        print(f"gmail.json: {d['total_unread']} okunmamış (son {d['window_days']} gün), "
              f"{d['important_unread']} önemli/kişisel")
    else:
        print(f"gmail.json: HATA - {d.get('error')}")
