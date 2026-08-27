# -*- coding: utf-8 -*-
"""
gmail_feed.py — Gmail'deki okunmamış maillerin özetini üretir ve panelin
GİZLİ gist'ine yazar (d:gmail). Repoya YAZMAZ: gönderen adı/adresi ve konu
başlığı kişiseldir, bu depo herkese açık (CLAUDE.md 1. kural).
MAIL GÖNDERMEZ, hiçbir maili değiştirmez/okundu işaretlemez (salt-okunur scope).

AKSİYONUN TANIMI
----------------
Panel sahibinin kuralı: AKSİYON = GERÇEK BİR İNSANIN YAZDIĞI MAİL. Otomatik
gönderilmiş bir mail ne kadar acil görünürse görünsün ("hesabınız kapanacak",
"gecikmiş ödemeniz var") cevap yazılacak bir muhatabı yoktur; yapılacak iş varsa
o işi bankanın/sitenin kendi uygulamasında yaparsın, gelen kutusunda değil.
Bu yüzden kart tek bir soruyu öne alır: BANA BİR İNSAN YAZDI MI?

Kova (bucket) sırası — ilk eşleşen kazanır:
  reply   gerçek bir insandan gelmiş, cevap bekliyor  <- kartta öne çıkan tek kova
  job     başvuru / mülakat / ATS bildirimi
  info    otomatik bildirim: sipariş, kargo, belge, ödeme, güvenlik uyarısı
  bulk    bülten / pazarlama — sayılır, listelenmez

info içindeki mailler bir "etiket" taşıyabilir (doğrulama, gecikmiş ödeme,
güvenlik...). Bu etiket bilgilendirmedir, alarm değil: sıralamayı değiştirmez,
kartta nötr renkte durur.

Ayrıca aynı mailin tekrarları (Monese 4 kez, GitHub 4 kez) tek satırda
birleştirilir; yoksa kart aynı şeyi dört kere gösteriyor.

Kimlik bilgileri ortam değişkenlerinden okunur (GitHub Actions secrets):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
Opsiyonel: ANTHROPIC_API_KEY (yoksa taslak üretilmez, kart normal çalışır)

Çalıştırma: python gmail_feed.py
"""
import base64
import json
import os
import re
import datetime as dt
from collections import Counter

import requests

import gist_io

IST = dt.timezone(dt.timedelta(hours=3))
WINDOW_DAYS = 7       # aksiyon gerektiren mail 3 günde kaybolmasın diye 7
MAX_FETCH = 100       # primary'de header çekilecek üst sınır (API kotası)
MAX_UPDATES = 40      # Updates sekmesinde taranacak üst sınır
CAP = {"reply": 10, "job": 5, "info": 6}   # kova başına gösterim

MAX_DRAFTS = 5        # tur başına en fazla kaç maile taslak yazılsın
MAX_THREAD_MSGS = 6   # konuşmanın son kaç mesajı modele verilsin
MAX_BODY_CHARS = 1500 # mesaj başına gövde sınırı

TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://www.googleapis.com/gmail/v1/users/me"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"
ANTHROPIC_VERSION = "2023-06-01"

# --- toplu/otomatik gönderim tespiti (kova değil, sadece "insan mı" sorusu) ---
BULK_LOCALPART_RE = re.compile(
    r"(noreply|no-reply|donotreply|do-not-reply|notification|bildirim|bulten|"
    r"kampanya|marketing|mailer|bounce|jobalerts|jobs-noreply|e-bulten|newsletter)",
    re.IGNORECASE,
)
# X-Mailer KASITEN yok: Apple Mail gibi gerçek istemciler de onu koyuyor.
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
    r"zalando\.|mango\.com|eventbrite\.com|pinterest\.com|duolingo\.com|"
    r"tiktok\.com|alibaba\.com|getmidas\.com|jobscan\.co)",
    re.IGNORECASE,
)

