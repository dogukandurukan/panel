# -*- coding: utf-8 -*-
"""
panel_feed.py — borsa.py verisinden panel için borsa.json üretir.
MAIL GÖNDERMEZ. Mevcut mail botuna dokunmaz.
Çalıştırma: python panel_feed.py
"""
import json
import re
import datetime as dt
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd
import yfinance as yf

import borsa as B          # senin mevcut botun
import config as C         # senin mevcut ayarların

IST = dt.timezone(dt.timedelta(hours=3))

# --- Buraya istediğin ABD hisselerini yaz (5 tane) ---
US_WATCH = ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA"]

# --- Dünya piyasaları: (yfinance kodu, panelde görünen ad) ---
# `world` alani DUNYA HABERI; bu ayri bir sey: endeks/emtia fiyatlari.
WORLD_IDX = [
    ("XU100.IS", "BIST 100"),
    ("^GSPC", "S&P 500"),
    ("^IXIC", "Nasdaq"),
    ("^GDAXI", "DAX"),
    ("BZ=F", "Brent"),
]

# Sparkline icin satir basina tutulan kapanis sayisi (~4.5 ay islem gunu).
HIST_GUN = 90


def _fmt(v):
    return f"{v:,.2f}" if v is not None and not pd.isna(v) else "—"


def _hist(df):
    """Sparkline serisi: son HIST_GUN kapanis. Veri yoksa alan hic yazilmaz —
    panel `hist` gormezse grafik cizmiyor (uydurma seri yok)."""
    if df is None or "Close" not in df:
        return None
    vals = [round(float(v), 2) for v in df["Close"].tail(HIST_GUN)
            if v is not None and not pd.isna(v)]
    return vals if len(vals) >= 5 else None


def _ind(m):
    """metrics() zaten hesapliyordu, panele hic tasinmamisti. Esikler burada
    kalsin diye etiketler borsa.py'nin kendi fonksiyonlarindan uretiliyor."""
    d = {"ma": B.ma_label(m), "rsiTxt": B.rsi_label(m["rsi"])}
    if not pd.isna(m["rsi"]):
        d["rsi"] = round(float(m["rsi"]), 1)
    if not pd.isna(m["volat"]):
        d["volat"] = round(float(m["volat"]), 1)
    if not pd.isna(m["vol_ratio"]) and m["vol_ratio"] > 0:
        d["volRatio"] = round(float(m["vol_ratio"]), 2)
    return d


def _row(code, m, df=None, ad=None):
    chg = m["day_chg"]
    r = {
        "code": code,
        "price": _fmt(m["last"]),
        "chg": f"{'+' if chg >= 0 else ''}{chg:.2f}%",
        "avg1w": _fmt(m["avg_1w"]),
        "avg1m": _fmt(m["avg_1m"]),
    }
    if ad:
        r["name"] = ad
    h = _hist(df)
    if h:
        r["hist"] = h
    r["ind"] = _ind(m)
    return r


def download_plain(codes):
    """ABD kodları için (.IS eki OLMADAN) günlük geçmiş indir."""
    if not codes:
        return {}
    raw = yf.download(codes, period="8mo", interval="1d", group_by="ticker",
                      auto_adjust=False, progress=False, threads=True)
    out = {}
    for c in codes:
        try:
            df = raw[c] if len(codes) > 1 else raw
            df = df.dropna(subset=["Close"])
            if not df.empty:
                out[c] = df
        except Exception:
            pass
    return out


def fetch_gold():
    """Gram altın (TL) ~ (ons altın USD / 31.1035) x USDTRY."""
    try:
        g = yf.download("GC=F", period="7d", interval="1d",
                        auto_adjust=False, progress=False)["Close"].squeeze().dropna()
        fx = yf.download("USDTRY=X", period="7d", interval="1d",
                         auto_adjust=False, progress=False)["Close"].squeeze().dropna()
        gram_last = float(g.iloc[-1]) / 31.1035 * float(fx.iloc[-1])
        gram_prev = float(g.iloc[-2]) / 31.1035 * float(fx.iloc[-2])
        chg = (gram_last / gram_prev - 1) * 100
        return {"price": f"{gram_last:,.2f}",
                "chg": f"{'+' if chg >= 0 else ''}{chg:.2f}%"}
    except Exception:
        return None


