# Devam notu — 26 Ağustos 2026

Bu dosya bir oturumdan diğerine devretmek için. Kalıcı proje kuralları
`CLAUDE.md`'de; burası **nerede kalındığı** ve **sırada ne olduğu**.

---

## 1. Bu oturumda ne yapıldı

### 25 Ağustos — Borsa kartı (yol haritası 4.1) bitti
Kullanıcının kararları: **90 günlük seri · çizgi (sparkline) · portföy YOK,
izleme listesi kalıyor** (`HOLDINGS` boş bırakıldı, kişisel veri public repoya
girmesin diye).

**Feed (`panel_feed.py`).** `borsa.py:download()` zaten 8 aylık günlük veri
indiriyordu; seri yazılmıyordu. Satırlara iki alan eklendi — **ek ağ isteği yok**:
- `hist`: son 90 kapanış (`HIST_GUN`). 5 kayıttan azsa alan **hiç yazılmıyor**.
- `ind`: `rsi`, `rsiTxt`, `ma`, `volat`, `volRatio`. Eşikler panelde tekrar
  yazılmadı; etiketler `B.ma_label()` / `B.rsi_label()`'den geliyor.
- Yeni `world_idx` alanı: BIST 100, S&P 500, Nasdaq, DAX, Brent (`WORLD_IDX`).
  `world` alanı dünya HABERİ; karışmasın diye ayrı ad.
- `indent=2` her `hist` sayısını ayrı satıra alıp dosyayı 7 katına çıkarıyordu;
  yalnızca sayısal diziler tek satıra toplanıyor. borsa.json 4 KB → 18 KB.

**Panel (`index.html`).** `priceSpark(vals,w,h,cls)` — `sparkline()` Ağırlık
kartına özel (rengi sabit), bu sürüm yön rengi alıyor ve geniş hâli CSS ile
esniyor. Satırda 66×20 sparkline; satıra tıklayınca **altında** açılan detay:
300×88 çizgi, en düşük/en yüksek, 90 günlük değişim, RSI, MA konumu, volatilite,
hacim oranı ve TradingView bağlantısı. Klavyeyle de açılıyor (`role=button`,
Enter/Space, `aria-expanded`). Yeni `#idxList` bölümü Dünya Piyasaları'nı basıyor.

**Saatlik veri alınmadı** — bilinçli. Feed günde 2 kez döndüğü için "saatlik"
zaten bayat olurdu; canlı grafik için TradingView bağlantısı var.

**Çıkan üç tuzak:**
1. Satır ↔ detay eşleşmesi id ile kurulamıyor: kodlarda `^GSPC`, `BZ=F` var.
   DOM sırası (`nextElementSibling`) kullanıldı; dinleyici kapsayıcıya bir kez
   bağlanıyor, `innerHTML` değişince kopmuyor.
2. Endekslerde Yahoo hacim vermiyor → `volRatio` 0 → detayda "×0" yazıyordu.
   Hem feed hem panel tarafında sıfır eleniyor.
3. Eski biçimli (hist/ind içermeyen) `borsa.json` önbelleğinde satır yalnızca
   TradingView bağı olan boş bir kutu açıyordu; artık gerçek veri yoksa satır
   tıklanabilir bile olmuyor.

**Doğrulama:** gerçek veriyle (6 BIST + 5 ABD + 5 endeks) Chrome'da; iki temada
da render edildi, 390 px'te yatay taşma yok, konsol hatası yok; aç/kapa, iç öğeye
tıklama, Enter, çoklu açık detay ve eski-biçim JSON testleri geçti.

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

### ÇÖZÜLDÜ: bildirimler geç geliyordu (26 Ağustos)
Kullanıcının şikâyeti: 12:15 antrenman hatırlatması 13:40'ta düşüyordu —
"o saatte saçma". Sebep GitHub Actions cron'unun rutin 30-40 dk gecikmesiydi;
pencereyi 120 dk'ya açmak bildirimin GELMESİNİ sağlamış ama ZAMANINDA
gelmesini sağlamamıştı.

Kullanıcının kararı: **erken cron + runner'da bekleme** (dört seçenek sunuldu).

**1. Cron'lar 35 dk önden kuruldu** (`push.yml`, `ONCE_DK`). Onunla eşleşen
`ILERI_DK = ONCE_DK + 5`.

**2. Betik erken uyandıysa dilim saatine kadar UYUYOR** (`time.sleep`), sonra
gönderiyor. Gecikmeyen koşuda bildirim erken değil TAM saatinde düşüyor;
gecikmiş koşuda uyku atlanıyor, hemen gidiyor. Bedeli boşta bekleyen runner
dakikası — depo public, Actions ücretsiz. Uyku `ILERI_DK` ile sınırlı ve
`timeout-minutes: 75` var; sapmış bir cron runner'ı saatlerce tutmuyor.

