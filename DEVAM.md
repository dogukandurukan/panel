# Devam notu — 24 Ağustos 2026

Bu dosya bir oturumdan diğerine devretmek için. Kalıcı proje kuralları
`CLAUDE.md`'de; burası **nerede kalındığı** ve **sırada ne olduğu**.

---

## 1. Bu oturumda ne yapıldı

### Push kurulumunun durumu ölçüldü (kod tamam, secret'lar eksik)
`push-yoklama` ilk kez çalıştırıldı (iş akışı bir önceki gece 01:21'de main'e
girdiği için cron'lar henüz dönmemişti; `total_count` 0'dı).

- **Üç secret'ın hiçbiri ekli değil.** Log: `secret tanımlı değil:
  PANEL_GIST_TOKEN, VAPID_PRIVATE — atlandı.` `gmail.json` içinde de
  `"draft_note": "ANTHROPIC_API_KEY yok - taslak uretilmedi"`.
- İyi haber: iş akışı sağlam. `pywebpush` derleniyor, betik çökmüyor, temiz
  çıkıyor. Zincirde kod tarafı ayakta.
- `push_feed.py` artık **hangi** secret'ın eksik olduğunu adıyla yazıyor
  (eskiden "şu veya bu" diyordu).
- **Plan bayatlaması kapatıldı.** Plan yalnızca kurulum anında gist'e
  yazılıyordu; program sonradan değişirse telefon aylarca eski işi sorardı.
  `pushPlanTazele()` açılışta karşılaştırıp yalnızca değiştiyse yazıyor.

### Spor / yemek / sabah rutini dinamikleşti
Kullanıcının verdiği üç karar (hepsi "önerilen"):

**1. Yük artışı — çift ilerleme, tek seans.**
Bir seansta hedef set sayısı kadar ÇALIŞMA seti (ısınma değil: reçete kilosunda
ya da üstünde) tekrar aralığının ÜST ucunda tamamlanırsa reçete artar; üst gövde
+2.5, alt gövde +5 kg. Tutmazsa kg aynı kalır — geri düşürme yok, kötü bir gün
programı bozmaz. Tek seans yetiyor çünkü şart tüm setlerin üst uçta olması.
- Reçete `d:prog`'da: `{hareket:{kg,tarih,eski}}`. Tohum, o hareketin son kaydı.
- Antrenman modunda "bugün 100 kg · 4 seti de 8 tekrar tamamlarsan 105 kg'a
  çıkar" satırı; artış olunca "↑ 100 → 105 kg". Artış günü reçete satırı
  gizleniyor — 105 bugünün değil, sonraki seansın kilosu.
- kg kutusu artık reçeteyle açılıyor; liste görünümünde de kg ve ↑ görünüyor.

**2. Kalori/karb — antrenman yoğunluğuna göre.**
`d:vol` gün başına tonaj (kg × tekrar) tutuyor; o günün tonajı **aynı
haftagününün** son 4 kaydının medyanıyla karşılaştırılıyor.
- ≥ %110 → karb +25, kcal +150 · ≤ %70 → karb −25, kcal −150
- Yoklamada "Atladım" → karb −40, kcal −250 ("antrenman atlandı")
- **Aşağı yönlü ayar antrenman ortasında uygulanmıyor** (hacim o an doğal olarak
  düşük görünür); seans bitene ya da spor dilimi geçene kadar bekliyor.
- Kayma `d:targets`'a yazılmıyor — orası kullanıcının tabanı. Barların altında
  "Karb 340 → 315 g · hacim son Çarşamba günlerinin %64'i" diye nedeni yazıyor.
- Karb kutusu artık gün tipinin tabanını gösteriyor (`CARB_BY_DAY`); elle
  yazılırsa `cAuto` kapanıp o değer sabitleniyor.

**3. Sabah rutini — uyku + o günkü antrenman.**
- Kısa uyku (medyan alışkanlığın 1 saat altı ya da 6 saat altı) → ağır core
  (plank / dead bug / güneş selamı) düşüyor, liste 4 harekete iniyor.
- Bacak günü (LEGS/LOWER) → kalça fleksörü ve ayak bileği başa alınıyor. Eşleşme
  kalıpla, adla değil: aynı hareket günden güne farklı yazılmış.
- Son 7 günde hiç tiklenmemiş hareket başa taşınıyor.
- Uyku girilmemişse **hiçbir varsayım yok**; liste gün tipinin listesi.
- Sıra zaten doğruysa "başa alındı" notu yazılmıyor.

**Kırılma noktası ve göçü:** tikler sıra numarasıyla anahtarlanıyordu; liste
dinamikleşince 3. sıra artık aynı hareket değil. `d:morning:GG` **ad ile**
anahtarlandı, `__n` o günün planlanan sayısını tutuyor (alışkanlık serisi bunu
payda alıyor). `loadMorning` eski numaralı kayıtları bir kez ada çeviriyor.

Ayrıca: init'te `targetsVer` if bloğunun içine düşmüş fazladan `loadYok()`
çağrısı temizlendi (asıl çağrı zaten init sonunda).

### Ağırlık Takibi'ne ilerleme modu
Kaydedilen kg dört yerde duruyordu ama hiçbir yerde toplanmıyordu; kart yalnızca
bugünü ve geçen haftanın aynı gününü gösteriyordu.

- Kart başlığında **Bugün / İlerleme** düğmeleri.
- **Haftalık tonaj**: son 8 hafta, elle çizilen SVG çubuk; altında "önceki N
  haftanın ortalaması". Son kova bu hafta değilse "Bu hafta" denmiyor,
  kovanın tarihi yazılıyor.
- **Hareket başına değişim**: ilk kayıttan bugüne kg farkı, yüzde, son 8 seansın
  sparkline'ı, yürürlükteki reçete. `d:wtlog`'dan türüyor.
- `d:vol` dünden itibaren yazıldığı için eski günler `d:sess`'ten bir kez geri
  dolduruluyor (`d:volFill` bayrağı). **`d:wtlog`'dan tonaj hesaplanamaz** —
  orada tekrar sayısı yok, yalnızca kg.
- Veri yetmiyorsa sayı uydurulmuyor; kart nedenini yazıyor.

### Kültür listeleri kısa devirden çıktı
Sorun derinlik değil tekrar aralığıydı: 26 sanatçı = ayda bir aynı sanatçı.

- FACTS 84 → **236**, FILMS 28 → **133**, BOOKS 25 → **110**, ARTISTS 26 → **92**.
- ARTISTS 4 alandan **5**'e çıktı: `[ad, tür·dönem, öne çıkan albüm, buradan
  başla, not]`. "Buradan başla" tek parça önerisi; kart artık film ve kitap
  kadar derin (önceden en sığ olan oydu).
- Mevcut 17 kitapla çakışma elendi, Türkçe adı yanlış hatırlanan filmler
  düzeltildi.
- Yazılan bilgiler geri dönülüp denetlendi, **14 madde düzeltildi**: galaksi-kum
  tanesi karşılaştırması tersti (doğrusu yıldız sayısı), PDF 1980'lerde çıkmadı,
  Güneş ışığının yolculuğu yüzeyden değil çekirdekten başlıyor. Yedi iddia da
  yumuşatıldı (Roma betonu, bakteri-hücre oranı, iki dillilik ve bunama).

---

### İçerik kalitesi turu (Dünya Gündemi, Almanca, kültür derinliği)
Kullanıcının geri bildirimi: haberler okunmaya değmiyor, Almanca hep aynı ve
çok basit, kültür kartları istenen detayda değil.

**Dünya Gündemi yanlış kaynağa bağlıymış.** Google News Türkiye'nin GENEL
akışı çekiliyordu; kart "FAST işlem limiti", "Kandil ne zaman", yurt içi
asayiş gösteriyordu. Artık altı dış kaynağın dünya bölümleri okunuyor
(BBC World, Guardian World, Al Jazeera, NPR World, Euronews, DW Türkçe),
kaynak başına en fazla 2 haber, tıklama yemi ve KAP bildirimi süzülüyor.

Canlıda üç tur döndü, her tur bir hata çıkardı:
1. Hepsi tek kaynaktan geldi — kaynak başına sayaç yoktu, neden görünmüyordu.
2. Sayaç konunca "her kaynak öğe veriyor, 0 alındı" çıktı: `find(a) or find(b)`
   zinciri ElementTree'nin falsy Element tuzağına düşüyordu.
3. Meşru kısa başlıklar eleniyordu (25 karakter alt sınırı).
Teşhis artık `borsa.json`'daki `_teshis` alanında — Actions log kuyruğu
Python çıktısını kesebiliyor.

**Almanca A1-A2'de sıkışmıştı.** Havuz 14 tema / 140 kelimeden 34 tema /
380 kelimeye çıktı ve her kelime kendi seviyesini taşıyor (A1 70, A2 86,
B1 96, B2 104, C1 24). Gramer 14 -> 58 madde; Konjunktiv I/II, Passiv,
Relativsatz, n-Deklination, Partizipialkonstruktion dahil.

Asıl mesele havuz büyüklüğü değil seçimdi: diziyi düz gezmek A1 temalarını
arka arkaya getiriyordu. Temel/ileri ayrımı yapıldı, üç günün biri temel.
Ölçüm: 30 günün 20'si B1 üstü, üst üste en fazla 1 temel gün.

**Kültür kartlarına katmanlı derinlik.** "devamı" düğmesi paragraf + iki
öneri açıyor. Derinlik opsiyonel alan; yoksa düğme de yok. İçerik önce
bugünden itibaren sırası gelen kayıtlara yazıldı — dört kartta da kesintisiz
**21 gün**. Sonrası doldukça düğme kendiliğinden görünür.

## 2. Kullanıcıda bekleyen işler

**Telefon bildirimi ÇALIŞIYOR** (25 Ağustos, `Antrenman (12:15) — 1/1 cihaza
gönderildi`). Secret'lar ekli: `VAPID_PRIVATE`, `PANEL_GIST_TOKEN`.

| # | İş | Nerede |
|---|---|---|
| 1 | `ANTHROPIC_API_KEY` secret'ı | Repo → Settings → Secrets → Actions. Mail cevap taslakları bu olmadan üretilmiyor; kod hazır. |
| 2 | Garanti mobilde "harcama bildirimi e-posta" açık mı? | Harcama kartının seviyesini belirliyor. |

### Push kurulumunda çıkan dört hata (hepsi log'dan bulundu)
1. **Kart bayat kalıyordu.** Yoklama kartı `initSync`'ten önce çiziliyor, o an
   `syncCfg` null; senkron kurulu olsa bile "önce senkronu kur" diyor ve
   kendini düzeltmiyordu. Artık `syncCfg` okunur okunmaz yeniden çiziliyor.
2. **Safari ile ana ekran uygulaması ayrı depolama kullanıyor.** İlk anahtar
   Safari'de üretilmişti; PWA onu görmediği için yeni çift üretti ve secret'ın
   güncellenmesi gerekti.
3. **`mailto:panel@localhost`** → Apple 403 `BadJwtToken`. localhost geçerli
   alan adı değil.
4. **`https://...` sub** → pywebpush reddetti; RFC izin verse de kütüphane
   ısrarla `mailto:` istiyor. Artık geçerli bir mailto var ve adres
   `VAPID_SUB` secret'ıyla değiştirilebiliyor.
