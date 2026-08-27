# Devam notu — 26 Ağustos 2026 (akşam)

Bu dosya bir oturumdan diğerine devretmek için. Kalıcı proje kuralları
`CLAUDE.md`'de; burası **nerede kalındığı** ve **sırada ne olduğu**.

---

## 1. Bu oturumda ne yapıldı

### 27 Ağustos — Gündem şeridi (4.6 uygulandı)
Tam genişlikte, eşit üç sütun: **Dünya | Türkiye | Piyasa & Şirket**.
Kart olarak gridde tek sütuna sıkışıyordu (663 px) ve dünya+piyasa haberleri
alt alta biniyordu. Şerit grid'in hemen altında, Quiz & Gramer'in üstünde.

- `.trio`: gap yerine `padding + border-left` — ayraç sütunlar arasında tam
  ortada duruyor (gazete sütunu hissi). 980 px'te 2 sütun (Piyasa alta tam
  genişlik), 700 px'te tek sütun, ayraçlar üst çizgiye dönüyor.
- Her sütun 6 haber; numaralandırma sütun başına yeniden başlıyor.

**Türkiye gündemi yeni** (`borsa.json` → `tr`): AA, TRT Haber, BBC Türkçe,
Habertürk, NTV. Kaynak başına en fazla 2, `_benzer` ile tekrar eleniyor.
NTV/Habertürk akışları SEO gürültüsüyle dolu ("Şans Topu Sonuçları Sorgulama
Ekranı", "Son dakika deprem mi oldu?"); `COP_KALIP`'a Türkiye'ye özgü
kalıplar eklendi (loto, sorgulama, deprem mi oldu, saat kaçta, canlı izle…).

**Dünya sütunu tamamen İngilizceye çekildi** (Euronews TR + DW Türkçe yerine
İngilizce sürümleri). Yan fayda: 4.4'teki "aynı olay iki dilde iki kez
listeye giriyor" açığı kapandı — kelime örtüşmesi diller arası çalışmıyordu.
Ayrıca Euronews'in günde birkaç kez attığı "Latest news bulletin | … Midday"
başlığı da elendi (haber değil, bültenin kendisi).

**`fetch_world` ve `fetch_tr` tek gövdeye indi** (`_harmanla`): kaynak başına
sınır, dönüşümlü harmanlama ve teşhis satırı ikisinde de aynı.

**feed.yml artık her gün koşuyor** (eskiden hafta içi). Borsa hafta sonu
kapalı ama aynı feed gündemi de üretiyor; Türkiye/dünya haberleri hafta sonu
bayatlamasın diye. Borsa satırları hafta sonu son kapanışı gösterir.

**Doğrulama:** 1440 / 980 / 700 / 390 px'te taşma yok, sütunlar eşit;
iki temada da render edildi; gerçek veriyle 6+6+6 haber; sayfa 5884 px.

### 26 Ağustos (3) — Yemek metninden kalori hesabı (4.9 uygulandı)
Kullanıcı: "listedekine uymadığım gün 'kahvaltıda şunu yedim' diye girsem ve
ona göre kalori hesaplasa mümkün mü?"

**Gömülü besin tablosu** (`BESIN`, ~115 kayıt): 100 g / 100 ml başına
[kcal, protein, karbonhidrat] + besine özel birim ağırlıkları
(`{adet:120}`, `{dilim:30}`, `{kase:250}`, `{kutu:80}`…). Dış API yok:
anahtar ister, repo herkese açık, panel statik (3. kural).

**`besinCoz(metin)`** öğün metnini "+", virgül ve " ve " ile parçalıyor:
- `70g yulaf`, `250ml süt` → doğrudan gram/ml.
- `2 kutu ton (~160g)` → **parantezdeki gram parçanın TAMAMI** sayılıyor,
  sayıyla tekrar çarpılmıyor.
- `3 yumurta` → sayı + birim yok → adet ağırlığı.
- `1 yemek kaşığı zeytinyağı` → birim tespiti KÖK ile (`kaşığı`, `bardağı`
  çekimli yazımlar birebir eşleşmiyordu).
- `salata` (miktarsız) → besinin KENDİ servis birimi (porsiyon/adet/kase).
  Kendi birimi yoksa genel varsayılana kaçılmıyor.

**İki ayrı kova, ikisi de tahmine kapalı (2. kural):** `bilinmeyen`
(besin tabloda yok) ve `miktarsiz` (besin belli, miktar çıkarılamıyor).
Biri doluysa **makro kutularına dokunulmuyor**, altta ne eksik yazıyor.

**Bayraklar:** `oto` (kutulara gerçekten yazıldı) ve `elle` (kullanıcı makro
kutusuna dokundu → otomatik bir daha ezmiyor, "otomatiğe dön" düğmesi var).
Metin değişince ikisi de sıfırlanıp yeniden hesaplanıyor.
- Açılışta hesaplama YAPILMIYOR: plandaki (MP) kürasyonlu değerler kalıyor,
  yalnız metin düzenlenince devreye giriyor. Not satırı da bu yüzden
  dokunulmamış öğünde boş — "otomatik hesaplandı" yazmak yalan olurdu.
- Kutular yerinde güncelleniyor, liste yeniden çizilmiyor (odak kaybolurdu).

**Doğrulama:** 15 örnek metin (pizza, döner+ayran, kumpir ve mercimek
çorbası, 2 top dondurma, tanınmayan "annemin karnıyarığı"), UI akışı
(otomatik → elle → otomatiğe dön), odak korunuyor, konsol hatası yok.

### 26 Ağustos (2) — Sayfa düzeni: sütun yerleştirme
Kullanıcı: "bazıları çok büyük bazıları çok kısa, kartların uzunlukları aynı
olsun, laptopta da düzgün gözüksün."

**Ölçüm önce yapıldı.** 1440 px'te grid 3 sütun, her satır en uzun karta
hizalanıyordu: **2724 px boşluk**, sayfa 7110 px. En kötüsü
`Antrenman 409 | Yemekler 921 | Uyku 392` satırı (1041 px boşluk).

**`gridDiz()` — elle yazılmış sütun yerleştirme.** Kartlar DOM sırasıyla o an
en kısa sütuna konuyor. Yeniden dizme yalnız üç durumda: açılış, feed'ler
indikten ~2.6 sn sonra, ve sütun sayısı değişince (1100/720 px eşikleri).
Kart açıp kapayınca DİZİLMİYOR — sayfa zıplamasın diye. JS çalışmazsa kartlar
gridin doğrudan çocuğu kalıyor, eski davranış aynen sürüyor.
- Kartlar taşınıyor (kopyalanmıyor): girdiler, dinleyiciler, açık detaylar korunuyor.
- Antrenman + Alışkanlık Serileri `.stack` içinde: kullanıcı serilerin
  antrenmanın altında durmasını istedi, birlikte taşınıyorlar.
- Sıra değişti: Alışkanlık yukarı, Dünya Gündemi onun eski yerine.

**Üç uzun kart kısaldı:**
- **Almanca 983 → 463** (4.7 uygulandı): kartta yalnız 5 kelime. Quiz + gramer
  alta tam genişlik şeride (`.dz`, yan yana). Quiz artık **cloze**: örnek
  cümlede hedef kelime boşluğa çevriliyor, şıklar Almanca. Kelime cümlede
  birebir geçmiyorsa (çekimli fiil, "davon ausgehen, dass") eski "ne demek"
  biçimine düşüyor — 5 kelimenin 3'ünde cloze çıkıyor.
- **Yemekler 921 → 759**: öğün satırı 97 → 78 px. Slot + porsiyon üstte,
  yemek adı TAM GENİŞLİKTE (kırpılmasın diye — ilk denemede 197 px'e düşüp
  okunmaz olmuştu), makrolar altta. Hedef kutusu (4 giriş, 60 px) meta'daki
  "hedefi düzenle" düğmesine alındı.
- Borsa zaten bir önceki turda ikiye bölünmüştü.

**Sonuç:** sayfa 7110 → **5968 px**, sütunlar arası fark 441 → 402 px,
yatay taşma yok. 390 / 900 / 1280 / 1440'ta doğrulandı; porsiyon, makro,
hedef, borsa detayı, quiz, su ve yeniden boyutlandırma sütunlara taşındıktan
sonra da çalışıyor.

**Çakışma notu:** bu iş sırasında bildirim tarafında `id="kAntrenman"` eklenmişti
(bildirime dokununca karta git). Rebase çakışması ikisi birlikte tutularak
çözüldü — `.stack` sarmalayıcı + id.

### 26 Ağustos — Borsa kartı ikiye bölündü, grafiğe imleç, Tarihten "devamı"
Kullanıcının geri bildirimi: borsa kartı çok uzun ve şekilsiz; grafikte hangi
gün hangi fiyat olduğu görünmüyor; Tarihten kartında "devamı" yok.

**Borsa tek karttan iki karta.** `Döviz & Piyasalar` (kur + gram altın + dünya
endeksleri + finans notu) ve `İzleme Listesi` (BIST + ABD + günün hareketi).
Grid `auto-fit` olduğu için ikisi ayrı sütuna düşüyor, tek kartın ekranı
doldurması bitti. İkinci kartın meta'sı `#borsaTime` (feed yaşı).

**Grafikte imleç.** `borsa.json` satırlarına `histD` eklendi (AA-GG). Tarih
saklanmak zorunda: işlem günleri hafta sonu/tatil atladığı için indeksten
hesaplanamıyor. Detay grafiğinde kesikli dikey çizgi + nokta, altında
"12 Ağu | 2,45"; grafiğin hemen altında x ekseni olarak ilk/son gün.
- Seri DOM'a yazılmıyor (90 sayı × 16 satır şişirir); hover anında
  `watch/us/worldIdx` dizisinden `data-i` sıra numarasıyla okunuyor.
- Dokunmatik: tek dokunuş da okuma yapıyor (`pointerdown` de dinleniyor) ve
  parmak kalkınca silinmiyor — `pointerleave` yalnız `pointerType==='mouse'`
  için kapatıyor. `touch-action:pan-y` ile sayfa kaydırma bozulmuyor.
- `histD` indent ile dosyayı 47 KB'a çıkardı; JSON sıkıştırma regex'i artık
  kısa METİN dizilerini de tek satıra topluyor (27 KB). Haber başlıkları
  12 karakter sınırının dışında kaldığı için okunur kalıyor.

**Tarihten "devamı".** `facts_feed.py` Vikipedi yanıtındaki `extract`'i zaten
alıp ATIYORDU — ek istek olmadan `detay` alanı eklendi (cümle sonunda kesilir,
≤520 karakter). Öneri satırları AYNI GÜNÜN diğer olayları ("aynı günden"
etiketi); panelde zaten var, feed'e maliyeti yok. `derinKutu()` artık öneri
başlığını parametre alıyor (film/kitap/sanatçıda "bunu sevdiysen" aynen).
Sayfa seçimi de iyileşti: adı olay metninde geçen sayfa tercih ediliyor.
**Bilinen sınır:** olay bir ülkeye bağlıysa (ör. "Birleşik Krallık, Mısır'a
bağımsızlığını verdi") detay o ülkenin genel maddesi oluyor. Gerçek veri,
ama derinliği zayıf.

**Doğrulama:** Chrome'da gerçek veriyle, iki temada. İmleç %2/25/50/75/99'da
doğru gün+fiyat veriyor, ayrılınca varsayılana dönüyor; 390 px'te taşma yok,
dokunmayla okuma çalışıyor; Tarihten kartında devamı açılıyor, "Başka" ile
olay değişince detay ve öneriler de değişiyor; film kartının önerisi bozulmadı.

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

### 26 Ağustos akşam — bildirim zamanlaması yeniden kuruldu + derin bağlantı

**Erken cron + uyku YETMEDİ, ölçümle görüldü.** O günün kayıtları:

| Dilim | Bildirim düştü | Gecikme |
|---|---|---|
| 08:00 sabah rutini | 08:40 **ve 08:58** (çift) | 40 dk |
| 12:15 antrenman | 12:56 | 41 dk |
| 18:30 gitar | 19:06 | 36 dk |

18:30'unki YENİ kodla çalıştı: cron 17:55'e kuruluydu, GitHub **71 dakika**
geciktirip 16:06 UTC'de çalıştırdı. 35 dakikalık erken payın üstünde.
`schedule` gecikmesinin tavanı yok; erken pay ne olursa olsun garanti vermiyor.

**Çift bildirimin sebebi bulundu ve kapatıldı.** 08:30 cron'u her gün kalkıyor
ama Çarşamba 08:30 dilimi yok; `cron_dilimi()` eşleşme bulamayınca "en yakın
dilim" tahminine düşüyor ve 08:00 cron'unun gönderdiğini ikinci kez
gönderiyordu. Artık cron biliniyorsa tahmine DÜŞMÜYOR: o dilim bugün yoksa
sessizce çıkıyor.

**Kullanıcının kararı: dış tetikleyici.**

**ÖNEMLİ — hangi uç nokta? Üçü de ölçüldü, aralarında dağlar kadar fark var:**

| Tetik | API çağrısından koşu oluşana kadar |
|---|---|
| `schedule` (cron) | 20-71 dakika |
| `repository_dispatch` | 98 sn · 124 sn · birkaç dakika — ve dört tetiğin bir kısmı **hiç koşu üretmedi** (API 204 döndü, iş akışı başlamadı) |
| `workflow_dispatch` uç noktası | **2 saniye** |

İlk tahminim `repository_dispatch`'ti ve YANLIŞTI: "olay tabanlı tetik
gecikmez" çıkarımını elle tetiklenen bir koşunun `created_at == started_at`
olmasına bakarak yapmıştım, ama o ölçüm koşu OLUŞTUKTAN sonraki kuyruğu
ölçüyor — asıl gecikme API çağrısı ile koşunun oluşması arasında.
Ölçünce `repository_dispatch` elendi. Dış zamanlayıcı **workflow_dispatch**
uç noktasını çağırıyor; `repository_dispatch` yedek olarak açık ama güvenilmez.

Yeni bölüşüm:
- **Zamanı önemli olanlar** (spor + sabah rutini: 08:00, 08:30, 09:00, 12:15,
  13:45, 20:00) → `repository_dispatch` ile DIŞARIDAN tetikleniyor.
  Bu saatlerin cron'ları push.yml'den KALDIRILDI.
- **Gerisi** (18:30 gitar/DJ, 21:30 proje, 23:00 yatış, 23:30 kitap) → cron'da
  kaldı, 35 dk erken pay + uyku düzeneğiyle. Kullanıcı "diğerleri gelmese de
  olur" dedi, oradaki gecikme önemsiz.

Dış tetikte tahmin de uyku da yok (`TETIK=repository_dispatch`): "şu anda
başlayan dilim" aranıyor, pencere dar (`DIS_ONCE_DK=3`, `DIS_GERI_DK=8`).
Gönderme bloğu `gonder()` fonksiyonuna çıkarıldı; cron ve dış tetik aynı yolu
kullanıyor.

> **AÇIK İŞ — kullanıcı yapacak.** Dış zamanlayıcı henüz KURULMADI. O kurulana
> kadar spor ve sabah rutini bildirimi HİÇ GELMEZ (cron'ları kaldırıldı).
> Kurulum aşağıda.

#### Dış zamanlayıcı kurulumu (cron-job.org, ücretsiz)

Tek bir iş yetiyor — dilim saatlerinin hepsi 15 dakikanın katı:

- **URL:** `https://api.github.com/repos/dogukandurukan/panel/actions/workflows/push.yml/dispatches`
- **Yöntem:** POST
- **Başlıklar:**
  `Accept: application/vnd.github+json` ·
  `Authorization: Bearer <TOKEN>` ·
  `Content-Type: application/json` ·
  `X-GitHub-Api-Version: 2022-11-28`
- **Gövde:** `{"ref":"main"}`
- **Zamanlama:** dakika `0,15,30,45` · saat `8,9,12,13,20` · her gün ·
  **saat dilimi Europe/Istanbul**. Günde 20 tetik; dilimi olmayan dakikalarda
  betik hiçbir şey yapmadan çıkıyor ("şu an başlayan dilim yok").
- **TOKEN:** fine-grained PAT, yalnızca `dogukandurukan/panel` deposu,
  izin **Actions: Read and write** (workflow_dispatch bunu istiyor).
  DİKKAT: bu token depoya yazabilir ve dış bir serviste duracak. Tek depoya
  kısıtlı tutmak şart; senkronun `PANEL_GIST_TOKEN`'ı ile AYNI token olmasın.

Kurulunca sınama: cron-job.org'da "şimdi çalıştır" → Actions'ta `push-yoklama`
koşusu **birkaç saniye içinde** görünmeli, log'da `dış tetik geldi ama şu an
başlayan dilim yok` ya da gerçek bir gönderim satırı olmalı. Koşu 1-2 dakika
gecikiyorsa yanlış uç noktayı çağırıyorsundur (repository_dispatch).

Dış tetik yolunda tahmin ve uzun uyku yok; tetik dilimden birkaç dakika önce
gelirse dilim saatine kadar bekliyor (erken bildirim de işe yaramaz).
`workflow_dispatch` elle denemede de aynı yolu kullanıyor — `zorla` kutusu
işaretlenirse pencere atlanıyor.

### Bildirime dokununca ne oluyor (26 Ağustos)

Kullanıcının isteği: bildirim seni sadece götürmesin, oraya varınca
**kaydedebiliyor** ol.

- `yokPlanUret()` plana yoklama TÜRÜNÜ de yazıyor: `[saat, ad, dilim, tür]`.
  Gönderici `YOK` tablosunu tekrar yazmıyor, program tek kaynakta kalıyor.
  Gist'teki plan panel açılınca `pushPlanTazele()` ile kendiliğinden tazeleniyor;
  o ana kadar eski 3 alanlı satırlar hedefsiz çalışıyor (çökmüyor).
- `push_feed.py` türe göre hedef ekliyor: **spor → `#antrenman`**,
  **rutin → `#rutin`**. Diğer türler paneli olduğu gibi açıyor.
- `sw.js` panel zaten açıkken yalnızca focus ediyordu; aynı URL'e gitmek
  hashchange tetiklemediği için hedef artık **postMessage** ile söyleniyor.
- **Spor bildirimi antrenman modunu DOĞRUDAN açıyor** (kullanıcının kararı):
  set girme ekranı (kg / tekrar / SET ✓) hemen geliyor, ikinci düğme yok.
  Yalnızca ağırlık günlerinde. Bedeli kabul edildi: antrenman başlangıç saati
  o an kaydediliyor, gerçekten başlanmadıysa kayıt erken görünür.

**Tuzak — tek kaydırma yetmiyor.** Kartların ÜSTÜNDEKİ besleyiciler (haber,
borsa, mail) sonradan yüklenip hedefi aşağı itiyor: ilk kaydırma sayfa
kısayken doğru yere gidiyor, içerik gelince kart ekrandan çıkıyor (ölçüldü:
kart 16 px'e kaydıktan sonra 1686 px'e itildi). Bu yüzden 350/900/1800/3000 ms'de
düzeltiliyor ve kullanıcı kendi kaydırırsa bırakılıyor. Ayrıca `scrollIntoView`
yerine **mutlak konum** yazılıyor — düzeltmeler tekrar tekrar çalışacağı için
işlemin idempotent olması gerekiyor.

### Sabah rutini dinlenme sayacı (26 Ağustos)

Kullanıcının kararı: **hareketler arası dinlenme**. Bir hareketi tikleyince
sıradaki için geri sayım başlıyor, sıradaki hareket listede vurgulanıyor,
süre bitince bip çalıp kutu "sırada · <hareket>" yazıyor.

- Süre seçimi 30/45/60/90 sn, `d:rutinDin`'de saklanıyor (varsayılan 45).
- Tiki GERİ ALMAK sayacı durduruyor; rutin bitince sayaç açılmıyor.
- Antrenman modundaki dinlenme sayacıyla aynı desen: mutlak zaman damgası
  (telefon arka plana atılınca doğru kalsın), saniyede bir yalnızca sayı
  güncelleniyor — kart yeniden çizilirse tikler titriyor.
- **BELLEKTE**, kaydedilmiyor: sayfa yenilenirse sayaç düşer. Rutin 12-15 dk
  ve telefon elde; bu kadar kısa ömürlü bir değeri senkrona yazmak gürültü olur.

**Doğrulama (gerçek tarayıcı, 375×812 mobil, iki tema):** #antrenman ve #rutin
kartın tepesine oturuyor (kart üstten 13-14 px), konsol hatası yok; spor
bağlantısı antrenman modunu açıp set girişini getiriyor; rutin sayacı geri
sayıyor (0:30 → 0:28), 0'da "sırada" durumuna geçiyor, "Bitir" kapatıyor,
tik geri alınınca durmuyor-başlamıyor. Test koşumu 17 senaryo, hepsi geçti.

> **Not — ölçüm ortamı tuzağı.** Tarayıcı panelinin görünüm alanı bir ara
> sıfır yükseklikte kaldı (`innerHeight: 0`); o hâldeyken `scrollIntoView`
> birikmeli davrandı ve ekran görüntüsü boş çıktı. Gerçek bir viewport
> ayarlamadan (resize_window) ölçüm alma.

---

## 2. Kullanıcıda bekleyen işler

**Telefon bildirimi ÇALIŞIYOR** (25 Ağustos, `Antrenman (12:15) — 1/1 cihaza
gönderildi`). Secret'lar ekli: `VAPID_PRIVATE`, `PANEL_GIST_TOKEN`.

| # | İş | Nerede |
|---|---|---|
| 0 | **Ret takibi Sheet'e bağlı.** Enpal'dan gelen ret maili panele düşmedi çünkü Enpal Sheet'te kayıtlı değil; `check_rejections.py` YALNIZCA Sheet'teki şirket adlarını Gmail'de arıyor. Kullanıcı elle Sheet'e eklemek istemiyor → 4.6'daki tarama çözülecek. |
| 0 | **Dış zamanlayıcıyı kur** (cron-job.org) — kurulana kadar spor ve sabah rutini bildirimi hiç gelmez | Yukarıdaki "Dış zamanlayıcı kurulumu" bölümü |
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

### 4.6 Gündem şeridi — BİTTİ (27 Ağustos, yukarı bak)

Kullanıcı onayladı: **tam genişlikte, eşit üç sütun** — `Dünya Gündemi`
(İngilizce, mevcut altı kaynak) | `Türkiye Gündemi` (**yeni**: NTV, Habertürk
gibi RSS'ler) | `Piyasa & Şirket` (bugünkü hisse haberleri).
Ayrıca **Alışkanlık Serileri kartı yukarı** alınacak: Sabah Rutini /
"Çarşamba rutini" bölgesinin altındaki boşluğa. Grid `align-items:start`
olduğu için uzun kartlar aynı satırda boşluk bırakıyor; asıl şekilsizlik bu.

Notlar: `panel_feed.py`'de `_rss_basliklar()` hazır, Türkiye kaynakları oraya
eklenebilir (`tr` alanı). Ama borsa-feed **hafta içi 09:00/14:00** koşuyor;
Türkiye gündemi hafta sonu bayatlar — ya `world` gibi kabul edilir ya da
gmail-feed'in (her gün) içine alınır. Bu, işe başlarken verilecek karar.

### 4.7 Almanca kartı — BİTTİ (26 Ağustos, yukarı bak)

Kalan: cloze 5 kelimenin ~3'ünde çıkıyor. Çekimli fiil / çok sözcüklü kalıp
girişlerinde (`davon ausgehen, dass`) örnek cümlede kelime birebir geçmediği
için eski biçime düşüyor. İstenirse kök eşleştirme yazılabilir.

### 4.7b (eski metin) Almanca kartı — kullanıcı istedi, yapılmadı

Kart çok uzun. İstenen: kartta **yalnızca 5 kelime** kalsın; quiz ve gramer
altta tam genişlikte yatay bir şeride taşınsın. Quiz "ne demek" yerine
**cümlede boşluk doldurma** olsun — kelime havuzunda örnek cümle zaten var
(`["traurig","üzgün","Warum bist du traurig?","A2"]`), hedef kelime cümleden
silinerek üretilebilir.

### 4.8 Ret takibi: şirket listesi olmadan tarama (Enpal)

Kullanıcı Sheet'e elle satır eklemek istemiyor. Yapılacak: `check_rejections.py`
ikinci geçiş — gelen kutusunda ret kalıbı olan mailleri şirket adı olmadan
bulup gönderen alan adından şirketi çıkarmak, Sheet'te olmayanları panelde
ayrı bir liste olarak göstermek. **Dikkat:** bu veri kişisel; public repoya
JSON olarak yazılamaz (1. kural), gizli gist'e ya da doğrudan mail okumaya
gitmeli — 4.2'deki harcama kararının aynısı.

### 4.9 Yemek girişi → kalori hesabı — BİTTİ (26 Ağustos, yukarı bak)

Açık uçlar:
- Tablo ~115 besin; kullanıcı tanınmayan bir şey yazdıkça büyütülmeli
  (not satırı zaten neyin tanınmadığını yazıyor).
- Yağ (Y) hesaplanmıyor: öğün kutularında yağ alanı yok, tabloda da tutulmadı.
  İstenirse dördüncü makro eklenebilir.
- Pişirme yağı sayılmıyor ("omlet" = yumurta ağırlığı). Kullanıcı yağı ayrı
  yazarsa (`+ 1 kaşık zeytinyağı`) hesaba giriyor.
- Porsiyon çipleri (— / ½ / ✓) hesabın ÜSTÜNE çarpılıyor; otomatik hesap
  tam porsiyon içindir.

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
