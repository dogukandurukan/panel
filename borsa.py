# -*- coding: utf-8 -*-
"""
BORSA BİLDİRİM SİSTEMİ — çekirdek
=================================
Kullanım:
    python borsa.py morning        # 09:00 maili (piyasa öncesi özet + tarama)
    python borsa.py noon           # 12:30 maili (gün içi durum)
    python borsa.py close          # 16:30 maili (kapanış özeti)
    python borsa.py preview close  # mail GÖNDERMEDEN sadece HTML dosyası üret

Bu sistem TAVSİYE VERMEZ. Objektif piyasa verisi + standart teknik gösterge
sunar. Al/sat kararı kullanıcınındır.
"""

import sys
import ssl
import os
import smtplib
import datetime as dt
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

import numpy as np
import pandas as pd
import yfinance as yf

import config as C

IST = dt.timezone(dt.timedelta(hours=3))  # Türkiye saati

# Kod -> şirket adı (haber aramasını isabetli yapmak için)
NAMES = {
    "THYAO": "Türk Hava Yolları", "ASELS": "Aselsan", "GARAN": "Garanti BBVA",
    "AKBNK": "Akbank", "ISCTR": "İş Bankası", "YKBNK": "Yapı Kredi",
    "SISE": "Şişecam", "EREGL": "Ereğli Demir Çelik", "KCHOL": "Koç Holding",
    "SAHOL": "Sabancı Holding", "BIMAS": "BİM Mağazalar", "FROTO": "Ford Otosan",
    "TUPRS": "Tüpraş", "PGSUS": "Pegasus", "TOASO": "Tofaş", "PETKM": "Petkim",
    "SASA": "Sasa Polyester", "HEKTS": "Hektaş", "TCELL": "Turkcell",
    "TTKOM": "Türk Telekom", "ENKAI": "Enka İnşaat", "ARCLK": "Arçelik",
    "VESTL": "Vestel", "TAVHL": "TAV Havalimanları", "OYAKC": "Oyak Çimento",
    "GUBRF": "Gübretaş", "ALARK": "Alarko Holding", "MGROS": "Migros",
    "ASTOR": "Astor Enerji", "TSKB": "TSKB", "DOAS": "Doğuş Otomotiv",
    "ODAS": "Odaş Elektrik", "SMRTG": "Smart Güneş", "EKGYO": "Emlak Konut",
    "KONTR": "Kontrolmatik", "YEOTK": "Yeo Teknoloji",
}


# ---------------------------------------------------------------------------
# Veri & göstergeler
# ---------------------------------------------------------------------------
def _t(code: str) -> str:
    """BIST kodunu yfinance formatına çevir (THYAO -> THYAO.IS)."""
    code = code.strip().upper()
    return code if code.endswith(".IS") else code + ".IS"


