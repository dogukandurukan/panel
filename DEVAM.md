# Panel — devir notu · 4 Eylül 2026

Kalıcı kurallar `CLAUDE.md`'de (repo public, uydurma gösterge yok, tek dosya,
iki tema, LinkedIn otomasyonu yok). **Bu dosya: panel bugün ne durumda, sırada
ne var, neye dokunulmayacak.** Oturum oturum anlatı git geçmişinde — commit
mesajları ayrıntılı, `git log --oneline` ile bak.

**Kullanıcı paneli 31 Ağustos 2026'da ciddi kullanmaya başladı.** Artık
geliştirme değil, gerçek veri var. Deneme kaydı bırakma, bırakırsan temizle.

---

## 1. Panel bugün ne durumda

`index.html` ~400 KB, tek dosya, bağımlılık yok. **İKİ SEKME** (tek sayfa çok
uzamıştı). Kartların kendisi sekmenin içinde. Sekme seçimi `d:tab`, tema gibi
CİHAZA özel (`SYNC_SKIP`'te).

**SABİT ŞERİT** (`.pinned` — sekmeden bağımsız, hep görünür):

| Kart | Veri |
|---|---|
| Günün Programı | `SCHED` + `d:sched:TARİH`, görünüm ezmesi `d:schedOvr:TARİH` |
| Bugün Yapılacaklar | `d:tasks` |
| ↳ **Bugün Harcadıkların** (aynı sütunda, `.stack`) | `d:money:YYYY-AA`, bugünün `out` kayıtları |
| Yoklama — başlık duruma göre değişir | `YOK` + `d:yok:TARİH` |

Yoklama **iki durumlu**: dilim sürüyorsa "Şu An Ne Yapıyorsun?", bittiyse
"Bugünü Kapat". Otomatik "atladı" işaretlemesi YOK — uydurma veri seriyi bozar.

**Sekme 1 — Spor & Sağlık** (`#tabSpor` / `#gridSpor`):

| Kart | Veri |
|---|---|
| Sabah Rutini + Koşu | `MORNING_*` + `d:morning:TARİH`, `d:runkm:TARİH` |
| Bugünün Antrenmanı | `WK` + `d:ex`, `d:sess`, `d:prog`, `d:vol` |
| Kaldırılan Ağırlık | `d:wtlog` |
| Alışkanlık Serileri | mevcut tiklerden türetilir |
| Uyku Takibi | `d:sleepLog` |
| Kilo Takibi | `d:bw` |
| Bugünün Yemekleri | `MP` + `d:meals:TARİH`, hedef `d:targets` |
| **Haftalık Değerlendirme** — şerit, en altta | yukarıdakilerin son 7 günü |

**Sekme 2 — Gündem, Kültür & İş** (`#tabDunya` / `#gridDunya` + şeritler):

| Kart | Veri |
|---|---|
| Gelen Kutusu | **gizli gist** `d:gmail` |
| Günün Bilgisi · Tarihten · Film · Sanatçı · Kitap | gömülü listeler + `facts.json` |
| Döviz & Piyasalar · İzleme Listesi | `borsa.json` |
| Bugün Ne Oluyor (Dünya \| Türkiye \| Piyasa) — şerit | `borsa.json`, başlıklar **linkli** |
| Almanca (kelime \| quiz \| gramer) — şerit | gömülü havuz + `d:dequiz`, `d:deWrong` |
| Bugünün 3 İşi — şerit | `jobs.json` |
| İş Başvuruları — şerit | Sheet (gviz/JSONP) + `d:myApps` + `d:retler` + `d:retElle` |
| Harcama & Kazanç — şerit | `d:money:YYYY-AA` + gün gün döküm |
| Ajan Telemetrisi — şerit, en altta | api.github.com, anahtarsız |

### Veri nereden geliyor

| Üretici | Nereye yazar | Cron (TR) |
|---|---|---|
| `panel_feed.py` (+`borsa.py`) | `borsa.json` → **repo** | her gün 09:00, 14:00 |
| `jobs_feed.py` | `jobs.json` → **repo** | her gün 08:00 |
| `facts_feed.py` | `facts.json` → **repo** | Pazartesi 09:00 |
| `gmail_feed.py` | **gizli gist** `d:gmail` | 08/11/14/17/20 |
| `check_rejections.py` | Sheet "Durum" + **gizli gist** `d:retler` | gmail-feed ile |
| `push_feed.py` | bildirim gönderir | dış tetikleyici (A1) |

**Kişisel veri repoya yazılmaz** (1. kural). Gelen kutusu ve ret verisi
senkronun gizli gist'ine (`panel-data.json`) `gist_io.yaz()` ile yazılır.
Actions log'una da şirket adı/konu basılmaz — log herkese açık.

---

## 2. AÇIK İŞLER

### A. Kullanıcının yapacakları (kod bekliyor değil)

| # | İş | Not |
|---|---|---|
| A1 | **Dış zamanlayıcıyı kur** (cron-job.org, ücretsiz) | **Kurulmadan spor/rutin bildirimi güvenilmez.** GitHub `schedule` 20-71 dk gecikiyor. Uç nokta **`workflow_dispatch`** olmalı (2 sn; `repository_dispatch` 98-124 sn). Adımlar: `git log --grep="dış tetikleyici"` |
| A2 | `ANTHROPIC_API_KEY` secret'ı | Mail cevap taslakları bunsuz üretilmiyor; kod hazır, sessizce devre dışı |
| A3 | Garanti mobilde "harcama bildirimi e-postası" açık mı? | C3'ün (harcama feed'i) seviyesini bu belirliyor |