5. **Pencere dardı.** 18:30 cron'u 19:06'da çalıştı (GitHub 36 dk geciktirdi),
   35 dakikalık pencere bir dakikayla kaçtı ve DJ bildirimi hiç gitmedi.
   Pencere 120 dakika oldu, bir sonraki dilim başlayınca kapanıyor.
   Zamanlanmış cron'la teslimat 25 Ağustos 21:51'de doğrulandı:
   `Kişisel proje (21:30) — 1/1 cihaza gönderildi`.

Göndericiye kalıcı iki teşhis eklendi: token kaç gist görüyor + gizli
anahtarın aboneliğin açık anahtarıyla eşleşip eşleşmediği. İkincisi
`BadJwtToken`'ın anahtar hatası mı iddia hatası mı olduğunu tek satırda
ayırıyor.

**Elle test:** Actions → push-yoklama → Run workflow → **zorla** kutusu.
Pencere ve "zaten işaretlenmiş" kontrolünü atlar, günün en yakın dilimi için
bildirim gönderir. Zamanlanmış koşularda davranış değişmez.

## 3. Doğrulanamamış olan

**Gerçek push teslimatı doğrulandı** (25 Ağustos): `1/1 cihaza gönderildi`.
Pencere mantığı da gerçek gecikmeyle sınandı ve düzeltildi.

