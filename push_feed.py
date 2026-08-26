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
  CRON             : tetikleyen cron ifadesi (github.event.schedule) — hangi
                     dilim için kurulduğunu kesinleştirir, boşsa tahmine düşer

Çalıştırma: python push_feed.py
"""
import datetime as dt
import json
import os
import sys
import time

import requests
from pywebpush import webpush, WebPushException

IST = dt.timezone(dt.timedelta(hours=3))
GITHUB_API = "https://api.github.com"
PUSH_FILE = "panel-push.json"
DATA_FILE = "panel-data.json"

# ZAMANLAMA — cron erken kalkar, betik dilim saatine kadar bekler
# ---------------------------------------------------------------
# GitHub Actions cron'u rutin olarak 30-40 dk gecikiyor (25 Ağustos: 18:30
# cron'u 19:06'da çalıştı). Pencereyi 120 dk'ya açmak bildirimin GELMESİNİ
# sağladı ama ZAMANINDA gelmesini sağlamadı: 12:15 antrenman hatırlatması
# 13:40'ta düşüyordu, ki o saatte hatırlatmanın anlamı kalmıyor.
#
# Çözüm iki parçalı:
#   1. Cron'lar dilimden ONCE_DK kadar ÖNCE kuruldu (push.yml).
#   2. Betik erken uyandıysa dilim saatine kadar UYUR, sonra gönderir.
# Böylece gecikmeyen bir koşuda bildirim erken değil TAM SAATİNDE düşer;
# gecikmiş bir koşuda ise uyku atlanır, bildirim hemen gider.
# Bedeli boşta bekleyen runner dakikası — depo public, Actions ücretsiz.
#
# GERI_DK 120'den 45'e İNDİ. 120 "her hâlükârda gelsin" içindi; artık cron
# 35 dk önden kalktığı için 45 dk'lık pay 80 dk'lık gerçek gecikmeyi karşılıyor.
# Daha fazla gecikmişse bildirim GÖNDERİLMİYOR: 1.5 saat geç gelen "başladın
# mı?" hatırlatma değil, gürültü.
#
# Pencere ayrıca bir sonraki dilim başlayınca kapanıyor — geç kalan bildirim
# asla sıradaki işin üstüne binmiyor.
ONCE_DK = 35        # cron'lar dilimden bu kadar önce kuruldu (push.yml ile AYNI olmalı)
GERI_DK = 45
ILERI_DK = ONCE_DK + 5   # erken kalkan cron pencereye girsin (5 dk cron sapma payı)

# VAPID 'sub' iddiası — iki kere tökezledi, ikisi de log'dan çıktı:
#   1. 'mailto:panel@localhost' → Apple 403 BadJwtToken. localhost geçerli bir
#      alan adı değil, Apple bunu doğruluyor.
#   2. 'https://...' → pywebpush kendi doğrulamasında reddetti: RFC 8292 https'e
#      izin verse de kütüphane ısrarla mailto: istiyor.
# Bu yüzden geçerli bir mailto şart. Depo herkese açık olduğundan kişisel
# e-posta buraya YAZILMAZ (1. kural): varsayılan kişisel olmayan bir adres,
# gerekirse VAPID_SUB secret'ıyla değiştirilir.
VAPID_SUB_VARSAYILAN = "mailto:panel@dogukandurukan.github.io"

# Bildirime dokununca panelin NERESİNE düşsün — yoklama türüne göre.
# "Antrenmana başladın mı?"ya dokunan kişi hangi hareketi kaç kg yapacağını
# arıyor; paneli açıp sayfanın başında bırakmak işe yaramıyordu.
# Yalnızca bu iki tür hedef taşıyor; kalanlar paneli olduğu gibi açıyor.
# Karşılığı index.html'deki BILDIRIM_HEDEF haritasında.
HEDEF_KART = {"spor": "#antrenman", "rutin": "#rutin"}


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


def cron_dilimi(bugun, plan):
    """Bu koşuyu tetikleyen cron hangi dilim için kurulmuştu? (indeks ya da None)

    NEDEN: cron'lar ONCE_DK kadar önden kalkıyor, yani iki dilim birbirine
    ONCE_DK'dan yakınsa (23:00 ve 23:30 gibi) "şu ana en yakın dilim" tahmini
    iki koşuyu da aynı dilime yönlendirip bildirimi ikizleyebiliyor. GitHub
    `github.event.schedule` ile tetikleyen cron ifadesini veriyor; tahmin
    yerine onu kullanınca eşleşme kesin oluyor ve ikiz bildirim imkânsız.

    Elle çalıştırmada (workflow_dispatch) bu değişken boş; o zaman None döner
    ve eski "pencereye düşen en yakın dilim" mantığı devreye girer.
    """
    ifade = os.environ.get("CRON", "").strip()
    if not ifade:
        return None
    parca = ifade.split()
    if len(parca) < 2:
        return None
    try:
        dk_utc, sa_utc = int(parca[0]), int(parca[1])
    except ValueError:
        return None
    # cron UTC → TR (+3sa) → hedeflenen dilim (+ONCE_DK)
    hedef_dk = (sa_utc * 60 + dk_utc + 180 + ONCE_DK) % 1440
    for i, x in enumerate(bugun):
        if dakika(x[0]) == hedef_dk:
            return i
    # Bulunamadı. İki ayrı sebep var, karıştırılmasın:
    #   NORMAL — cron her gün kalkıyor ama o dilim bugün yok (12:15 antrenman
    #            cron'u Perşembe kalkar, Perşembe "Dinlenme + uyku" ve yoklama
    #            sorulmaz). Sessiz geçilir.
    #   ARIZA  — dilim hiçbir günde yok, yani push.yml programdan ayrışmış.
    #            Bu sessiz kalırsa bildirim aylarca yanlış saatte gelir.
    if not any(dakika(x[0]) == hedef_dk for gun in plan.values() for x in (gun or [])):
        print(f"uyarı: '{ifade}' cron'u hiçbir gündeki dilime denk gelmiyor "
              "(push.yml ile index.html'deki program ayrışmış).")
        return "ARIZA"
    return "BUGUN_YOK"


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

    # 403 BadJwtToken iki ayrı sebepten gelebiliyor: bozuk iddia ya da secret'taki
    # gizli anahtarın aboneliğin açık anahtarıyla eşleşmemesi. Ayırt etmek için
    # gizli anahtardan açık anahtarı türetip gist'tekiyle karşılaştır.
    kayitli = push.get("vapidPublic") or ""
    if kayitli:
        try:
            import base64
            from py_vapid import Vapid02
            from cryptography.hazmat.primitives import serialization
            ham = Vapid02.from_string(private_key=gizli).public_key.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint)
            turetilen = base64.urlsafe_b64encode(ham).rstrip(b"=").decode()
            if turetilen == kayitli:
                print("anahtar kontrolü: secret abonelikle EŞLEŞİYOR.")
            else:
                print("anahtar kontrolü: EŞLEŞMİYOR — VAPID_PRIVATE secret'ı "
                      "aboneliğin açık anahtarına ait değil. Panelde bildirimi "
                      "kaldırıp yeniden kurmak ya da doğru gizli anahtarı "
                      "yazmak gerekiyor.")
        except Exception as e:
            print(f"anahtar kontrolü yapılamadı: {type(e).__name__}: {e}")

    simdi = dt.datetime.now(IST)
    # JS getDay(): Pazar 0 ... Cumartesi 6
    js_gun = (simdi.weekday() + 1) % 7
    bugun = plan.get(str(js_gun)) or []
    if not bugun:
        print(f"bugün ({js_gun}) için yoklama dilimi yok.")
        return 0

    su_an = simdi.hour * 60 + simdi.minute
    # ZORLA: pencereyi ve "zaten işaretlenmiş" kontrolünü atlar. Zinciri
    # gerçek bir yoklama saatini beklemeden denemek için; günün en yakın
    # dilimini seçer.
    zorla = os.environ.get("ZORLA", "").strip().lower() in ("1", "true", "yes")
    def pencerede(i):
        bas = dakika(bugun[i][0])
        son = bas + GERI_DK
        if i + 1 < len(bugun):                 # sıradaki iş başlayınca kapan
            son = min(son, dakika(bugun[i + 1][0]))
        return bas - ILERI_DK <= su_an <= son

    hedef = None if zorla else cron_dilimi(bugun, plan)
    if hedef == "BUGUN_YOK":
        # Bu cron her gün kalkıyor ama hedeflediği dilim bugün yok (12:15
        # antrenman cron'u Perşembe de kalkar, o gün antrenman yok).
        # TAHMİNE DÜŞÜLMEZ: 25 Ağustos'ta tam bu yüzden çift bildirim gitti —
        # 08:30 cron'u Çarşamba kalkıp "en yakın dilim" diye 08:00'i seçti ve
        # 08:00 cron'unun gönderdiğini ikinci kez gönderdi (08:40 + 08:58).
        print(f"{simdi:%H:%M} — bu cron'un dilimi bugün programda yok, "
              "yapılacak bir şey yok.")
        return 0
    if hedef == "ARIZA":
        hedef = None                      # program ayrışmış; tahmin son çare
    if hedef is not None:
        # Tetikleyen cron biliniyor: tahmin yok, dilim kesin.
        if not pencerede(hedef):
            gec = su_an - dakika(bugun[hedef][0])
            print(f"{simdi:%H:%M} — {bugun[hedef][0]} dilimi için kurulan cron "
                  f"{gec} dk gecikmeyle çalıştı; pencere ({GERI_DK} dk) kapanmış, "
                  "bildirim gönderilmedi. Bu saatte hatırlatmanın faydası yok.")
            return 0
        adaylar = [bugun[hedef]]
    else:
        adaylar = bugun if zorla else [x for i, x in enumerate(bugun) if pencerede(i)]
    if not adaylar:
        sonraki = [x[0] for x in bugun if dakika(x[0]) > su_an]
        print(f"{simdi:%H:%M} — penceredeki yoklama yok."
              + (f" Sıradaki dilim {sonraki[0]}." if sonraki else " Günün dilimleri bitti."))
        return 0
    # Birden fazlaysa şu ana en yakını.
    # Satır [saat, ad, dilim] ya da [saat, ad, dilim, tür]: tür panele sonradan
    # eklendi ve gist'teki plan ancak kullanıcı paneli açınca tazeleniyor,
    # o yüzden dördüncü alan OPSİYONEL okunuyor.
    secilen = min(adaylar, key=lambda x: abs(su_an - dakika(x[0])))
    saat, ad, dilim = secilen[0], secilen[1], secilen[2]
    tur = secilen[3] if len(secilen) > 3 else ""

    gun_anahtari = simdi.strftime("%Y-%m-%d")
    if zorla:
        print(f"ZORLA açık — pencere ve işaret kontrolü atlandı.")
    elif cevaplanmis(veri, gun_anahtari, dilim):
        print(f"{ad} ({saat}) zaten işaretlenmiş — bildirim gönderilmedi.")
        return 0

    # --- dilim saatine kadar bekle -------------------------------------
    # Cron ONCE_DK önden kalkıyor. Gecikmediyse burada erkeniz; bildirimi
    # şimdi atmak "30 dk erken" demek olurdu, o yüzden dilim saatini bekliyoruz.
    # Gecikmişse bekle 0/negatif çıkar ve uyku hiç çalışmaz.
    bekle = dakika(saat) - su_an
    if zorla:
        bekle = 0
    if bekle > 0:
        # Emniyet kemeri: sapmış bir cron yüzünden saatlerce runner tutmayalım.
        bekle = min(bekle, ILERI_DK)
        print(f"{simdi:%H:%M} — {saat} dilimi için erken uyandık, "
              f"{bekle} dk beklenip tam saatinde gönderilecek.")
        time.sleep(bekle * 60)
        # Uyurken kullanıcı paneli açıp işi işaretlemiş olabilir: gist'i
        # yeniden okuyup son bir kez bak. Okunamazsa bildirimi yutma, gönder.
        try:
            _, veri_ham2 = gist_dosyalari(token)
            veri2 = json.loads(veri_ham2) if veri_ham2 else {}
            if cevaplanmis(veri2, gun_anahtari, dilim):
                print(f"{ad} ({saat}) beklerken işaretlendi — bildirim gönderilmedi.")
                return 0
        except Exception as e:
            print(f"uyku sonrası kontrol yapılamadı ({e}) — bildirim yine de gönderiliyor.")

    sub = os.environ.get("VAPID_SUB", "").strip() or VAPID_SUB_VARSAYILAN
    if not sub.startswith("mailto:"):
        sub = "mailto:" + sub
    vapid_claims = {"sub": sub}

    govde = json.dumps({
        "title": ad,
        "body": f"{saat} · başladın mı?",
        "tag": f"yok-{gun_anahtari}-{dilim}",
        "url": "./index.html" + HEDEF_KART.get(tur, ""),
        "icon": "icon-192.png",
    }, ensure_ascii=False)

    basarili, olu = 0, []
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s["endpoint"], "keys": s["keys"]},
                data=govde,
                vapid_private_key=gizli,
                vapid_claims=dict(vapid_claims),
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
