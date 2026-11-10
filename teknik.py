# -*- coding: utf-8 -*-
"""
teknik.py — günlük fiyat geçmişinden kural tabanlı teknik yorum.

tradermonty/claude-trading-skills içindeki `technical-analyst` yaklaşımından
uyarlandı (trend → ortalamalar → destek/direnç → iki yönlü senaryo), ama
model kullanmıyor: aynı veri her zaman aynı yorumu üretir.

BU BİR YATIRIM TAVSİYESİ DEĞİL. Etiketler ('olası alım' / 'olası satış')
yalnızca aşağıdaki mekanik kuralların toplamıdır; panel ve bildirim bunu
açıkça yazar. Kural eklerken/değiştirirken tests/test_teknik.py'yi güncelle.

PUAN KURALLARI (toplanır)
  trend     : 20g ort > 50g ort ve fiyat > 50g ort  → +1   (tersi -1)
  kesişim   : son KESISIM_GUN içinde 20g, 50g'yi yukarı kesti → +2 (aşağı -2)
  kırılım   : kapanış önceki 20 günün en yükseğinin üstünde ve hacim
              ≥ 1.5× ortalama → +2 (en düşüğün altında → -2). Hacim teyidi
              yoksa ±1.
  RSI       : < 30 aşırı satım +1 · > 70 aşırı alım -1 — AMA trendin
              tersine puan vermez: düşüşteki aşırı satım "düşen bıçak",
              yükselişteki aşırı alım güç işaretidir. O durumda yalnızca
              olay olarak yazılır, puan 0.
  Durum: puan ≥ 2 'olasi_alim', ≤ -2 'olasi_satis', olay varsa 'izle',
  yoksa 'notr'.
"""
import math

KISA, UZUN = 20, 50
KESISIM_GUN = 3
KIRILIM_GUN = 20
HACIM_TEYIT = 1.5
RSI_DUSUK, RSI_YUKSEK = 30, 70

DURUM_AD = {"olasi_alim": "olası alım", "olasi_satis": "olası satış",
            "izle": "izle", "notr": "nötr"}


def _ort(seri, n, son=0):
    """seri[-n-son : -son] ortalaması; yeterli veri yoksa None."""
    bit = len(seri) - son
    if bit < n:
        return None
    parca = seri[bit - n:bit]
    return sum(parca) / n


def _rsi(kapanis, n=14):
    """Wilder RSI. Yetersiz veride None."""
    if len(kapanis) < n + 1:
        return None
    kazanc = kayip = 0.0
    for i in range(1, n + 1):
        d = kapanis[i] - kapanis[i - 1]
        kazanc += max(d, 0)
        kayip += max(-d, 0)
    kazanc /= n
    kayip /= n
    for i in range(n + 1, len(kapanis)):
        d = kapanis[i] - kapanis[i - 1]
        kazanc = (kazanc * (n - 1) + max(d, 0)) / n
        kayip = (kayip * (n - 1) + max(-d, 0)) / n
    if kayip == 0:
        return 100.0
    return 100 - 100 / (1 + kazanc / kayip)


def _fmt(v):
    if v is None:
        return "—"
    return f"{v:,.2f}" if v < 1000 else f"{v:,.0f}"


