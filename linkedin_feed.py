# -*- coding: utf-8 -*-
"""
linkedin_feed.py — LinkedIn İŞ UYARISI maillerindeki ilanları panele taşır.

NEDEN BÖYLE
-----------
LinkedIn'in bireysel iş arama API'si yok ve siteyi otomatik gezmek Kullanıcı
Sözleşmesi'ne aykırı (CLAUDE.md 7. kural). Ama kullanıcı LinkedIn'de bir arama
kaydedip "iş uyarısı" kurduğunda ilanlar KENDİ GELEN KUTUSUNA düşüyor. Bu betik
LinkedIn'e hiç istek atmaz; yalnızca kullanıcının Gmail'indeki uyarı maillerini
okur (gmail_feed ile aynı salt-okunur yetki) ve ilanları panele taşır.

Böylece Türkiye ilanları (İstanbul remote / hibrit) panele girebiliyor —
anahtarsız iş panolarında Türkiye ilanı yok (23 Eyl ölçümü: 1741 ilanda 2).

NEREYE YAZAR
------------
Gizli gist'e `d:linkedinIsler` anahtarı (repoya DEĞİL — bu depo herkese açık,
ilanlar kullanıcının kendi aramalarından geliyor). Panel senkronla okuyup
Günün İşleri kartındaki Türkiye bölümüne koyuyor.

BİÇİM
-----
{"v":1,"zaman":"YYYY-AA-GG SS:DD","isler":[
   {"id","title","company","location","url","ts","alert"} ...]}

SINIR
-----
Uyarı maili yalnızca başlık, şirket, konum ve bağlantı taşır; ilan metni yok.
Bu yüzden beceri eşleşmesi ve puanlama yapılmaz — panel bu ilanları "LinkedIn
uyarısı" kaynağıyla, puansız gösterir. Cover letter odağı başlıktan tahmin edilir.

Çalıştırma: python linkedin_feed.py
Ortam: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, PANEL_GIST_TOKEN
Test:   python3 -m unittest tests/test_linkedin_feed.py   (ağ gerektirmez)
"""
import base64
import datetime as dt
import html as html_mod
import json
import os
import re

# requests ve gist_io yalnızca AĞ tarafında gerekiyor; ayrıştırıcı saf stdlib
# olsun diye içeri alındı — testler bağımlılık kurmadan çalışıyor.
IST = dt.timezone(dt.timedelta(hours=3))
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://www.googleapis.com/gmail/v1/users/me"

WINDOW_DAYS = 4         # uyarı mailleri günlük gelir; 4 gün = hafta sonu payı
MAX_MAILS = 12          # tur başına okunacak uyarı maili
MAX_ISLER = 40          # gist'e yazılacak ilan üst sınırı
GONDERENLER = ("jobalerts-noreply@linkedin.com", "jobs-noreply@linkedin.com",
               "jobs-listings@linkedin.com", "notifications-noreply@linkedin.com")
SORGU = ("from:(" + " OR ".join(GONDERENLER) + ") "
         "newer_than:{gun}d -in:chats")

# LinkedIn mail gövdesindeki ilan bağlantısı: /jobs/view/<id>
ILAN_RE = re.compile(r'<a\b[^>]*href="([^"]*?/jobs/view/(\d+)[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)
ETIKET_RE = re.compile(r"<[^>]+>")
BOSLUK_RE = re.compile(r"[\s ‌​]+")


def temiz(h):
    t = html_mod.unescape(h or "")
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t)
    t = ETIKET_RE.sub(" ", t)
    t = html_mod.unescape(t)
    return BOSLUK_RE.sub(" ", t).strip()


