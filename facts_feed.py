# -*- coding: utf-8 -*-
"""
facts_feed.py — Türkçe Vikipedi'den "İlginç Bilgiler" havuzunu (facts.json) üretir.

NEDEN KÜRATÖRLÜ KONU LİSTESİ, RASTGELE MAKALE DEĞİL:
Vikipedi'nin random uç noktası ağırlıklı olarak köy / canlı türü taslakları döndürür;
ayrıca sıradan bir makalenin özeti "ilginç bilgi" değil sadece bir tanımdır
("X, Y familyasından bir kuş türüdür"). Bu yüzden burada, ÖZETİN KENDİSİ zaten
şaşırtıcı olan konular seçildi (Tardigrad, Antikythera düzeneği, Mpemba etkisi,
Dunning-Kruger etkisi, Turritopsis dohrnii ...). Böylece hem otomatik/güncel kalıyor
hem de kalite garanti altına alınıyor.

Vikipedi REST API'si (anahtar gerektirmez):
  https://tr.wikipedia.org/api/rest_v1/page/summary/<baslik>

Üretilen facts.json paneldeki "İlginç Bilgiler" kartını besler. Dosya yoksa panel
index.html içine gömülü kısa listeye geri düşer (borsa.json / gmail.json ile aynı desen).

Çalıştırma: python facts_feed.py
"""
import datetime as dt
import json
import re
import time
import urllib.parse

import requests

IST = dt.timezone(dt.timedelta(hours=3))
API = "https://tr.wikipedia.org/api/rest_v1/page/summary/"
SEARCH_API = "https://tr.wikipedia.org/w/api.php"
UA = "panel-facts/1.0 (https://github.com/dogukandurukan/panel)"

MIN_LEN = 110         # bundan kısa özetler "bilgi" sayılmayacak kadar cılız (tautolojik tanımlar)
MAX_LEN = 340         # kartta 2-3 satırı geçmesin
REQUEST_PAUSE = 0.15  # Vikipedi'ye kibar davran