def rsi(series: pd.Series, period: int) -> float:
    """Wilder RSI — son değeri döndürür."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    val = out.iloc[-1]
    return float(val) if pd.notna(val) else float("nan")


def download(codes):
    """Bir liste kod için günlük geçmişi indir. {kod: DataFrame} döndürür."""
    tickers = [_t(c) for c in codes]
    if not tickers:
        return {}
    raw = yf.download(
        tickers, period="8mo", interval="1d",
        group_by="ticker", auto_adjust=False, progress=False, threads=True,
    )
    out = {}
    for c in codes:
        t = _t(c)
        try:
            df = raw[t] if len(tickers) > 1 else raw
            df = df.dropna(subset=["Close"])
            if not df.empty:
                out[c] = df
        except Exception:
            pass
    return out


def metrics(df: pd.DataFrame) -> dict:
    """Bir kağıdın son göstergeleri."""
    close = df["Close"]
    vol = df["Volume"]
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else last
    day_chg = (last / prev - 1) * 100 if prev else 0.0

    # haftalık (~5 işlem günü)
    wk_ref = float(close.iloc[-6]) if len(close) > 5 else prev
    wk_chg = (last / wk_ref - 1) * 100 if wk_ref else 0.0

    ma_s = float(close.rolling(C.MA_SHORT).mean().iloc[-1]) if len(close) >= C.MA_SHORT else float("nan")
    ma_l = float(close.rolling(C.MA_LONG).mean().iloc[-1]) if len(close) >= C.MA_LONG else float("nan")

    last_vol = float(vol.iloc[-1])
    avg_vol = float(vol.rolling(20).mean().iloc[-1]) if len(vol) >= 20 else float(vol.mean())
    vol_ratio = last_vol / avg_vol if avg_vol else float("nan")

    # volatilite: son 14 günlük getirilerin std'si (%)
    rets = close.pct_change().dropna()
    volat = float(rets.tail(14).std() * 100) if len(rets) >= 5 else float("nan")

    # dönem ortalamaları (fiyat referansı)
    def _avg(k):
        return float(close.tail(k).mean()) if len(close) else float("nan")
    avg_1w = _avg(5)      # ~geçen hafta
    avg_1m = _avg(21)     # ~son 1 ay
    avg_6m = _avg(126)    # ~son 6 ay

    return {
        "last": last, "day_chg": day_chg, "wk_chg": wk_chg,
        "ma_s": ma_s, "ma_l": ma_l, "rsi": rsi(close, C.RSI_PERIOD),
        "last_vol": last_vol, "avg_vol": avg_vol, "vol_ratio": vol_ratio,
        "volat": volat, "avg_1w": avg_1w, "avg_1m": avg_1m, "avg_6m": avg_6m,
    }


def rsi_label(v):
    if pd.isna(v):
        return "—"
    if v >= 70:
        return "aşırı alım"
    if v <= 30:
        return "aşırı satım"
    return "nötr"


def condition_flags(m):
    """Göstergeleri OKUNUR DURUM etiketlerine çevirir. TAVSİYE DEĞİL — sadece
    verinin ne durumda olduğunu düz Türkçeyle söyler (AL/SAT demez)."""
    flags = []
    vr = m["vol_ratio"]
    if not pd.isna(vr):
        if vr >= 3:
            flags.append("🔊 hacim patlaması")
        elif vr >= 1.5:
            flags.append("🔊 hacim yüksek")
    last, ma_s, ma_l = m["last"], m["ma_s"], m["ma_l"]
    if not pd.isna(ma_s) and not pd.isna(ma_l):
        if last > ma_s > ma_l:
            flags.append("📈 yukarı trend")
        elif last < ma_s < ma_l:
            flags.append("📉 aşağı trend")
    rsi_v = m["rsi"]
    if not pd.isna(rsi_v):
        if rsi_v >= 70:
            flags.append("🔴 aşırı alım")
        elif rsi_v <= 30:
            flags.append("🟢 aşırı satım")
    if not pd.isna(m["volat"]) and m["volat"] >= 6:
        flags.append("🎢 çok volatil")
    return " · ".join(flags[:3]) if flags else "—"


def ma_label(m):
    """Fiyat MA'ların neresinde?"""
    last = m["last"]
    if not pd.isna(m["ma_s"]) and not pd.isna(m["ma_l"]):
        if last > m["ma_s"] > m["ma_l"]:
            return "MA20 & MA50 üstünde (yukarı eğilim)"
        if last < m["ma_s"] < m["ma_l"]:
            return "MA20 & MA50 altında (aşağı eğilim)"
    if not pd.isna(m["ma_s"]):
        return "MA20 üstünde" if last > m["ma_s"] else "MA20 altında"
    return "—"


