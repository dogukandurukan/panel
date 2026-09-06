# Öneri Motoru — tasarım

**Tarih:** 6 Eylül 2026
**Durum:** onaylandı, uygulama planı bekliyor

## Amaç

Panel bugün bir **gösterge tablosu**: veriyi gösteriyor, yorumu kullanıcı
yapıyor. İstenen, veriyi girdikten sonra **yön gösteren** bir katman —
"şu oldu, şunu yap" diyen, gerektiğinde de değişikliği uygulayan.

Kapsam kullanıcı tarafından seçildi: **spor & beslenme, para, iş arama**.
Rutin & uyku kapsam dışı (Alışkanlık Serileri kartı zaten onu gösteriyor).

## Karar: model yok

Öneriler `index.html` içinde **deterministik JS kuralları**. Model çağrısı,
API anahtarı, backend yok. Gerekçeleri:

- `DEVAM.md` §3'teki "LLM eklenmedi" kararıyla tutarlı.
- Anahtarsız ve çevrimdışı çalışır; repo public olduğu için anahtar zaten
  giremez (kural 1).
- Kural tabanlı olması *sınırı da* belirliyor: panel yalnızca önceden
  yazdığımız çıkarımları yapar, sürpriz üretmez. Bu kabul edildi.

Bunun bedeli açıkça kabul edildi: kurallar tarayıcıda çalışır, yani
**panel açılmadan öneri güncellenmez**.

## Yerleşim

Sabit şeridin (`.pinned`) **üstünde**, tam genişlik ince bir bant:
`#oneriBox`. Sekmeden bağımsız olmalı — kapsam iki sekmeye yayılıyor
(spor sekme 1'de, para + iş sekme 2'de).

**Hiçbir kural tetiklenmezse bant `hidden`.** Her gün "iyi gidiyorsun"
diyen bir kart üç gün sonra okunmaz hale gelir; kural 2'nin ("bağlanacak
veri yoksa öğe konulmaz") aynısı burada da geçerli.

Gizli sekme tuzağı (`DEVAM.md` §5.16) bandı etkilemez: `.pinned` gibi
sekmelerin dışında, hep ölçülebilir durumda.

## Yapı

```
ONERI = [ {id, alan, kos(ctx)}, … ]
```

| Alan | Anlamı |
|---|---|
| `id` | Kararlı kimlik. Susturma kaydı buna bağlı — **değiştirilmez** |
| `alan` | `'spor'` \| `'para'` \| `'is'` — rozet ve sıralama için |
| `kos(ctx)` | `null` (tetiklenmedi) ya da `{bas, metin, delta?}` |

`ctx` **bir kez** toplanır ve tüm kurallara aynı nesne geçer; her kural
ayrı ayrı `localStorage` gezmez (`hdTopla()` zaten 7 günlük döngü yapıyor,
sekiz kural sekiz kez dönmemeli). İçeriği:

- son 14 günün `d:meals:*`, `d:ex:*`, `d:vol`, `d:bw`
- `d:prog` + `hareketGecmisi()`
- `d:money:` bu ay ve geçen ay
- `d:myApps`, `d:retler`, `d:retElle`

Yeni kural eklemek = tabloya bir satır. Motor değişmez.

## Kurallar — ilk sürüm

| # | id | Alan | Koşul | Çıktı |
|---|---|---|---|---|
| 1 | `kcal-hukum` | spor | `hdHukum()` bir hüküm döndürüyorsa | metin + **[Uygula]** (`kcalOfs`) |
| 2 | `protein-dusuk` | spor | Son 7 günün protein ort. hedefin 15 g+ altında, **en az 4 gün kaydı** var | metin |
| 3 | `hareket-tikandi` | spor | Programdaki herhangi bir harekette `takiliSeans(ad) >= 3` | metin (kaç hareket, hangileri) |
| 4 | `tonaj-dusus` | spor | Tonaj 2 hafta üst üste düşüyor (3 haftalık `d:vol` ister) | metin |
| 5 | `kategori-sicrama` | para | Bir kategori, geçen ayın **aynı gün penceresinde** %60+ yüksek ve fark ≥ ₺500 | metin |
| 6 | `ay-sonu-acik` | para | Değişken gider tempo tahmini + kalan sabit gider > ay geliri | metin |
| 7 | `basvuru-tempo` | is | Son 7 günün başvurusu, önceki 7 günün yarısından az (önceki ≥ 3) | metin |
| 8 | `donus-yok` | is | Son 21 günde ≥ 10 başvuru ve hiçbirinin durumu `Bekliyor`/`Ret` dışına çıkmamış | metin |

### Kural notları

**1 — hedefli refactor.** `renderHaftalik()` içindeki dört dallı hüküm
mantığı `hdHukum(bu, onceki, trend)` → `{metin, delta}` olarak ayrıştırılır.
Haftalık Değerlendirme onu render eder, öneri motoru kural olarak çağırır.
Mantık iki yerde durmaz.

Bu ayrıca **C1 (faz anahtarı)** için hazırlık: cut geldiğinde hükmün
tersine çevrilmesi gereken tek yer `hdHukum()` olur.