### B. Karar bekleyenler

- **"Bugünün 3 İşi" başvurunca yenisini getirmiyor.** `jobs_feed.py` havuzdan
  (23-25 ilan) yalnızca `PICK = 3` yazıyor, panelde yedek yok. Öneri:
  `PICK = 8` + panel başvurulmamış ilk 3'ü göstersin. Kullanıcı "şimdilik
  dokunmayalım" dedi — **sorulmadan değiştirme.**
- **Harcama verisi nereye?** Şu an `d:money:*` localStorage + senkron gist.
  Repoya yazılamaz. A3 cevaplanınca `harcama_feed.py` netleşir.

### C. Kodlanacaklar (öncelik sırasıyla)

1. **Faz anahtarı (`d:phase`)** — bulk/cut. Cut'ta: protein 210-220, "Atladım"
   cezası −250 kcal'a döner, shake suyla (250 kcal), kalori bakım −400/500.
   **Haftalık Değerlendirme'nin hüküm mantığı şu an yalnız bulk'a göre
   yazılı** (`renderHaftalik()` içindeki dört dal); faz gelince cut için
   tersine çevrilmeli. `bwSuggestion()` de aynı durumda.
2. **Harcama/gelir kategorileri** — `harcama_feed.py`, Garanti bildirim
   maillerini ayrıştırır. `gmail_feed.py`'deki `classify()`/`notify_tag()`
   deseni örnek; "Otomatik bildirim" kovası bu mailleri zaten yakalıyor.
   A3'e bağlı.
3. **Takviye checklist (`d:supp:TARİH`)** — kreatin (her gün, seri
   göstergesi), D3, omega-3, magnezyum, whey.
4. **Yürüyüş takibi (`d:walk:TARİH`)** — sabah/akşam köpek + gym gidiş-dönüş.
   Kalori hedefine ETKİ ETMEZ (yük zaten 2950 tabanına dahil).
5. **Kültür derinliği** — FILMS/ARTISTS/BOOKS/FACTS'te 21 günlük "devamı"
   metni var, **~14 Eylül'den sonra düğme kaybolmaya başlar.** Devamı yazılmalı.

### D. Küçük açık uçlar

- Günün Bilgisi derinliğinde **öneri yok**, yalnızca paragraf var.
- Tarihten "devamı": olay bir ÜLKEYE bağlıysa detay o ülkenin genel maddesi
  oluyor (gerçek veri ama sığ).
- Cloze quiz 5 kelimenin ~3'ünde çıkıyor; çekimli fiil/çok sözcüklü kalıpta
  eski "ne demek" biçimine düşüyor. Kök eşleştirme yazılabilir.
- `MORN_AGIR` / `MORN_BACAK` kalıpları elle yazıldı; hareket adı değişirse
  eşleşme sessizce kaybolur.
- Yemek İÇERİĞİ sabit (`MP`); yüksek hacimli günde porsiyonu büyütmek ayrı iş.
- Besin tablosu ~115 kayıt; tanınmayan yazıldıkça büyütülmeli. Yağ (Y)
  hesaplanmıyor — kutularda alan yok.