# ---------------------------------------------------------------------------
# HTML parçaları
# ---------------------------------------------------------------------------
def _num(v, suf="", dp=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"{v:,.{dp}f}{suf}"


def _chg(v):
    """Renkli yüzde değişim."""
    if pd.isna(v):
        return '<span style="color:#888">—</span>'
    color = "#137333" if v > 0 else ("#c5221f" if v < 0 else "#666")
    sign = "+" if v > 0 else ""
    return f'<span style="color:{color};font-weight:600">{sign}{v:.2f}%</span>'


def portfolio_table(data):
    if not C.HOLDINGS:
        return ('<p style="color:#666;margin:6px 0 18px">Portföyünde kayıtlı kağıt yok. '
                'Hisse aldıktan sonra <code>config.py</code> içindeki HOLDINGS listesine ekle.</p>')
    rows = []
    total_cost = total_val = 0.0
    for code, lots, cost in C.HOLDINGS:
        if code not in data:
            rows.append(f"<tr><td>{code}</td><td colspan='6' style='color:#888'>veri yok</td></tr>")
            continue
        m = metrics(data[code])
        val = m["last"] * lots
        cst = cost * lots
        pnl = val - cst
        pnl_pct = (m["last"] / cost - 1) * 100 if cost else 0
        total_cost += cst
        total_val += val
        pnl_color = "#137333" if pnl >= 0 else "#c5221f"
        rows.append(
            f"<tr>"
            f"<td style='font-weight:600'>{code}</td>"
            f"<td>{lots:g} lot</td>"
            f"<td>{_num(cost)}</td>"
            f"<td>{_num(m['last'])}</td>"
            f"<td>{_chg(m['day_chg'])}</td>"
            f"<td style='color:{pnl_color};font-weight:600'>{pnl:+,.0f} TL</td>"
            f"<td style='color:{pnl_color};font-weight:600'>{pnl_pct:+.2f}%</td>"
            f"</tr>"
        )
    tot_pnl = total_val - total_cost
    tot_pct = (total_val / total_cost - 1) * 100 if total_cost else 0
    tot_color = "#137333" if tot_pnl >= 0 else "#c5221f"
    foot = (
        f"<tr style='border-top:2px solid #ddd;font-weight:700'>"
        f"<td colspan='5'>TOPLAM</td>"
        f"<td style='color:{tot_color}'>{tot_pnl:+,.0f} TL</td>"
        f"<td style='color:{tot_color}'>{tot_pct:+.2f}%</td></tr>"
    )
    header = "<tr><th>Kod</th><th>Adet</th><th>Maliyet</th><th>Son</th><th>Günlük</th><th>K/Z</th><th>K/Z %</th></tr>"
    return f"<table>{header}{''.join(rows)}{foot}</table>"


def indicators_table(codes, data):
    rows = ["<tr><th>Kod</th><th>Son</th><th>Günlük</th><th>Haftalık</th>"
            "<th>RSI</th><th>Hacim×ort</th><th>Durum</th></tr>"]
    for code in codes:
        if code not in data:
            continue
        m = metrics(data[code])
        rsi_v = m["rsi"]
        rsi_col = "#c5221f" if rsi_v >= 70 else ("#137333" if rsi_v <= 30 else "#333")
        rows.append(
            f"<tr>"
            f"<td style='font-weight:600'>{code}</td>"
            f"<td>{_num(m['last'])}</td>"
            f"<td>{_chg(m['day_chg'])}</td>"
            f"<td>{_chg(m['wk_chg'])}</td>"
            f"<td style='color:{rsi_col}'>{_num(rsi_v,dp=0)} <span style='color:#888;font-size:11px'>{rsi_label(rsi_v)}</span></td>"
            f"<td>{_num(m['vol_ratio'],'×',1)}</td>"
            f"<td style='font-size:12px;color:#555'>{condition_flags(m)}</td>"
            f"</tr>"
        )
    return f"<table>{''.join(rows)}</table>"


# Haber tonu için basit Türkçe kelime listeleri (kaba tahmin — kesin değil)
_POS_WORDS = [
    "arttı", "artış", "yükseldi", "yükseliş", "yükseltildi", "rekor", "kâr", "kar etti",
    "net kâr", "büyüme", "büyüdü", "ihale", "anlaşma", "sözleşme", "imzala", "güçlü",
    "zirve", "temettü", "kazanç", "sipariş", "yatırım", "ortaklık", "edinim", "satın al",
    "hedef fiyat yüksel", "potansiyel", "olumlu", "beklenti aştı", "prim",
]
_NEG_WORDS = [
    "düştü", "düşüş", "düşürüldü", "geriledi", "gerileme", "zarar", "ceza", "dava",
    "soruşturma", "iflas", "küçül", "kayıp", "iptal", "uyarı", "kriz", "negatif",
    "temerrüt", "gözaltı", "borç", "sat tavsiye", "hedef fiyat düşür", "beklentiyi karşılamadı",
    "karşılamadı", "zayıf",
]


def news_tone(title: str):
    """Başlığın tonunu kabaca tahmin et. (🟢 olumlu / 🔴 olumsuz / ⚪ nötr)"""
    t = title.lower()
    pos = sum(1 for w in _POS_WORDS if w in t)
    neg = sum(1 for w in _NEG_WORDS if w in t)
    if pos > neg:
        return "🟢", "#137333"
    if neg > pos:
        return "🔴", "#c5221f"
    return "⚪", "#999"


def price_table(codes, data):
    """Anlık fiyat + hafta / 1 ay / 6 ay ortalamaları."""
    rows = ["<tr><th>Kod</th><th>Anlık</th><th>Hafta ort.</th>"
            "<th>1 ay ort.</th><th>6 ay ort.</th><th>6 aya göre</th></tr>"]
    for code in codes:
        if code not in data:
            continue
        m = metrics(data[code])
        a6 = m["avg_6m"]
        vs6 = (m["last"] / a6 - 1) * 100 if a6 and not pd.isna(a6) else float("nan")
        if pd.isna(vs6):
            vs6_html = "—"
        else:
            arrow = "▲" if vs6 >= 0 else "▼"
            col = "#137333" if vs6 >= 0 else "#c5221f"
            vs6_html = f"<span style='color:{col}'>{arrow} {abs(vs6):.1f}%</span>"
        rows.append(
            f"<tr><td style='font-weight:600'>{code}</td>"
            f"<td style='font-weight:600'>{_num(m['last'])}</td>"
            f"<td style='color:#666'>{_num(m['avg_1w'])}</td>"
            f"<td style='color:#666'>{_num(m['avg_1m'])}</td>"
            f"<td style='color:#666'>{_num(m['avg_6m'])}</td>"
            f"<td>{vs6_html}</td></tr>"
        )
    return f"<table>{''.join(rows)}</table>"


def _reltime(when: dt.datetime) -> str:
    """'3s önce', '1g önce' gibi göreli zaman."""
    now = dt.datetime.now(dt.timezone.utc)
    diff = now - when
    mins = diff.total_seconds() / 60
    if mins < 60:
        return f"{int(mins)}dk önce"
    if mins < 60 * 24:
        return f"{int(mins // 60)}s önce"
    return f"{int(mins // 1440)}g önce"


def fetch_news(code: str, n: int, max_age_days: int):
    """Bir hisse için Google News Türkçe başlıklarını çek.
    [(başlık, kaynak, göreli_zaman, link)] döndürür. Hata olursa boş liste."""
    name = NAMES.get(code, "")
    # "teknik analiz" / "hisse yorum" gibi otomatik spam'i eleyip
    # gerçek haberi (KAP, bilanço, satış, ihale) öne çıkaran sorgu
    excl = '-"teknik analiz" -"hisse yorum"'
    query = f'"{name}" {code} {excl}' if name else f'{code} hisse {excl}'
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "tr", "gl": "TR", "ceid": "TR:tr"}
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=12).read()
        root = ET.fromstring(raw)
    except Exception:
        return []

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_age_days)
    out = []
    for it in root.findall(".//item"):
        title_el = it.find("title")
        if title_el is None or not title_el.text:
            continue
        title = title_el.text
        src_el = it.find("source")
        src = src_el.text if src_el is not None and src_el.text else ""
        # kaynağın adı bazen başlığın sonunda tekrar eder, temizle
        if src and title.endswith(src):
            title = title[: -len(src)].rstrip(" -–|").strip()
        pub_el = it.find("pubDate")
        when = None
        if pub_el is not None and pub_el.text:
            try:
                when = parsedate_to_datetime(pub_el.text)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=dt.timezone.utc)
            except Exception:
                when = None
        if when is not None and when < cutoff:
            continue
        link_el = it.find("link")
        link = link_el.text if link_el is not None else "#"
        rel = _reltime(when) if when else ""
        out.append((title, src, rel, link))
        if len(out) >= n:
            break
    return out


