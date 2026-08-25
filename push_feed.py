# -*- coding: utf-8 -*-
"""
push_feed.py — Yoklama saatinde telefona web push bildirimi gönderir.

NEDEN GIST'TEN OKUYOR
---------------------
Abonelik uç noktası cihazı tanımlayan kalıcı bir adrestir ve bu repo herkese
açık. Bu yüzden panel, aboneliği repoya değil senkronun kullandığı GİZLİ gist'e
yazar (panel-push.json). Bu betik de oradan okur.

NE OKUR
-------
gist / panel-push.json : {vapidPublic, plan, subs:[{endpoint, keys:{p256dh,auth}}]}
gist / panel-data.json : panelin senkron verisi — "bu yoklama zaten
                         cevaplanmış mı" kontrolü için (d:yok:GG, d:sched:GG)

plan, index.html'deki SCHED + YOK tablolarından panel tarafından üretilir.
Program burada KOPYALANMAZ; tek kaynak index.html'de kalır.

ORTAM DEĞİŞKENLERİ (GitHub Actions secrets)
  PANEL_GIST_TOKEN : gist okuma izni olan token
  VAPID_PRIVATE    : panelin kurulum sırasında bir kez gösterdiği gizli anahtar

Çalıştırma: python push_feed.py
"""
import datetime as dt
import json
import os
import sys

import requests
from pywebpush import webpush, WebPushException

IST = dt.timezone(dt.timedelta(hours=3))
GITHUB_API = "https://api.github.com"
PUSH_FILE = "panel-push.json"
DATA_FILE = "panel-data.json"

# Zamanlanmış iş akışları gecikebiliyor; dilimin başlangıcına bu kadar yakınsa
# bildirim gönderilir. Geriye doğru geniş, ileriye dar: erken uyandırma yok.
GERI_DK = 35
ILERI_DK = 5

VAPID_CLAIMS = {"sub": "mailto:panel@localhost"}


def gh(yol, token):
    r = requests.get(GITHUB_API + yol, timeout=25, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
    })
    r.raise_for_status()
    return r.json()


def gist_dosyalari(token):
    """Panelin gist'ini bulur ve iki dosyanın içeriğini döndürür.

    Teşhis: "panel-push.json bulunamadı" iki ayrı sebepten çıkabiliyor —
    ya telefondaki kurulum gist'e yazmamış, ya da token gist'leri göremiyor.
    Ayırmak için sayı basılıyor. DİKKAT: bu depo herkese açık, dolayısıyla
    Actions log'u da açık. Gist ADLARI yazılmaz, yalnızca sayı ve iki bilinen
    dosyanın varlığı yazılır.
    """
    liste = gh("/gists?per_page=100", token) or []
    veri_var = any(DATA_FILE in ((g or {}).get("files") or {}) for g in liste)
    push_var = any(PUSH_FILE in ((g or {}).get("files") or {}) for g in liste)
    print(f"teşhis: token {len(liste)} gist görüyor · "
          f"{DATA_FILE}: {'var' if veri_var else 'yok'} · "
          f"{PUSH_FILE}: {'var' if push_var else 'yok'}")

    for g in liste:
        files = (g or {}).get("files") or {}
        if PUSH_FILE not in files:
            continue
        tam = gh("/gists/" + g["id"], token)          # liste içerikleri kırpabilir
        dosya = tam.get("files") or {}
        def oku(ad):
            f = dosya.get(ad) or {}
            if f.get("truncated") and f.get("raw_url"):
                return requests.get(f["raw_url"], timeout=25).text
            return f.get("content") or ""
        return oku(PUSH_FILE), oku(DATA_FILE)
    return "", ""


def dakika(hhmm):
    s, d = hhmm.split(":")
    return int(s) * 60 + int(d)


def cevaplanmis(veri, gun_anahtari, dilim):
    """Panelde bu dilim zaten işaretlenmişse bildirim gönderilmez."""
    d = (veri or {}).get("data") or {}
    yok = d.get("d:yok:" + gun_anahtari) or {}
    if str(dilim) in yok or dilim in yok:
        return True
    sched = d.get("d:sched:" + gun_anahtari) or {}
    return bool(sched.get(str(dilim)) or sched.get(dilim))


def main():
    token = os.environ.get("PANEL_GIST_TOKEN", "").strip()
    gizli = os.environ.get("VAPID_PRIVATE", "").strip()
    # Hangisinin eksik olduğunu adıyla söyle: kurulum log'a tek bakışta anlaşılsın.
    eksik = [ad for ad, deger in (("PANEL_GIST_TOKEN", token),
                                  ("VAPID_PRIVATE", gizli)) if not deger]
    if eksik:
        print("secret tanımlı değil: " + ", ".join(eksik) + " — atlandı.")
        return 0

    try:
        push_ham, veri_ham = gist_dosyalari(token)
    except Exception as e:
        print(f"gist okunamadı: {e}")
        return 1
    if not push_ham:
        print("panel-push.json bulunamadı — panelden 'Telefon bildirimini kur' yapılmamış.")
        return 0

    push = json.loads(push_ham)
    veri = json.loads(veri_ham) if veri_ham else {}
    subs = push.get("subs") or []
    plan = push.get("plan") or {}
    if not subs:
        print("kayıtlı cihaz yok.")
        return 0

    simdi = dt.datetime.now(IST)
    # JS getDay(): Pazar 0 ... Cumartesi 6
    js_gun = (simdi.weekday() + 1) % 7
    bugun = plan.get(str(js_gun)) or []
    if not bugun:
        print(f"bugün ({js_gun}) için yoklama dilimi yok.")
        return 0

    su_an = simdi.hour * 60 + simdi.minute
    adaylar = [x for x in bugun if -ILERI_DK <= su_an - dakika(x[0]) <= GERI_DK]
    if not adaylar:
        print(f"{simdi:%H:%M} — penceredeki yoklama yok.")
        return 0
    # Birden fazlaysa şu ana en yakını
    saat, ad, dilim = min(adaylar, key=lambda x: abs(su_an - dakika(x[0])))

    gun_anahtari = simdi.strftime("%Y-%m-%d")
    if cevaplanmis(veri, gun_anahtari, dilim):
        print(f"{ad} ({saat}) zaten işaretlenmiş — bildirim gönderilmedi.")
        return 0

    govde = json.dumps({
        "title": ad,
        "body": f"{saat} · başladın mı?",
        "tag": f"yok-{gun_anahtari}-{dilim}",
        "url": "./index.html",
        "icon": "icon-192.png",
    }, ensure_ascii=False)

    basarili, olu = 0, []
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s["endpoint"], "keys": s["keys"]},
                data=govde,
                vapid_private_key=gizli,
                vapid_claims=dict(VAPID_CLAIMS),
                ttl=1800,
            )
            basarili += 1
        except WebPushException as e:
            kod = getattr(e.response, "status_code", None)
            # 404/410: abonelik ölmüş (uygulama silinmiş, izin kaldırılmış)
            if kod in (404, 410):
                olu.append(s.get("endpoint", "")[:40])
            print(f"gönderilemedi ({kod}): {e}")
        except Exception as e:
            print(f"gönderilemedi: {e}")

    print(f"{ad} ({saat}) — {basarili}/{len(subs)} cihaza gönderildi."
          + (f" ölü abonelik: {len(olu)}" if olu else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