- Kültür listeleri gömülü; `index.html` ~400 KB. Büyürse ayrı JSON'a taşınmalı.
- İnsan maili taraması yalnızca okunmamışları geziyor.
- `.ana` (seçili düğme) sınıfı yalnızca `.yok-btns` ve `.ss-efor` içinde
  boyanıyor. `ssBitir`, `ssSonraki` ve sabah rutini `mrest` düğmeleri
  `ibtn ana` yazıp düz görünüyor. Genel kural yazılabilir.
- Yoklama `YOK` tablosuna eklenecek/çıkarılacak iş var mı? ("bobo" bilerek
  dışarıda.)

---

## 3. VERİLMİŞ KARARLAR — tekrar açma, "hata" sanıp düzeltme

| Karar | Tarih | Gerekçe |
|---|---|---|
| **Cumartesi koşusu seriye SAYILMAZ.** `SCHED[6]`'da "Koşu + kahve + kahvaltı" var ama `WK[6].run=false` | 3 Eyl | Kullanıcı "bazen koşuyorum, zorunlu değil" dedi. Km girilip kaydediliyor, seriyi ne kırıyor ne uzatıyor. Pazar'daki "Bisiklet" de koşu sayılmıyor — bisiklet koşu değil. |
| **Piyasa haber linkleri Google yönlendirmesine gidiyor** (`news.google.com/rss/articles/...`) | 30 Ağu | Kullanıcı kabul etti. Linki çözmeye çalışma — kırılgan. Dünya/Türkiye zaten doğrudan kaynağa gidiyor. |
| **`WK` sıralaması: aynı kas grubu ARKA ARKAYA** | 30 Ağu | Eski dizilim itiş/çekiş dönüşümlüydü (bench → row → OHP → pulldown), kullanıcı "alakasız" buldu. Yeni hareket eklerken bu kuralı bozma. Gün 5'te OHP göğüs bloğundan sonra geliyor — bilinen bedel, kabul edildi. |
| **Günün Programı düzenlemesi SADECE GÖRÜNÜM** | 29 Ağu | `d:schedOvr:TARİH` yalnız ekranı değiştiriyor; yoklama ve bildirim hâlâ orijinal `SLOTS`/`SCHED`'e bakıyor. Kullanıcı bunu bilerek böyle istedi (tam entegrasyon `SCHED`'in veri modelini + `yokPlanUret`'i + push senkronunu değiştirmeyi gerektirirdi). |
| **İki sekme DENEME sürecinde** | 29 Ağu | Kullanıcı tek ekrana dönmek isterse **TARTIŞMA AÇMA**, sadece `git revert ec11cd6`. Tek commit, temiz geri alınır. `d:tab` artakalır, zararsız. |
| **LLM / Jarvis bağlanmadı** | 3 Eyl | Konuşuldu, kullanıcı "çok gerek görmedim" dedi. Günlük brifing reddedildi (veri zaten ekranda). Doğal dille giriş istenirse önce **yerel ayrıştırıcı** yazılacak (anahtarsız, çevrimdışı, gizlilik sorunsuz); model ancak o yetmezse yedek olarak. Kendiliğinden yeniden önerme. |
| **`PICK = 3`'e dokunulmadı** | — | B bölümüne bak. |

---

## 4. Bilinen sorunlar / doğrulanmamış olanlar

**Zamanlanmış işler düzensiz.** Saatler şaşabiliyor (borsa-feed 06:00/11:00 UTC
yerine 18:30'da koştuğu oldu). Feed'ler için sorun değil, **bildirim için
ölümcül** — çözümü A1. Kontrol: `gh run list --event schedule --limit 8`.

**Git geçmişinde eski `gmail.json` sürümleri duruyor** (gönderen adı/adresi,
konu). İleriye dönük sızıntı durdu; geçmişi temizlemek `git filter-repo` +
force-push ister, repoya push eden başka oturumlar olduğu için yapılmadı.

**`d:vol` tabanı en az 2 aynı-haftagünü kaydı istiyor** → hacme bağlı karb
ayarı programın ilk iki haftasında devreye girmiyor. Kart bunu yazıyor.

**Haftalık Değerlendirme 2. haftadan önce eksik.** Kalori/protein ilk haftadan
çalışır; tonaj karşılaştırması ve kilo trendi iki haftalık kayıt ister. O
satırlar "karşılaştırma için iki hafta kayıt gerekiyor" der, sayı uydurmaz.

**Canlı sayfa bazen sandbox'tan doğrulanamıyor** (proxy `github.io`'ya 403).
iOS ana ekran kısayolu önbellek tutabiliyor; değişiklik görünmezse sert yenile.