# ===== DÜNYA GÜNDEMİ =====
# Eskiden Google News Türkiye'nin GENEL akışı çekiliyordu; "Dünya Gündemi"
# başlığı altına FAST işlem limiti, kandil takvimi ve yurt içi asayiş düşüyordu.
# Kaynak yanlıştı: genel akış yerel manşet akışıdır. Artık doğrudan dış haber
# servislerinin dünya bölümleri okunuyor. Hepsi anahtarsız RSS.
WORLD_FEEDS = [
    # Dünya bölümleri — genel akış değil. Türkçe kaynakların genel akışı
    # yurt içi manşetle doluyor, o yüzden ağırlık dış servislerin world
    # bölümlerinde; Türkçe olanlar dengeyi kuruyor.
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Guardian World", "https://www.theguardian.com/world/rss"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
    # Türkçe kaynaklarda genel akış yurt içi manşetle doluyor; bu ikisi
    # dünya/Avrupa ağırlıklı. BBC Türkçe genel akışı bu yüzden çıkarıldı.
    ("Euronews", "https://tr.euronews.com/rss?level=theme&name=news"),
    ("DW Türkçe", "https://rss.dw.com/rdf/rss-tur-all"),
]
# Tek kaynak listeyi doldurmasın
KAYNAK_BASI_MAX = 2

# Kaynak başına teşhis. Actions log'unun kuyruğu Python çıktısını kesebiliyor,
# bu yüzden teşhis borsa.json'a da yazılıyor: hangi kaynak kaç öğe verdi, kaçı
# elendi, ham başlık neydi. Panel bunu okumuyor; sorun ayıklamak için.
TESHIS = []

# Manşet gibi görünüp haber taşımayan kalıplar. Hisse akışında da aynı süzgeç
# çalışıyor: oradaki gürültü büyük ölçüde KAP bildirimi ve etiket yığını.
COP_KALIP = (
    "kandil", "burç", "hava durumu", "namaz vakti", "iftar", "sahur",
    "maç kaç kaç", "canlı anlatım", "puan durumu", "ne zaman, saat kaçta",
    "işte o anlar", "sosyal medya yıkıldı", "olay yarattı", "şoke etti",
    "bomba iddia", "son dakika haberi:", "tıkla öğren", "işte detaylar",
    "kaçıncı bölüm", "fragman", "çekiliş", "zam geldi mi",
)
# Hisse haberlerine özgü gürültü
COP_HISSE = ("hisse #", "#hisse", "game informer")


def _kucult(metin):
    """Türkçe güvenli küçültme.

    Python'un lower()'ı 'İ' harfini 'i' + birleşen nokta (U+0307) olarak
    çeviriyor; bu yüzden 'İlişkin' içeren bir başlıkta 'ilişkin' kalıbı
    eşleşmiyor ve süzgeç sessizce boşa çalışıyordu.
    """
    return (metin or "").replace("İ", "i").replace("I", "ı").lower()


def _cop_mu(baslik, ekstra=()):
    """Manşet gerçekten haber mi, tıklama yemi mi?"""
    d = _kucult(baslik)
    # Uzunluk eşiği 25 karakterdi ve "SASA'dan SPK başvurusu" gibi meşru
    # manşetleri eliyordu. Ölçü karakter değil kelime: iki kelimeden kısa
    # başlık haber değil, etiket yığınıdır.
    if len(d) < 12 or len(d.split()) < 3:
        return True
    if d.count("#") >= 2:                 # #ALARK #HISSE #HEDEF ...
        return True
    if sum(1 for c in baslik if c.isupper()) > len(baslik) * 0.6:
        return True                       # TAMAMI BÜYÜK HARF
    return any(k in d for k in COP_KALIP + tuple(ekstra))


