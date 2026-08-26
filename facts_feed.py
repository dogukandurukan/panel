# -*- coding: utf-8 -*-
"""
facts_feed.py — "Tarihten Bir Not" kartını besleyen facts.json'u üretir.

NE ÜRETİR
---------
Vikipedi'nin "bugün tarihte" uç noktasından, bugünden başlayarak HISTORY_DAYS
günlük olayları çeker ve facts.json'a şu biçimde yazar:

    {"history": {"08-24": [{"year": 2023, "text": "...", "title": "...",
                            "url": "..."}, ...], ...}}

Feed haftada bir (Pazartesi) çalıştığı için 10 gün önden alınır; bir hafta
atlansa bile kart boşta kalmaz.

NEDEN SADECE TARİH VERİSİ
-------------------------
Bu dosya eskiden ayrıca kürasyonlu bir konu listesinden (Tardigrad, Antikythera
düzeneği, Mpemba etkisi...) Vikipedi özetleri çekip "İlginç Bilgiler" kartını
besliyordu. O yaklaşım bırakıldı: Vikipedi özeti bir TANIMDIR, ilginç bilgi
değil. "Entropi, bir sistemin mekanik işe çevrilemeyecek termal enerjisini
temsil eden termodinamik terimidir..." cümlesi doğrudur ama kimse okumaz.
Günün Bilgisi kartı artık index.html içindeki kürasyonlu tek cümlelik listeyi
kullanıyor. Eski konu listesi git geçmişinde duruyor.

Buradaki olay metinleri ise zaten kısa ve doğrudan ("Hindistan, Chandrayaan-3
aracı ile Ay'ın güney kutbuna inen ilk ülke oldu.") — kartın istediği biçim bu.

NEDEN TARAYICIDAN DEĞİL
-----------------------
Panel bu uç noktayı doğrudan çağırmıyor: CORS davranışı doğrulanamadı ve kartın
tek bir dış servise canlı bağımlı olması istenmedi. Diğer feed'lerle aynı desen —
Actions çeker, panel statik JSON okur. facts.json yoksa panel index.html içindeki
gömülü HISTORY listesine düşer (o liste tarihe bağlı değildir, "bugün" demez).

Vikipedi REST API'si (anahtar gerektirmez):
  https://tr.wikipedia.org/api/rest_v1/feed/onthisday/events/<AA>/<GG>

Çalıştırma: python facts_feed.py
"""
import datetime as dt
import json
import re
import time

import requests

IST = dt.timezone(dt.timedelta(hours=3))
ONTHISDAY_API = "https://tr.wikipedia.org/api/rest_v1/feed/onthisday/events/"
UA = "panel-facts/1.0 (https://github.com/dogukandurukan/panel)"

HISTORY_DAYS = 10        # haftalık çalışıyor; bir hafta atlansa da açık kalmasın
HISTORY_PER_DAY = 3      # "Başka" düğmesinin gezinebilmesi için gün başına birkaç olay
MIN_EXTRACT = 80         # bu uzunlukta özeti olan sayfa "olayı gerçekten anlatıyor" sayılır
DETAY_MAX = 520          # "devamı" paragrafı; cümle sonunda kesilir
REQUEST_PAUSE = 0.15     # Vikipedi'ye kibar davran


def temizle(metin):
    return re.sub(r"\s+", " ", (metin or "").strip())


def _adi_gecen(sayfa, metin):
    """Sayfa adının ilk sözcüğü olay metninde geçiyor mu?"""
    ad = (sayfa.get("title") or "").replace("_", " ").strip()
    if not ad:
        return False
    return ad.lower() in metin.lower()


def _kisalt(metin, n):
    """Cümle ortasında kesme; n'den kısa son cümle sınırına kadar al."""
    if len(metin) <= n:
        return metin
    kes = metin[:n]
    nokta = max(kes.rfind(". "), kes.rfind("! "), kes.rfind("? "))
    return (kes[:nokta + 1] if nokta > n // 3 else kes.rstrip() + "…").strip()


def fetch_onthisday(session, ay, gun):
    """Bir günün olaylarını çeker ve HISTORY_PER_DAY tanesini seçer."""
    r = session.get(f"{ONTHISDAY_API}{ay:02d}/{gun:02d}", timeout=25)
    r.raise_for_status()

    olaylar = []
    for ev in r.json().get("events", []):
        yil, metin = ev.get("year"), temizle(ev.get("text"))
        if not yil or not metin:
            continue
        # Olaya bağlı sayfalardan özeti olan biri seçilir. Panel bu sayfayı
        # BAŞLIK olarak kullanmıyor — Vikipedi olayı sık sık yanlış özneye
        # bağlıyor (Chandrayaan-3 inişine "Hindistan") — yalnızca bağlantı ve
        # "devamı" paragrafı olarak veriyor. Bu yüzden ADI OLAY METNİNDE GEÇEN
        # sayfa tercih ediliyor: "Hindistan" genel ülke maddesi yerine olayın
        # gerçek öznesine denk gelme ihtimali yükseliyor.
        adaylar = [p for p in (ev.get("pages") or [])
                   if len(temizle(p.get("extract"))) >= MIN_EXTRACT]
        sayfa = next((p for p in adaylar if _adi_gecen(p, metin)), None) \
            or (adaylar[0] if adaylar else {})
        kayit = {
            "year": yil,
            "text": metin,
            "title": sayfa.get("title", ""),
            "url": ((sayfa.get("content_urls") or {}).get("desktop") or {}).get("page", ""),
        }
        # "devamı" paragrafı: özet ZATEN bu yanıtın içinde geliyordu ve
        # atılıyordu; ek istek yok. Kartın ön yüzünde değil, düğme arkasında —
        # bir tanım olması burada sorun değil, olayın öznesini açıklıyor.
        detay = _kisalt(temizle(sayfa.get("extract")), DETAY_MAX)
        if detay:
            kayit["detay"] = detay
        olaylar.append(kayit)

    # Bağlantısı olanlar önce; sonra listeye eşit aralıkla yayılarak seç ki
    # gün başına düşen üç olay da aynı dönemden çıkmasın.
    havuz = [o for o in olaylar if o["url"]] or olaylar
    if len(havuz) <= HISTORY_PER_DAY:
        return havuz
    adim = len(havuz) / HISTORY_PER_DAY
    return [havuz[int(i * adim)] for i in range(HISTORY_PER_DAY)]


def build():
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "application/json"})

    bugun = dt.datetime.now(IST).date()
    history, atlanan = {}, []
    for i in range(HISTORY_DAYS):
        g = bugun + dt.timedelta(days=i)
        try:
            olaylar = fetch_onthisday(session, g.month, g.day)
        except Exception as e:
            atlanan.append(f"{g:%m-%d} ({e})")
            continue
        if olaylar:
            history[f"{g:%m-%d}"] = olaylar
        time.sleep(REQUEST_PAUSE)

    return {
        "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        # Tek bir gün bile gelmediyse ok=False: panel gömülü listeye düşsün.
        "ok": len(history) > 0,
        "history_days": len(history),
        "history": history,
    }, atlanan


if __name__ == "__main__":
    d, atlanan = build()
    with open("facts.json", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    toplam = sum(len(v) for v in d["history"].values())
    print(f"facts.json: {d['history_days']} gün, {toplam} olay")
    if atlanan:
        print("atlanan günler: " + ", ".join(atlanan))
