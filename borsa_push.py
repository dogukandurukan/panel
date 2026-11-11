# -*- coding: utf-8 -*-
"""
borsa_push.py — borsa-feed koşusundan sonra (09:00 / 14:00) teknik sinyal
özetini telefona web push olarak yollar.

Veri: panel_feed.py'nin az önce yazdığı borsa.json → "sinyaller".
Abonelik ve anahtar: push_feed.py ile aynı (gizli gist + VAPID_PRIVATE).

Etiketler teknik.py'deki mekanik kuralların toplamıdır — YATIRIM TAVSİYESİ
DEĞİL. Bildirim bunu kısaca yazar; ayrıntı panelde (Keşif › Piyasa).

Hafta sonu gönderilmez: borsa kapalı, veri cumadan beri aynı.

ZAMANLAMA (11 Kas): GitHub `schedule` bu feed'de saatlerce gecikiyor ya da
hiç çalışmıyor (10 Kas 09:00 koşusu 17:43'te, 11 Kas'ta hiç). Zamanında
bildirim dış zamanlayıcıdan (cron-job.org → workflow_dispatch) gelir. Geciken
schedule koşusu veriyi yine günceller ama bildirimi yalnızca PENCERE içinde
atar — akşam 21:00'de "09:00 özeti" gelmesin.
Çalıştırma: python borsa_push.py   (BORSA_ZORLA=true hafta sonu kontrolünü atlar)
"""
import datetime as dt
import json
import os
import sys

import push_feed as P

IST = dt.timezone(dt.timedelta(hours=3))
PENCERELER = ((9, 11), (14, 16))   # TR saati [başlangıç, bitiş)
EN_FAZLA = 4          # gövdede adı geçen kağıt sayısı (iOS ~4 satır gösteriyor)


def ozet_metni(d):
    """borsa.json -> (başlık, gövde). Ağsız, test edilebilir."""
    s = d.get("sinyaller") or []
    saat = (d.get("updated") or "")[-5:]
    tarama = d.get("sinyalTarama") or {}
    toplam = (tarama.get("bist") or 0) + (tarama.get("abd") or 0)
    if not s:
        return (f"Borsa · {saat}",
                f"{toplam} kağıt tarandı, kural eşleşmesi yok. · tavsiye değil")
    alim = sum(1 for x in s if x["durum"] == "olasi_alim")
    satis = len(s) - alim
    parca = []
    if alim:
        parca.append(f"{alim} olası alım")
    if satis:
        parca.append(f"{satis} olası satış")
    satirlar = []
    for x in s[:EN_FAZLA]:
        ok = "▲" if x["durum"] == "olasi_alim" else "▼"
        neden = ", ".join((x.get("kisa") or [])[:2]) or x.get("trend", "")
        satirlar.append(f"{ok} {x['code']} {x['price']} — {neden}")
    if len(s) > EN_FAZLA:
        satirlar.append(f"+{len(s) - EN_FAZLA} kağıt panelde")
    satirlar.append("kural tabanlı · tavsiye değil")
    return f"Borsa · {saat} · " + ", ".join(parca), "\n".join(satirlar)


def main():
    simdi = dt.datetime.now(IST)
    zorla = os.environ.get("BORSA_ZORLA", "").lower() == "true"
    if simdi.weekday() >= 5 and not zorla:
        print("hafta sonu — borsa kapalı, bildirim yok.")
        return 0
    tetik = os.environ.get("TETIK", "")
    if tetik == "schedule" and not any(a <= simdi.hour < b for a, b in PENCERELER):
        print(f"schedule koşusu {simdi:%H:%M}'de geldi (pencere dışı) — veri güncellendi, bildirim yok.")
        return 0
    token = os.environ.get("PANEL_GIST_TOKEN", "").strip()
    gizli = os.environ.get("VAPID_PRIVATE", "").strip()
    eksik = [ad for ad, deger in (("PANEL_GIST_TOKEN", token),
                                  ("VAPID_PRIVATE", gizli)) if not deger]
    if eksik:
        print("secret tanımlı değil: " + ", ".join(eksik) + " — atlandı.")
        return 0
    with open("borsa.json", encoding="utf-8") as f:
        d = json.load(f)
    baslik, govde = ozet_metni(d)
    try:
        push_ham, _ = P.gist_dosyalari(token)
    except Exception as e:
        print(f"gist okunamadı: {e}")
        return 1
    subs = (json.loads(push_ham).get("subs") if push_ham else None) or []
    if not subs:
        print("kayıtlı cihaz yok.")
        return 0
    paket = json.dumps({
        "title": baslik, "body": govde,
        "tag": "borsa-" + simdi.strftime("%Y-%m-%d-%H"),
        "url": "./index.html#borsa", "icon": "icon-192.png",
    }, ensure_ascii=False)
    basarili, olu = P.hepsine_gonder(paket, subs, gizli, ttl=4 * 3600)
    print(f"{baslik} — {basarili}/{len(subs)} cihaza gönderildi."
          + (f" ölü abonelik: {len(olu)}" if olu else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
