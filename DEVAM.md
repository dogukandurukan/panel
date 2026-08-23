# Devam notu — 23 Ağustos 2026

Bu dosya bir oturumdan diğerine devretmek için. Kalıcı proje kuralları
`CLAUDE.md`'de; burası **nerede kalındığı** ve **sırada ne olduğu**.

---

## 1. Bu oturumda ne yapıldı

Hepsi `main`'de ve canlıda: https://dogukandurukan.github.io/panel/

### Gelen Kutusu kartı yeniden kuruldu
Kart "24 okunmamış / 0 önemli" gösterip hiçbir şey listelemiyordu.

- **Aksiyonun tanımı panel sahibinin kuralı oldu: aksiyon = gerçek bir insanın
  yazdığı mail.** Otomatik gönderim ne kadar acil dille yazılırsa yazılsın
  ("hesabınız kapanacak", "gecikmiş ödemeniz var") kartta alarm üretmez. Bu
  kural `CLAUDE.md`'ye 5. değişmez kural olarak yazıldı — yeniden tartışma.
- `classify()` tek soru soruyor: bunu bir insan mı yazdı? Kovalar:
  `reply` (öne çıkan tek kova) / `job` / `info` / `bulk`.
- Aksiyon kalıpları silinmedi, `notify_tag()`'e taşındı: otomatik mailin ne
  hakkında olduğunu adlandıran **nötr** etiket üretiyorlar (doğrulama, gecikmiş
  ödeme, güvenlik, belge). Sıralamayı etkilemezler.