**Canlı sayfa sandbox'tan doğrulanamıyor.** Ajan proxy'si `github.io`'ya CONNECT
isteğini 403 ile reddediyor; dağıtımın başarısı yalnızca Actions kaydından
okunabiliyor. Değişikliği görmek için tarayıcıda sert yenileme gerekebilir
(`sw.js` önbellek tutmuyor ama iOS ana ekran kısayolu tutabiliyor).

**Dinamik program gerçek tarayıcıda doğrulandı** (Playwright + `context.clock`,
iki temada da): 7 günün hepsi JS hatasız; çift ilerleme tetikleniyor (4×8 @100
→ `d:prog` 105) ve tutmayan seansta (4×6) tetiklenmiyor; sonraki Çarşamba kutu
105 ile açılıyor; kısa uykuda liste 7 → 3 harekete iniyor; atlanan antrenmanda
karb 340 → 300; eski numaralı sabah tikleri ada göçüyor (`{Kedi-inek, Plank,
__n:7}`, sayaç 2/7).

Gerçek veriyle görülmemiş olan: `d:vol` tabanı en az **2 aynı-haftagünü kaydı**
istiyor, yani hacim ayarı ilk iki hafta devreye girmeyecek. Kart o sırada
"karşılaştırma için en az 2 Çarşamba kaydı gerekiyor" yazıyor.

