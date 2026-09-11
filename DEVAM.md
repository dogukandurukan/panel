# Panel — devir notu · 11 Eylül 2026

Kalıcı kurallar `CLAUDE.md`'de (repo public, uydurma gösterge yok, tek dosya,
iki tema, LinkedIn otomasyonu yok). **Bu dosya: panel bugün ne durumda, sırada
ne var, neye dokunulmayacak.** Oturum oturum anlatı git geçmişinde — commit
mesajları ayrıntılı, `git log --oneline` ile bak.

**Kullanıcı paneli 31 Ağustos 2026'da ciddi kullanmaya başladı.** Artık
geliştirme değil, gerçek veri var. Deneme kaydı bırakma, bırakırsan temizle.

## ⏳ TARİHİ GEÇECEK ŞEYLER — önce buna bak

| Ne | Ne zaman | Yapılacak |
|---|---|---|
| **Kültür derinliği** | **6 Ekim** | Dört listede 44'er kayıt var, sonrası boş. Yazılmadan önce ayrı JSON'a taşıma kararı verilmeli (dosya 518 KB). |

**Sakatlık uyarlaması 12 Eylül'de BİTTİ** (11 Eyl'de kullanıcı bildirdi).
15-22 Eylül kayıtları `EX_OVR`'dan silindi, 15 Eylül Salı'dan itibaren normal
`WK` işliyor. Geçmiş günler (10-12 Eyl) duruyor — silinseydi o günlerin
tikleri yanlış programla eşleşirdi. Kalıpları geri gerekirse:
`git show 237feca^:index.html` (KOSU_CORE, LOWER_MAKINE).