- Aynı gönderenden aynı konu tek satırda birleşiyor (×4 rozeti).
- Her satırda tik var; tiklenen mail **kalıcı olarak** listeden çıkıyor.
  Anahtar kovaya göre değişiyor (`gmail_feed.hide_key`):
  `reply` → mesaj kimliği (aynı kişi tekrar yazarsa görünür),
  diğerleri → gönderen+konu (ELOGO'nun yarınki kopyası da gelmez).
  Çıkış kapısı: "N mail kapatıldı · göster".
- Pencere 3 → 7 gün. Sayaçlar görünen satırlardan hesaplanıyor.

### Kültür kartları
- Beş kart (bilgi, tarih, film, sanatçı, kitap) günde **tek kayıt** gösteriyor.
- **Vikipedi özeti kullanılmıyor** — tanım üretiyor, ilginç bilgi değil.
  Günün Bilgisi `index.html` içindeki kürasyonlu listeden besleniyor (84 madde,
  ortalama 66 karakter). `facts.json`'daki `items` artık okunmuyor.
- Tarihten Bir Not gerçekten bugüne bağlı: `facts_feed.py` Vikipedi'nin
  onthisday uç noktasından 10 günlük olay çekiyor. Sayfa başlığı **başlık olarak
  kullanılmıyor** — Vikipedi olayı sık sık yanlış özneye bağlıyor
  (Chandrayaan-3 inişine "Hindistan"). Yıl başlık, olay metin.
- `facts_feed.py` 327 → 130 satıra indi; kullanılmayan konu listesi kaldırıldı.
  facts.json 68 KB → 7,6 KB.
- Günün Kitabı `[başlık, yazar, yıl, tür, not]` yapısına geçti, 25 kitap
  yeniden yazıldı.

### Yoklama kartı (yeni)
Günün Programı'ndaki boş kutu iki anlama geliyordu: "yapmadım" ve "henüz sırası
gelmedi". Yoklama bu ayrımı kuruyor — **dinamik spor/yemek programı bu veriye
dayanacak.**

- Sırası gelmiş ama cevaplanmamış ilk işi tek soru olarak sorar (Evet/Atladım),
  cevabı saatiyle `d:yok:GG`'ye yazar.
- "Evet" Günün Programı'ndaki tiki de atıyor — tek gerçek, iki görünüm.
- Döküm: yapılan ✓, atlanan ✗, bekleyen ?, sırası gelmemiş ·
- Her dilim sorulmaz; `YOK` tablosunda yalnızca takip edilenler var
  (sabah rutini, spor türevleri, gitar, DJ, kişisel proje, kitap, yatış).
- Not kutusu **az önce cevaplanan** işe bağlanır, atlanan işe de yazılabilir.

### Antrenman modu (yeni)
"Bugünün Antrenmanı" kartının ikinci modu — üçüncü kart açılmadı.

- Yoklamada spor dilimine "Evet" demek modu doğrudan açıyor ve kartı ekrana
  kaydırıyor.
- Tek hareket büyük: sıra, hedef (4 × 5-8), önceki kayıt, kg + tekrar kutuları,
  hedef kadar boş set kutucuğu.
- Set kaydedilince **dinlenme sayacı kendiliğinden başlar**; süre dolunca renk
  değişir, WebAudio ile bip ve titreşim. Hedef set dolunca "Sonraki hareket"
  vurgulanır.
- Sayaç geri sayan değil, **bitiş damgası** tutar — tarayıcı arka planda
  zamanlayıcıyı kısınca bile doğru kalır. Saniyede yalnızca sayacın metni
  güncellenir; kart yeniden çizilirse kg kutusundaki odak kaybolur.
- Kayıt üç yere: `d:sess:GG` (set set), `d:wtlog` (günün en ağır seti — Ağırlık
  Takibi kartı ve Excel çıktısı bu biçimi okuyor), `d:ex:GG` (hedef set dolunca
  tik — alışkanlık serisi buna bakıyor).

### Web push (kurulum bekliyor)
- `sw.js` — service worker. Sadece push→bildirim ve bildirime dokununca paneli
  açma. Önbellek/offline **yok** (panel güncel JSON okumalı).
- Panelde WebCrypto ile VAPID anahtar üretimi. Gizli anahtar hiçbir yere
  kaydedilmiyor, bir kez gösterilip secret'a yapıştırılması isteniyor.
- **Abonelik repoya değil, senkronun gizli gist'ine yazılıyor** (`panel-push.json`).
  Repo public; uç nokta cihazı tanımlayan kalıcı adres. Bu yüzden senkron
  kurulu değilken push kurulamıyor.
- `push_feed.py` + `push.yml` gönderici. Bildirimin ne soracağı gist'teki
  plandan geliyor; plan `index.html`'deki SCHED+YOK'tan panel tarafından
  üretiliyor — **program Python'a kopyalanmadı.**
- Pencere asimetrik: 35 dk geriye, 5 dk ileriye (cron gecikir, erken uyandırma
  olmasın). Dilim zaten işaretliyse bildirim gitmez.
- `pywebpush` ortak `requirements.txt`'te **değil** — alt bağımlılığı http-ece
  bazı ortamlarda derlenmiyor; çökerse diğer feed'ler etkilenmemeli.
- `manifest.json` + `icon-180/192/512.png` eklendi. iOS web push yalnızca Ana
  Ekrana eklenmiş sitelerde çalışıyor ve manifest olmadan ikon yerine sayfa
  görüntüsü çıkıyordu.

---

## 2. Kullanıcıda bekleyen işler

| # | İş | Nerede |
|---|---|---|
| 1 | `ANTHROPIC_API_KEY` secret'ı | Repo → Settings → Secrets → Actions. Mail cevap taslakları bu olmadan üretilmiyor; kod hazır. |
| 2 | `PANEL_GIST_TOKEN` secret'ı | Gists **okuma** izinli fine-grained token. Gönderici aboneliği gist'ten okuyacak. |
| 3 | `VAPID_PRIVATE` secret'ı | Panelde "Telefon bildirimini kur" basınca bir kez gösterilecek. |
| 4 | Paneli telefonda Ana Ekrana ekle | iOS web push başka türlü çalışmıyor. |
| 5 | `push-yoklama` iş akışını elle çalıştır | Actions → Run workflow. Bildirim düşmezse log'da hangi aşama yazıyor. |
| 6 | Garanti mobil uygulamasında "harcama bildirimi e-posta" açık mı? | Harcama kartının hangi seviyede çalışacağını belirliyor. |

---

## 3. Doğrulanamamış olan

**Gerçek push teslimatı test edilmedi.** Sandbox'ta push servisine erişim yok.
Doğrulananlar: VAPID anahtar formatı (65 bayt açık / 32 bayt gizli), base64url
gidiş-dönüş, plan üretimi, service worker kaydı, göndericinin 9 senaryosu
(dilim seçimi, gecikmiş cron, pencere dışı, JS getDay ↔ Python weekday
eşlemesi, iki farklı "zaten cevaplanmış" yolu). Zincirin son halkası ancak
telefonda görülür.

---

## 4. Sıradaki yol haritası

Kullanıcının belirlediği sıra: **yoklama → spor/yemek → borsa → harcama.**
Yoklama bitti.

### 4.1 Spor / yemek / sabah rutini dinamikleşmesi (sırada)
Şu an üçü de sabit dizi (`WK`, `MP`, `MORNING_*`). Kullanıcının isteği:
haftalık/aylık gelişime ve **istikrara** göre kendiliğinden ayarlanması.

Veri artık var: `d:yok:GG` (atlama açıkça işaretli), `d:sess:GG` (set set kg ve
tekrar), `d:wtlog`, `d:sleepLog`, alışkanlık serileri (`habPast`, 90 gün).

Karar bekleyen sorular:
- Yük artırma ne kadar agresif olsun? Kaç hafta istikrar şart?
- Yemek kalori hedefi neye göre kaysın — kilo mu, antrenman yoğunluğu mu?

### 4.2 Borsa kartı
Sparkline/mum grafikleri, hisseye tıklayınca TradingView ya da saatlik veri,
dünya piyasaları. `borsa.py` daha fazla veri yazacak, panelde elle çizilen SVG.
Connector gerekmiyor; yfinance/Stooq anahtarsız.

### 4.3 Harcama / gelir kategorileri
Garanti bireysel API vermiyor ama **zaten yapılandırılmış bildirim maili
gönderiyor** (para transferi, HGS ekstre, kart ödeme tutarları). Yeni bir
`harcama_feed.py` bunları ayrıştırabilir — mevcut Gmail OAuth'u kullanır,
ek maliyet yok.

### 4.4 Küçük açık uçlar
- Yoklama `YOK` tablosuna eklenecek/çıkarılacak iş var mı? ("bobo" bilerek
  dışarıda bırakıldı.)
- İnsan maili taraması yalnızca **okunmamışları** geziyor. Okuyup cevap
  yazmadığın mail karta düşmüyor; genişletmek kolay ama istenmedi.
- Günün Filmi/Sanatçısı listeleri gömülü; kitap gibi genişletilebilir.

---

## 5. Çalışma alışkanlıkları (bu projede işe yarayan)

- **Gerçek veriyle test et.** Gmail sınıflandırıcısı gerçek gelen kutusundan
  geçirilince dört ayrı kalıp hatası çıktı ("action needed", "geciken ödemeniz",
  ashbyhq, "thank you for your application"). Varsayımla yazılsa kaçardı.
- **Tarayıcıda doğrula.** Playwright + Chromium kurulu; `context.clock` ile
  saati sabitleyip ileri sarmak yoklama/antrenman/dinlenme sayacı testlerinde
  şart oldu. İki temada da (`almanak`, `hud`) render et.
- JS sözdizimi kontrolü: `<script>` bloklarını çıkarıp `node --check`.
- Kullanıcı ürün kararını verir. "Aksiyon = insan maili" kuralı böyle oluştu;
  itiraz edilirse veriyi göster, karar onun.
