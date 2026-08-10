# -*- coding: utf-8 -*-
"""
panel_feed.py — borsa.py verisinden panel için borsa.json üretir.
MAIL GÖNDERMEZ. Mevcut mail botuna dokunmaz.
Çalıştırma: python panel_feed.py
"""
import json
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


def _fmt(v):
    return f"{v:,.2f}" if v is not None and not pd.isna(v) else "—"


def _row(code, m):
    chg = m["day_chg"]
    return {
        "code": code,
        "price": _fmt(m["last"]),
        "chg": f"{'+' if chg >= 0 else ''}{chg:.2f}%",
        "avg1w": _fmt(m["avg_1w"]),
        "avg1m": _fmt(m["avg_1m"]),
    }


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


def fetch_world(n=4):
    url = "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=12).read())
    except Exception:
        return []
    out = []
    for it in root.findall(".//item")[:n]:
        t = it.find("title"); s = it.find("source")
        if t is None or not t.text:
            continue
        src = s.text if s is not None and s.text else ""
        out.append("🌍 " + t.text + (f"  ({src})" if src else ""))
    return out


def build():
    codes = list(dict.fromkeys(
        [h[0] for h in C.HOLDINGS] + list(C.WATCHLIST) + list(C.UNIVERSE)))
    data = B.download(codes)

    watch = (B.pick_dynamic_watchlist(data)
             if getattr(C, "DYNAMIC_WATCHLIST", False) else list(C.WATCHLIST))

    # BIST izleme listesi (+ ortalamalar)
    watch_rows = [_row(code, B.metrics(data[code])) for code in watch if code in data]

    # ABD hisseleri
    usdata = download_plain(US_WATCH)
    us_rows = [_row(code, B.metrics(usdata[code])) for code in US_WATCH if code in usdata]

    # Haberler
    mentioned = B.pick_dynamic_watchlist(data, n=99, per_cat=C.TOP_N)
    news_codes = [h[0] for h in C.HOLDINGS] + list(watch) + mentioned
    news_items, seen = [], set()
    for code in news_codes:
        if code in seen:
            continue
        seen.add(code)
        for title, src, rel, link in B.fetch_news(
                code, getattr(C, "NEWS_PER_STOCK", 2),
                getattr(C, "NEWS_MAX_AGE_DAYS", 3)):
            emoji, _ = B.news_tone(title)
            news_items.append(f"{emoji} {title}" + (f"  ({src})" if src else ""))
        if len(news_items) >= 8:
            break

    return {
        "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "watch": watch_rows,
        "us": us_rows,
        "gold": fetch_gold(),
        "news": news_items[:8],
        "world": fetch_world(4),
    }


if __name__ == "__main__":
    d = build()
    with open("borsa.json", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"borsa.json: {len(d['watch'])} BIST, {len(d['us'])} ABD, "
          f"altın={'var' if d['gold'] else 'yok'}, {len(d['news'])} haber, {len(d['world'])} dünya")