def analiz(kapanis, hacim=None):
    """kapanis: eskiden yeniye float listesi. hacim: aynı uzunlukta ya da None.

    Döner: {durum, ad, puan, olaylar[], trend, rsi, destek, direnc,
            senaryo{yukari, asagi}, ozet} — veri yetersizse None.
    """
    k = [float(x) for x in kapanis if x is not None and not math.isnan(float(x))]
    if len(k) < UZUN + KESISIM_GUN:
        return None
    son = k[-1]
    puan = 0
    olaylar = []
    kisa = []          # bildirim için kısa etiketler, olaylarla aynı sırada

    # trend
    o_kisa, o_uzun = _ort(k, KISA), _ort(k, UZUN)
    if o_kisa > o_uzun and son > o_uzun:
        trend, puan = "yükseliş", puan + 1
    elif o_kisa < o_uzun and son < o_uzun:
        trend, puan = "düşüş", puan - 1
    else:
        trend = "yatay"

    # kesişim: KESISIM_GUN gün önce ilişki tersti, bugün değişti
    kisa_once, uzun_once = _ort(k, KISA, KESISIM_GUN), _ort(k, UZUN, KESISIM_GUN)
    if kisa_once is not None and uzun_once is not None:
        if kisa_once <= uzun_once and o_kisa > o_uzun:
            puan += 2
            olaylar.append("20 günlük ortalama 50 günlüğü yukarı kesti")
            kisa.append("20/50 kesişim ↑")
        elif kisa_once >= uzun_once and o_kisa < o_uzun:
            puan -= 2
            olaylar.append("20 günlük ortalama 50 günlüğü aşağı kesti")
            kisa.append("20/50 kesişim ↓")

    # kırılım (bugün hariç önceki KIRILIM_GUN gün)
    onceki = k[-KIRILIM_GUN - 1:-1]
    tepe, dip = max(onceki), min(onceki)
    hacim_orani = None
    if hacim and len(hacim) == len(kapanis):
        h = [float(x) for x in hacim if x is not None]
        if len(h) > KIRILIM_GUN and h[-1] > 0:
            ort_h = sum(h[-KIRILIM_GUN - 1:-1]) / KIRILIM_GUN
            hacim_orani = h[-1] / ort_h if ort_h else None
    teyit = hacim_orani is not None and hacim_orani >= HACIM_TEYIT
    hacim_notu = f" (hacim ortalamanın {hacim_orani:.1f} katı)" if teyit else " (hacim teyidi yok)"
    if son > tepe:
        puan += 2 if teyit else 1
        olaylar.append(f"son 20 günün zirvesi {_fmt(tepe)} kırıldı" + hacim_notu)
        kisa.append("zirve kırılımı" + (" (hacimli)" if teyit else ""))
    elif son < dip:
        puan -= 2 if teyit else 1
        olaylar.append(f"son 20 günün dibi {_fmt(dip)} aşağı kırıldı" + hacim_notu)
        kisa.append("dip kırılımı" + (" (hacimli)" if teyit else ""))

    # RSI
    r = _rsi(k)
    if r is not None and r < RSI_DUSUK:
        if trend != "düşüş":
            puan += 1
            olaylar.append(f"RSI {r:.0f} — aşırı satım bölgesi")
            kisa.append(f"RSI {r:.0f}")
        else:
            olaylar.append(f"RSI {r:.0f} — aşırı satım, ama trend düşüşte (dönüş teyidi yok)")
    elif r is not None and r > RSI_YUKSEK:
        if trend != "yükseliş":
            puan -= 1
            olaylar.append(f"RSI {r:.0f} — aşırı alım bölgesi")
            kisa.append(f"RSI {r:.0f}")
        else:
            olaylar.append(f"RSI {r:.0f} — aşırı alım, trend yükselişte (güç işareti)")

    if puan >= 2:
        durum = "olasi_alim"
    elif puan <= -2:
        durum = "olasi_satis"
    elif olaylar:
        durum = "izle"
    else:
        durum = "notr"

    # destek/direnç: kırılım olduysa kırılan seviye yeni destek/direnç olur
    destek = tepe if son > tepe else (min(k[-KIRILIM_GUN:]) if son < dip else dip)
    direnc = dip if son < dip else (max(k[-KIRILIM_GUN:]) if son > tepe else tepe)
    if destek > direnc:
        destek, direnc = direnc, destek

    ozet = f"Trend {trend}"
    if olaylar:
        ozet += " · " + olaylar[0]
    return {
        "durum": durum,
        "ad": DURUM_AD[durum],
        "puan": puan,
        "olaylar": olaylar,
        "kisa": kisa,
        "trend": trend,
        "rsi": round(r, 1) if r is not None else None,
        "destek": round(destek, 2),
        "direnc": round(direnc, 2),
        "senaryo": {
            "yukari": f"{_fmt(direnc)} üstünde kapanış yükselişi teyit eder",
            "asagi": f"{_fmt(destek)} altında kapanış zayıflık işareti",
        },
        "ozet": ozet,
    }