def _kap_bildirimi(baslik):
    """KAP duyuruları haber değil, zorunlu bildirim. Tek bir cümleyi aramak
    yetmiyordu — biçim sabit: 'KAP *** ŞİRKET *** KOD *** <bildirim türü>'."""
    d = _kucult(baslik)
    return d.startswith("kap ") or "***" in baslik or "i̇lişkin bildirim" in d \
        or "ilişkin bildirim" in d or "özel durum açıklaması" in d


def _rss_basliklar(url, n, ad=""):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        ham = urllib.request.urlopen(req, timeout=12).read()
        root = ET.fromstring(ham)
    except Exception as e:
        TESHIS.append(f"{ad or url}: OKUNAMADI {type(e).__name__}: {str(e)[:70]}")
        return []
    # RSS 2.0 (item) ve RDF/RSS 1.0 (rdf:item) birlikte
    # RSS 2.0 (item), RDF/RSS 1.0 (rdf:item) ve Atom (entry) birlikte
    ogeler = (root.findall(".//item")
              or root.findall(".//{http://purl.org/rss/1.0/}item")
              or root.findall(".//{http://www.w3.org/2005/Atom}entry"))
    out, elendi, ilk_ham = [], 0, ""
    for it in ogeler:
        # DİKKAT: 'a or b' burada çalışmaz. ElementTree'de çocuğu olmayan bir
        # Element falsy sayılır, <title> de çocuksuzdur — 'or' onu atlayıp
        # None'a düşer ve HER kaynak sessizce boş döner. Açıkça None kontrolü.
        t = None
        for etiket in ("title",
                       "{http://purl.org/rss/1.0/}title",
                       "{http://www.w3.org/2005/Atom}title"):
            bulunan = it.find(etiket)
            if bulunan is not None and bulunan.text:
                t = bulunan
                break
        if t is None:
            continue
        baslik = " ".join(t.text.split())
        if not ilk_ham:
            ilk_ham = baslik
        if _cop_mu(baslik):
            elendi += 1
            continue
        out.append(baslik)
        if len(out) >= n:
            break
    TESHIS.append(f"{ad or url}: {len(ogeler)} öğe / {len(out)} alındı / "
                  f"{elendi} elendi" + (f" | ilk: {ilk_ham[:60]}" if ilk_ham else ""))
    return out


def _benzer(a, b):
    """Aynı olayın iki kaynaktaki hâli: kelime örtüşmesi yüksekse tekrar sayılır."""
    ka = {w for w in _kucult(a).split() if len(w) > 4}
    kb = {w for w in _kucult(b).split() if len(w) > 4}
    if not ka or not kb:
        return False
    return len(ka & kb) / min(len(ka), len(kb)) > 0.6


def fetch_world(n=6):
    """Her kaynaktan en fazla KAYNAK_BASI_MAX haber; dönüşümlü harmanlanır."""
    kaynak = {}
    for ad, url in WORLD_FEEDS:
        kaynak[ad] = _rss_basliklar(url, KAYNAK_BASI_MAX, ad)

    out = []
    for tur in range(KAYNAK_BASI_MAX):          # önce herkesin 1., sonra 2.'si
        for ad, _ in WORLD_FEEDS:
            if tur >= len(kaynak.get(ad, [])):
                continue
            baslik = kaynak[ad][tur]
            if any(_benzer(baslik, b) for _, b in out):
                continue
            out.append((ad, baslik))
            if len(out) >= n:
                break
        if len(out) >= n:
            break

    calisan = sorted({a for a, _ in out})
    olu = [ad for ad, _ in WORLD_FEEDS if not kaynak.get(ad)]
    ozet = (f"SONUÇ: {len(out)} haber · veren: {', '.join(calisan) or 'yok'}"
            + (f" · boş dönen: {', '.join(olu)}" if olu else ""))
    TESHIS.append(ozet)
    print("  " + ozet)
    return [f"🌍 {b}  ({a})" for a, b in out]