---

## 4. Sıradaki yol haritası

Kullanıcının belirlediği sıra: **yoklama → spor/yemek → borsa → harcama.**
Yoklama ve spor/yemek bitti. Bu oturumun tamamı `main`'de ve canlıda
(Pages dağıtımı 24.08 10:01 UTC, başarılı).

### 4.1 Borsa kartı (sırada — ayrı oturumda yapılacak)

**Bugün ne var.** `panel_feed.py`, `borsa.py`'yi kütüphane gibi kullanıp
`borsa.json` üretiyor. Alanlar:

| Alan | İçerik |
|---|---|
| `watch` | BIST satırları: `{code, price, chg, avg1w, avg1m}` |
| `us` | ABD satırları, aynı biçim (`US_WATCH` panel_feed.py içinde) |
| `gold` | `{price, chg}` — gram altın, `GC=F` × `USDTRY=X` |
| `news` | hisse haberleri (süzgeçten geçmiş) |
| `world` | dünya gündemi |
| `_teshis` | feed sorun ayıklama alanı; panel okumuyor |

`borsa.py` içinde hazır ama panele hiç taşınmamış olanlar: `rsi()`,
`metrics()`, `condition_flags()`, `ma_label()`, `pick_dynamic_watchlist()`,
`screen_tables()`. Gösterge hesabı zaten var; panel yalnızca fiyat ve yüzde
okuyor.

Evren `config.py`'de: `UNIVERSE` 36 hisse, `DYNAMIC_WATCHLIST=True` olduğu
için izleme listesi her koşuda otomatik seçiliyor. `HOLDINGS` boş — portföy
girilmemiş; girilirse portföy tablosu da üretilebilir.

**Yapılacaklar (kullanıcının isteği).** Sparkline/mum grafiği, hisseye
tıklayınca saatlik veri ya da TradingView bağlantısı, dünya piyasaları.
Grafik `index.html` içinde elle çizilen SVG olmalı (CDN yok — 3. kural);
Ağırlık Takibi için yazılan `sparkline()` örnek alınabilir. `borsa.py` fiyat
serisini `borsa.json`'a yazmalı; şu an yalnızca özet yazıyor.

**Karar bekleyen.** Kaç günlük seri (30/90/365)? Mum mu çizgi mi? Portföy
girilecek mi, yoksa kart izleme listesi olarak mı kalacak?

### 4.2 Harcama / gelir kategorileri (ayrı oturumda yapılacak)