# --- info etiketleri ---
# Otomatik maili sınıflandırmaz, yalnızca "ne hakkında" olduğunu adlandırır.
# Pazarlama dili ("son gün", "%50 indirim") KASITEN yok: etiket taşımayan
# otomatik mail zaten bülten sayılır.
ACTION_SUBJECT = [
    (re.compile(r"(verify|confirm)\s+(your|the)\b|doğrula(y|n)|teyit ed|onayınız", re.I), "doğrulama"),
    (re.compile(r"action (required|needed)|immediate action|aksiyon gerek|işlem yapmanız", re.I), "bildirim"),
    (re.compile(r"(suspend|deactivat|clos|restrict|delet)\w*\s+(your|the)\s+(account|shop|store|listing)"
                r"|(your|the)\s+(account|shop|store)\s+will\s+(close|be closed|be suspended)"
                r"|keep your account active|hesabınız(ın)? (kapat|askıya|dondur)"
                r"|üyeliğiniz(in)? (sonland|iptal)", re.I), "hesap riski"),
    (re.compile(r"security alert|new sign-?in|unusual (activity|sign)|personal access token"
                r"|two-?factor|güvenlik uyar|şüpheli (giriş|hareket)", re.I), "güvenlik"),
    (re.compile(r"password reset|reset your password|şifre(ni|nizi)? (sıfırla|yenile)", re.I), "şifre"),
    (re.compile(r"payment (failed|declined|due|unsuccessful)|past due|overdue"
                r"|ödeme(niz)? (alınamadı|başarısız|bekle)|son ödeme tarihi|gecikmiş borç", re.I), "ödeme"),
    (re.compile(r"\b(invoice|e-?fatura|e-?arşiv|beyanname|hatalı belge)\b", re.I), "belge"),
    (re.compile(r"expires? (today|tomorrow|in \d)|expiring soon|süresi dol(uyor|acak)"
                r"|son (başvuru|teslim) tarihi|deadline", re.I), "süre"),
    (re.compile(r"randevu|appointment (confirm|reminder|scheduled)|mülakat|interview invit", re.I), "randevu"),
    (re.compile(r"signature request|sign the document|imzan(ız|ızı)|e-imza", re.I), "imza"),
]
# Gövde önizlemesinde (snippet) aranacak DAR küme. Konu genelse ("ELOGO
# Bilgilendirme") aksiyonu ancak burada yakalayabiliyoruz; geniş tutulursa
# sipariş maili de aksiyon sanılır, o yüzden sadece tartışmasız ifadeler.
ACTION_SNIPPET = [
    (re.compile(r"verify your (details|identity|account)|hesabınızı doğrula", re.I), "doğrulama"),
    (re.compile(r"hatalı belge|reddedilen belge|belgeleriniz.{0,25}hata", re.I), "belge"),
    (re.compile(r"ödemeniz alınamadı|payment (was )?(declined|failed)", re.I), "ödeme"),
    # Banka gecikme maillerinin konusu çoğu zaman sadece marka adı ("GARANTİ BBVA")
    # oluyor; aksiyon ancak gövde önizlemesinden anlaşılıyor.
    # "gecikmiş / geciken / geciken bir ödeme" — banka her mailde farklı çekim
    # kullanıyor, kök üzerinden yakalanıyor. Asgari ödeme uyarısı da buraya girer.
    (re.compile(r"gecik(miş|en)\s+(bir\s+)?ödeme|ödemeniz gecik|ödemesi gecikmiş"
                r"|borcunuz bulunmakta|son ödeme tarihi geç"
                r"|(asgari|minimum) ödeme\w*[^.]{0,40}ödenmemiş", re.I), "gecikmiş ödeme"),
    (re.compile(r"action is required|acil işlem", re.I), "bildirim"),
]
JOB_DOMAIN_RE = re.compile(
    r"(jobs-noreply@linkedin|greenhouse\.io|myworkday|lever\.co|smartrecruiters"
    r"|taleo|workable|jobvite|icims|kariyer\.net|hiring|ashbyhq|teamtailor"
    r"|personio|recruitee|breezy\.hr|bamboohr)", re.I)
