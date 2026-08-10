# -*- coding: utf-8 -*-
"""
panel_feed.py — borsa.py verisinden panel için borsa.json üretir.
MAIL GÖNDERMEZ. Mevcut mail botuna dokunmaz; sadece onun fonksiyonlarını
kullanıp panelin okuduğu borsa.json'u yazar.
Çalıştırma: python panel_feed.py
"""
import json
import datetime as dt
import urllib.request
import xml.etree.ElementTree as ET

import borsa as B          # senin mevcut botun
import config as C         # senin mevcut ayarların

IST = dt.timezone(dt.timedelta(hours=3))


def fetch_world(n=4):
    """Google News Türkiye genel başlıkları — 'Dünya Gündemi' için."""
    url = "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=12).read())
    except Exception:
        return []
    out = []
    for it in root.findall(".//item")[:n]:
        t = it.find("title")
        s = it.find("source")
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

    # İzleme listesi -> {code, price, chg}
    watch_rows = []
    for code in watch:
        if code not in data:
            continue
        m = B.metrics(data[code])
        chg = m["day_chg"]
        watch_rows.append({
            "code": code,
            "price": f"{m['last']:,.2f}",
            "chg": f"{'+' if chg >= 0 else ''}{chg:.2f}%",
        })

    # Haberler (mailde geçen kağıtlar için) -> "🟢 başlık  (kaynak)"
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
        "news": news_items[:8],
        "world": fetch_world(4),
    }


if __name__ == "__main__":
    d = build()
    with open("borsa.json", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"borsa.json yazıldı: {len(d['watch'])} hisse, "
          f"{len(d['news'])} haber, {len(d['world'])} dünya başlığı")
