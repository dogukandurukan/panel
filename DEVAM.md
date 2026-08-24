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

---

## 2. Kullanıcıda bekleyen işler

| # | İş | Nerede |
|---|---|---|
| 1 | `ANTHROPIC_API_KEY` secret'ı | Repo → Settings → Secrets → Actions. Mail cevap taslakları bu olmadan üretilmiyor; kod hazır. |
| 2 | `PANEL_GIST_TOKEN` secret'ı | Gists **okuma** izinli fine-grained token. |
| 3 | `VAPID_PRIVATE` secret'ı | Panelde "Telefon bildirimini kur" basınca bir kez gösterilecek. Önce ⇅ Senkron kurulu olmalı. |
| 4 | Paneli telefonda Ana Ekrana ekle | iOS web push başka türlü çalışmıyor. |
| 5 | `push-yoklama`'yı yoklama saatinde elle çalıştır | Log artık hangi aşamada takıldığını adıyla yazıyor. |
| 6 | Garanti mobilde "harcama bildirimi e-posta" açık mı? | Harcama kartının seviyesini belirliyor. |

---

## 3. Doğrulanamamış olan

**Gerçek push teslimatı hâlâ test edilmedi** — sandbox'ta push servisine erişim
yok, secret'lar da eksik. Zincirin son halkası ancak telefonda görülür.

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
Yoklama ve spor/yemek bitti.

### 4.1 Borsa kartı (sırada)
Sparkline/mum grafikleri, hisseye tıklayınca TradingView ya da saatlik veri,
dünya piyasaları. `borsa.py` daha fazla veri yazacak, panelde elle çizilen SVG.
Connector gerekmiyor; yfinance/Stooq anahtarsız.

### 4.2 Harcama / gelir kategorileri
Garanti bireysel API vermiyor ama **zaten yapılandırılmış bildirim maili
gönderiyor** (para transferi, HGS ekstre, kart ödeme tutarları). Yeni bir
`harcama_feed.py` bunları ayrıştırabilir — mevcut Gmail OAuth'u kullanır.

### 4.3 Dinamik programın açık uçları
- **Deload yok.** Üst uç tutmayınca kg sabit kalıyor; üst üste 3 seans
  tutmazsa "kiloyu %10 düşür" önerisi mantıklı olur ama istenmedi.
- **Yemek İÇERİĞİ hâlâ sabit** (`MP`); değişen yalnızca hedef sayılar. Yüksek
  hacimli günde porsiyonun kendisini büyütmek ayrı bir iş.
- Tekrar aralığı olmayan hareketlerde (`3 set`, `2 × 30 sn / taraf`) ilerleme
  hesaplanmıyor — kasıtlı.
- `MORN_AGIR` / `MORN_BACAK` kalıpları elle yazıldı; hareket adı değişirse
  eşleşme sessizce kaybolur.

### 4.4 Küçük açık uçlar (önceki oturumdan)
- Yoklama `YOK` tablosuna eklenecek/çıkarılacak iş var mı? ("bobo" bilerek
  dışarıda.)
- İnsan maili taraması yalnızca okunmamışları geziyor.
- Günün Filmi/Sanatçısı listeleri gömülü; kitap gibi genişletilebilir.

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