def news_section(codes):
    """İlgili hisseler için haber bloğu."""
    if not getattr(C, "SHOW_NEWS", False):
        return ""
    n = getattr(C, "NEWS_PER_STOCK", 2)
    age = getattr(C, "NEWS_MAX_AGE_DAYS", 3)
    blocks = []
    seen = []
    for code in codes:
        if code in seen:
            continue
        seen.append(code)
        items = fetch_news(code, n, age)
        if not items:
            continue
        lis = []
        for title, src, rel, link in items:
            meta = " · ".join(x for x in (src, rel) if x)
            emoji, _col = news_tone(title)
            lis.append(
                f"<li style='margin:5px 0;list-style:none'>"
                f"<span style='margin-right:4px'>{emoji}</span>"
                f"<a href='{link}' style='color:#0b3d2e;text-decoration:none'>{title}</a>"
                f"<div style='font-size:11px;color:#999;margin-left:20px'>{meta}</div></li>"
            )
        name = NAMES.get(code, code)
        blocks.append(
            f"<div style='margin-bottom:12px'>"
            f"<div style='font-weight:600;font-size:13px;color:#0b3d2e'>{code} "
            f"<span style='font-weight:400;color:#999;font-size:12px'>{name}</span></div>"
            f"<ul style='margin:4px 0 0;padding-left:0'>{''.join(lis)}</ul></div>"
        )
    if not blocks:
        return ""
    return ("<h2>📰 İlgili Haberler <span style='font-size:12px;color:#888;font-weight:400'>"
            "(son " + str(age) + " gün · 🟢 olumlu 🔴 olumsuz ⚪ nötr)</span></h2>"
            "<div style='font-size:11px;color:#aaa;margin:-4px 0 8px'>Ton otomatik tahmindir, "
            "başlığa tıklayıp kendin oku.</div>" + "".join(blocks))