JOB_SUBJECT_RE = re.compile(
    r"application (was |has been )?(sent|received|submitted|update)|your application"
    r"|thank you for (your |)(applying|application|interest in joining)"
    r"|başvurun(uz)?|başvuru(nuz)? (alınmış|iletil)|mülakat|interview|pozisyon(unuz)?"
    r"|bewerbung|candidate|aday(lığınız)?", re.I)
# "özet / summary / haftalık rapor" KASITEN yok: bülten dilinin ta kendisi.
# Midas'ın "son 7 günün özeti" maili bu yüzden info sanılıyordu.
INFO_SUBJECT_RE = re.compile(
    r"\border\b|sipariş|kargo|shipping|shipped|delivered|teslim|receipt|makbuz"
    r"|welcome|hoş geldin|abonel|subscription (renew|confirm)|back in stock"
    r"|available again|güncelleme|değişiklik|parcel|will arrive|paketin", re.I)


def get_access_token():
    r = requests.post(TOKEN_URL, data={
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def list_ids(headers, q, cap):
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
        if not page_token or len(ids) >= cap:
            break
    return ids[:cap]


def fetch_meta(headers, msg_id):
    # metadataHeaders ile SINIRLAMA YOK: toplu-posta parmak izi (Feedback-ID,
    # X-Mailgun-*, X-SMTPAPI ...) hangi başlıkta geleceği önceden bilinmiyor.
    r = requests.get(f"{API_BASE}/messages/{msg_id}", headers=headers,
                     params={"format": "metadata"}, timeout=20)
    r.raise_for_status()
    md = r.json()
    hdrs = {h["name"]: h["value"] for h in md.get("payload", {}).get("headers", [])}
    hdrs["__thread_id"] = md.get("threadId", "")
    hdrs["__snippet"] = md.get("snippet", "")     # format=metadata snippet'i de döndürür
    return hdrs, int(md.get("internalDate", "0"))


def is_bulk(hdrs):
    """Bu maili bir insan mı yazdı, bir sistem mi gönderdi?"""
    if "List-Unsubscribe" in hdrs or "List-Unsubscribe-Post" in hdrs:
        return True
    if hdrs.get("Precedence", "").lower() in ("bulk", "list", "junk"):
        return True
    for name in hdrs:
        if BULK_HEADER_RE.match(name):
            return True
    sender = hdrs.get("From", "")
    return bool(BULK_LOCALPART_RE.search(sender) or BULK_DOMAIN_RE.search(sender))


def notify_tag(subject, snippet):
    """Otomatik mailin konusunu adlandırır: doğrulama / ödeme / güvenlik ...
    Kovayı DEĞİŞTİRMEZ; yalnızca kartta gösterilecek nötr bir etikettir."""
    for rx, why in ACTION_SUBJECT:
        if rx.search(subject):
            return why
    for rx, why in ACTION_SNIPPET:
        if rx.search(snippet):
            return why
    return ""


def classify(subject, snippet, sender, bulk):
    """(kova, etiket) döndürür.

    İlk ve belirleyici soru: bunu bir insan mı yazdı? Evetse cevap bekleyen
    maildir, konusu ne olursa olsun. Hayırsa otomatik gönderimdir ve hiçbir
    konu kalıbı onu "aksiyon" seviyesine çıkarmaz."""
    if not bulk:
        return "reply", ""
    if JOB_DOMAIN_RE.search(sender) or JOB_SUBJECT_RE.search(subject):
        return "job", ""
    etiket = notify_tag(subject, snippet)
    if etiket or INFO_SUBJECT_RE.search(subject):
        return "info", etiket
    return "bulk", ""


def parse_from(raw):
    # "Ad Soyad <mail@ornek.com>" ya da "mail@ornek.com"
    m = re.match(r'^\s*"?([^"<]*)"?\s*<([^>]+)>\s*$', raw or "")
    if m:
        return (m.group(1).strip() or m.group(2)), m.group(2)
    return raw, raw


def hide_key(bucket, msg_id, email, subject):
    """Panelde "Hallettim" tikinin kalıcı anahtarı.

    İki farklı davranış gerekiyor:
      reply -> MESAJ kimliği. İnsan tekrar yazarsa yeni mesaj yeni kimlik alır
               ve mail tekrar görünür; kapattığın şey o tek mesajdır.
      diğer -> GÖNDEREN + konu. ELOGO her gün aynı maili yolluyor; bunu bir kez
               kapatınca yarınki kopyası da gelmesin isteniyor.
    """
    if bucket == "reply":
        return "m:" + msg_id
    return "s:" + (email or "").lower() + "|" + norm_subject(subject)


def norm_subject(s):
    """Tekrar tespiti için konu normalizasyonu: Re:/Fwd: ve sayılar atılır."""
    s = re.sub(r"^\s*((re|fw|fwd|yan|ilt)\s*:\s*)+", "", (s or ""), flags=re.I)
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", s)).strip().lower()


def sender_label(name, email):
    """Bülten özetinde marka adı: "Duolingo <hello@duolingo.com>" -> Duolingo."""
    if name and "@" not in name:
        return name.strip()[:24]
    dom = (email or "").split("@")[-1].lower()
    # Gönderim altyapısı katmanlarını soy: service-mail.zalando.de -> zalando.
    # Tek geçiş yetmiyor, katmanlar üst üste biniyor (info.getmidas.com gibi).
    for _ in range(4):
        yeni = re.sub(r"^(mail|info|service|news|email|smtp|send|em|mkt)[-.]", "", dom)
        if yeni == dom:
            break
        dom = yeni
    return (dom.split(".")[0] or dom)[:24]


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
        return re.sub(r"<[^>]+>", " ", _decode(payload.get("body", {}).get("data")))
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
    r = requests.get(f"{API_BASE}/threads/{thread_id}", headers=headers,
                     params={"format": "full"}, timeout=25)
    r.raise_for_status()
    msgs = []
    for m in r.json().get("messages", []):
        h = {x["name"]: x["value"] for x in m.get("payload", {}).get("headers", [])}
        _, sender_mail = parse_from(h.get("From", ""))
        msgs.append({
            "from": h.get("From", ""),
            "date": h.get("Date", ""),
            "is_me": my_address in (sender_mail or "").lower(),
            "body": strip_quoted(_plain_body(m.get("payload", {})))[:MAX_BODY_CHARS],
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
    r = requests.post(ANTHROPIC_URL, timeout=60, json={
        "model": model,
        "max_tokens": 700,
        "system": DRAFT_SYSTEM,
        "messages": [{"role": "user", "content":
                      f"Konu: {subject}\n\nKONUŞMA DÖKÜMÜ:\n{transcript}"}],
    }, headers={
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


# ---------------------------------------------------------------------------

def err(msg):
    return {
        "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "ok": False, "error": msg,
        "total_unread": 0, "important_unread": 0,
        "counts": {"reply": 0, "job": 0, "info": 0, "bulk": 0},
        "items": [], "bulk_top": [],
    }


def collect(headers, ids, only_bucket):
    """id listesini sınıflandırılmış kayıtlara çevirir.
    only_bucket verilirse yalnızca o kovaya düşenler alınır."""
    out = []
    for mid in ids:
        try:
            hdrs, internal_date = fetch_meta(headers, mid)
        except Exception:
            continue
        name, email = parse_from(hdrs.get("From", ""))
        subject = hdrs.get("Subject", "(konu yok)")
        snippet = hdrs.get("__snippet", "")
        bucket, why = classify(subject, snippet, hdrs.get("From", ""), is_bulk(hdrs))
        if only_bucket and bucket != only_bucket:
            continue
        out.append({
            "id": mid,
            "thread_id": hdrs.get("__thread_id", ""),
            "from": name, "email": email,
            "subject": subject,
            "date": hdrs.get("Date", ""),
            "bucket": bucket, "why": why,
            "key": hide_key(bucket, mid, email, subject),
            "ts": internal_date,
        })
    return out


def dedupe(records):
    """Aynı gönderenden aynı konu = tek satır + kaç kez geldiği."""
    seen = {}
    # Aynı mailin hem okunmamış hem okunmuş kopyası varsa okunmamış kazansın.
    for r in sorted(records, key=lambda x: x["ts"], reverse=True):
        key = ((r["email"] or "").lower(), norm_subject(r["subject"]))
        if key in seen:
            seen[key]["dupes"] += 1
            continue
        r["dupes"] = 1
        seen[key] = r
    return list(seen.values())


def build():
    try:
        token = get_access_token()
    except Exception as e:
        return err(f"auth_failed: {e}")
    headers = {"Authorization": f"Bearer {token}"}

    base = f"is:unread in:inbox newer_than:{WINDOW_DAYS}d -in:chats"
    try:
        primary_ids = list_ids(headers, f"{base} category:primary", MAX_FETCH)
    except Exception as e:
        return err(f"list_failed: {e}")
    # Updates sekmesi: insan yazdıysa buraya düşmez, o yüzden yalnızca insan
    # çıkanlar alınıyor. Gmail nadiren de olsa kişisel maili Updates'e atıyor;
    # bültenleri almamak için diğer kovalar eleniyor.
    try:
        update_ids = list_ids(headers, f"{base} category:updates", MAX_UPDATES)
    except Exception:
        update_ids = []

    records = collect(headers, primary_ids, None)
    records += collect(headers, update_ids, "reply")
    records = dedupe(records)
    records.sort(key=lambda x: x["ts"], reverse=True)

    counts = Counter(r["bucket"] for r in records)
    bulk_top = Counter(sender_label(r["from"], r["email"])
                       for r in records if r["bucket"] == "bulk").most_common(5)

    shown, per = [], Counter()
    for r in records:
        b = r["bucket"]
        if b == "bulk" or per[b] >= CAP.get(b, 0):
            continue
        per[b] += 1
        del r["ts"]
        shown.append(r)

    # --- konuşma geçmişi + cevap taslağı (yalnız aksiyon/cevap kovaları) ---
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
    for it in shown:
        if it["bucket"] != "reply" or not it.get("thread_id"):
            continue
        try:
            msgs = fetch_thread(headers, it["thread_id"], my_address)
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
        "total_unread": len(primary_ids),
        "counts": {k: counts.get(k, 0) for k in ("reply", "job", "info", "bulk")},
        # geriye dönük uyum: eski panel sürümü bu alanı okuyor
        "important_unread": counts.get("reply", 0),
        "drafts": drafted,
        "model": model or "",
        "items": shown,
        "bulk_top": bulk_top,
    }
    if draft_note:
        out["draft_note"] = draft_note
    return out


if __name__ == "__main__":
    d = build()
    # ÖNCEDEN gmail.json olarak BU DEPOYA yazılıyordu: gönderen adı, e-posta
    # adresi ve konu başlığı herkese açık bir repoda duruyordu (1. kurala
    # aykırı). Artık senkronun gizli gist'ine yazılıyor, panel oradan okuyor.
    print(gist_io.yaz("d:gmail", json.dumps(d, ensure_ascii=False)))
    if d.get("ok"):
        c = d["counts"]
        print(f"gmail: {d['total_unread']} okunmamış (son {d['window_days']} gün) — "
              f"cevap bekleyen {c['reply']}, iş {c['job']}, "
              f"bilgi {c['info']}, bülten {c['bulk']}")
    else:
        print(f"gmail: HATA - {d.get('error')}")