**Sağlık kuralı (9 Eyl'de eklendi, duruyor):** programı etkileyen KISIT
yazılır, sebebi yazılmaz. Depo herkese açık; sağlık bilgisi 1. kuralın
yasakladığı kişisel verinin en hassas türü ve git geçmişi kalıcı.

---

## 1. Panel bugün ne durumda

`index.html` ~518 KB, tek dosya, bağımlılık yok. **İKİ SEKME** (tek sayfa çok
uzamıştı). Kartların kendisi sekmenin içinde. Sekme seçimi `d:tab`, tema gibi
CİHAZA özel (`SYNC_SKIP`'te).

**ÖNERİ BANDI** (`#oneriBox` — sabit şeridin de sekmelerin de üstünde):
Dokuz kurallık deterministik motor (`ONERI` tablosu). Kurallar aşağıdaki
kartların verisinden türüyor, yeni anahtar istemiyor; `d:oneriKapali` her
öneriyi `[×]` ile 7 gün susturuyor. **Hiçbir kural tetiklenmezse bant
`hidden`** — boşluk bile bırakmıyor. Sonuç `d:oneri`'ye yazılıyor, senkron
gist'e taşıyor, `push_feed.py` 24 saatten tazeyse bildirimin gövdesine
tek satır ekliyor.

| Kural | Alan | Neye bakıyor |
|---|---|---|
| `kcal-hukum` | spor | `hdHukum()` — Haftalık Değerlendirme'nin hükmü, [Uygula] düğmesiyle |
| `protein-dusuk` | spor | 7 günlük protein açığı (en az 4 gün kaydı) |
| `hareket-tikandi` | spor | `takiliSeans()` ≥ 3 olan program hareketleri |
| `tonaj-dusus` | spor | `d:vol` 2 hafta üst üste düşüyor |
| `zorlanma` | spor | Seans kapanışı (`d:sess:*.his`): aynı bölge 2+ kez ya da 2+ "çok zor" |
| `kategori-sicrama` | para | Kategori, geçen ayın **aynı gün penceresine** göre %60+ ve ≥₺500 |
| `ay-sonu-acik` | para | Değişken gider tempo + kalan sabit gider > gelir |
| `basvuru-tempo` | is | Son 7 gün, önceki 7 günün yarısından az |
| `donus-yok` | is | 21 günde ≥10 başvuru ve **hiç** ret/dönüş eşleşmesi yok |

**MUAF GÜN ve 14 GÜNLÜK PLAN** (9 Eyl): Antrenman kartındaki `14 gün ↓`
düğmesi önümüzdeki iki haftayı listeliyor ve her satırda `muaf` düğmesi var.
Muaf gün `d:off` anahtarında (tek anahtar, `{tarih:1}`) tutuluyor.
Muaf günde: `gunProg` MUAF_GUN döndürüyor (alışkanlıklar 'skip', seri
kırılmıyor), `gunSched` takip edilen işleri boşaltıyor (yoklama yok,
bildirim yok), `hdTopla` günü tamamen atlıyor (tatilde tutturulmayan
kalori haftanın hükmünü bozmuyor). Takip edilmeyen işler (İş, Yemek)
ekranda duruyor.

**SABİT ŞERİT** (`.pinned` — sekmeden bağımsız, hep görünür):

| Kart | Veri |
|---|---|
| Günün Programı — **← → ile gün gezinme** | `SCHED` + `d:sched:TARİH`, görünüm ezmesi `d:schedOvr:TARİH` |
| Bugün Yapılacaklar | `d:tasks` |
| ↳ **Bugün Harcadıkların** (aynı sütunda, `.stack`) | `d:money:YYYY-AA`, bugünün `out` kayıtları |
| Yoklama — başlık duruma göre değişir | `YOK` + `d:yok:TARİH` |

**GÜN GEZİNME (11 Eyl):** Günün Programı başlığındaki `←` `→` ±30 gün
geziyor, `bugün` düğmesi geri getiriyor. Başka gün **SALT OKUNUR** — tik
`d:sched:BUGÜN`'e, düzenleme `d:schedOvr:BUGÜN`'e yazıyor, yarının satırını
tiklemek bugünün kaydını bozardı. Gezinilen günün altında o günün antrenmanı
(başlık + hareket listesi) ve `bu günü muaf yap` düğmesi var. Gezinilen gün
`schedGun` değişkeninde, CİHAZA BİLE yazılmıyor: sayfa yenilenince bugüne
dönüyor, "hangi gündeydim" şaşkınlığı olmasın.

Yoklama **iki durumlu**: dilim sürüyorsa "Şu An Ne Yapıyorsun?", bittiyse
"Bugünü Kapat". Otomatik "atladı" işaretlemesi YOK — uydurma veri seriyi bozar.

**Sekme 1 — Spor & Sağlık** (`#tabSpor` / `#gridSpor`):

| Kart | Veri |
|---|---|
| Sabah Rutini + Koşu | `MORNING_*` + `d:morning:TARİH`, `d:runkm:TARİH` |
| Bugünün Antrenmanı — **`Bugün yapamadım`** | `WK` (+ `EX_OVR` tek gün ezmesi) + `d:ex`, `d:sess`, `d:prog`, `d:vol` |
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

**`Bugün yapamadım` (11 Eyl):** Atlamayı işaretlemenin tek yolu Yoklama
kartının içindeki `Atladım`dı, kullanıcı bulamadı — antrenmanı düşünürken
baktığı yer Antrenman kartı. Düğme `d:yok`'a AYNI kaydı yazıyor (ayrı anahtar
açılmadı), ikinci basış geri alıyor. Hangi dilime yazılacağını `antSlotIdx()`
buluyor: 'Antrenman' ile başlayan dilim → ezmenin `slot` etiketi → günün ilk
'spor' dilimi. Spor dilimi yoksa düğme gizli.

**`kaydedildi ✓` işareti (11 Eyl):** panelde yazı kutuları her tuşta kaydediyor,
kaydet düğmesi yok — kullanıcı yazdığının uçtuğunu sanıp "send" aradı.
`kaydettiGoster(id)` 1.8 sn görünen bir onay basıyor; şu an yoklama not
kutusunda ve koşu km kutusunda. **Yeni bir otomatik kaydeden kutu eklersen
aynı deseni kur.** Günün Programı'nın satır düzenlemesine ayrıca görünür bir
`✓` düğmesi kondu (blur zaten kaydediyordu, görünmüyordu) — `pointerdown` +
`preventDefault` ile bağlı, normal `click`'te blur önce düşüp düğmeyi silerdi.

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
   **Hüküm mantığı artık `hdHukum(bu,t)`'da** — hem Haftalık Değerlendirme
   hem öneri bandı onu çağırıyor, yani cut için çevrilecek **TEK yer** orası.
   `bwSuggestion()` hâlâ ayrı, o da çevrilmeli.
   `hdHukum()` "her şey yolunda" dalında `iyi:true` döndürüyor; öneri bandı
   susma kararını o bayrağa bakarak veriyor. **Cut cümlelerini yazarken
   bayrağı düşürme** — düşerse bant her gün "iyi gidiyorsun" demeye başlar.
2. **Harcama/gelir kategorileri** — `harcama_feed.py`, Garanti bildirim
   maillerini ayrıştırır. `gmail_feed.py`'deki `classify()`/`notify_tag()`
   deseni örnek; "Otomatik bildirim" kovası bu mailleri zaten yakalıyor.
   A3'e bağlı.
3. **Takviye checklist (`d:supp:TARİH`)** — kreatin (her gün, seri
   göstergesi), D3, omega-3, magnezyum, whey.
4. **Yürüyüş takibi (`d:walk:TARİH`)** — sabah/akşam köpek + gym gidiş-dönüş.
   Kalori hedefine ETKİ ETMEZ (yük zaten 2950 tabanına dahil).
5. **Kültür derinliği** — 7 Eylül'de dört listeye 23'er kayıt daha yazıldı;
   derinlik artık **6 Ekim'e kadar kesintisiz** (her listede 44 kayıt).
   Ekim başında yeniden yazılmalı. Kontrol için:
   `node` ile listeleri okuyup `doy()` sırasına göre boş kayıt ara —
   FACTS'te derinlik `Array.isArray(x)`, diğerlerinde `x.length>5`.

### D. Küçük açık uçlar

- Günün Bilgisi derinliğinde **öneri yok**, yalnızca paragraf var.
- **Öneri motorundan ertelenenler** (7 Eyl incelemelerinde bulundu, düzeltilmedi):
  `tonaj-dusus` guard'ı "üç tam hafta" değil "üç pencere boş değil" kontrol
  ediyor; dar bir aralıkta en eski hafta kısmi olabilir — yalnızca yanlış
  SESSİZLİĞE yol açar, uydurma düşüşe değil. `ay-sonu-acik`'ta ileri tarihli
  bir GELİR kaydı uyarıyı bastırabilir. `retler`/`retElle` tarih taşımadığı
  için eski bir Gmail retti aynı şirkete yapılan YENİ başvurunun penceresini
  de susturabilir (veri modelinin önceden var olan boşluğu). Tonaj pencere
  sabitleri (0-6/7-13/14-20) adlandırılmış sabit değil.
- Tarihten "devamı": olay bir ÜLKEYE bağlıysa detay o ülkenin genel maddesi
  oluyor (gerçek veri ama sığ).
- Cloze quiz 5 kelimenin ~3'ünde çıkıyor; çekimli fiil/çok sözcüklü kalıpta
  eski "ne demek" biçimine düşüyor. Kök eşleştirme yazılabilir.
- `MORN_AGIR` / `MORN_BACAK` kalıpları elle yazıldı; hareket adı değişirse
  eşleşme sessizce kaybolur.
- Yemek İÇERİĞİ sabit (`MP`); yüksek hacimli günde porsiyonu büyütmek ayrı iş.
- Besin tablosu ~115 kayıt; tanınmayan yazıldıkça büyütülmeli. Yağ (Y)
  hesaplanmıyor — kutularda alan yok.
- Kültür listeleri gömülü; `index.html` **518 KB** (7 Eyl'de derinlikle
  birlikte 465'ten çıktı). Her derinlik turu ~50 KB ekliyor. **Bir sonraki
  turdan önce ayrı JSON'a taşımaya karar verilmeli** — mobilde ilk açılış
  bunu tek parça indiriyor.
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
| **Öneri motoru MODELSİZ.** Kurallar `index.html`'de, deterministik | 7 Eyl | Kullanıcı kanal olarak "panelde kart + telefona bildirim" seçti, kapsam olarak spor/para/iş (rutin-uyku dışarıda, Alışkanlık Serileri zaten gösteriyor). LLM kararıyla tutarlı: anahtarsız, çevrimdışı, gizlilik sorunsuz. **Bedeli bilerek kabul edildi:** kurallar tarayıcıda çalışıyor, panel açılmadan `d:oneri` güncellenmiyor, 24 saatten eskisi bildirime girmiyor. **Kuralları `push_feed.py`'ye kopyalamayı ÖNERME** — iki kaynak, kaçınılmaz sapma. |
| **Bant sadece tetiklenince görünür** | 7 Eyl | Her gün "iyi gidiyorsun" diyen kart üç gün sonra okunmaz. Söyleyecek şey yoksa `hidden`, boşluk da bırakmıyor. En fazla `ONERI_MAX`=3 öneri, gerisi "+N öneri daha". |
| **`donus-yok` ret varken SUSAR** | 7 Eyl | "Hiç dönüş yok" ancak gerçekten hiç dönüş yokken söylenebilir — ret de bir dönüştür. Ret sayısı `d:myApps[].status`'tan gelmiyor (orası hep 'Bekliyor'), İş Başvuruları kartının kullandığı `retElle`/`retler` eşleştirmesinden geliyor. Kural neden söylemiyor, yalnızca sayıyor: panelin "CV'n kötü" diyecek verisi yok. |
| **`SABIT_KAT` kullanıcının GERÇEK sabit giderlerini kapsamalı** | 7 Eyl | Liste `['Kira','Fatura']`di; araba ödemesi kategori olarak yoktu, "Ulaşım/Diğer" giriliyordu ve ay sonu tahmini onu değişken sanıp 30 ile çarpıyordu. §5.19'un tuzağı kategori listesi eksik olduğu için arka kapıdan geri gelmişti. `Kredi` (araba + Akbank + Garanti; hangisi olduğu NOT alanına, her banka için ayrı kategori dağılımı okunmaz hâle getirirdi) ve `Araba` (kredi değil; yakıt/bakım/sigorta) eklendi. **Düzenli ayda bir ödenen yeni bir kalem çıkarsa listeye eklenmeli.** `Kredi/Taksit` artık seçenek değil ama SABIT_KAT'ta duruyor: kategori adı her kaydın içine metin olarak yazılıyor, listeden çıkarılırsa o etiketli eski kayıtlar değişken sayılıp yine 30 ile çarpılırdı. Silmeden önce o kayıtların kalmadığından emin ol. |
| **Artış freni: önceki seans "çok zor" ise reçete artmaz** | 7 Eyl | Kullanıcı onayladı. Kilo DÜŞMÜYOR, sabit kalıyor — "paneli kiloyu kendiliğinden geri çekmesin" kuralı duruyor, yalnızca panelin kendi artışı frenleniyor. Fren iki şeyle açılıyor: "çok zor" YA DA herhangi bir bölge işareti (8 Eyl'de eklendi). Bölge işareti hareket bazında değil BÜTÜN seansa uygulanıyor — hareket adını bölgeye eşlemek ("Bench press" → omuz?) daha isabetli olurdu ama §5'teki elle-kalıp tuzağı olurdu. Kaba ama sessizce yanlış çalışmayan davranış seçildi; hata yönü de doğru tarafa düşüyor, fazladan frenlemek gereken yerde frenlememekten iyi. Pencere 7 gün, yoksa bir kez "çok zor" deyip bir daha cevaplamayan biri freni kalıcı açık bırakırdı. Seans ekranında yazıyor — sessiz çalışmıyor. |
| **Elle başvuru girişi** | 7 Eyl | Kullanıcı ağırlıklı LinkedIn'den başvuruyor, o başvurular hiçbir yere düşmüyordu; `basvuru-tempo` ve `donus-yok` yalnızca `d:myApps`'e baktığı için hep sessiz kalıyordu. İş Başvuruları kartına şirket+pozisyon satırı eklendi, anahtar `el:` önekli. `appRows()` zaten Sheet ile birleştirip tekrarı ayıklıyor. |
| **LLM / Jarvis bağlanmadı** | 3 Eyl | Konuşuldu, kullanıcı "çok gerek görmedim" dedi. Günlük brifing reddedildi (veri zaten ekranda). Doğal dille giriş istenirse önce **yerel ayrıştırıcı** yazılacak (anahtarsız, çevrimdışı, gizlilik sorunsuz); model ancak o yetmezse yedek olarak. Kendiliğinden yeniden önerme. |
| **Kalori hedefi 2500'de KALIYOR** | 11 Eyl | Sakatlık uyarlaması bitip normal programa dönülünce soruldu: bulk'a dönülmeyecek, hedef 2500. Hedef `kcalOfs` damgasında, KODDAN EZME (§5.2). Kendiliğinden yeniden sorma — kullanıcı değiştirmek isterse Haftalık Değerlendirme'nin [Uygula] düğmesi ya da "hedefi düzenle" zaten var. Faz anahtarı (C1) hâlâ yazılmadı; yazılırsa bu hedefi taban almalı. |
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
21. **Öneri kuralı `id`'leri KARARLIDIR.** `d:oneriKapali` susturmayı id'ye
    göre tutuyor; bir id değişirse kullanıcının `[×]`'i sessizce kaybolur ve
    susturduğu öneri geri gelir. Kural yeniden adlandırma, sil-yeniden yaz.
22. **Pencere kaç güne bölündüyse metin onu yazsın.** Protein kuralı önce
    "Son 7 günde ortalama" diyordu ama ortalama 4-6 güne de bölünmüş
    olabiliyordu. `renderHaftalik()`'in deseni doğru: gerçek gün sayısını yaz.
23. **Yüzde kıyasında TABAN da eşiği geçmeli.** `kategori-sicrama` önce
    yalnız farkın ≥₺500 olmasına bakıyordu; geçen ay ₺20 harcanan bir
    kategoride "%5900 yukarıda" gibi anlamsız ama kendinden emin bir sonuç
    çıkıyordu. Taban da aynı eşiğe bağlı.
24. **Tek günlük program ezmesi `EX_OVR`'a yazılır, `WK`'ya DEĞİL.** `WK`'yı
    değiştirmek o haftagününü kalıcı değiştirir. `EX_OVR` tarihe bağlı
    (`'YYYY-AA-GG'`) ve ertesi hafta kendiliğinden düşer. Bugünün listesini
    okuyan her yer `gununEx()` çağırıyor — `WK[dow].ex` yazma.
    **Kayıt WK ile aynı şekli taşıyor: `{title, run, ex}`** — başlık ve koşu
    bayrağı da ezilebiliyor, yalnızca hareket listesi değil.
    `gunProg(tarih)` bir TARİHİN programını veriyor; günü haftagününden değil
    tarihten türeten her hesap onu çağırıyor (9 Eyl'de `exSayilir`,
    `hdTopla`, alışkanlık halkaları hepsi tarihe duyarlı hâle getirildi).
    Alışkanlıkta 'skip' artık Pazar'a değil, o günün ağırlık hareketi olup
    olmamasına bakıyor — ezmeyle koşuya çevrilmiş gün kaçırılmış antrenman
    sayılmıyor. **`d:ex` tikleri hâlâ İNDEKSE bağlı (§5.5):** bir tarihin
    ezmesini o gün geçtikten SONRA değiştirirsen eski tiklerin anlamı kayar.
    **Koşu/hafif günlerde şartnamede `×` kullanma** — `setHedef()` onu
    ağırlık hareketi sayar ve gün ağırlık günü olur ('30 sn / bacak, 2 tur'
    yaz, '2 × 30 sn' değil).
25. **Bildirim, öneri uğruna düşmemeli.** `oneri_satiri()` gist'ten gelen
    bozuk bir yapıda istisna atarsa `main()` içinde sarmalayıcı olmadığı için
    YOKLAMA bildirimi de gitmiyordu. Gist içeriği dış veri: tipini doğrula,
    istisnayı geniş yakala, sessizliğe düş.

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
| 8 Eyl | Seans kapanışı (nasıl geçti / zorlayan yer) · **artış freni** · `EX_OVR` tek günlük program uyarlaması · Araba/Kredi sabit gider · elle başvuru girişi · kültür derinliği 6 Ekim'e kadar · mobil taşma |
| 9 Eyl | **Sakatlık uyarlaması** (10-22 Eyl, üst gövde yok) · `gunProg()` ile hesaplar tarihe bağlandı · `SCHED` de tarihe bağlandı + bildirim planına `t:TARİH` · **14 günlük plan + muaf gün** · kategori süzgeci · kayıt kategorisi düzenlenebilir · `Kredi` kategorisi |
| 11 Eyl | Harcamalara `Bobo` kategorisi · **sakatlık uyarlaması bitti** (15-22 Eyl kayıtları silindi, 13 Eyl Pazar'a LEGS) · `gunSched` Antrenman dilimi olmayan güne ezme etiketi yazıyor · **Günün Programı'na ← → gün gezinme** + o günün antrenmanı + muaf düğmesi · Antrenman kartına **Bugün yapamadım** · `kaydedildi ✓` işareti |
| 6-7 Eyl | **ÖNERİ MOTORU** — panel gösterge tablosundan tavsiye veren katmana geçti. `hdHukum()` ayrıştırıldı · bant + motor iskeleti · 8 kural (spor/para/iş) · `[×]` ile 7 gün susturma · bildirime öneri satırı. Tasarım `docs/superpowers/specs/`, plan `docs/superpowers/plans/` altında. |
