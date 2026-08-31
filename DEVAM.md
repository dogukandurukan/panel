# Panel — devir notu · 29 Ağustos 2026

Kalıcı kurallar `CLAUDE.md`'de (repo public, uydurma gösterge yok, tek dosya,
iki tema, LinkedIn otomasyonu yok). **Bu dosya: panel bugün ne durumda, sırada
ne var.** Oturum oturum anlatı git geçmişinde — commit mesajları ayrıntılı.

---

## 1. Panel bugün ne durumda

`index.html` ~395 KB, tek dosya, bağımlılık yok. **29 Ağustos'ta İKİ SEKMEYE
bölündü** (tek sayfa çok uzamıştı). Kartların kendisi sekmenin içinde duruyor —
içindekiler listesi değil. Sekme seçimi `d:tab`, tema gibi CİHAZA özel
(`SYNC_SKIP`'te), telefondaki seçim Mac'i oynatmıyor.

**SABİT ŞERİT** (`.pinned` — sekmeden bağımsız, her zaman görünür; günü bunlar
yönlendiriyor, bir sekmeye gömülselerdi gün boyu sekme değiştirmek gerekirdi):

| Kart | Veri |
|---|---|
| Günün Programı | `SCHED` + `d:sched:TARİH`, görünüm ezmesi `d:schedOvr:TARİH` |
| Bugün Yapılacaklar | `d:tasks` |
| Yoklama — başlık duruma göre değişir | `YOK` + `d:yok:TARİH` |

Yoklama kartı **iki durumlu**: dilim devam ediyorsa "Şu An Ne Yapıyorsun?"
(canlı soru), dilim bittiyse "Bugünü Kapat" (bekleyenler tek listede, satır
başına ✓/✗). Cevap bekleyenler günlük dökümde tekrar listelenmez. Otomatik
"atladı" işaretlemesi YOK — uydurma veri seri hesabını bozar.

**Sekme 1 — Spor & Sağlık** (`#tabSpor` / `#gridSpor`):

| Kart | Veri |
|---|---|
| Sabah Rutini + Koşu | `MORNING_*` + `d:morning:TARİH`, `d:runkm:TARİH` |
| Bugünün Antrenmanı | `WK` + `d:ex`, `d:sess`, `d:prog`, `d:vol` |
| Kaldırılan Ağırlık (set kayıtları) | `d:wtlog` |
| Alışkanlık Serileri | mevcut tiklerden türetilir |
| Uyku Takibi | `d:sleepLog` |
| Kilo Takibi (vücut ağırlığı) | `d:bw` |
| Bugünün Yemekleri | `MP` + `d:meals:TARİH`, hedef `d:targets` |

**Sekme 2 — Gündem, Kültür & İş** (`#tabDunya` / `#gridDunya` + altında tam
genişlik şeritler):

| Kart | Veri |
|---|---|
| Gelen Kutusu | **gizli gist** `d:gmail` |
| Günün Bilgisi · Tarihten · Film · Sanatçı · Kitap | gömülü listeler + `facts.json` |
| Döviz & Piyasalar · İzleme Listesi | `borsa.json` |
| Bugün Ne Oluyor (Dünya \| Türkiye \| Piyasa) — **şerit** | `borsa.json` `world`/`tr`/`news` |
| Almanca (kelime \| quiz \| gramer) — **şerit** | gömülü havuz + `d:dequiz`, `d:deWrong` |
| Bugünün 3 İşi — **şerit** | `jobs.json` |
| İş Başvuruları — **şerit** | Google Sheet (gviz/JSONP) + `d:myApps` + `d:retler` |
| Harcama & Kazanç — **şerit** | `d:money:YYYY-AA` (tamamen elle) |
| Ajan Telemetrisi — **şerit, en altta** | api.github.com, anahtarsız |

### Veri nereden geliyor

| Üretici | Nereye yazar | Cron (TR) |
|---|---|---|
| `panel_feed.py` (+`borsa.py`) | `borsa.json` → **repo** | her gün 09:00, 14:00 |
| `jobs_feed.py` | `jobs.json` → **repo** | her gün 08:00 |
| `facts_feed.py` | `facts.json` → **repo** | Pazartesi 09:00 |
| `gmail_feed.py` | **gizli gist** `d:gmail` | 08/11/14/17/20 |
| `check_rejections.py` | Sheet "Durum" + **gizli gist** `d:retler` | gmail-feed ile birlikte |
| `push_feed.py` | bildirim gönderir | dış tetikleyici (aşağı bak) |

**Kişisel veri repoya yazılmaz** (1. kural). Gelen kutusu ve ret verisi
senkronun gizli gist'ine (`panel-data.json`) `gist_io.yaz()` ile yazılır;
panel oradan senkronla okur. Actions log'una da şirket adı/konu basılmaz —
log herkese açık.

---

## 2. AÇIK İŞLER

### A. Kullanıcının yapacakları (kod bekliyor değil)

| # | İş | Not |
|---|---|---|
| A1 | **Dış zamanlayıcıyı kur** (cron-job.org, ücretsiz) | **Kurulmadan spor/rutin bildirimi güvenilmez.** GitHub `schedule` 20-71 dk gecikiyor, tavanı yok. Uç nokta **`workflow_dispatch`** olmalı (ölçüm: 2 sn; `repository_dispatch` 98-124 sn ve bazen hiç koşmuyor). Kurulum adımları git geçmişinde: `git log --grep="dış tetikleyici"` |
| A2 | `ANTHROPIC_API_KEY` secret'ı | Mail cevap taslakları bunsuz üretilmiyor; kod hazır, sessizce devre dışı |
| A3 | Garanti mobilde "harcama bildirimi e-postası" açık mı? | 4.2'nin (harcama kartı) seviyesini bu belirliyor |

### B. Karar bekleyenler

- **"Bugünün 3 İşi" başvurunca yenisini getirmiyor.** `jobs_feed.py` havuzdan
  (23-25 ilan) yalnızca `PICK = 3` yazıyor, panelde yedek yok. Öneri:
  `PICK = 8` + panel başvurulmamış ilk 3'ü göstersin. Kullanıcı "şimdilik
  dokunmayalım" dedi.
- **Harcama verisi nereye?** Kişisel → repoya yazılamaz. `gist_io.py` hazır,
  aynı yoldan (gizli gist) gidebilir. A3 cevaplanınca netleşir.

### C. Kodlanacaklar (öncelik sırasıyla)

0. ~~UI: tek sayfa 2 sekmeye bölünsün~~ — **yapıldı (29 Ağu, canlıda).**
   Kartların KENDİSİ sekmenin içinde; içindekiler/link listesi DEĞİL.

   **DENEME SÜRECİNDE — kullanıcı tek ekrana dönebilir.** Kullanıcı 29 Ağu'da
   "biraz deneyeceğim, belki yine tek ekrana geçerim" dedi. Dönmek istersen
   TARTIŞMA AÇMA, sadece geri al:
   ```
   git revert ec11cd6      # sekme bölünmesi (index.html)
   ```
   Tek commit, temiz geri alınır. `ec11cd6` öncesi hâl = tek sayfa, tek
   `#grid`, `.duo` şeridi (Yapılacaklar + Gelen Kutusu). Sonraki commit'ler
   sekmeye dokunmadıysa çakışma çıkmaz. `d:tab` anahtarı artakalır, zararsız.
1. ~~Vücut ağırlığı takibi (`d:bw`)~~ — **yapıldı (29 Ağu, canlıda).** Kilo
   Takibi kartı (Uyku Takibi'nden sonra, Yemekler'den önce), 7g hareketli
   ortalama + haftalık trend, ±150 kcal öneri metni (bulk mantığı: 2 hafta
   sabit → +150, %0,75/hafta'dan hızlı artış → −150). Sadece metin, targets'a
   dokunmuyor — istenirse elle "hedefi düzenle"den girilir. `d:wtlog` KALDIRILAN
   kiloyu tuttuğu için o kart "Kaldırılan Ağırlık" oldu. Repoya kilo yazılmıyor,
   `d:wtlog`/`d:sleepLog` gibi localStorage + gist senkronu.
2. **Faz anahtarı (`d:phase`)** — bulk/cut. Cut'ta: protein 210-220,
   "Atladım" cezası −250 kcal'a döner, shake suyla (250 kcal), kalori
   bakım −400/500. Not: yeni Kilo Takibi'nin trend kuralı şu an yalnızca
   bulk'a göre yazılı (yukarı trend hızlıysa −150); faz anahtarı gelince
   cut'ta muhtemelen tersine (yavaş kilo kaybı → −150 yerine farklı eşik)
   çevrilmesi gerekecek — bwSuggestion()'a bak.
3. **Harcama/gelir kategorileri (4.2)** — `harcama_feed.py`, Garanti bildirim
   maillerini ayrıştırır. `gmail_feed.py`'deki `classify()`/`notify_tag()`
   deseni örnek; "Otomatik bildirim" kovası bu mailleri zaten yakalıyor.
4. **Takviye checklist (`d:supp:TARİH`)** — kreatin (her gün, seri göstergesi),
   D3, omega-3, magnezyum, whey.
5. **Yürüyüş takibi (`d:walk:TARİH`)** — sabah/akşam köpek + gym gidiş-dönüş.
   Kalori hedefine ETKİ ETMEZ (yük zaten 2950 tabanına dahil).
6. ~~Günün Programı düzenleme~~ — **yapıldı (29 Ağu, canlıda).** Saat ve iş
   metni tıklanınca inline input, `d:schedOvr:TARİH`'e kaydediyor. Kasıtlı
   olarak SADECE görünüm: "şu an" vurgusu, Yoklama ve bildirim planı hâlâ
   orijinal `SLOTS`/`SCHED`'e göre çalışıyor — ekranda yazan ile bildirimde
   sorulan iş farklı olabilir, kullanıcı bunu bilerek bu şekilde istedi
   (tam entegre versiyon SCHED'in veri modelini + `yokPlanUret`'i + push
   senkronunu değiştirmeyi gerektirirdi, çok daha büyük iş).
7. ~~Gündem kartına haber linki~~ — **yapıldı (30 Ağu).** Başlığa tıklayınca
   haberin kaynağına gidiyor (`target="_blank" rel="noopener"`).
   - `panel_feed.py`: `_link_bul()` eklendi — RSS/RDF `<link>` METİN, Atom
     `<link href>` ÖZNİTELİK (rel="self" beslemedir, `alternate` alınır),
     son çare `<guid>`. `_rss_basliklar()` artık `(başlık, link)` çifti,
     `_harmanla()` linki taşıyor. Üç şerit de `{"t","link"}` sözlüğü döndürüyor.
     11 kaynağın 11'i link veriyor (elle koşturularak doğrulandı).
   - `index.html` `newsRows()`: link http(s) ise `<a>` sarar, değilse/yoksa
     eski düz metin. **GERİYE UYUMLU** — eski `borsa.json` ve önbellekteki
     (`d:world`/`d:tr`/`d:news`) düz string'ler de basılıyor, yalnız linksiz.
   - CSS: `.news-t a` rengi metinden miras, alt çizgi düz `--line`
     (ayırıcılar noktalı `--line2`, karışmasın). İki temada da kontrol edildi.
   - **Karar:** Piyasa şeridi Google News RSS'ten geliyor, linkleri
     `news.google.com/rss/articles/...` yönlendirmesi. Kullanıcı 30 Ağu'da
     "yönlendirme kabul" dedi — linki çözmeye çalışma, kırılgan. Dünya/Türkiye
     zaten doğrudan kaynağa gidiyor.

8. ~~Antrenman kartı: dinlenme 45 sn · kas grubu sıralaması · efor düğmesi~~
   — **yapıldı (30 Ağu).**
   - Dinlenme varsayılanı 60 → **45 sn** (`sess.restSn||45`). 90/120/180
     düğmeleri duruyor: 45 sn ağır bileşikte (4 × 5-8 bench/squat) kısa kalır.
   - **`WK` sıralama kuralı: aynı kas grubu arka arkaya.** Eski dizilim
     itiş/çekiş dönüşümlüydü (bench → row → OHP → pulldown), kullanıcı
     "alakasız" buldu. Değişen günler: 1 (UPPER), 2 (LOWER), 5 (PUSH),
     6 (LEGS). Gün 4 (PULL) zaten blok blokmuş, dokunulmadı.
     **Yeni hareket eklerken bu kuralı bozma** — `WK` üstündeki nota yazıldı.
   - Gün 1'e **Incline DB press 3 × 8-12** eklendi. Haftalık göğüs 14 → 17 set;
     o güne kadar sırt 7 sete karşı göğüs 4 setti. Gün 1 artık 8 hareket.
   - **Efor etiketi:** set kaydına `z` alanı (`'k'` kolay / `'z'` zor / boş).
     Son kaydedilen sete "kolay geldi / zordu" düğmeleriyle yazılıyor, aynı
     düğmeye basınca siliniyor, cipte görünüyor. **Çift ilerleme kuralına
     KARIŞMIYOR** — kilo hâlâ yalnızca "hedef set × üst uç tekrar" ile artıyor;
     efor sadece not düşürüyor (`eforNot()`): artış oldu + zor geldiyse "aynı
     kiloda kalmak da seçenek", artış yok + kolay geldiyse "tekrarı üst uca
     taşı". Panelin kuralı: kiloyu kullanıcı adına kendiliğinden oynatma.
   - `.ana` sınıfı yalnızca `.yok-btns` içinde boyanıyormuş; seçili efor
     görünsün diye `.ss-efor .ibtn.ana` eklendi. **Aynı eksik `ssBitir`,
     `ssSonraki` ve sabah rutini `mrest` düğmelerinde de var** — onlar hâlâ
     `ibtn ana` yazıp düz görünüyor, istenirse genel kural yazılabilir.
   - `d:ex:TARİH` ve `d:sess` INDEKSE bağlı: sıra değişince eski kayıtların
     anlamı kayar. 30 Ağu'da sorun olmadı (veri sıfırlanmıştı, Pazar tam
     dinlenme). Sırayı bir daha değiştirirsen bunu hesaba kat.

9. ~~İş Başvuruları: elle ret~~ — **yapıldı (30 Ağu).** Gmail taraması yalnızca
   ret MAİLİ geleni yakalıyordu; telefonda söylenen ya da hiç dönülmeyen
   başvuru "Bekliyor" kalıyordu. Artık her satırda **`ret ✗`** düğmesi var,
   basınca satır otomatik retle **aynı** görünüyor (kırmızı rozet, Ret
   sayacına giriyor) ve `ret · geri al`'a dönüyor.
   - Anahtar: `d:retElle` = `["şirket|pozisyon", …]`, `appAnahtar()` ile
     normalize. Senkronda (SYNC_SKIP'te değil), cihazlar arası geçiyor.
   - **Durum ÜZERİNE BİNİYOR, Sheet değişmiyor** — panel Sheet'e yazamıyor
     (public site, yazma yetkisi gömülemez). `renderBasvuru` satırı KOPYALAYIP
     `r[4]='Ret'` yapıyor; kaynak dizi bozulursa geri alma çalışmıyordu.
   - Sheet/Gmail zaten "Ret" diyorsa düğme çıkmıyor (yapacak bir şey yok).
   - "Bugünün 3 İşi" kartında o ilan `✓ başvuruldu` yerine **`✗ ret`** rozeti
     alıyor (`.job-done.ret`, `--down`). Başvuru geri alınırsa elle ret işareti
     de siliniyor.

10. ~~Bugün Harcadıkların kartı~~ — **yapıldı (30 Ağu).** Sabit şeritte
   **Bugün Yapılacaklar'ın ALTINDA** (ikisi `.stack` içinde, aynı sütun).
   Kategori seçimi + tutar + not, başlıkta günün toplamı.
   - **AYRI ANAHTAR YOK:** aynı `d:money:YYYY-AA` dizisine yazıyor, yalnızca
     bugünün `k:'out'` kayıtlarını süzüyor. Ayrı anahtar olsaydı aylık toplam,
     kategori dağılımı ve Excel çıktısı bu kayıtları görmezdi.
   - Aylık kart geçmiş aya kaydırılmış olabilir (`mCur`); bu kart **her zaman**
     `thisMonth()` anahtarıyla çalışıyor (`ayKayitlari()`/`ayKaydet()`), aynı ay
     ise `mData` üzerinden. Geçen aya kaydırılmışken eklenen kayıt doğru aya
     gitti — denendi.
   - Silme aylık dizideki GERÇEK indeksi kullanıyor (süzerken indeks taşınıyor).
   - İki kart da birbirini tazeliyor: aylık karttan ekle/sil → üst kart döner,
     tersi de.
11. ~~İş Başvuruları: yalnızca 5 satır görünüyordu~~ — **yapıldı (30 Ağu).**
   Varsayılan hâlâ 5; altında **"↓ tümünü göster (N)"** düğmesi tamamını açıyor,
   "↑ ilk 5'i göster" daraltıyor. Seçim `basvuruHepsi` değişkeninde, yalnızca o
   oturumda (kayıt tutmaya değmez). Elle ret düğmesi açık listede de doğru
   satırı işaretliyor — indeks `goster` dizisine göre.

### D. Küçük açık uçlar

- **Kültür derinliği 21 gün doldu sayılır:** FILMS 21/133, ARTISTS 21/92,
  BOOKS 21/110, FACTS 21/236 kayıtta "devamı" var. ~14 Eylül'den sonra düğme
  kaybolmaya başlar; devamı yazılmalı.
- Günün Bilgisi derinliğinde **öneri yok**, yalnızca paragraf var.
- Tarihten "devamı": olay bir ÜLKEYE bağlıysa detay o ülkenin genel maddesi
  oluyor (gerçek veri ama sığ).
- Cloze quiz 5 kelimenin ~3'ünde çıkıyor; çekimli fiil/çok sözcüklü kalıpta
  eski "ne demek" biçimine düşüyor. Kök eşleştirme yazılabilir.
- `MORN_AGIR` / `MORN_BACAK` kalıpları elle yazıldı; hareket adı değişirse
  eşleşme sessizce kaybolur.
- Yemek İÇERİĞİ sabit (`MP`); yüksek hacimli günde porsiyonu büyütmek ayrı iş.
- Besin tablosu ~115 kayıt; tanınmayan yazıldıkça büyütülmeli (not satırı
  neyin tanınmadığını yazıyor). Yağ (Y) hesaplanmıyor — kutularda alan yok.
- Kültür listeleri gömülü; `index.html` 391 KB. Büyürse ayrı JSON'a taşınmalı.
- İnsan maili taraması yalnızca okunmamışları geziyor.
- Yoklama `YOK` tablosuna eklenecek/çıkarılacak iş var mı? ("bobo" bilerek dışarıda.)

---

### E. 31 Ağustos 2026 — panel ciddi kullanıma geçti

Kullanıcı 30 Ağu (Pazar) "artık geliştirme değil, 31 Ağustos'tan itibaren
gerçekten kullanacağım" dedi. Geliştirme sırasında biriken deneme kayıtları
**bir kerelik sıfırlama** ile silindi (`RESET_VERSION='2026-08-31-temiz'`,
`sifirla()` — TARGETS_VERSION deseninin aynısı, damgayı taşımayan cihaz kendi
açılışında bir kez temizliyor).

- **Silinen:** `d:morning: d:runkm: d:ex: d:sess: d:meals: d:water: d:dequiz:
  d:yok: d:sched: d:schedOvr:` önekleri + `d:prog d:vol d:volFill d:deWrong
  d:tasks d:water d:sleepLog d:wtlog d:bw`. Alışkanlık serileri bu tiklerden
  hesaplandığı için onlar da sıfırdan başlıyor.
- **Korunan (kullanıcı öyle istedi):** `d:sync` (token!), `d:targets` +
  `d:targetsVer`, `d:money:*`, `d:myApps`, `d:jobsApplied`, `d:jobProfile`,
  `d:theme`, `d:tab`, besleme önbellekleri.
- **İki tuzak, ikisi de çözüldü:** (1) silinen anahtarın `d:mtime` damgası
  BUGÜNE çekiliyor — yoksa yedekteki eski değer `mergeRemote`'un "uzak daha
  yeni mi" testini geçip geri geliyordu. (2) `d:resetVer` **`SYNC_SKIP`'te**:
  senkronla yayılsaydı ikinci cihaz "zaten sıfırlandı" sanıp kendi eski
  verisini silmez, sonra yedeğe geri basardı.
- `d:volFill` sıfırlama sonrası kendini yeniden yazıyor (geri doldurma bayrağı,
  `d:vol` boş kaldığı için zararsız) — beklenen davranış.
- Yeni bir sıfırlama gerekirse: `RESET_VERSION`'ı değiştir, yeter.

---

## 3. Bilinen sorunlar / doğrulanmamış olanlar

**Zamanlanmış işler düzensiz.** 27 Ağustos'ta 14 saat hiç dönmedi; 28'inde
döndü ama saatleri şaşkın (borsa-feed 06:00/11:00 UTC yerine 18:30 ve 21:17'de
koştu). Feed'ler için sorun değil (veri birkaç saat geç tazelenir), **bildirim
için ölümcül** — çözümü A1'deki dış zamanlayıcı. Kontrol:
`gh run list --event schedule --limit 8` ya da panelin Ajan Telemetrisi kartı.

**Git geçmişinde eski `gmail.json` sürümleri duruyor** (gönderen adı/adresi,
konu). İleriye dönük sızıntı durdu; geçmişi temizlemek `git filter-repo` +
force-push ister, repoya push eden başka oturumlar olduğu için yapılmadı.

**`d:vol` tabanı en az 2 aynı-haftagünü kaydı istiyor** → hacme bağlı karb
ayarı yeni programın ilk iki haftasında devreye girmeyecek. Kart bunu yazıyor.

**Canlı sayfa bazen sandbox'tan doğrulanamıyor** (proxy `github.io`'ya 403).
O durumda dağıtım yalnızca Actions kaydından okunur. iOS ana ekran kısayolu
önbellek tutabiliyor; değişiklik görünmezse sert yenileme.

---

## 4. Bu projede öğrenilmiş tuzaklar (kalıcı)

1. **localStorage varsayılanı ezer.** `DEFAULT_TARGETS`'ı değiştirmek yetmez;
   `TARGETS_VERSION` bump edilmezse eski kayıt geri yazar.
2. **`targets.c` haftalık taban DEĞİL** — sürüm göçünde O GÜNÜN karbıyla
   tohumlanıyor. Günlük kcal için ayrı `CARB_BAZ` sabiti var.
3. **`gviz` fetch() ile çalışmaz** (CORS). İş Başvuruları JSONP kullanıyor.
4. **ElementTree'de `find(a) or find(b)` tuzağı:** çocuğu olmayan Element
   falsy; RSS başlıkları sessizce boş dönüyordu. Açıkça `is not None`.
5. **HTML temizlerken önce `html.unescape`, SONRA etiket sil.**
6. **Türkçe `lower()` tuzağı:** `İ` → `i`+U+0307; süzgeçler sessizce boşa
   çalışıyordu. `_kucult()` kullan.
7. **Veri biçimi değişince geçiş kodu yaz** (`myApps`, `d:morning` ad
   anahtarına göçü, `d:vol` geri doldurma).
8. **Blok yerleştirirken (python splice) neyi sildiğini kontrol et.**
9. **Test etmeden "çalışıyor" deme.** `/ret/i` "Reddedildi" ile eşleşmiyordu;
   `won't be taking` kalıp listesindeki `not be taking` ile eşleşmiyordu.
10. **Sıra korumalı sütun yerleştirme:** kartlar "en kısa sütuna" atılırsa
    kullanıcının akışı dağılır. `gridDiz()` sırayla bölüyor; ölçüm için önce
    hepsi 1. sütuna konur (boy sütun genişliğine bağlı).
11. **Dokunmatikte `pointerleave` parmak kalkınca da atıyor** — grafik imleci
    yalnız `pointerType==='mouse'` iken kapatılıyor.
12. **GİZLİ SEKMENİN GRIDİ ÖLÇÜLEMEZ.** `display:none` altındaki kartın
    `offsetHeight`'ı 0; `gridDizBir()` gizli gridde dizmeyi ATLIYOR, sekme
    açılınca (`tabGec`) yapıyor. Yeni bir kart/sekme eklerken bunu koru,
    yoksa kartlar tek sütuna yığılır. Pencere boyutu gizli sekmedeyken
    değişirse o grid bayat kalır — açılışta düzeliyor, bu kasıtlı.
13. **Bir karta kaydıran her yol önce sekmesini açmalı** (`tabAc(el)`).
    Bildirim derin bağlantısı (`bildirimeGit`) ve yoklama→antrenman geçişi
    bunu yapıyor; yeni bir "şu karta git" akışı eklersen aynısını yap,
    yoksa gizli sekmedeki karta kaydırıp sayfayı boşuna oynatırsın.
14. **Gizli sekmede `scrollHeight` de 0.** Öğün metni textarea'sının boyu
    içeriğe göre ayarlanıyor (`mealBoy`); gizliyken ölçülemediği için
    atlanıyor, `tabGec` açılışta `mealBoyHepsi()` ile düzeltiyor. İçeriğe
    göre boyutlanan YENİ bir alan eklersen aynı deseni kur (12. maddenin
    kardeşi — ölçüme dayanan her şey bu tuzağa düşer).

---

## 5. Çalışma yöntemi

- Kullanıcı Türkçe konuşur, öz cevap ister. **Ürün kararını kullanıcı verir.**
- Repo yerelde kalıcı değil: `cd "$SCRATCHPAD" && git clone .../panel.git`
- Değişiklikten sonra: yerelde sun (`python3 -m http.server 8901`) → Chrome ile
  doğrula (`playwright`, `channel="chrome"`; ms-playwright indirilemiyor,
  sistem Chrome'u kullan) → **7 günü de gez** (`context.clock.install`) →
  **iki temayı da** render et → kişisel veri taraması → commit + push →
  canlıda doğrula (`curl | grep`).
- JS sözdizimi: `<script>` bloklarını çıkarıp `node --check`.
- Repoya başka oturumlar da push ediyor: push öncesi `git fetch && rebase`.

---

## 6. Oturum geçmişi (özet — ayrıntı commit mesajlarında)

| Tarih | Ne yapıldı |
|---|---|
| 25 Ağu | Borsa kartı: 90 günlük sparkline, dünya piyasaları, TradingView bağlantısı |
| 26 Ağu | Borsa ikiye bölündü + grafikte imleç · Tarihten "devamı" · sayfa düzeni (sütun yerleştirme) · yemek metninden kalori hesabı · bildirim zamanlaması + derin bağlantı |
| 27 Ağu | Gündem şeridi (Dünya/Türkiye/Piyasa) · ret takibi (Sheet'siz tarama) · `gmail.json` gizli gist'e taşındı · **program v2** (UL+PPL, 2950 kcal) |
| 28 Ağu | Kart sırası kullanıcının akışına göre kuruldu · Almanca tek şerit · dinlenme 90→60 sn |