def get_access_token():
    import requests
    r = requests.post(TOKEN_URL, data={
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def _decode(data):
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "===").decode("utf-8", "ignore")
    except Exception:
        return ""


def _html_body(payload):
    """Uyarı mailinde ilanlar HTML'de; text/plain sürümü çoğu zaman boş."""
    if payload.get("mimeType") == "text/html":
        return _decode(payload.get("body", {}).get("data"))
    parcalar = []
    for part in payload.get("parts", []) or []:
        parcalar.append(_html_body(part))
    govde = "\n".join(p for p in parcalar if p)
    return govde or _decode(payload.get("body", {}).get("data"))


def ilanlari_ayikla(govde, konu=""):
    """Mail HTML'inden ilanları çıkar.

    LinkedIn kartı: başlık bir /jobs/view/<id> bağlantısı, hemen ardından
    şirket ve konum düz metin geliyor. Şablon zaman zaman değişiyor, bu yüzden
    BAĞLANTIYI çapa alıp devamındaki metni okuyoruz; şirket/konum çıkmazsa ilan
    yine de (başlık + bağlantı ile) alınır, sessizce düşmez.
    """
    out, gorulen = [], set()
    for m in ILAN_RE.finditer(govde or ""):
        url, ilan_id, ic = m.group(1), m.group(2), temiz(m.group(3))
        if not ic or len(ic) < 3 or ilan_id in gorulen:
            continue
        # Görsel/bağlantı metni olmayan çapa (ör. "Şimdi başvur") başlık değildir
        if re.fullmatch(r"(şimdi\s+başvur|apply now|görüntüle|view job|see job)\W*", ic, re.I):
            continue
        gorulen.add(ilan_id)
        kuyruk = temiz(govde[m.end(): m.end() + 600])
        sirket, konum = sirket_konum(kuyruk)
        out.append({
            "id": "li-" + ilan_id,
            "title": ic[:120],
            "company": (sirket or "—")[:80],
            "location": (konum or "")[:80],
            "url": url.split("?")[0],
            "alert": konu[:120],
        })
    return out


def sirket_konum(metin):
    """Başlıktan sonraki metin: "Şirket · İstanbul, Türkiye (Remote) · 2 gün önce".
    Ayraç · veya satır sonu olabilir; ilk iki anlamlı parça alınır."""
    if not metin:
        return "", ""
    parcalar = [p.strip(" ·-—|") for p in re.split(r"[·•|]|\s{2,}", metin) if p.strip(" ·-—|")]
    parcalar = [p for p in parcalar if not re.fullmatch(r"(şimdi\s+başvur|apply now|easy apply|kolay başvuru)\W*", p, re.I)]
    sirket = parcalar[0] if parcalar else ""
    konum = ""
    for p in parcalar[1:4]:
        if re.search(r"türkiye|turkey|istanbul|i̇stanbul|ankara|izmir|remote|uzaktan|hybrid|hibrit|"
                     r"germany|deutschland|netherlands|united kingdom|london|berlin|amsterdam|\(.*\)", p, re.I):
            konum = p
            break
    if not konum and len(parcalar) > 1:
        konum = parcalar[1]
    return sirket, konum


def build():
    import requests
    try:
        token = get_access_token()
    except Exception as e:
        return {"v": 1, "ok": False, "error": f"auth_failed: {type(e).__name__}", "isler": []}
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{API_BASE}/messages", headers=headers, timeout=20,
                         params={"q": SORGU.format(gun=WINDOW_DAYS), "maxResults": MAX_MAILS})
        r.raise_for_status()
        idler = [m["id"] for m in (r.json().get("messages") or [])]
    except Exception as e:
        return {"v": 1, "ok": False, "error": f"list_failed: {type(e).__name__}", "isler": []}

    isler, mail_sayisi = [], 0
    for mid in idler:
        try:
            m = requests.get(f"{API_BASE}/messages/{mid}", headers=headers,
                             params={"format": "full"}, timeout=25).json()
        except Exception:
            continue
        mail_sayisi += 1
        hdrs = {h["name"]: h["value"] for h in (m.get("payload") or {}).get("headers", [])}
        ts = int(m.get("internalDate", "0"))
        for j in ilanlari_ayikla(_html_body(m.get("payload") or {}), hdrs.get("Subject", "")):
            j["ts"] = ts
            isler.append(j)

    # aynı ilan birden çok uyarı mailinde olabilir: en yenisi kalsın
    tek = {}
    for j in sorted(isler, key=lambda x: -x["ts"]):
        tek.setdefault(j["id"], j)
    sirali = sorted(tek.values(), key=lambda x: -x["ts"])[:MAX_ISLER]
    return {"v": 1, "ok": True, "zaman": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
            "mails": mail_sayisi, "isler": sirali}


if __name__ == "__main__":
    import gist_io
    d = build()
    # Actions logu herkese açık: ŞİRKET/İLAN ADI BASILMAZ, yalnızca sayılar.
    print(gist_io.yaz("d:linkedinIsler", json.dumps(d, ensure_ascii=False)))
    if d.get("ok"):
        print(f"linkedin: {d['mails']} uyarı maili okundu, {len(d['isler'])} ilan çıkarıldı")
        if not d["isler"]:
            print("linkedin: ilan çıkmadı — LinkedIn'de 'iş uyarısı' kurulu mu? "
                  "(Jobs > arama > Create alert; mailler jobalerts-noreply@linkedin.com'dan gelir)")
    else:
        print(f"linkedin: HATA - {d.get('error')}")