# Özeti kendi başına ilginç olan konular. 404 olanlar sessizce atlanır ve raporlanır.
TOPICS = [
    # --- Zihin / algı / davranış ---
    "Dunning-Kruger etkisi", "Plasebo etkisi", "Nosebo etkisi", "Stockholm sendromu",
    "Sinestezi", "Déjà vu", "Pareidoli", "Tekinsiz vadi", "Doğrulama yanlılığı",
    "Seyirci etkisi", "Zeigarnik etkisi", "Kelebek etkisi", "Mandela etkisi",
    "Fantom uzuv", "Hafıza sarayı", "Uyku felci", "Lucid rüya", "Ayna nöron",
    # --- Fizik / kozmoloji ---
    "Kara delik", "Solucan deliği", "Kuantum dolanıklığı", "Schrödinger'in kedisi",
    "Fermi paradoksu", "Karanlık madde", "Karanlık enerji", "Nötron yıldızı",
    "Olay ufku", "Büyük Patlama", "Genel görelilik", "Özel görelilik", "Işık yılı",
    "Antimadde", "Higgs bozonu", "Süperiletkenlik", "Mpemba etkisi", "Casimir etkisi",
    "Nötrino", "Entropi", "Termodinamiğin ikinci yasası", "Süperakışkanlık",
    "Zaman genişlemesi", "Belirsizlik ilkesi", "Çift yarık deneyi",
    # --- Uzay / gök cisimleri ---
    "Voyager 1", "Oort bulutu", "Kuiper kuşağı", "Olympus Mons", "Europa (uydu)",
    "Titan (uydu)", "Enceladus", "Halley Kuyruklu Yıldızı", "Uluslararası Uzay İstasyonu",
    "Hubble Uzay Teleskobu", "James Webb Uzay Teleskobu", "Güneş tutulması",
    "Kuzey ışıkları", "Samanyolu", "Andromeda Gökadası", "Süpernova", "Pulsar",
    "Kızıl dev", "Beyaz cüce", "Ay", "Mars", "Venüs", "Jüpiter", "Satürn",
    # --- Canlılar ---
    "Su ayısı", "Ahtapot", "Aksolotl", "Turritopsis dohrnii", "Çıplak köstebek faresi",
    "Biyolüminesans", "Elektrikli yılan balığı", "Ekolokasyon", "Ornitorenk",
    "Bal arısı", "Karınca", "Mavi balina", "Deniz atı", "Kutup ayısı", "Yarasa",
    "Mikoriza", "Fotosentez", "Pando (ağaç)", "General Sherman (ağaç)",
    "Bakteriyofaj", "Mercan resifi", "Göç (hayvan)", "Kış uykusu", "Kamuflaj",
    "Simbiyoz", "Bağırsak mikrobiyotası", "Ölümsüzlük",
    # --- Genetik / hücre ---
    "DNA", "CRISPR", "Telomer", "Mitokondri", "Kök hücre", "İnsan Genom Projesi",
    "Epigenetik", "Kromozom", "Ribozom", "Apoptoz",
    # --- Tarih / arkeoloji ---
    "Antikythera düzeneği", "Rosetta Taşı", "Göbekli Tepe", "Çatalhöyük",
    "Terracotta Ordusu", "Pompeii", "Machu Picchu", "Nazca çizgileri", "Stonehenge",
    "İpek Yolu", "Kara Ölüm", "Truva", "Efes", "Derinkuyu Yeraltı Şehri", "Ayasofya",
    "Büyük İskenderiye Kütüphanesi", "Hammurabi Kanunları", "Çivi yazısı",
    "Hiyeroglif", "Mumyalama", "Vikingler", "Rönesans", "Sanayi Devrimi",
    "Berlin Duvarı", "Çernobil felaketi", "Titanic", "Manhattan Projesi",
    # --- Teknoloji / bilgisayar ---
    "Enigma makinesi", "Turing testi", "ARPANET", "Moore yasası", "Transistör",
    "Kriptografi", "Küresel Konumlandırma Sistemi", "Lityum iyon pil", "Yapay zekâ",
    "Makine öğrenimi", "Blok zinciri", "Açık kaynak", "Unicode", "QR kod",
    "Bilgisayar virüsü", "Kuantum bilgisayar", "Matbaa",
    # --- Malzeme / kimya ---
    "Aerojel", "Grafen", "Vantablack", "Elmas", "Helyum", "Cıva", "Titanyum",
    "Periyodik tablo", "Radyokarbon tarihleme", "Süper yapıştırıcı", "Kevlar",
    "Nanoteknoloji", "Sıvı kristal", "Ozon tabakası",
    # --- Yer / jeoloji ---
    "Mariana Çukuru", "Everest Dağı", "Atacama Çölü", "Ölü Deniz", "Baykal Gölü",
    "Amazon Nehri", "Sahra Çölü", "Antarktika", "Yellowstone Kalderası", "Pamukkale",
    "Van Gölü", "Kapadokya", "Levha tektoniği", "Deprem", "Volkan", "Ay tutulması",
    "Gayzer", "Mağara", "Buzul", "Tsunami", "Hurrikan",
    # --- Matematik ---
    "Altın oran", "Fibonacci dizisi", "Pi sayısı", "Fraktal", "Möbius şeridi",
    "Monty Hall problemi", "Doğum günü problemi", "Gödel'in eksiklik teoremleri",
    "Asal sayı", "Sonsuzluk", "Kaos teorisi", "Dört renk teoremi", "Öklid",
    "Sıfır", "Oyun teorisi", "Büyük sayılar yasası",
    # --- Dil / kültür / insan ---
    "Esperanto", "Sesli harf", "Yazının tarihi", "Rüya", "Müzik kuramı",
    "Umami", "Kahve", "Çay", "Baharat ticareti", "Zeytin", "Ekmek", "Peynir",
    "Olimpiyat Oyunları", "Satranç", "Go (oyun)",
]


