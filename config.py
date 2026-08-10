# -*- coding: utf-8 -*-
"""
BORSA BİLDİRİM SİSTEMİ — AYAR DOSYASI (panel/repo sürümü)
========================================================
Bu, panel reposuna konulan sürümdür. Mail ayarları (e-posta adresi)
buradan ÇIKARILDI çünkü repo herkese açık ve feed maile ihtiyaç duymaz.
Lokaldeki config.py'ne dokunma; mail botun onu kullanmaya devam eder.
"""

# 1) PORTFÖY
HOLDINGS = [
    # ("THYAO", 100, 280.0),
]

# 2) İZLEME LİSTESİ
DYNAMIC_WATCHLIST = True

WATCHLIST = [      # yalnızca DYNAMIC_WATCHLIST = False ise kullanılır
    "THYAO",
    "ASELS",
    "SISE",
]

# 3) TARAMA EVRENİ
UNIVERSE = [
    "THYAO", "ASELS", "GARAN", "AKBNK", "ISCTR", "YKBNK", "SISE", "EREGL",
    "KCHOL", "SAHOL", "BIMAS", "FROTO", "TUPRS", "PGSUS", "TOASO", "PETKM",
    "SASA", "HEKTS", "TCELL", "TTKOM", "ENKAI",
    "ARCLK", "VESTL", "TAVHL", "OYAKC", "GUBRF", "ALARK", "MGROS",
    "ASTOR", "TSKB", "DOAS", "ODAS", "SMRTG", "EKGYO", "KONTR", "YEOTK",
]

# 4) MAİL AYARLARI — panel feed'i mail göndermez; kişisel adres çıkarıldı.
#    (İsimler duruyor ki borsa.py import edilirken sorun çıkmasın.)
EMAIL_FROM = ""
EMAIL_TO   = ""
SMTP_HOST  = "smtp.gmail.com"
SMTP_PORT  = 465

# 5) HABER AYARLARI
SHOW_NEWS         = True
NEWS_PER_STOCK    = 3
NEWS_MAX_AGE_DAYS = 3

# 6) GÖSTERGE AYARLARI
RSI_PERIOD = 14
MA_SHORT   = 20
MA_LONG    = 50
TOP_N      = 3
