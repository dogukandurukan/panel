# panel (Daily) — katkı kuralları

> Nerede kalındığı ve sıradaki işler: **`DEVAM.md`**. Yeni bir oturuma
> başlarken önce onu oku.

Tek dosyalık kişisel kontrol panosu. GitHub Pages'ten yayınlanıyor:
https://dogukandurukan.github.io/panel/

## Değişmez kurallar

1. **Bu repo PUBLIC.** Hiçbir API anahtarı, token veya kişisel veri (telefon,
   e-posta, CV metni) buraya girmez. Gmail kimlik bilgileri yalnızca GitHub
   Actions secrets'ta durur ve tarayıcıya hiç inmez. Kullanıcının cover letter
   profili yalnızca kendi tarayıcısının `localStorage`'ında tutulur.
2. **Her gösterge gerçek veriye bağlı olacak.** Arkasında veri olmayan nabız,
   sahte akış çizgisi, dekoratif "çalışıyor" göstergesi konulmaz. Nabız yalnızca
   `status==='in_progress'` iken atar; akış oku yalnızca ajan son 1 saatte
   çalıştıysa akar. Bağlanacak veri yoksa öğe eklenmez.
3. **Tek dosya, sıfır bağımlılık.** `index.html` içinde HTML+CSS+JS. CDN
   script'i, npm paketi, build adımı eklenmez. PDF üretimi bile elle yazıldı
   (`makePDF`) — jsPDF bilerek eklenmedi.
4. **İki tema korunur.** `almanak` (varsayılan) ve `hud`. Renkler `:root`
   değişkenlerinde; HUD `html[data-theme="hud"]` altında izole. Yeni kart
   eklerken iki temada da kontrol et. `prefers-reduced-motion` yeni
   animasyonları da kapsamalı.
5. **Gelen kutusunda aksiyon = insan maili.** Bir maili "aksiyon bekliyor"
   diye öne çıkarmanın tek ölçütü, onu gerçek bir insanın yazmış olmasıdır.
   Otomatik gönderim ne kadar acil dille yazılırsa yazılsın ("hesabınız
   kapanacak", "gecikmiş ödemeniz var") kartta alarm üretmez: cevap yazılacak
   bir muhatabı yoktur, yapılacak iş varsa o iş ilgili uygulamada yapılır.
   Bunlar "Otomatik bildirim" bölümünde nötr etiketle durur.
6. **Program kendi verisinden ayarlanır, dışarıdan dayatılmaz.** Yük artışı
   (çift ilerleme), günlük karbonhidrat/kalori ve sabah rutini; `d:sess`,
   `d:vol`, `d:yok` ve `d:sleepLog` kayıtlarından türer. Veri yoksa ayar da
   yoktur — kart o zaman tabanı gösterir ve nedenini yazar. Günlük kayma
   `d:targets`'a **yazılmaz**; orası kullanıcının tabanı.
7. **LinkedIn otomasyonu yok.** Bireysel iş arama API'si yok ve otomatik erişim
   Kullanıcı Sözleşmesi'ne aykırı. Panel yalnızca ilana bağlantı verir.

## Veri akışı

Panel canlı API'ye kimlik doğrulamayla bağlanmaz; Actions'ın ürettiği statik
JSON okur.

| Dosya | Üreten | Workflow | Ne zaman (TR) |
|---|---|---|---|
| `borsa.json` | `panel_feed.py` | `feed.yml` | hafta içi 09:00 / 14:00 |
| `gmail.json` | `gmail_feed.py` | `gmail-feed.yml` | her gün 09:00 / 14:00 |
| `facts.json` | `facts_feed.py` | `facts-feed.yml` | Pazartesi 09:00 |

`facts.json` yalnızca "bugün tarihte" verisi taşır (10 gün önden). Günün Bilgisi,
Günün Filmi/Sanatçısı/Kitabı kartları `index.html` içindeki kürasyonlu listelerden
beslenir — Vikipedi özeti tanım üretiyor, ilginç bilgi değil.

**Kültür listeleri kısa olmamalı.** Liste uzunluğu = tekrar aralığı: 26 sanatçı,
sanatçının ayda bir dönmesi demekti. Taban 90 öğe (FACTS 236, FILMS 133,
BOOKS 110, ARTISTS 92). Yeni öğe eklerken alan sayısı sabit: film ve sanatçı 5,
kitap 5. Eklenen her madde doğrulanabilir olmalı — emin olunmayan iddia
yumuşatılır ya da yazılmaz.
| `jobs.json` | `jobs_feed.py` | `jobs-feed.yml` | her gün 08:00 |

Bir istisna: `push_feed.py` dosya üretmez, telefona web push bildirimi gönderir
(`push.yml`, yoklama saatlerinde). Abonelik bilgisi **repoya değil, senkronun
kullandığı gizli gist'e** yazılır — uç nokta cihazı tanımlayan kalıcı bir adres
ve bu repo herkese açık. VAPID gizli anahtarı yalnızca Actions secret'ında durur;
panel onu üretip bir kez gösterir, saklamaz. Bildirimin hangi saatte ne soracağı
`index.html`'deki SCHED + YOK tablolarından panel tarafından üretilip gist'e
yazılır; program Python tarafına kopyalanmaz.

Panelin kendi ürettiği türev anahtarlar (hepsi senkronla taşınır):
`d:prog` hareket başına çift ilerleme reçetesi, `d:vol` gün başına tonaj
(kg × tekrar) — yemek hedefi bunu okuyor.

Ayrıca doğrudan tarayıcıdan, anahtarsız: Google Sheets (gviz/JSONP, salt
okunur), GitHub Actions API (15 dk), Open-Meteo (30 dk).

## Bilinen tuzaklar

- **localStorage varsayılanı ezer.** Sabiti değiştirmek yetmez; kayıtlı değer
  üzerine biner. `TARGETS_VERSION` sürüm etiketi desenini kullan.
- **`gviz` fetch() ile çalışmaz** (CORS). İş Başvuruları JSONP kullanıyor.
- **Veri biçimi değişince geçiş kodu yaz.** Örnek: `renderJobs` içinde eski
  `jobsApplied` kayıtlarını `myApps`'e taşıyan bir kerelik geçiş var; `loadMorning`
  sıra numaralı sabah tiklerini ada çeviriyor.
- **Güne göre değişen listede tikleri sıra numarasıyla anahtarlama.** Sabah
  rutini dinamikleşince 3. sıradaki hareket değişti; `d:morning:GG` artık ad ile
  anahtarlanıyor ve `__n` o günün planlanan hareket sayısını tutuyor (seri oranı
  bunu payda alıyor).
- **Yeni pencere/belge üretirken `background` açıkça ver** — kullanıcı koyu
  moddaysa varsayılan tuval siyah oluyor.
- **HTML temizlerken önce unescape, sonra etiket sil.**
- **Test etmeden "çalışıyor" deme.** Tarayıcıda gerçek veriyle doğrula ve 7
  günü de gez — antrenman, yemek ve günlük program güne göre değişiyor.

## Yerel çalışma

```bash
python3 -m http.server 8899   # http://localhost:8899/index.html
python3 jobs_feed.py          # feed'i elle çalıştır (yalnızca stdlib)
```