**3. GERI_DK 120 → 45.** 120 "her hâlükârda gelsin" içindi. Cron 35 dk önden
kalktığı için 45 dk'lık pay 80 dk'lık gerçek gecikmeyi karşılıyor; daha
fazla gecikmişse bildirim GÖNDERİLMİYOR. Kullanıcının açık tercihi: 1.5 saat
geç gelen "başladın mı?" hatırlatma değil, gürültü. Log sebebi yazıyor.

**4. Uyku sonrası ikinci kontrol.** Beklerken kullanıcı paneli açıp işi
işaretlemiş olabilir; gist yeniden okunup `cevaplanmis` tekrar bakılıyor.
Okunamazsa bildirim yutulmuyor, gönderiliyor.

**Çıkan tuzak — ikiz bildirim.** Cron'lar 35 dk önden kalkınca birbirine
35 dk'dan yakın iki dilim (23:00 ve 23:30) sorun oluyor: "şu ana en yakın
dilim" tahmini 22:25 ve 22:55 koşularının İKİSİNİ de 23:00'e yönlendiriyordu.
Çözüm tahmini kaldırmak: `github.event.schedule` tetikleyen cron ifadesini
veriyor, `CRON` env'i olarak geçiriliyor ve `cron_dilimi()` bunu doğrudan
dilime çeviriyor (cron UTC + 3sa + ONCE_DK). Eşleşme kesin, ikiz imkânsız.
Elle çalıştırmada (`workflow_dispatch`) `CRON` boş → eski tahmin mantığı.

`cron_dilimi()` eşleşme bulamazsa iki durumu ayırıyor: dilim BUGÜN yok
(normal — 12:15 cron'u Perşembe de kalkıyor, o gün antrenman yok) sessiz
geçiliyor; dilim HİÇBİR günde yoksa `push.yml` programdan ayrışmış demektir,
log'a uyarı basılıyor.

**DİKKAT:** `SCHED`/`YOK` içinde bir dilimin saati değişirse `push.yml`'deki
cron da 35 dk önden yeniden yazılmalı.

**Doğrulama.** İki ayrı testle, ikisi de scratchpad'de (repoya girmedi):
- 12 senaryoluk koşum testi (gist/webpush/saat mock'lu): zamanında cron
  35 dk uyuyup 12:15'te gönderiyor · 36 dk gecikme uykusuz hemen gönderiyor ·
  85 dk gecikme GÖNDERMİYOR · 23:00 ve 23:30 cron'ları ayrı dilimlere gidiyor
  (ikiz yok) · uyurken işaretlenince gönderilmiyor · ZORLA uyumuyor ·
  CRON boşken tahmine düşüyor. Hepsi geçti.
- `index.html`'deki SLOTS+SCHED+YOK'tan gerçek plan çıkarılıp push.yml'deki
  10 cron'a karşı denetlendi: 10/10 doğru dilime denk geliyor ve plandaki
  hiçbir dilim cron'suz kalmıyor.

Gerçek teslimat bir sonraki zamanlanmış koşuda görülecek — Actions log'unda
"erken uyandık, N dk beklenip tam saatinde gönderilecek" satırı aranmalı.

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
Yoklama, spor/yemek ve borsa bitti. **Sırada yalnızca harcama/gelir (4.2) var.**

### 4.1 Borsa kartı — BİTTİ (25 Ağustos)

Yapılanlar yukarıda. `borsa.json` alanları artık: `watch`, `us`, **`world_idx`**,
`gold`, `news`, `world`, `_teshis`; hisse satırlarında **`hist`** (90 kapanış) ve
**`ind`** (rsi/ma/volat/volRatio).

Açık uçlar:
- `borsa.py`'de hâlâ panele taşınmamış olanlar: `condition_flags()`,
  `screen_tables()`, `portfolio_table()` (portföy girilmediği için gereksiz).
- Gram altının serisi yok (`fetch_gold` yalnızca özet döndürüyor); istenirse
  `hist` oraya da eklenebilir.
- Dünya piyasaları listesi elle yazıldı (`WORLD_IDX`); TradingView sembolleri
  panelde `TVSYM` haritasında — yeni endeks eklenirse iki yere de yazılmalı,
  yoksa bağlantı sessizce çıkmaz (kasıtlı: yanlış sayfa açmaktansa hiç açmamak).

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