def clean(text: str) -> str:
    """Vikipedi özetini kart için sadeleştir."""
    t = re.sub(r"\s+", " ", text or "").strip()
    t = re.sub(r"\[\d+\]", "", t)              # dipnot izleri
    t = re.sub(r"\s*\([^)]{0,30}dinle[^)]*\)", "", t, flags=re.I)  # "(telaffuz: ... dinle)"
    return t.strip()


def first_sentences(text: str, min_len: int = 150, max_sentences: int = 3) -> str:
    """
    İlk cümlelerden, en az min_len karaktere ulaşacak kadarını al.
    Kısaltmalarda ve ondalıklarda bölmemek için nokta+boşluk+büyük harf kalıbı kullanılır.
    """
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ])", text)
    out = ""
    for i, p in enumerate(parts):
        out = (out + " " + p).strip() if out else p
        if len(out) >= min_len or i + 1 >= max_sentences:
            break
    return out


def summary_by_title(session, title):
    """Verilen başlığın özetini getirir. Bulunamazsa (None, sebep) döner."""
    url = API + urllib.parse.quote(title.replace(" ", "_"), safe="")
    r = session.get(url, timeout=20)
    if r.status_code != 200:
        return None, f"http {r.status_code}"
    d = r.json()
    if d.get("type") != "standard":
        return None, f"tip: {d.get('type')}"          # disambiguation vb.
    extract = clean(d.get("extract", ""))
    if len(extract) < MIN_LEN:
        return None, f"cok kisa ({len(extract)})"
    text = first_sentences(extract)
    if len(text) > MAX_LEN:
        cut = text[:MAX_LEN]
        text = cut[: cut.rfind(" ")].rstrip(" ,;:") + "…"   # kelime ortasında kesme
    return {
        "text": text,
        "title": d.get("titles", {}).get("normalized") or d.get("title") or title,
        "url": d.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }, None


def search_title(session, term):
    """
    Başlık birebir tutmadığında Vikipedi aramasıyla doğru makaleyi bul.
    tr.wikipedia başlıkları tahmin edilenden farklı olabiliyor
    ('Su ayısı' -> 'Tardigrada', 'Çernobil felaketi' -> 'Çernobil faciası' gibi),
    bu yedek olmadan en ilginç konuların çoğu 404 ile düşüyordu.
    """
    r = session.get(SEARCH_API, timeout=20, params={
        "action": "query", "list": "search", "srsearch": term,
        "srlimit": 1, "srnamespace": 0, "format": "json",
    })
    if r.status_code != 200:
        return None
    hits = r.json().get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None


def fetch_summary(session, topic):
    item, why = summary_by_title(session, topic)
    if item is not None:
        return item, None
    # birebir başlık tutmadı -> arama ile dene
    found = search_title(session, topic)
    time.sleep(REQUEST_PAUSE)
    if not found or found.lower() == topic.lower():
        return None, why
    item2, why2 = summary_by_title(session, found)
    if item2 is not None:
        item2["via_search"] = topic
        return item2, None
    return None, f"{why} / arama '{found}': {why2}"


def build():
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "application/json"})

    items, skipped = [], []
    seen_titles = set()
    for topic in TOPICS:
        try:
            item, why = fetch_summary(session, topic)
        except Exception as e:
            item, why = None, f"hata: {e}"
        if item is None:
            skipped.append(f"{topic} ({why})")
        elif item["title"].lower() in seen_titles:
            skipped.append(f"{topic} (yinelenen -> {item['title']})")
        else:
            seen_titles.add(item["title"].lower())
            items.append(item)
        time.sleep(REQUEST_PAUSE)

    return {
        "updated": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "ok": len(items) > 0,
        "count": len(items),
        "requested": len(TOPICS),
        "items": items,
    }, skipped


if __name__ == "__main__":
    data, skipped = build()
    with open("facts.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"facts.json: {data['count']}/{data['requested']} bilgi yazildi")
    if skipped:
        print(f"atlanan {len(skipped)}:")
        for s in skipped:
            print("  -", s)