def build():
    codes = list(dict.fromkeys(
        [h[0] for h in C.HOLDINGS] + list(C.WATCHLIST) + list(C.UNIVERSE)))
    data = B.download(codes)

    watch = (B.pick_dynamic_watchlist(data)
             if getattr(C, "DYNAMIC_WATCHLIST", False) else list(C.WATCHLIST))

    # BIST izleme listesi (+ ortalamalar)
    watch_rows = [_row(code, B.metrics(data[code]), data[code])
                  for code in watch if code in data]

    # ABD hisseleri
    usdata = download_plain(US_WATCH)
    us_rows = [_row(code, B.metrics(usdata[code]), usdata[code])
               for code in US_WATCH if code in usdata]

    # Dünya piyasaları (endeks + emtia)
    idxdata = download_plain([c for c, _ in WORLD_IDX])
    idx_rows = [_row(code, B.metrics(idxdata[code]), idxdata[code], ad)
                for code, ad in WORLD_IDX if code in idxdata]

    # Haberler
    mentioned = B.pick_dynamic_watchlist(data, n=99, per_cat=C.TOP_N)
    news_codes = [h[0] for h in C.HOLDINGS] + list(watch) + mentioned
    news_items, seen = [], set()
    hisse_ham, hisse_elenen = [], 0
    for code in news_codes:
        if code in seen:
            continue
        seen.add(code)
        for title, src, rel, link in B.fetch_news(
                code, getattr(C, "NEWS_PER_STOCK", 2),
                getattr(C, "NEWS_MAX_AGE_DAYS", 3)):
            # Hisse akışı etiket yığını ve KAP bildirimiyle doluyordu
            hisse_ham.append(title[:70])
            if _cop_mu(title, COP_HISSE) or _kap_bildirimi(title):
                hisse_elenen += 1
                continue
            emoji, _ = B.news_tone(title)
            news_items.append(f"{emoji} {title}" + (f"  ({src})" if src else ""))
        if len(news_items) >= 8:
            break

    dunya = fetch_world(6)

    return {
        "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "watch": watch_rows,
        "us": us_rows,
        "world_idx": idx_rows,
        "gold": fetch_gold(),
        "news": news_items[:8],
        "world": dunya,
        "_teshis": {
            "dunya": TESHIS,
            "hisse": f"{len(hisse_ham)} başlık geldi, {hisse_elenen} elendi",
            "hisse_ham": hisse_ham[:6],
        },
    }


if __name__ == "__main__":
    d = build()
    metin = json.dumps(d, ensure_ascii=False, indent=2)
    # indent=2 her `hist` sayisini ayri satira aliyor: dosya 7 katina cikiyor.
    # Yalnizca sayi iceren diziler tek satira toplaniyor (okunurluk kaybi yok).
    metin = re.sub(r"\[\s+((?:-?\d+(?:\.\d+)?,\s+)+-?\d+(?:\.\d+)?)\s+\]",
                   lambda m: "[" + re.sub(r"\s+", " ", m.group(1)) + "]", metin)
    with open("borsa.json", "w", encoding="utf-8") as f:
        f.write(metin + "\n")
    seri = sum(1 for r in d["watch"] + d["us"] + d["world_idx"] if r.get("hist"))
    print(f"borsa.json: {len(d['watch'])} BIST, {len(d['us'])} ABD, "
          f"{len(d['world_idx'])} endeks, {seri} seri, "
          f"altın={'var' if d['gold'] else 'yok'}, {len(d['news'])} haber, {len(d['world'])} dünya")