Bant hükmü *tekrar etmiyor*, **yukarı taşıyor**: Haftalık Değerlendirme
sekme 1'in en altında, günlük akışta görünmüyor.

**3 — mevcut fonksiyonu yeniden kullanır.** `takiliSeans(ad)` ve eşiği
(`>= 3`) zaten var; `tikanmaNot()` bunu gösteriyor ama **yalnızca o
hareketin seansı açılınca**. Bant bunu bütün program için özetler:
"3 hareket 3+ seanstır aynı kiloda: Bench, Row, OHP." Ayrıntı antrenman
kartında kalır, eşik kopyalanmaz.

**5 ve 6 — pencere eşitliği zorunlu** (`DEVAM.md` §5.19). Ayın 6'sındaki
harcama, geçen ayın **ilk 6 gününe** göre kıyaslanır. Ay sonu tahmininde
sabit gider (`SABIT_KAT`) günlük ortalamayla çarpılmaz — kira 30 kez
sayılır. Değişken gider tempoyla, sabit gider kalan takvim gerçeğiyle
hesaplanır.

**8 — "görüşme" diye bir alan yok.** Panel bir başvurunun durumunu
`d:myApps[].status` ve Sheet'in "Durum" sütunundan biliyor; başvuru
açılırken `Bekliyor` yazılıyor, `check_rejections.py` `Ret` yapıyor.
Kural bu yüzden dolaylı bakıyor: pencerede başvuru sayısı ≥ 10 ve
**hiçbiri** `Bekliyor`/`Ret` dışına çıkmamışsa tetiklenir. Kullanıcı
Sheet'te bir satırı elle başka bir duruma çevirdiyse (ör. "Görüşme")
kural susar.

Çıktı bir *gözlem* olarak yazılır ("21 günde 14 başvuru, 9 ret, hiç
dönüş yok"), "CV'n kötü" hükmü olarak değil — panelin bunu bilecek
verisi yok.

## Susturma

`d:oneriKapali` = `{id: kapatıldığı_tarih}`. Her önerinin `[×]`'i var.
Koşul 7 gün sonra hâlâ geçerliyse öneri tekrar çıkar.

Aynı uyarıyı her gün göstermek onu görünmez yapar; susturma bandın
okunur kalmasının şartı.

## Bildirim

`renderOneri()` sonucu `d:oneri` anahtarına yazılır:

```
d:oneri = {t: <ms>, list: [{alan, bas, metin}, …]}
```

Senkron bunu gist'e taşır — **`SYNC_SKIP`'e konmaz** (feed önbelleği değil,
kullanıcı verisinden türemiş çıktı).

`push_feed.py`, yoklama bildirimini gönderirken `d:oneri` **24 saatten
tazeyse** en öncelikli **bir** öneriyi bildirimin gövdesine ekler.
Ayrı bildirim ve ayrı cron **yok** — dış zamanlayıcı (`DEVAM.md` A1)
kurulmadan zamanlama zaten güvenilmez, ikinci bir akış eklemek riski
ikiye katlar.

`d:oneri` bayatsa bildirime hiçbir şey eklenmez. Eski öneriyi taze
göstermek kural 2'nin ihlali olur.

## Dokunulan yerler

| Dosya | Değişiklik |
|---|---|
| `index.html` | `#oneriBox` bandı, `ONERI` tablosu, `renderOneri()`, `oneriCtx()`, `hdHukum()` ayrıştırma, `d:oneri` yazımı, iki tema CSS |
| `push_feed.py` | Bildirim gövdesine öneri satırı |
| `DEVAM.md` | Yeni kart, yeni anahtarlar, C1 ile ilişki |

## Yapılmayacaklar (YAGNI)

- Model / LLM çağrısı
- Ayrı "Öneriler" sekmesi
- Öneri geçmişi veya arşivi
- Rutin & uyku kuralları (kullanıcı kapsam dışı bıraktı)
- Yatırım tavsiyesi — panel fiyat gösterir, yorum yapmaz
- Kuralların Python'a kopyalanması (iki kaynak, kaçınılmaz sapma)

## Doğrulama

`DEVAM.md` §6'daki yöntem: yerelde sun → gerçek veriyle doğrula → iki
temayı da kontrol et (`almanak`, `hud`) → 7 günü de gez → kişisel veri
taraması → commit + push → canlıda doğrula.

Bu iş için ek olarak:

- **Bant boşken**: hiçbir kural tetiklenmiyorken sayfada boşluk kalmamalı.
- **Kural 1**: bandın hükmü ile Haftalık Değerlendirme'nin hükmü aynı
  cümle olmalı — ayrışırlarsa refactor kaçmış demektir.
- **Kural 5/6**: ay başında (1-3. gün) kıyas penceresi çok kısa; kural
  sayı uydurmak yerine sessiz kalmalı.
- **Susturma**: `[×]`'ten sonra yenilemede geri gelmemeli, 7 gün sonra
  gelmeli.
- **Yeni kullanıcı / boş veri**: hiçbir kural, veri yokken tetiklenmemeli
  (`DEVAM.md` §5.20 — kaydı olan ama boş gün ≠ sıfır).