def pick_dynamic_watchlist(data, n=6, per_cat=2):
    """O günün objektif olarak en hareketli kağıtlarını seç (kural bazlı, tavsiye değil).
    Her kategoriden (hacim / oynayan / volatilite) top `per_cat` kağıdın birleşimi."""
    rows = []
    for code, df in data.items():
        if code not in C.UNIVERSE:
            continue
        try:
            rows.append((code, metrics(df)))
        except Exception:
            continue

    def ranked(key, absval=False):
        good = [r for r in rows if not pd.isna(r[1][key])]
        keyf = (lambda x: abs(x[1][key])) if absval else (lambda x: x[1][key])
        return sorted(good, key=keyf, reverse=True)

    picks = []
    for src in (ranked("vol_ratio")[:per_cat], ranked("day_chg", True)[:per_cat],
                ranked("volat")[:per_cat]):
        for code, _ in src:
            if code not in picks:
                picks.append(code)
    return picks[:n]


def screen_tables(data):
    """Objektif tarama: en yüksek hacim oranı, en çok oynayan, en yüksek volatilite."""
    rows = []
    for code, df in data.items():
        try:
            m = metrics(df)
            rows.append((code, m))
        except Exception:
            continue

    def top(key, reverse=True, absval=False):
        keyf = (lambda x: abs(x[1][key])) if absval else (lambda x: x[1][key])
        good = [r for r in rows if not pd.isna(r[1][key])]
        return sorted(good, key=keyf, reverse=reverse)[: C.TOP_N]

    def mini(items, valfmt):
        cells = []
        for code, m in items:
            cells.append(
                f"<tr><td style='font-weight:600'>{code}</td>"
                f"<td>{_num(m['last'])}</td>"
                f"<td>{_chg(m['day_chg'])}</td>"
                f"<td>{valfmt(m)}</td>"
                f"<td style='font-size:12px;color:#555'>RSI {_num(m['rsi'],dp=0)} · {rsi_label(m['rsi'])}</td></tr>"
            )
        return "<table>" + "".join(cells) + "</table>"

    vol = mini(top("vol_ratio"), lambda m: f"hacim {_num(m['vol_ratio'],'×ort',1)}")
    mov = mini(top("day_chg", absval=True), lambda m: f"|değişim|")
    vlt = mini(top("volat"), lambda m: f"volatilite {_num(m['volat'],'%',1)}")

    return f"""
    <h3>🔊 En yüksek hacim (ortalamasına göre)</h3>{vol}
    <h3>⚡ Günün en çok oynayanları</h3>{mov}
    <h3>🎢 En yüksek volatilite (14g)</h3>{vlt}
    """