**Bugün ne var.** Bütçe kartı tamamen elle ve tamamen yerel:
`d:money:YYYY-MM` altında `{k:'in'|'out', c:kategori, a:tutar, n:not, d:tarih}`
dizisi. Kategoriler `MCATS` sabitinde (gider 8, gelir 4). Aylar arası gezinme
ve dışa aktarma var.

**Yapılacak.** Garanti bireysel API vermiyor ama **yapılandırılmış bildirim
maili gönderiyor** (para transferi, HGS ekstre, kart ödeme tutarları). Yeni bir
`harcama_feed.py` bunları ayrıştırıp kayıt üretebilir — mevcut Gmail OAuth'unu
kullanır, ek maliyet yok. Ayrıştırma için `gmail_feed.py`'deki `classify()` /
`notify_tag()` desenine bakılabilir; oradaki "Otomatik bildirim" kovası zaten
bu mailleri yakalıyor.

**Dikkat — bu, işe başlamadan verilecek ilk karar.** Harcama verisi kişiseldir
ve bu repo herkese açık (1. kural). `gmail.json` gibi repoya JSON yazılamaz;
kayıtlar ya senkronun gizli gist'ine yazılmalı ya da panel maili doğrudan
okumalı.

**Karar bekleyen.** Garanti mobilde "harcama bildirimi e-postası" ayarı açık
mı? Kartın hangi seviyede çalışabileceğini bu belirliyor.


### 4.3 Dinamik programın açık uçları
- **Deload yok.** Üst uç tutmayınca kg sabit kalıyor; üst üste 3 seans
  tutmazsa "kiloyu %10 düşür" önerisi mantıklı olur ama istenmedi.
- **Yemek İÇERİĞİ hâlâ sabit** (`MP`); değişen yalnızca hedef sayılar. Yüksek
  hacimli günde porsiyonun kendisini büyütmek ayrı bir iş.
- Tekrar aralığı olmayan hareketlerde (`3 set`, `2 × 30 sn / taraf`) ilerleme
  hesaplanmıyor — kasıtlı.
- `MORN_AGIR` / `MORN_BACAK` kalıpları elle yazıldı; hareket adı değişirse
  eşleşme sessizce kaybolur.

### 4.4 İçerik turundan kalanlar
- **Kültür derinliği 21 gün.** FILMS 21/133, ARTISTS 21/92, BOOKS 21/110,
  FACTS 21/236. 14 Eylül civarında düğme kaybolmaya başlar; devam yazılmalı.
- **Diller arası tekrar elenmiyor.** Aynı olay iki dilde gelince ikisi de
  listeye giriyor (BBC "Ukrainian strikes" + Euronews "Ukrayna ... vurdu").
  Kelime örtüşmesi diller arasında çalışmıyor; şimdilik bilinçli bırakıldı.
- **Günün Bilgisi derinliğinde öneri yok**, yalnızca paragraf var — film/kitap
  /sanatçıda iki öneri çıkıyor.

### 4.5 Küçük açık uçlar (önceki oturumdan)
- Yoklama `YOK` tablosuna eklenecek/çıkarılacak iş var mı? ("bobo" bilerek
  dışarıda.)
- İnsan maili taraması yalnızca okunmamışları geziyor.
- Kültür listeleri genişletildi ama hâlâ gömülü; büyürse ayrı bir JSON'a
  taşımak gerekebilir (index.html şu an ~230 KB).

---

## 5. Çalışma alışkanlıkları (bu projede işe yarayan)

- **Gerçek veriyle test et.** Gmail sınıflandırıcısı gerçek gelen kutusundan
  geçirilince dört ayrı kalıp hatası çıktı.
- **Tarayıcıda doğrula, birim testle yetinme.** Bu oturumda `↑ 100 → undefined`
  hatasını yalnızca UI akışı yakaladı: `d:prog` alanı `kg`, kod `yeni` okuyordu.
  Fonksiyonu tek tek çağıran test bunu göremezdi.
- `context.clock.install` ile günü sabitle; 7 günü de gez — antrenman, yemek ve
  rutin güne göre değişiyor. İki temada da (`almanak`, `hud`) render et.
- JS sözdizimi kontrolü: `<script>` bloklarını çıkarıp `node --check`.
- Kullanıcı ürün kararını verir.