---

## 5. Bu projede öğrenilmiş tuzaklar (kalıcı)

1. **localStorage varsayılanı ezer.** `DEFAULT_TARGETS`'ı değiştirmek yetmez;
   `TARGETS_VERSION` bump edilmezse eski kayıt geri yazar.
2. **Kullanıcının kalori ayarı `kcalOfs`'ta.** Haftalık Değerlendirme'nin
   "uygula" düğmesi ve elle "hedefi düzenle" bu damgayı yazıyor; sürüm göçü
   farkı YENİ tabanın üzerine tekrar bindiriyor. Yeni bir hedef alanı
   eklersen aynı deseni kur, yoksa sürüm bump'ı kullanıcının ayarını siler.
3. **`targets.c` haftalık taban DEĞİL** — sürüm göçünde O GÜNÜN karbıyla
   tohumlanıyor. Günlük kcal için ayrı `CARB_BAZ` sabiti var.
4. **Program günleri değişince DÖRT tablo birlikte güncellenir:** `WK`,
   `SCHED`, `MORNING_SHORT`, `MP`. 27 Ağu'da `SCHED` atlandı, 3 Eylül'e kadar
   Perşembe öğlen "Dinlenme + uyku" yazdı ve o gün spor yoklaması hiç
   sorulmadı (yoklama `SCHED`'den, bildirim yoklamadan türüyor).
   **Kontrol:** her ağırlık gününde 12:15 dilimi "Antrenman" olmalı, ağırlık
   olmayan günde olmamalı.
5. **`d:ex` ve `d:sess` İNDEKSE bağlı.** `WK`'da sıra değişirse eski
   kayıtların anlamı kayar. 30 Ağu'daki sıralama değişiminde sorun olmadı
   (veri sıfırlanmıştı, Pazar tam dinlenmeydi) — bir daha değiştirirsen
   hesaba kat.
6. **Anahtar silerken `d:mtime` damgasını bugüne çek.** Silme mtime'a
   dokunmuyor; yedekteki eski değer `mergeRemote`'un "uzak daha yeni mi"
   testini geçip geri geliyor (`sifirla()` bunu yapıyor).
7. **`gviz` fetch() ile çalışmaz** (CORS). İş Başvuruları JSONP kullanıyor.
8. **ElementTree'de `find(a) or find(b)` tuzağı:** çocuğu olmayan Element
   falsy; RSS başlıkları sessizce boş dönüyordu. Açıkça `is not None`.
   Aynı yerde: RSS'te `<link>` METİN, Atom'da `<link href>` ÖZNİTELİK.
9. **HTML temizlerken önce `html.unescape`, SONRA etiket sil.**
10. **Türkçe `lower()` tuzağı:** `İ` → `i`+U+0307; süzgeçler sessizce boşa
    çalışıyordu. `_kucult()` kullan.
11. **Veri biçimi değişince geçiş kodu yaz** (`myApps`, `d:morning` ad
    anahtarına göçü, `d:vol` geri doldurma, haber string→sözlük).
12. **Blok yerleştirirken (python splice) neyi sildiğini kontrol et.**
13. **Test etmeden "çalışıyor" deme.** `/ret/i` "Reddedildi" ile eşleşmiyordu;
    `won't be taking` kalıp listesindeki `not be taking` ile eşleşmiyordu.
14. **Sıra korumalı sütun yerleştirme:** kartlar "en kısa sütuna" atılırsa
    kullanıcının akışı dağılır. `gridDiz()` sırayla bölüyor.
15. **Dokunmatikte `pointerleave` parmak kalkınca da atıyor** — grafik imleci
    yalnız `pointerType==='mouse'` iken kapatılıyor.
16. **GİZLİ SEKMENİN GRIDİ ÖLÇÜLEMEZ.** `display:none` altındaki kartın
    `offsetHeight`'ı 0; `gridDizBir()` gizli gridde dizmeyi ATLIYOR, sekme
    açılınca (`tabGec`) yapıyor. Yeni kart/sekme eklerken bunu koru.
17. **Bir karta kaydıran her yol önce sekmesini açmalı** (`tabAc(el)`).
18. **Gizli sekmede `scrollHeight` de 0.** Öğün textarea boyu (`mealBoy`)
    gizliyken ölçülemiyor, `tabGec` açılışta `mealBoyHepsi()` ile düzeltiyor.
    İçeriğe göre boyutlanan YENİ alan eklersen aynı deseni kur.
19. **Hesap penceresi ile toplam penceresi aynı olmalı.** Haftalık
    Değerlendirme'de ortalama "bugüne kadar"a bölünürken toplam ileri tarihli
    kaydı da içeriyordu, ortalama uçuyordu. Ay sonu tahmininde de sabit gideri
    günlük ortalamayla çarpmak kirayı 30 kez saydırıyordu.
20. **Kaydı olan ama boş gün ≠ sıfır.** Yemek kaydı var ama porsiyon
    işaretlenmemişse "0 kcal yedim" değil "girilmemiş" sayılır; yoksa
    ortalama sahte biçimde düşer. Kaç güne bölündüğü ekranda yazar.

---

## 6. Çalışma yöntemi

- Kullanıcı Türkçe konuşur, **öz cevap ister** (adım adım anlatma).
  **Ürün kararını kullanıcı verir** — belirsizse sor, uydurma.
- **Repo `~/panel`'de duruyor ama BAYAT olabilir.** İlk iş:
  `cd ~/panel && git fetch && git pull --ff-only`. (4 Eylül oturumunda 13
  commit gerideydi; `DEVAM.md`'de madde yok sanıp yanlış rapor verilecekti.)
  Feed'ler repoya otomatik commit atıyor, arada başka oturum da push ediyor.
- Değişiklikten sonra sırayla: yerelde sun (`python3 -m http.server 8901`) →
  tarayıcıda **gerçek veriyle** doğrula → **iki temayı da** kontrol et
  (`data-theme` = `almanak` / `hud`) → gerekiyorsa 7 günü de gez (`dow`
  sabitlenmiş test kopyası en kolayı) → kişisel veri taraması → commit + push
  → canlıda doğrula.
- JS sözdizimi: `<script>` bloklarını çıkarıp `node --check`.
- Kişisel veri taraması (push öncesi, 1. kural):
  `grep -rInE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(\+90|0)5[0-9]{9}|gh[pousr]_[A-Za-z0-9]{20,}|sk-ant-" index.html *.py`
- Canlı doğrulama: `curl -s "https://dogukandurukan.github.io/panel/index.html?cb=1" | LC_ALL=C grep -c "YENİ_ŞEY"`.
  **`LC_ALL=C` şart** — kabuk değişkenine alıp grep'lersen Türkçe karakterde
  "character not in range" verip sessizce eşleşmiyor.
- Push öncesi `git fetch && git rebase origin/main`.

---

## 7. Oturum geçmişi (özet — ayrıntı commit mesajlarında)

| Tarih | Ne yapıldı |
|---|---|
| 25 Ağu | Borsa kartı: 90 günlük sparkline, dünya piyasaları, TradingView bağlantısı |
| 26 Ağu | Borsa ikiye bölündü + grafikte imleç · Tarihten "devamı" · sayfa düzeni · yemek metninden kalori · bildirim zamanlaması + derin bağlantı |
| 27 Ağu | Gündem şeridi · ret takibi · `gmail.json` gizli gist'e · **program v2** (UL+PPL, 2950 kcal) |
| 28 Ağu | Kart sırası kullanıcının akışına göre · Almanca tek şerit · dinlenme 90→60 sn |
| 29 Ağu | **İki sekmeye bölündü** (deneme) · Kilo Takibi kartı · Günün Programı düzenleme · yoklama iki durumu |
| 30 Ağu | Gündem başlıkları linklendi · **bir kerelik sıfırlama** (rutin/alışkanlık/uyku/kilo verisi temizlendi, `RESET_VERSION`) |
| 31 Ağu | **Panel ciddi kullanıma geçti.** Antrenman: 45 sn dinlenme + kas grubu sıralaması + efor etiketi · İş Başvuruları elle ret · Bugün Harcadıkların kartı · başvuru listesinde "tümünü göster" |
| 1 Eyl | Harcama gün gün döküm + sabit gider ayrımı + tarih alanı · **Haftalık Değerlendirme kartı** |
| 3 Eyl | **`SCHED` düzeltildi** (aktivite günü Perşembe→Çarşamba, v2 ile ayrışmıştı) · alışkanlık paydasından bilgi satırları çıkarıldı · LLM tartışıldı, eklenmedi |
