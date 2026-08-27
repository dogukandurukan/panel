# -*- coding: utf-8 -*-
"""
gist_io.py — panelin GİZLİ gist'ine anahtar yazar.

NEDEN VAR
---------
Bu depo herkese açık (CLAUDE.md 1. kural). Kişisel veri (gelen kutusu
başlıkları, ret mailleri) repoya JSON olarak yazılamaz. Panelin senkronu
zaten gizli bir gist kullanıyor; besleyiciler de oraya yazıyor, panel
senkronla okuyor.

BİÇİM
-----
gist / panel-data.json : {"v":1,"updated":<ms>,"data":{"d:anahtar":{"v":"<metin>","t":<ms>}}}
Panelin `mergeRemote` işlevi anahtar başına `t` damgasına bakar: uzaktaki
damga yereldekinden yeniyse üzerine yazar. Bu yüzden her yazımda t=şimdi.

Token: PANEL_GIST_TOKEN (fine-grained, "Gists: read and write").
Yoksa yazılmaz — çağıran betik ÇÖKMEZ, durum metni döner.
"""
import json
import os
import time

import requests

GITHUB_API = "https://api.github.com"
DATA_FILE = "panel-data.json"


def _basliklar(token):
    return {"Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json"}


def yaz(anahtar, deger):
    """`deger` bir METİN olmalı (panel localStorage'ı metin tutuyor).
    Döndürdüğü metin doğrudan log'a basılabilir — şirket/konu İÇERMEZ,
    Actions log'u da herkese açık."""
    token = os.environ.get("PANEL_GIST_TOKEN", "").strip()
    if not token:
        return f"gist: PANEL_GIST_TOKEN yok — {anahtar} yazılamadı"
    try:
        h = _basliklar(token)
        liste = requests.get(f"{GITHUB_API}/gists?per_page=100",
                             headers=h, timeout=25).json()
        hedef = next((g for g in liste
                      if DATA_FILE in ((g or {}).get("files") or {})), None)
        if not hedef:
            return (f"gist: {DATA_FILE} bulunamadı "
                    f"(token {len(liste)} gist görüyor) — {anahtar} yazılamadı")
        tam = requests.get(f"{GITHUB_API}/gists/{hedef['id']}",
                           headers=h, timeout=25).json()
        f = (tam.get("files") or {}).get(DATA_FILE) or {}
        ham = (requests.get(f["raw_url"], timeout=25).text
               if f.get("truncated") and f.get("raw_url") else f.get("content") or "{}")
        paket = json.loads(ham or "{}")
        paket.setdefault("v", 1)
        data = paket.setdefault("data", {})
        if (data.get(anahtar) or {}).get("v") == deger:
            return f"gist: {anahtar} zaten güncel, yazılmadı"
        data[anahtar] = {"v": deger, "t": int(time.time() * 1000)}
        paket["updated"] = int(time.time() * 1000)
        r = requests.patch(f"{GITHUB_API}/gists/{hedef['id']}", headers=h, timeout=25,
                           json={"files": {DATA_FILE: {"content": json.dumps(paket, ensure_ascii=False)}}})
        r.raise_for_status()
        return f"gist: {anahtar} yazıldı ({len(deger)} bayt)"
    except Exception as e:
        return f"gist: {anahtar} yazılamadı: {type(e).__name__}: {str(e)[:90]}"