# ---------------------------------------------------------------------------
# Mail gövdesi
# ---------------------------------------------------------------------------
SESSIONS = {
    "morning": ("🌅 Sabah Bülteni", "09:00 — piyasa öncesi durum ve günün tarama listesi"),
    "noon":    ("🕧 Öğle Güncellemesi", "12:30 — gün içi durum"),
    "close":   ("🌆 Kapanış Özeti", "16:30 — günün kapanış tablosu"),
}


def build_html(session: str) -> str:
    title, subtitle = SESSIONS[session]
    now = dt.datetime.now(IST).strftime("%d.%m.%Y %H:%M")

    # ihtiyaç duyulan tüm kodları tek seferde indir
    all_codes = list(dict.fromkeys(
        [h[0] for h in C.HOLDINGS] + list(C.WATCHLIST) + list(C.UNIVERSE)
    ))
    data = download(all_codes)

    if getattr(C, "DYNAMIC_WATCHLIST", False):
        watch = pick_dynamic_watchlist(data)
    else:
        watch = list(C.WATCHLIST)

    # bölüm sırası oturuma göre değişir
    portfolio = f"<h2>📁 Portföyün</h2>{portfolio_table(data)}"
    wl_note = ("<span style='font-size:12px;color:#888;font-weight:400'>"
               "(bugün otomatik seçildi — objektif kriter)</span>"
               if getattr(C, "DYNAMIC_WATCHLIST", False) else "")
    watchlist = f"<h2>👀 İzleme Listesi {wl_note}</h2>{indicators_table(watch, data)}"
    prices = f"<h2>💰 Fiyat & Ortalamalar</h2>{price_table(watch, data)}"
    screen = f"<h2>🔎 Bugünün Taraması <span style='font-size:12px;color:#888;font-weight:400'>(objektif veri — tavsiye değil)</span></h2>{screen_tables(data)}"

    # Haber: maildeki TÜM bahsedilen kağıtlar (portföy + izleme + taramada geçen top-N)
    mentioned = pick_dynamic_watchlist(data, n=99, per_cat=C.TOP_N)
    news_codes = [h[0] for h in C.HOLDINGS] + list(watch) + mentioned
    news = news_section(news_codes)

    if session == "morning":
        body = portfolio + screen + watchlist + prices + news
    elif session == "noon":
        body = portfolio + watchlist + prices + news
    else:  # close
        body = portfolio + watchlist + prices + screen + news

    disclaimer = (
        "<div style='margin-top:28px;padding:14px 16px;background:#fff8e1;"
        "border:1px solid #ffe082;border-radius:8px;font-size:13px;color:#6d4c00'>"
        "⚠️ <b>Uyarı:</b> Bu mail yatırım tavsiyesi değildir. \"Durum\" etiketleri "
        "(aşırı alım, hacim patlaması, trend vb.) verinin ne durumda olduğunu "
        "<b>tanımlar</b> — al/sat önerisi <b>değildir</b>. Al/sat kararı ve sorumluluğu "
        "tamamen sana aittir. Veri gecikmeli olabilir."
        "</div>"
    )

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f4f5f7;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1a1a1a">
<div style="max-width:640px;margin:0 auto;padding:20px">
  <div style="background:#0b3d2e;color:#fff;padding:20px 24px;border-radius:12px 12px 0 0">
    <div style="font-size:20px;font-weight:700">{title}</div>
    <div style="font-size:13px;opacity:.85;margin-top:4px">{subtitle}</div>
    <div style="font-size:12px;opacity:.7;margin-top:8px">{now} · BIST</div>
  </div>
  <div style="background:#fff;padding:22px 24px;border-radius:0 0 12px 12px">
    {body}
    {disclaimer}
  </div>
  <div style="text-align:center;color:#aaa;font-size:11px;margin-top:14px">
    borsa-notification · kendi kurduğun sistem
  </div>
</div>
<style>
  h2{{font-size:16px;margin:22px 0 8px;padding-bottom:6px;border-bottom:2px solid #0b3d2e;color:#0b3d2e}}
  h3{{font-size:13px;margin:14px 0 6px;color:#333}}
  table{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:6px}}
  th{{text-align:left;background:#f0f2f5;padding:7px 8px;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.3px}}
  td{{padding:7px 8px;border-bottom:1px solid #eee}}
</style>
</body></html>"""


# ---------------------------------------------------------------------------
# Gönderim
# ---------------------------------------------------------------------------
def send(session: str, html: str):
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        raise SystemExit(
            "HATA: GMAIL_APP_PASSWORD ortam değişkeni tanımlı değil.\n"
            "Kurulum için README.md'ye bak. (Mail göndermeden denemek için: "
            "python borsa.py preview " + session + ")"
        )
    title = SESSIONS[session][0]
    now = dt.datetime.now(IST).strftime("%d.%m %H:%M")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{title} · {now}"
    msg["From"] = C.EMAIL_FROM
    msg["To"] = C.EMAIL_TO
    msg.attach(MIMEText("HTML mail — görüntülemek için HTML destekli istemci gerekir.", "plain"))
    msg.attach(MIMEText(html, "html"))
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(C.SMTP_HOST, C.SMTP_PORT, context=ctx) as s:
        s.login(C.EMAIL_FROM, pw)
        s.sendmail(C.EMAIL_FROM, [C.EMAIL_TO], msg.as_string())
    print(f"✓ Gönderildi: {session} -> {C.EMAIL_TO}")


def detect_session(now: dt.datetime) -> str:
    """Saate göre uygun oturumu seç (launchd 'auto' modunda kullanılır)."""
    mins = now.hour * 60 + now.minute
    if mins < 11 * 60:            # 11:00 öncesi
        return "morning"
    if mins < 14 * 60 + 30:       # 14:30 öncesi
        return "noon"
    return "close"


# ---------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    preview = False
    if args and args[0] == "preview":
        preview = True
        args = args[1:]
    session = args[0] if args else "auto"

    # 'auto' = saate göre seç + hafta sonu otomatik gönderme yok
    if session == "auto":
        now = dt.datetime.now(IST)
        if now.weekday() >= 5:    # 5=Cumartesi, 6=Pazar
            print("Hafta sonu — otomatik mail gönderilmiyor (borsa kapalı).")
            return
        session = detect_session(now)

    if session not in SESSIONS:
        raise SystemExit(f"Geçersiz oturum: {session}. Seçenekler: morning | noon | close | auto")

    print(f"Veri çekiliyor ({session}) ...")
    html = build_html(session)

    if preview:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"preview_{session}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✓ Önizleme yazıldı (mail GÖNDERİLMEDİ): {path}")
    else:
        send(session, html)


if __name__ == "__main__":
    main()
