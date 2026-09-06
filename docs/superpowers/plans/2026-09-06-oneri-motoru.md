# Öneri Motoru Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Panele, yalnızca bir kural tetiklendiğinde görünen, veriden çıkarım yapıp yön gösteren bir öneri bandı eklemek.

**Architecture:** `index.html` içinde deterministik kural tablosu (`ONERI`). Kurallar saf fonksiyon: tek seferde toplanan bir `ctx` nesnesi alır, `null` ya da `{bas, metin, delta?}` döner. `renderOneri()` tabloyu gezer, sonucu sabit şeridin üstündeki `#oneriBox` bandına basar ve `d:oneri` anahtarına yazar. `push_feed.py` bu anahtarı gist'ten okuyup taze ise bildirimin gövdesine bir satır ekler.

**Tech Stack:** Düz HTML + CSS + ES2020 JS (framework yok, build yok, bağımlılık yok) · Python 3 + `requests` + `pywebpush` (yalnızca `push_feed.py`)

**Spec:** `docs/superpowers/specs/2026-09-06-oneri-motoru-design.md`

## Global Constraints

Bunlar `CLAUDE.md` ve `DEVAM.md`'den geliyor; **her görev için geçerli**:

- **Repo PUBLIC.** Hiçbir API anahtarı, token veya kişisel veri (telefon, e-posta, CV metni, şirket adı) repoya girmez. Push öncesi tarama zorunlu:
  `grep -rInE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(\+90|0)5[0-9]{9}|gh[pousr]_[A-Za-z0-9]{20,}|sk-ant-" index.html *.py`
- **GitHub Actions log'u da herkese açık.** `push_feed.py` öneri METNİNİ log'a basmaz — yalnızca eklenip eklenmediğini.
- **Tek dosya, bağımlılık yok.** CDN script'i, npm paketi, build adımı eklenmez. Test koşumu için yazılan yardımcı **repoya commit edilmez** (scratchpad'de kalır).
- **İki tema korunur:** `almanak` (varsayılan) ve `hud`. Yeni CSS yalnızca `:root` değişkenlerini kullanır — mevcut değişkenler: `--paper --card --ink --muted --line --line2 --accent --up --down --serif`. Sabit renk kodu yazılmaz.
- **Her gösterge gerçek veriye bağlı.** Veri yoksa kural `null` döner ve hiçbir şey görünmez. Sayı uydurulmaz.
- **Yatırım tavsiyesi yok.** Para kuralları yalnızca kullanıcının kendi harcama/gelir kaydından çıkarım yapar.
- **Anahtar sırası korunur:** `ONERI` tablosundaki sıra öncelik sırasıdır. Bildirime giden `list[0]`'dır.
- **Kural `id`'leri kararlıdır.** Susturma kaydı (`d:oneriKapali`) bunlara bağlı; bir `id` değişirse kullanıcının susturması sessizce kaybolur.

## Doğrulama zemini — ÖNCE OKU

**Bu repoda test çerçevesi yok** ve eklenmeyecek (bağımlılık yok kuralı). Bunun yerine iki katmanlı doğrulama kullanılıyor:

1. **Node koşum yardımcısı (scratchpad, commit EDİLMEZ).** Kurallar saf fonksiyon olduğu için `index.html`'den çıkarılıp Node'da sahte `ctx` ile koşturulabiliyor. Görev 2 bu yardımcıyı kuruyor, sonraki her kural görevi onu kullanıyor. Kırmızı→yeşil döngüsü burada dönüyor.
2. **Tarayıcıda gerçek veriyle doğrulama.** `DEVAM.md` §6'nın yöntemi: `python3 -m http.server 8901` → gerçek veri → **iki tema** → gerekiyorsa 7 gün.

Her görevin sonunda ayrıca sözdizimi kontrolü:
`node --check <(python3 -c "import re,sys;print(''.join(re.findall(r'<script>(.*?)</script>',open('index.html',encoding='utf-8').read(),re.S)))")`

---

### Task 1: `hdHukum()` ayrıştırması

Haftalık Değerlendirme'nin dört dallı hükmünü saf fonksiyona çıkarır. **Davranış değişmez** — bu görevin tek çıktısı, aynı cümleyi iki yerden çağırabilmek. Kural 1 (Görev 3) ve gelecekteki faz anahtarı (C1) buna dayanacak.

**Files:**
- Modify: `index.html` (`renderHaftalik()` içindeki hüküm bloğu, ~4583-4604)
- Test: scratchpad `oneri-test.mjs` (Görev 2'de kalıcılaşıyor; burada tek seferlik elle kıyas)

**Interfaces:**
- Consumes: `BW_FLAT_PCT`, `BW_FAST_PCT`, `hdTopla()` çıktısı (`{gun,kcal,p,c,hKcal,hP,hC,sporGun,sporTam,tonaj}`), `bwTrend()` çıktısı (`{thisAvg,lastAvg,pct,n}` ya da `null`)
- Produces: `hdHukum(bu, t)` → `{metin: string, delta: number, eksik?: true}`
  - `delta` sıfır dışıysa çağıran taraf "Uygula" düğmesi gösterir
  - `eksik:true` yalnızca veri yetersizken döner; öneri motoru bunu görünce susar

- [ ] **Step 1: Mevcut hüküm metnini kaydet (kıyas tabanı)**

Tarayıcıda paneli aç, Haftalık Değerlendirme kartındaki hüküm cümlesini ve varsa düğme etiketini bir yere kopyala. Refactor sonrası **birebir aynı** olmalı.

```bash
cd ~/panel && python3 -m http.server 8901
```

- [ ] **Step 2: `hdHukum()`'u yaz**

`renderHaftalik()`'in HEMEN ÜSTÜNE ekle:

```js
/* Hüküm mantığı ayrı: hem Haftalık Değerlendirme hem öneri bandı çağırıyor.
   Faz anahtarı (d:phase) geldiğinde cut için tersine çevrilecek TEK yer burası.
   Hedefi tutturamadıysan çözüm hedefi YÜKSELTMEK değil, önce mevcut hedefi
   tutturmak — dalların sırası bunu koruyor. */
function hdHukum(bu,t){
  const ortK=bu.gun?bu.kcal/bu.gun:0,hedK=bu.gun?bu.hKcal/bu.gun:0;
  if(!bu.gun||!t)return {eksik:true,delta:0,
    metin:'Hüküm için hem yemek kaydı hem de iki haftalık tartı gerekiyor. '+
      (bu.gun?'':'Yemek kaydı eksik. ')+(t?'':'Tartı kaydı eksik.')};
  if(t.pct>BW_FAST_PCT)return {delta:-150,
    metin:'Haftalık %'+t.pct.toFixed(2)+' ile hızlı artıyorsun (yağlanma riski). Hedefi 150 kcal azaltmayı düşün.'};
  if(Math.abs(t.pct)<BW_FLAT_PCT&&ortK<hedK-100)return {delta:0,
    metin:'Kilon sabit ama hedefinin günde '+Math.round(hedK-ortK)+' kcal altında kaldın. '+
      'Hedefi yükseltmek açığı büyütür — önce mevcut '+Math.round(hedK)+' kcal\'i tutturmayı dene.'};
  if(Math.abs(t.pct)<BW_FLAT_PCT)return {delta:150,
    metin:'Hedefini tutturdun ama kilon 2 haftadır sabit. Hedefi 150 kcal artırmayı düşün.'};
  return {delta:0,
    metin:'Haftalık %'+t.pct.toFixed(2)+' ile bulk aralığındasın. Hedefe dokunma, böyle devam.'};
}
```

- [ ] **Step 3: `renderHaftalik()` içindeki bloğu çağrıyla değiştir**

Şu bloğu (yorum satırı dahil, `const ortK=…` satırından `if(ub)ub.onclick=…` satırına kadar olan hüküm kısmı):

```js
  /* Hüküm: hedefi tutturamadıysan çözüm hedefi YÜKSELTMEK değil, önce
     mevcut hedefi tutturmak. Kilo verisi yoksa hüküm de yok. */
  const ortK=bu.gun?bu.kcal/bu.gun:0,hedK=bu.gun?bu.hKcal/bu.gun:0;
  let hukum='',dugme=0;
  if(!bu.gun||!t){
```
…dört dallı `if/else` zinciri…
```js
  html+='<div class="hd-hukum"><p>'+esc(hukum)+'</p>'+
    (dugme?'<button class="ibtn" id="hdUygula">Hedefi '+Math.round(num(targets.kcal))+' → '+
      Math.round(num(targets.kcal)+dugme)+' kcal yap</button>':'')+'</div>';
```

şununla değiştir:

```js
  const h=hdHukum(bu,t);
  html+='<div class="hd-hukum"><p>'+esc(h.metin)+'</p>'+
    (h.delta?'<button class="ibtn" id="hdUygula">Hedefi '+Math.round(num(targets.kcal))+' → '+
      Math.round(num(targets.kcal)+h.delta)+' kcal yap</button>':'')+'</div>';
```

ve fonksiyonun sonundaki düğme bağlamasını:

```js
  const ub=document.getElementById('hdUygula');
  if(ub)ub.onclick=()=>hdUygula(h.delta);
```

**DİKKAT** (`DEVAM.md` §5.12): blok değiştirirken `html+='<div class="hd-not">…'` satırını ve `el.innerHTML=html;` satırını silme — onlar hükümden sonra geliyor ve kalmalı.

- [ ] **Step 4: Sözdizimi kontrolü**

```bash
cd ~/panel && python3 -c "import re;print(''.join(re.findall(r'<script>(.*?)</script>',open('index.html',encoding='utf-8').read(),re.S)))" > /tmp/panel-check.js && node --check /tmp/panel-check.js && echo OK
```
Beklenen: `OK`

- [ ] **Step 5: Tarayıcıda kıyas**

Paneli yenile. Haftalık Değerlendirme'deki hüküm cümlesi ve düğme etiketi **Step 1'de kaydettiğinin birebir aynısı** olmalı. Farklıysa refactor kaçmış demektir — düzelt.

- [ ] **Step 6: Commit**

```bash
cd ~/panel && git add index.html && git commit -m "Haftalık Değerlendirme hükmü hdHukum() fonksiyonuna ayrıştırıldı

Davranış değişmedi; hüküm cümlesi birebir aynı. Ayrıştırmanın iki
sebebi var: öneri bandı aynı hükmü sekme 1'in altından yukarı taşıyacak
ve mantığın iki yerde durmasını istemiyoruz; faz anahtarı (C1) geldiğinde
cut için tersine çevrilecek tek yer burası olacak.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Motor iskeleti, bant ve koşum yardımcısı

Kural tablosu boşken bandı kurar. Bu görevin sonunda **panelde hiçbir görsel değişiklik olmamalı** — bant var ama `hidden`. Ayrıca sonraki bütün kural görevlerinin kullanacağı Node koşum yardımcısı burada kuruluyor.

**Files:**
- Modify: `index.html` (markup: `#syncBox`'ın hemen altı ~671; CSS: `:root` blokunun sonrası; JS: `renderHaftalik()`'ten önce yeni bölüm; `boot`/init içinde çağrı)
- Modify: `index.html` — `takiliSeans()` imzası (~2179)
- Create (scratchpad, **commit edilmez**): `$SCRATCHPAD/oneri-test.mjs`

**Interfaces:**
- Consumes: `sGet/sSet`, `todayKey()`, `dayBack(n)`, `num()`, `esc()`, `hdTopla()`, `HD_PENCERE`, `bwTrend()`, `hareketGecmisi()`, `thisMonth()`, `shiftMonth()`, `myApps`, `retler`, `retElle`, `vol`
- Produces:
  - `ONERI` — kural dizisi, `[{id:string, alan:'spor'|'para'|'is', kos:(ctx)=>null|{bas,metin,delta?}}]`
  - `oneriCtx()` → `Promise<ctx>`; `ctx` alanları: `{bu, onceki, trend, gecmis, vol, money:{ay,buAy,gecenAy}, apps, retler, retElle, bugunGun}`
  - `renderOneri()` → `Promise<void>`
  - `ONERI_MAX` = 3, `ONERI_SUSMA` = 7
  - `takiliSeans(ad, gecmis?)` — ikinci parametre eklendi, geriye dönük uyumlu

- [ ] **Step 1: Koşum yardımcısını yaz (kırmızı)**

Kurallar saf fonksiyon olduğu için `index.html`'den çıkarılıp Node'da sahte `ctx` ile koşturulabiliyorlar. Yardımcı üç şey yapıyor: motor bloğunu çıkarıyor, kuralların dokunduğu **mevcut** fonksiyonları (`hdHukum`, `takiliSeans`, `setHedef`) index.html'den adıyla çekiyor, kalanları taklit ediyor.

**`WK` taklit ediliyor, gerçeği çekilmiyor:** gerçek tablo çok büyük ve regexle çıkarması kırılgan. Kural mantığı burada, gerçek programla uyum ise her görevin tarayıcı adımında doğrulanıyor.

```bash
mkdir -p "$SCRATCHPAD" && cat > "$SCRATCHPAD/oneri-test.mjs" <<'EOF'
/* Öneri kurallarını Node'da koşturur. index.html'den ÖNERİ MOTORU bloğunu ve
   kuralların dokunduğu mevcut fonksiyonları çıkarır, kalanını taklit eder.
   Bu dosya repoya GİRMEZ — panelin "tek dosya, bağımlılık yok" kuralı. */
import { readFileSync } from 'node:fs';

const html = readFileSync(process.env.HOME + '/panel/index.html', 'utf8');

const blok = /\/\* ===== ÖNERİ MOTORU =====([\s\S]*?)\/\* ===== ÖNERİ MOTORU SONU ===== \*\//.exec(html);
if (!blok) { console.error('HATA: ÖNERİ MOTORU bloğu bulunamadı'); process.exit(1); }

/* Mevcut fonksiyonlar adıyla çekiliyor: taklit edilirse test gerçek davranışı
   değil taklidi doğrular.

   Süslü parantez sayarak kapanışı buluyor. "\n}"e kadar oku demek YETMİYOR:
   setHedef sütun 0'da kapanmıyor ('…:null;}' ile bitiyor), o yol 31 satır
   yutup sonraki üç fonksiyonu da içine alıyordu.

   Sınır: dize ya da regex içindeki süslü parantez sayımı bozar. Çekilen üç
   fonksiyonda yok; yenisini eklerken kontrol et. */
function cek(ad) {
  const i = html.indexOf('\nfunction ' + ad + '(');
  if (i < 0) { console.error('HATA: ' + ad + '() bulunamadı'); process.exit(1); }
  let derinlik = 0, basladi = false;
  for (let j = i; j < html.length; j++) {
    const c = html[j];
    if (c === '{') { derinlik++; basladi = true; }
    else if (c === '}') { derinlik--; if (basladi && derinlik === 0) return html.slice(i, j + 1); }
  }
  console.error('HATA: ' + ad + '() kapanmıyor'); process.exit(1);
}

const yardimcilar = `
const num=v=>Number(v)||0;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dayBack=n=>{const d=new Date(BUGUN+'T12:00:00');d.setDate(d.getDate()-n);return d.toLocaleDateString('sv-SE');};
const todayKey=()=>BUGUN;
const tl=n=>'₺'+Math.round(n).toLocaleString('tr-TR');
const SABIT_KAT=['Kira','Fatura'];
const BW_FLAT_PCT=0.2, BW_FAST_PCT=0.75;
let wtlog={};
function hareketGecmisi(){return {};}   /* kurallar ctx.gecmis geçiriyor, fallback kullanılmıyor */
/* Gerçek WK çok büyük; kural mantığı için temsilî bir tablo yeterli.
   Gerçek programla uyum tarayıcı adımında doğrulanıyor. */
const WK={
 0:{ex:[['Antrenman yok','—']]},
 1:{ex:[['Bench press','4 × 5-8'],['Incline DB press','3 × 8-12'],['Barbell row','4 × 6-10']]},
 2:{ex:[['Back squat','4 × 5-8'],['Leg press','3 × 10-12']]},
 3:{ex:[['Basket / tenis','45-75 dk']]},
 4:{ex:[['Barbell row','4 × 6-10'],['Face pull','3 × 15-20']]},
 5:{ex:[['Overhead press','3 × 6-10']]},
 6:{ex:[['Hip thrust','4 × 8-12']]}};
`;

export function kur(bugun = '2026-09-15') {
  const src = 'const BUGUN=' + JSON.stringify(bugun) + ';' + yardimcilar +
    cek('setHedef') + cek('takiliSeans') + cek('hdHukum') + blok[1] +
    '\nreturn {ONERI, hdHukum, takiliSeans};';
  return new Function(src)();
}

export function kural(id, bugun) {
  const { ONERI } = kur(bugun);
  const k = ONERI.find(x => x.id === id);
  if (!k) throw new Error('kural yok: ' + id);
  return k;
}

export function esitle(ad, gercek, beklenen) {
  const a = JSON.stringify(gercek), b = JSON.stringify(beklenen);
  if (a === b) { console.log('  ✓ ' + ad); return true; }
  console.log('  ✗ ' + ad + '\n    beklenen: ' + b + '\n    gerçek:   ' + a);
  process.exitCode = 1;
  return false;
}

export function tetiklendi(ad, sonuc) {
  if (sonuc && sonuc.bas) { console.log('  ✓ ' + ad + ' → ' + sonuc.bas); return true; }
  console.log('  ✗ ' + ad + ' → tetiklenmedi (null döndü)');
  process.exitCode = 1;
  return false;
}

export function susuyor(ad, sonuc) {
  if (sonuc === null) { console.log('  ✓ ' + ad + ' (sustu)'); return true; }
  console.log('  ✗ ' + ad + ' → susması gerekirken tetiklendi: ' + JSON.stringify(sonuc));
  process.exitCode = 1;
  return false;
}
EOF

cat > "$SCRATCHPAD/t-iskelet.mjs" <<'EOF'
import { kur } from './oneri-test.mjs';
const { ONERI } = kur();
if (!Array.isArray(ONERI)) { console.log('✗ ONERI dizi değil'); process.exit(1); }
console.log('✓ ONERI tablosu okundu, kural sayısı: ' + ONERI.length);
EOF

node "$SCRATCHPAD/t-iskelet.mjs"
```

Beklenen: `HATA: ÖNERİ MOTORU bloğu bulunamadı` — blok henüz yok. **Kırmızı.**

**Not:** `cek('hdHukum')` Görev 1'in tamamlanmış olmasını gerektiriyor. `hdHukum() bulunamadı` hatası alırsan Görev 1 atlanmış demektir.

- [ ] **Step 2: Bant markup'ını ekle**

`index.html`'de `<div id="syncBox" style="display:none"></div>` satırının **hemen altına**, `<!-- SABİT ŞERİT` yorumunun üstüne:

```html
  <!-- ÖNERİ BANDI: sekmelerin de sabit şeridin de üstünde. Kapsam iki sekmeye
       yayıldığı için (spor sekme 1, para+iş sekme 2) hiçbir sekmenin içine
       giremez. Kural tetiklenmezse hidden — söyleyecek şey yokken yer kaplamaz. -->
  <div id="oneriBox" class="oneri" hidden></div>
```

- [ ] **Step 3: CSS'i ekle (iki tema)**

`:root` blokunun bittiği yerin altına, mevcut kart CSS'lerinin yanına. **Yalnızca değişken kullan** — sabit renk yazma:

```css
  .oneri{margin:0 0 18px;display:flex;flex-direction:column;gap:8px}
  .oneri-r{display:flex;align-items:flex-start;gap:10px;background:var(--card);
    border:1px solid var(--line);border-left:3px solid var(--accent);
    border-radius:8px;padding:10px 12px}
  .oneri-ic{flex:1;min-width:0}
  .oneri-bas{font-weight:600;color:var(--ink);font-size:14px}
  .oneri-mt{color:var(--muted);font-size:13px;margin-top:2px;line-height:1.45}
  .oneri-et{flex:none;font-size:11px;letter-spacing:.04em;text-transform:uppercase;
    color:var(--muted);border:1px solid var(--line2);border-radius:4px;padding:2px 6px;margin-top:2px}
  .oneri-kap{flex:none;background:none;border:0;color:var(--muted);cursor:pointer;
    font-size:16px;line-height:1;padding:2px 4px}
  .oneri-kap:hover{color:var(--down)}
  .oneri-daha{color:var(--muted);font-size:12px;padding-left:2px}
  @media(max-width:640px){.oneri-et{display:none}}
```

- [ ] **Step 4: `takiliSeans()`'a ikinci parametre ekle**

Kural 3 bütün program hareketlerini gezecek; `takiliSeans()` her çağrıda `hareketGecmisi()`'ni yeniden kurarsa aynı iş 20+ kez yapılır. Ayrıca geçmişi dışarıdan vermek kuralı test edilebilir yapıyor.

`function takiliSeans(ad){` satırını şununla değiştir:

```js
/* gecmis verilmezse kendi kurar (mevcut çağrılar bu yolu kullanıyor);
   öneri motoru ctx'deki hazır geçmişi geçiriyor — hem hızlı hem test edilebilir. */
function takiliSeans(ad,gecmis){
```

ve gövdenin ilk satırındaki `const g=hareketGecmisi()[ad]||[];` yerine:

```js
  const g=(gecmis||hareketGecmisi())[ad]||[];
```

- [ ] **Step 5: Motoru yaz**

`renderHaftalik()` bölümünün bittiği yerin altına (`/* ===== HARCAMA & KAZANÇ =====` yorumunun ÜSTÜNE). Blok sınırlayıcı yorumlar **aynen** yazılmalı — koşum yardımcısı onları arıyor:

```js
/* ===== ÖNERİ MOTORU =====
   Panel bir gösterge tablosuydu: veriyi gösteriyor, yorumu kullanıcı yapıyordu.
   Bu katman veriden çıkarım yapıp yön gösteriyor.

   Model YOK — kurallar burada, deterministik. Bedeli: kurallar tarayıcıda
   çalışır, panel açılmadan öneri güncellenmez. Kuralları push_feed.py'ye
   kopyalamak iki kaynak demek olurdu, kopyalanmadı.

   Kural saf fonksiyon: ctx alır, null ya da {bas,metin,delta?} döner.
   ctx BİR KEZ toplanıyor — hdTopla() 7 günlük döngü yapıyor, sekiz kural
   sekiz kez dönmemeli. */
const ONERI_MAX=3;      // banda basılan en fazla öneri
const ONERI_SUSMA=7;    // [×] sonrası kaç gün susar
let oneriKapali={},oneriSon='';

const gunFark=(a,b)=>Math.round((new Date(b+'T12:00:00')-new Date(a+'T12:00:00'))/86400000);

/* Programdaki ağırlık hareketleri (tekrar aralığı olanlar). Aktivite/dinlenme
   günlerindeki '45-75 dk' gibi satırlar setHedef()'ten geçmiyor. */
function programHareketleri(){
  const s={};
  for(let d=0;d<7;d++)(WK[d].ex||[]).forEach(e=>{if(setHedef(e[1]))s[e[0]]=1;});
  return Object.keys(s);
}

/* Ayın 1..sonGun günlerine düşen kayıtlar. Kıyas pencereleri EŞİT olmalı
   (DEVAM.md §5.19): ayın 6'sındaki harcama geçen ayın ilk 6 gününe bakar. */
function ayPenceresi(kayitlar,sonGun){
  return (kayitlar||[]).filter(r=>{const g=+String(r.d||'').slice(8,10);
    return g>=1&&g<=sonGun;});
}

async function oneriCtx(){
  const ay=thisMonth();
  return {
    bu:await hdTopla(0,HD_PENCERE-1),
    onceki:await hdTopla(HD_PENCERE,HD_PENCERE*2-1),
    trend:bwTrend(),
    gecmis:hareketGecmisi(),
    vol:vol||{},
    money:{ay,buAy:await sGet('d:money:'+ay)||[],
           gecenAy:await sGet('d:money:'+shiftMonth(ay,-1))||[]},
    apps:myApps||[],retler:retler||[],retElle:retElle||[],
    bugunGun:new Date().getDate()
  };
}

/* Sıra = öncelik. Bildirime giden list[0]. id'ler KARARLI: susturma kaydı
   bunlara bağlı, değişirse kullanıcının [×]'i sessizce kaybolur. */
const ONERI=[];

async function renderOneri(){
  const el=document.getElementById('oneriBox');if(!el)return;
  const ctx=await oneriCtx(),bugun=todayKey(),liste=[];
  for(const k of ONERI){
    const kapali=oneriKapali[k.id];
    if(kapali&&gunFark(kapali,bugun)<ONERI_SUSMA)continue;
    let r=null;
    /* Bir kuralın hatası bandın tamamını boşaltmasın. */
    try{r=await k.kos(ctx);}catch(e){console.warn('öneri kuralı hata:',k.id,e);}
    if(r&&r.bas)liste.push({id:k.id,alan:k.alan,bas:r.bas,metin:r.metin||'',delta:r.delta||0});
  }
  if(!liste.length){el.hidden=true;el.innerHTML='';await oneriYaz([]);return;}
  const goster=liste.slice(0,ONERI_MAX),kalan=liste.length-goster.length;
  const ETIKET={spor:'Spor',para:'Para',is:'İş'};
  el.innerHTML=goster.map(o=>
    '<div class="oneri-r"><span class="oneri-et">'+esc(ETIKET[o.alan]||'')+'</span>'+
    '<div class="oneri-ic"><div class="oneri-bas">'+esc(o.bas)+'</div>'+
    (o.metin?'<div class="oneri-mt">'+esc(o.metin)+'</div>':'')+
    (o.delta?'<button class="ibtn" data-oneri-uygula="'+esc(String(o.delta))+'" style="margin-top:8px">'+
      'Hedefi '+Math.round(num(targets.kcal))+' → '+Math.round(num(targets.kcal)+o.delta)+' kcal yap</button>':'')+
    '</div><button class="oneri-kap" data-oneri-kapat="'+esc(o.id)+'" title="7 gün sustur">×</button></div>'
  ).join('')+(kalan?'<div class="oneri-daha">+'+kalan+' öneri daha (bantta ilk '+ONERI_MAX+' gösteriliyor)</div>':'');
  el.hidden=false;
  el.querySelectorAll('[data-oneri-kapat]').forEach(b=>b.onclick=async()=>{
    oneriKapali[b.dataset.oneriKapat]=todayKey();
    await sSet('d:oneriKapali',oneriKapali);renderOneri();});
  el.querySelectorAll('[data-oneri-uygula]').forEach(b=>b.onclick=()=>hdUygula(num(b.dataset.oneriUygula)));
  await oneriYaz(goster);
}

/* Bildirim için gist'e taşınan özet. Aynı içerik tekrar yazılmıyor:
   sSet her yazmada senkron push'u tetikliyor (4 sn gecikmeli). */
async function oneriYaz(liste){
  const sade=liste.map(o=>({alan:o.alan,bas:o.bas,metin:o.metin}));
  const imza=JSON.stringify(sade);
  if(imza===oneriSon)return;
  oneriSon=imza;
  await sSet('d:oneri',{t:Date.now(),list:sade});
}
/* ===== ÖNERİ MOTORU SONU ===== */
```

- [ ] **Step 6: Açılışta yükle ve çağır**

Init bloğunda (`jobProfile=await sGet(…)` satırlarının olduğu yer, ~5623) `oneriKapali` yüklemesini ekle:

```js
  oneriKapali=await sGet('d:oneriKapali')||{};
```

ve `renderHaftalik()` çağrısının hemen ardına `renderOneri();` ekle. Bant, Haftalık Değerlendirme'nin okuduğu verinin aynısını okuyor; ondan sonra çalışması sırayı garantiliyor.

- [ ] **Step 7: Koşum yardımcısını tekrar çalıştır (yeşil)**

```bash
node "$SCRATCHPAD/t-iskelet.mjs"
```
Beklenen: `✓ ONERI tablosu okundu, kural sayısı: 0`

- [ ] **Step 8: Sözdizimi kontrolü**

```bash
cd ~/panel && python3 -c "import re;print(''.join(re.findall(r'<script>(.*?)</script>',open('index.html',encoding='utf-8').read(),re.S)))" > /tmp/panel-check.js && node --check /tmp/panel-check.js && echo OK
```

- [ ] **Step 9: Tarayıcıda doğrula — GÖRSEL DEĞİŞİKLİK OLMAMALI**

```bash
cd ~/panel && python3 -m http.server 8901
```
- Bant `hidden`, sayfada fazladan boşluk yok.
- Konsolda hata yok.
- **İki temayı da** aç (`data-theme` = `almanak`, `hud`) — ikisinde de sayfa aynı görünmeli.
- Konsolda `document.getElementById('oneriBox').hidden` → `true` olmalı.

- [ ] **Step 10: Commit**

```bash
cd ~/panel && git add index.html && git commit -m "Öneri motoru iskeleti: bant, ctx toplayıcı, boş kural tablosu

Kural tablosu boş, dolayısıyla bant hep gizli — panelde görsel değişiklik
yok. Kurallar saf fonksiyon (ctx alır, null ya da öneri döner), ctx bir kez
toplanıyor: hdTopla() 7 günlük döngü yapıyor, sekiz kural sekiz kez dönmemeli.

Bant sekmelerin ve sabit şeridin üstünde: kapsam iki sekmeye yayılıyor
(spor sekme 1, para+iş sekme 2), hiçbir sekmenin içine giremez.

takiliSeans() ikinci parametre aldı (geçmiş dışarıdan verilebiliyor).
Geriye dönük uyumlu; kural 3 bütün programı gezerken hareketGecmisi()'ni
20+ kez yeniden kurmasın diye.

Bir kuralın hatası bandın tamamını boşaltmasın diye her kural try/catch
içinde çağrılıyor.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Kural 1 — kalori hükmü (`kcal-hukum`)

İlk gerçek kural. Haftalık Değerlendirme'nin hükmünü sekme 1'in altından yukarı taşır ve "Uygula" düğmesini yanında getirir.

**Files:**
- Modify: `index.html` (`ONERI` dizisi)
- Test: `$SCRATCHPAD/t-kcal.mjs`

**Interfaces:**
- Consumes: `hdHukum(bu,t)` (Görev 1), `ctx.bu`, `ctx.trend`
- Produces: `ONERI[0]` = `{id:'kcal-hukum', alan:'spor', kos}`

- [ ] **Step 1: Testi yaz (kırmızı)**

```bash
cat > "$SCRATCHPAD/t-kcal.mjs" <<'T1'
import { kural, tetiklendi, susuyor, esitle } from './oneri-test.mjs';
const k = kural('kcal-hukum');
const ctx = (gun, kcal, hKcal, pct) => ({
  bu:{gun,kcal:kcal*gun,p:0,c:0,hKcal:hKcal*gun,hP:0,hC:0,sporGun:0,sporTam:0,tonaj:0},
  trend: pct===null?null:{thisAvg:80,lastAvg:80,pct,n:6}
});
console.log('kcal-hukum:');
susuyor('veri yokken susar', k.kos(ctx(0,0,0,null)));
susuyor('tartı yokken susar', k.kos(ctx(5,2900,2950,null)));
susuyor('bulk aralığındayken susar', k.kos(ctx(6,2950,2950,0.4)));
tetiklendi('hızlı artışta tetiklenir', k.kos(ctx(6,3300,2950,1.2)));
esitle('hızlı artışta delta -150', k.kos(ctx(6,3300,2950,1.2)).delta, -150);
tetiklendi('kilo sabitken tetiklenir', k.kos(ctx(6,2960,2950,0.05)));
esitle('kilo sabitken delta +150', k.kos(ctx(6,2960,2950,0.05)).delta, 150);
esitle('hedefin altındayken delta 0', k.kos(ctx(6,2700,2950,0.05)).delta, 0);
T1
node "$SCRATCHPAD/t-kcal.mjs"
```
Beklenen: `kural yok: kcal-hukum` hatası. **Kırmızı.**

- [ ] **Step 2: Kuralı ekle**

`const ONERI=[];` satırını şununla değiştir:

```js
const ONERI=[
  /* 1 — Haftalık Değerlendirme'nin hükmü. Tekrar değil, YUKARI TAŞIMA:
     o kart sekme 1'in en altında, günlük akışta görünmüyor. Mantık
     hdHukum()'da, iki yerde durmuyor. */
  {id:'kcal-hukum',alan:'spor',kos(ctx){
    const h=hdHukum(ctx.bu,ctx.trend);
    if(h.eksik)return null;                       // veri yoksa sus, sayı uydurma
    if(!h.delta&&/böyle devam/.test(h.metin))return null;  // her şey yolundaysa susar
    return {bas:h.delta>0?'Kilon 2 haftadır sabit':(h.delta<0?'Hızlı kilo alıyorsun':'Hedefinin altında kaldın'),
      metin:h.metin,delta:h.delta};
  }},
];
```

- [ ] **Step 3: Testi çalıştır (yeşil)**

```bash
node "$SCRATCHPAD/t-kcal.mjs"
```
Beklenen: bütün satırlar `✓`, çıkış kodu 0.

- [ ] **Step 4: Sözdizimi kontrolü**

```bash
cd ~/panel && python3 -c "import re;print(''.join(re.findall(r'<script>(.*?)</script>',open('index.html',encoding='utf-8').read(),re.S)))" > /tmp/panel-check.js && node --check /tmp/panel-check.js && echo OK
```

- [ ] **Step 5: Tarayıcıda doğrula**

Paneli aç. Kilo ve yemek verisi varsa bant görünmeli.
- **Bandın metni, Haftalık Değerlendirme'deki hüküm cümlesinin AYNISI olmalı.** Ayrışıyorsa `hdHukum()` çağrısı kaçmış.
- Düğme varsa tıkla: hedef değişmeli, hem bant hem Haftalık Değerlendirme hem Yemekler kartı güncellenmeli.
- **İki temayı da** kontrol et.

- [ ] **Step 6: Commit**

```bash
cd ~/panel && git add index.html && git commit -m "Öneri kuralı 1: kalori hükmü bandda, uygula düğmesiyle

Haftalık Değerlendirme'nin hükmü sekme 1'in en altında duruyordu, günlük
akışta görünmüyordu. Bant onu yukarı taşıyor; mantık hdHukum()'da kaldığı
için iki yerde iki cümle olma riski yok.

Her şey yolundayken ('böyle devam') susuyor: her gün 'iyi gidiyorsun' diyen
bir bant üç gün sonra okunmaz hale gelir.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---
### Task 4: Susturma (`d:oneriKapali`)

Bandın etkileşim modelini kurallar yığılmadan önce oturtur. Görev 2'de `[×]` düğmesi ve `oneriKapali` okuması zaten yazıldı; burada susturmanın gerçekten çalıştığı doğrulanıyor ve senkron ayarı yapılıyor.

**Files:**
- Modify: `index.html` (`SYNC_SKIP` — dokunulmayacağının doğrulanması; `sifirla()` listesi)
- Test: `$SCRATCHPAD/t-susma.mjs`

**Interfaces:**
- Consumes: `oneriKapali` (Görev 2), `gunFark(a,b)`
- Produces: `d:oneriKapali` = `{<kural id>: '<YYYY-AA-GG>'}`

- [ ] **Step 1: Testi yaz (kırmızı)**

```bash
cat > "$SCRATCHPAD/t-susma.mjs" <<'T2'
import { kur, esitle } from './oneri-test.mjs';
const { ONERI } = kur('2026-09-15');
/* gunFark bloğun içinde tanımlı; blok üzerinden erişemiyoruz, davranışı
   burada aynen kurup eşiği doğruluyoruz. */
const gunFark=(a,b)=>Math.round((new Date(b+'T12:00:00')-new Date(a+'T12:00:00'))/86400000);
console.log('susturma:');
esitle('aynı gün kapatıldıysa fark 0', gunFark('2026-09-15','2026-09-15'), 0);
esitle('6 gün sonra hâlâ susuyor (6 < 7)', gunFark('2026-09-09','2026-09-15') < 7, true);
esitle('7 gün sonra tekrar çıkar', gunFark('2026-09-08','2026-09-15') < 7, false);
esitle('ay sınırını geçerken doğru sayar', gunFark('2026-08-31','2026-09-07'), 7);
/* id kararlılığı: susturma bunlara bağlı, sessizce değişmemeli */
esitle('kural id listesi', ONERI.map(k=>k.id), ['kcal-hukum']);
T2
node "$SCRATCHPAD/t-susma.mjs"
```

Beklenen: hepsi `✓`. (Bu test Görev 2+3 tamamsa doğrudan yeşil geçer — susturma mantığı orada yazıldı. Kırmızıya düşerse `gunFark` ya da `ONERI` sırası bozulmuş demektir.)

- [ ] **Step 2: `SYNC_SKIP`'i kontrol et — DEĞİŞİKLİK YAPMA**

```bash
cd ~/panel && grep -n "SYNC_SKIP=" index.html
```

`d:oneri` ve `d:oneriKapali` bu listede **olmamalı**. İkisi de feed önbelleği değil, kullanıcının verisinden türeyen çıktı — cihazlar arasında taşınmalı. Listede görünüyorlarsa çıkar.

- [ ] **Step 3: `sifirla()` listesine ekle**

`RESET_TEK` dizisine (`DEVAM.md` §5.6 — silinen anahtarın `d:mtime` damgası bugüne çekilmeli, `sifirla()` bunu zaten yapıyor) iki anahtarı ekle:

```js
const RESET_TEK=['d:prog','d:vol','d:volFill','d:deWrong','d:tasks','d:water',
  'd:oneri','d:oneriKapali',
```
(Mevcut dizinin devamı olduğu gibi kalır.)

- [ ] **Step 4: Tarayıcıda susturmayı doğrula**

Panelde bant görünürken:
1. `[×]`'e bas → öneri kaybolmalı, başka öneri yoksa bant tamamen gizlenmeli.
2. Sayfayı yenile → **geri gelmemeli**.
3. Konsolda: `localStorage.getItem('d:oneriKapali')` → `{"kcal-hukum":"<bugün>"}` içermeli.
4. Konsolda tarihi 8 gün geriye al ve yenile:
   ```js
   localStorage.setItem('d:oneriKapali', JSON.stringify({'kcal-hukum':'2026-08-25'}));location.reload();
   ```
   → öneri **geri gelmeli**.
5. Konsolu temizle: `localStorage.removeItem('d:oneriKapali')`

- [ ] **Step 5: Commit**

```bash
cd ~/panel && git add index.html && git commit -m "Öneri susturma: [×] 7 gün susturuyor, sıfırlamaya dahil

Aynı uyarıyı her gün göstermek onu görünmez yapıyor. [×] kuralın id'sini
ve tarihi d:oneriKapali'ya yazıyor; koşul 7 gün sonra hâlâ geçerliyse
öneri tekrar çıkıyor.

d:oneri ve d:oneriKapali SYNC_SKIP'te DEĞİL: feed önbelleği değil,
kullanıcının verisinden türeyen çıktı, cihazlar arasında taşınmalı.
RESET_TEK'e eklendi.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Spor kuralları — protein, tıkanan hareket, tonaj

Üç kural, aynı veri alanı. Hepsi mevcut veriden okuyor, yeni anahtar istemiyor.

**Files:**
- Modify: `index.html` (`ONERI` dizisi)
- Test: `$SCRATCHPAD/t-spor.mjs`

**Interfaces:**
- Consumes: `ctx.bu` (`{gun,p,hP}`), `ctx.gecmis`, `ctx.vol`, `programHareketleri()`, `takiliSeans(ad,gecmis)`
- Produces: `ONERI` içine `protein-dusuk`, `hareket-tikandi`, `tonaj-dusus`

- [ ] **Step 1: Testi yaz (kırmızı)**

```bash
cat > "$SCRATCHPAD/t-spor.mjs" <<'T3'
import { kural, tetiklendi, susuyor, esitle } from './oneri-test.mjs';
const BUGUN='2026-09-15';
const gunOnce=n=>{const d=new Date(BUGUN+'T12:00:00');d.setDate(d.getDate()-n);
  return d.toLocaleDateString('sv-SE');};

console.log('protein-dusuk:');
const p = kural('protein-dusuk', BUGUN);
const pctx=(gun,pOrt,pHed)=>({bu:{gun,p:pOrt*gun,hP:pHed*gun}});
susuyor('kayıt yokken susar', p.kos(pctx(0,0,0)));
susuyor('3 günlük kayıt yetmez', p.kos(pctx(3,150,210)));
susuyor('açık 15 g altındaysa susar', p.kos(pctx(6,200,210)));
tetiklendi('açık 15 g üstündeyse tetiklenir', p.kos(pctx(6,180,210)));
susuyor('hedefin üstündeyse susar', p.kos(pctx(6,230,210)));

console.log('hareket-tikandi:');
const h = kural('hareket-tikandi', BUGUN);
const gec=(ad,kgler)=>({[ad]:kgler.map((kg,i)=>[gunOnce(30-i*3),kg])});
susuyor('geçmiş boşken susar', h.kos({gecmis:{}}));
susuyor('2 seans aynı kilo yetmez', h.kos({gecmis:gec('Bench press',[60,62.5,62.5])}));
tetiklendi('3 seans aynı kilo tetikler', h.kos({gecmis:gec('Bench press',[60,62.5,62.5,62.5])}));
susuyor('programda olmayan hareket sayılmaz', h.kos({gecmis:gec('Kürek çekme',[60,60,60,60])}));

console.log('tonaj-dusus:');
const t = kural('tonaj-dusus', BUGUN);
const volDiz=(h0,h1,h2)=>{const v={};
  for(let i=0;i<=6;i++)v[gunOnce(i)]=h0/7;
  for(let i=7;i<=13;i++)v[gunOnce(i)]=h1/7;
  for(let i=14;i<=20;i++)v[gunOnce(i)]=h2/7;
  return v;};
susuyor('veri yokken susar', t.kos({vol:{}}));
susuyor('artıyorsa susar', t.kos({vol:volDiz(30000,28000,26000)}));
susuyor('tek hafta düşüş yetmez', t.kos({vol:volDiz(26000,30000,28000)}));
tetiklendi('iki hafta üst üste düşüş tetikler', t.kos({vol:volDiz(24000,27000,30000)}));
T3
node "$SCRATCHPAD/t-spor.mjs"
```
Beklenen: `kural yok: protein-dusuk`. **Kırmızı.**

- [ ] **Step 2: Üç kuralı ekle**

`ONERI` dizisinde `kcal-hukum`'un ARDINA:

```js
  /* 2 — Protein açığı. En az 4 günlük kayıt istiyor: iki günün ortalaması
     hüküm vermeye yetmez. Kaydı olan ama porsiyon işaretlenmemiş gün
     hdTopla()'da zaten sayılmıyor (DEVAM.md §5.20). */
  {id:'protein-dusuk',alan:'spor',kos(ctx){
    if(!ctx.bu||ctx.bu.gun<4)return null;
    const pOrt=ctx.bu.p/ctx.bu.gun,pHed=ctx.bu.hP/ctx.bu.gun,acik=pHed-pOrt;
    if(acik<15)return null;
    return {bas:'Protein günde ort. '+Math.round(acik)+' g eksik',
      metin:'Son 7 günde ortalama '+Math.round(pOrt)+' g, hedef '+Math.round(pHed)+' g. '+
        'Akşam shake\'ini suyla değil sütle yaparsan ~12 g gelir.'};
  }},

  /* 3 — Tıkanan hareket. Eşik (3 seans) ve sayım takiliSeans()'ta zaten var;
     tikanmaNot() bunu gösteriyor ama YALNIZCA o hareketin seansı açılınca.
     Bant bütün program için özetliyor, eşik kopyalanmıyor. */
  {id:'hareket-tikandi',alan:'spor',kos(ctx){
    const tikanan=programHareketleri().filter(ad=>takiliSeans(ad,ctx.gecmis)>=3);
    if(!tikanan.length)return null;
    return {bas:tikanan.length+' hareket 3+ seanstır aynı kiloda',
      metin:tikanan.slice(0,4).join(', ')+
        (tikanan.length>4?' ve '+(tikanan.length-4)+' tane daha':'')+
        '. Antrenman kartında her biri için not var.'};
  }},

  /* 4 — Tonaj düşüşü. Üç haftalık pencere gerekiyor; d:vol dolmadan
     (DEVAM.md §4) bu kural sessiz kalır, sayı uydurmaz. */
  {id:'tonaj-dusus',alan:'spor',kos(ctx){
    const t=(a,b)=>{let s=0;for(let i=a;i<=b;i++)s+=num((ctx.vol||{})[dayBack(i)]);return s;};
    const h0=t(0,6),h1=t(7,13),h2=t(14,20);
    if(!h0||!h1||!h2)return null;
    if(!(h0<h1&&h1<h2))return null;
    const bin=n=>Math.round(n).toLocaleString('tr-TR');
    return {bas:'Tonaj 2 haftadır düşüyor',
      metin:bin(h2)+' → '+bin(h1)+' → '+bin(h0)+' kg. Deload ya da uyku tarafına bakmak isteyebilirsin.'};
  }},
```

- [ ] **Step 3: Testi çalıştır (yeşil)**

```bash
node "$SCRATCHPAD/t-spor.mjs" && node "$SCRATCHPAD/t-kcal.mjs"
```
Beklenen: hepsi `✓`. (Eski test de koşuyor — regresyon kontrolü.)

- [ ] **Step 4: Sözdizimi kontrolü**

```bash
cd ~/panel && python3 -c "import re;print(''.join(re.findall(r'<script>(.*?)</script>',open('index.html',encoding='utf-8').read(),re.S)))" > /tmp/panel-check.js && node --check /tmp/panel-check.js && echo OK
```

- [ ] **Step 5: Tarayıcıda doğrula**

- Gerçek veriyle bandı aç; tetiklenen kurallar mantıklı mı bak.
- `hareket-tikandi` tetikliyorsa: adı geçen hareketin seansını Antrenman kartında aç, `tikanmaNot()` de aynı şeyi söylüyor olmalı. **Söylemiyorsa eşikler ayrışmış.**
- **İki temayı da** kontrol et; üç öneri birden çıktıysa `ONERI_MAX` kesmesi ve "+N öneri daha" satırı doğru görünmeli.

- [ ] **Step 6: Commit**

```bash
cd ~/panel && git add index.html && git commit -m "Öneri kuralları 2-4: protein açığı, tıkanan hareket, tonaj düşüşü

Üçü de mevcut veriden okuyor, yeni anahtar istemiyor.

Protein en az 4 günlük kayıt istiyor — iki günün ortalaması hüküm vermeye
yetmez. Tıkanma kuralı takiliSeans()'ın eşiğini yeniden kullanıyor;
tikanmaNot() aynı şeyi zaten söylüyor ama yalnızca o hareketin seansı
açılınca, bant bütün programı özetliyor. Tonaj üç haftalık pencere
istiyor, d:vol dolmadan sessiz kalıyor.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Para kuralları — kategori sıçraması, ay sonu açığı

`DEVAM.md` §5.19'un iki tuzağı burada: **pencere eşitliği** ve **sabit gideri günlük ortalamayla çarpmama**.

**Files:**
- Modify: `index.html` (`ONERI` dizisi)
- Test: `$SCRATCHPAD/t-para.mjs`

**Interfaces:**
- Consumes: `ctx.money` (`{ay, buAy, gecenAy}`), `ctx.bugunGun`, `ayPenceresi()`, `SABIT_KAT`, `tl()`
- Produces: `ONERI` içine `kategori-sicrama`, `ay-sonu-acik`
- Kayıt biçimi: `{k:'in'|'out', c:kategori, a:tutar, n:not, d:'YYYY-AA-GG'}`

- [ ] **Step 1: Testi yaz (kırmızı)**

```bash
cat > "$SCRATCHPAD/t-para.mjs" <<'T4'
import { kural, tetiklendi, susuyor, esitle } from './oneri-test.mjs';
const BUGUN='2026-09-15';
const cik=(g,c,a)=>({k:'out',c,a,d:'2026-09-'+String(g).padStart(2,'0')});
const cikG=(g,c,a)=>({k:'out',c,a,d:'2026-08-'+String(g).padStart(2,'0')});
const gel=(g,a)=>({k:'in',c:'Maaş',a,d:'2026-09-'+String(g).padStart(2,'0')});

console.log('kategori-sicrama:');
const ks = kural('kategori-sicrama', BUGUN);
const m=(buAy,gecenAy,gun=15)=>({money:{ay:'2026-09',buAy,gecenAy},bugunGun:gun});
susuyor('ay başında susar (pencere kısa)', ks.kos(m([cik(1,'Yeme-içme',3000)],[cikG(1,'Yeme-içme',200)],3)));
susuyor('geçen ay kayıt yoksa oran anlamsız', ks.kos(m([cik(2,'Yeme-içme',3000)],[])));
susuyor('fark 500 altındaysa susar', ks.kos(m([cik(2,'Yeme-içme',900)],[cikG(2,'Yeme-içme',500)])));
susuyor('oran %60 altındaysa susar', ks.kos(m([cik(2,'Market',2600)],[cikG(2,'Market',2000)])));
tetiklendi('sıçrama tetikler', ks.kos(m([cik(2,'Yeme-içme',2400)],[cikG(2,'Yeme-içme',1100)])));
susuyor('sabit kategori sayılmaz (kira günü kayar)',
  ks.kos(m([cik(8,'Kira',12000)],[cikG(3,'Kira',11000)])));
esitle('pencere eşit: geçen ayın 16-31i sayılmaz',
  ks.kos(m([cik(2,'Yeme-içme',2400)],[cikG(2,'Yeme-içme',1100),cikG(28,'Yeme-içme',9000)])) !== null, true);

console.log('ay-sonu-acik:');
const aa = kural('ay-sonu-acik', BUGUN);
susuyor('ayın ilk haftasında susar', aa.kos(m([cik(2,'Market',5000),gel(1,40000)],[],5)));
susuyor('gelir yoksa açık hesaplanamaz', aa.kos(m([cik(2,'Market',5000)],[])));
susuyor('tempo geliri aşmıyorsa susar', aa.kos(m([cik(2,'Market',3000),gel(1,60000)],[cikG(3,'Kira',12000)])));
tetiklendi('açık tahmini tetikler',
  aa.kos(m([cik(2,'Market',9000),cik(9,'Yeme-içme',9000),gel(1,30000)],[cikG(3,'Kira',12000)])));
T4
node "$SCRATCHPAD/t-para.mjs"
```
Beklenen: `kural yok: kategori-sicrama`. **Kırmızı.**

- [ ] **Step 2: İki kuralı ekle**

`ONERI` dizisinde `tonaj-dusus`'un ARDINA:

```js
  /* 5 — Kategori sıçraması. PENCERE EŞİTLİĞİ zorunlu (DEVAM.md §5.19):
     ayın 15'indeki harcama geçen ayın İLK 15 gününe bakar, tüm ayına değil.
     Sabit kategoriler dışarıda: kira geçen ay 3'ünde, bu ay 8'inde ödendiyse
     kıyas anlamsız çıkar. */
  {id:'kategori-sicrama',alan:'para',kos(ctx){
    const g=ctx.bugunGun;
    if(g<5)return null;                       // pencere çok kısa, sayı uydurma
    const topla=kayitlar=>{const o={};
      ayPenceresi(kayitlar,g).filter(r=>r.k==='out'&&SABIT_KAT.indexOf(r.c)<0)
        .forEach(r=>{o[r.c]=(o[r.c]||0)+num(r.a);});return o;};
    const bu=topla(ctx.money.buAy),gecen=topla(ctx.money.gecenAy);
    let en=null;
    for(const c in bu){
      const eski=gecen[c]||0;
      if(eski<=0)continue;                    // geçen ay hiç yoksa oran anlamsız
      const fark=bu[c]-eski;
      if(fark<500)continue;
      const oran=fark/eski*100;
      if(oran<60)continue;
      if(!en||fark>en.fark)en={c,fark,oran,tutar:bu[c],eski};
    }
    if(!en)return null;
    return {bas:en.c+' bu ay %'+Math.round(en.oran)+' yukarıda',
      metin:'Ayın ilk '+g+' gününde '+tl(en.tutar)+' — geçen ay aynı dönem '+tl(en.eski)+'.'};
  }},

  /* 6 — Ay sonu açığı. SABİT GİDER GÜNLÜK ORTALAMAYLA ÇARPILMAZ
     (DEVAM.md §5.19): kira 30 kez sayılırdı. Değişken gider tempoyla,
     sabit gider geçen ayın toplamı tavan kabul edilerek yürütülüyor. */
  {id:'ay-sonu-acik',alan:'para',kos(ctx){
    const g=ctx.bugunGun;
    if(g<7)return null;
    const y=+ctx.money.ay.slice(0,4),ay=+ctx.money.ay.slice(5,7);
    const gunSayisi=new Date(y,ay,0).getDate();
    const out=(ctx.money.buAy||[]).filter(r=>r.k==='out');
    const deg=out.filter(r=>SABIT_KAT.indexOf(r.c)<0).reduce((a,r)=>a+num(r.a),0);
    const sab=out.filter(r=>SABIT_KAT.indexOf(r.c)>-1).reduce((a,r)=>a+num(r.a),0);
    const gelir=(ctx.money.buAy||[]).filter(r=>r.k==='in').reduce((a,r)=>a+num(r.a),0);
    if(gelir<=0)return null;                  // gelir bilinmiyorsa açık hesaplanamaz
    const gecenSab=(ctx.money.gecenAy||[]).filter(r=>r.k==='out'&&SABIT_KAT.indexOf(r.c)>-1)
      .reduce((a,r)=>a+num(r.a),0);
    const kalanSabit=Math.max(0,gecenSab-sab);
    const tahmin=deg/g*gunSayisi+sab+kalanSabit;
    if(tahmin<=gelir)return null;
    return {bas:'Bu tempoyla ay '+tl(tahmin-gelir)+' açıkla kapanır',
      metin:'Değişken gider günde ort. '+tl(deg/g)+'; ay sonu tahmini '+tl(tahmin)+
        ', bu ayki gelir '+tl(gelir)+'.'};
  }},
```

- [ ] **Step 3: Testi çalıştır (yeşil)**

```bash
node "$SCRATCHPAD/t-para.mjs" && node "$SCRATCHPAD/t-spor.mjs" && node "$SCRATCHPAD/t-kcal.mjs"
```

- [ ] **Step 4: Sözdizimi kontrolü**

```bash
cd ~/panel && python3 -c "import re;print(''.join(re.findall(r'<script>(.*?)</script>',open('index.html',encoding='utf-8').read(),re.S)))" > /tmp/panel-check.js && node --check /tmp/panel-check.js && echo OK
```

- [ ] **Step 5: Tarayıcıda gerçek harcama verisiyle doğrula**

**Bu adım önemli — para kuralları gerçek kayıtla test edilmeli.**
- Harcama & Kazanç kartındaki toplamlarla bandın söylediği sayılar tutmalı.
- Ay sonu tahmini kirayı 30 kez saymamalı: tahmin, gelirin makul bir katı olmalı. Uçuk bir sayı çıkıyorsa `kalanSabit` mantığı bozuk.
- **Ayın ilk haftasında** paneli aç (konsolda test için `bugunGun` küçük bir ay seçilebilir): kurallar susmalı.

- [ ] **Step 6: Commit**

```bash
cd ~/panel && git add index.html && git commit -m "Öneri kuralları 5-6: kategori sıçraması, ay sonu açığı

DEVAM.md §5.19'un iki tuzağı da tasarıma yazılmıştı, kod ikisini de
uyguluyor: kıyas pencereleri eşit (ayın 15'i geçen ayın İLK 15 gününe
bakıyor, tüm ayına değil) ve sabit gider günlük ortalamayla çarpılmıyor
(kira 30 kez sayılırdı). Sabit gider geçen ayın toplamı tavan kabul
edilerek yürütülüyor.

Sabit kategoriler kategori kıyasının dışında: kira geçen ay 3'ünde, bu ay
8'inde ödendiyse aynı gün penceresinde biri var biri yok görünüyor.

Ay başında ikisi de susuyor — pencere kısayken sayı uydurmak yerine
sessiz kalıyor.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---
### Task 7: İş kuralları — başvuru temposu, dönüş yokluğu

**Files:**
- Modify: `index.html` (`ONERI` dizisi)
- Test: `$SCRATCHPAD/t-is.mjs`

**Interfaces:**
- Consumes: `ctx.apps` (`d:myApps` → `[{key,company,position,location,date:'YYYY-AA-GG',status,url}]`), `dayBack(n)`
- Produces: `ONERI` içine `basvuru-tempo`, `donus-yok`

**Bilinen sınır — metne yansıtılmalı:** `d:myApps` yalnızca **panelden** "Başvurdum" denen ilanları tutuyor. Google Sheet'e elle girilen başvurular burada yok. Kural bu yüzden "başvuru yapmıyorsun" demiyor, "panelden kaydedilen başvuru" diyor.

- [ ] **Step 1: Testi yaz (kırmızı)**

```bash
cat > "$SCRATCHPAD/t-is.mjs" <<'T5'
import { kural, tetiklendi, susuyor } from './oneri-test.mjs';
const BUGUN='2026-09-15';
const gunOnce=n=>{const d=new Date(BUGUN+'T12:00:00');d.setDate(d.getDate()-n);
  return d.toLocaleDateString('sv-SE');};
const app=(n,status='Bekliyor')=>({key:'k'+n+status,company:'X',position:'Y',
  date:gunOnce(n),status});
const coklu=(gunler,status)=>gunler.map(n=>app(n,status));

console.log('basvuru-tempo:');
const bt = kural('basvuru-tempo', BUGUN);
susuyor('kayıt yokken susar', bt.kos({apps:[]}));
susuyor('önceki hafta 3 altındaysa susar', bt.kos({apps:coklu([1,8,9])}));
susuyor('tempo korunuyorsa susar', bt.kos({apps:coklu([0,1,2,3,7,8,9,10])}));
tetiklendi('tempo yarıya düştüyse tetikler', bt.kos({apps:coklu([1,7,8,9,10,11,12])}));

console.log('donus-yok:');
const dy = kural('donus-yok', BUGUN);
susuyor('10 altında başvuru susar', dy.kos({apps:coklu([1,2,3,4,5])}));
tetiklendi('21 günde 12 başvuru, hepsi Bekliyor/Ret',
  dy.kos({apps:[...coklu([1,2,3,4,5,6],'Bekliyor'),...coklu([7,8,9,10,11,12],'Ret')]}));
susuyor('biri Görüşme olduysa susar',
  dy.kos({apps:[...coklu([1,2,3,4,5,6],'Bekliyor'),...coklu([7,8,9,10,11],'Ret'),app(12,'Görüşme')]}));
susuyor('pencere dışı başvurular sayılmaz', dy.kos({apps:coklu([25,26,27,28,29,30,31,32,33,34,35])}));
T5
node "$SCRATCHPAD/t-is.mjs"
```
Beklenen: `kural yok: basvuru-tempo`. **Kırmızı.**

- [ ] **Step 2: İki kuralı ekle**

`ONERI` dizisinde `ay-sonu-acik`'ın ARDINA:

```js
  /* 7 — Başvuru temposu. d:myApps YALNIZCA panelden "Başvurdum" denenleri
     tutuyor; Sheet'e elle girilenler burada yok. Metin bu yüzden
     "panelden kaydedilen" diyor, "hiç başvurmuyorsun" demiyor. */
  {id:'basvuru-tempo',alan:'is',kos(ctx){
    const apps=ctx.apps||[];
    const son7=apps.filter(a=>a.date>=dayBack(6)).length;
    const onceki7=apps.filter(a=>a.date>=dayBack(13)&&a.date<dayBack(6)).length;
    if(onceki7<3)return null;                 // kıyas tabanı yoksa hüküm yok
    if(son7>=onceki7/2)return null;
    return {bas:'Başvuru temposu düştü',
      metin:'Son 7 günde '+son7+', önceki 7 günde '+onceki7+
        ' başvuru (panelden kaydedilenler).'};
  }},

  /* 8 — Dönüş yokluğu. Panelde "görüşme" diye bir alan yok; durum
     Bekliyor/Ret ikilisinden ibaret (check_rejections.py Ret yazıyor).
     Kural dolaylı bakıyor: hiçbiri bu ikilinin dışına çıkmamışsa tetiklenir.
     Sheet'te bir satır elle "Görüşme" yapıldıysa susar.
     Çıktı GÖZLEM olarak yazılıyor — panelin "CV'n kötü" diyecek verisi yok. */
  {id:'donus-yok',alan:'is',kos(ctx){
    const liste=(ctx.apps||[]).filter(a=>a.date>=dayBack(20));
    if(liste.length<10)return null;
    const disari=liste.filter(a=>['Bekliyor','Ret'].indexOf(String(a.status||'Bekliyor'))<0);
    if(disari.length)return null;
    const ret=liste.filter(a=>a.status==='Ret').length;
    return {bas:'21 günde '+liste.length+' başvuru, hiç dönüş yok',
      metin:ret+' ret, '+(liste.length-ret)+' cevapsız. Mektup odağını ya da '+
        'ilan seçimini gözden geçirmek isteyebilirsin.'};
  }},
```

- [ ] **Step 3: Bütün testleri çalıştır (yeşil)**

```bash
for t in kcal spor para is susma; do node "$SCRATCHPAD/t-$t.mjs" || break; done
```
Beklenen: hepsi `✓`.

**DİKKAT:** `t-susma.mjs` içindeki `esitle('kural id listesi', …)` artık sekiz id bekliyor olmalı. Güncelle:

```bash
cd "$SCRATCHPAD" && python3 - <<'PY'
import re,io
p='t-susma.mjs'
s=open(p,encoding='utf-8').read()
s=s.replace("['kcal-hukum']",
  "['kcal-hukum','protein-dusuk','hareket-tikandi','tonaj-dusus',"
  "'kategori-sicrama','ay-sonu-acik','basvuru-tempo','donus-yok']")
open(p,'w',encoding='utf-8').write(s)
PY
node "$SCRATCHPAD/t-susma.mjs"
```

- [ ] **Step 4: Sözdizimi kontrolü**

```bash
cd ~/panel && python3 -c "import re;print(''.join(re.findall(r'<script>(.*?)</script>',open('index.html',encoding='utf-8').read(),re.S)))" > /tmp/panel-check.js && node --check /tmp/panel-check.js && echo OK
```

- [ ] **Step 5: Tarayıcıda doğrula**

- Bandın söylediği başvuru sayıları, İş Başvuruları şeridindeki kayıtlarla tutmalı.
- **İki temayı da** kontrol et.

- [ ] **Step 6: Commit**

```bash
cd ~/panel && git add index.html && git commit -m "Öneri kuralları 7-8: başvuru temposu, dönüş yokluğu

d:myApps yalnızca panelden 'Başvurdum' denen ilanları tutuyor, Sheet'e
elle girilenler orada yok. Metin bu yüzden 'panelden kaydedilenler'
diyor — 'hiç başvurmuyorsun' demiyor.

Panelde 'görüşme' diye bir alan yok; durum Bekliyor/Ret ikilisi. Kural 8
dolaylı bakıyor: hiçbir başvuru bu ikilinin dışına çıkmamışsa tetikleniyor,
Sheet'te bir satır elle 'Görüşme' yapıldıysa susuyor. Çıktı gözlem olarak
yazıldı; panelin bundan fazlasını söyleyecek verisi yok.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Bildirime öneri satırı (`push_feed.py`)

Panelin yazdığı `d:oneri`'yi gist'ten okur ve **taze ise** yoklama bildiriminin gövdesine ekler. Ayrı bildirim ve ayrı cron yok.

**Files:**
- Modify: `push_feed.py` (yeni `oneri_satiri()`; `gonder()` imzası ve gövdesi; `main()` içindeki çağrılar)
- Test: `$SCRATCHPAD/t-push.py`

**Interfaces:**
- Consumes: `veri["data"]["d:oneri"]` = `{"t": <ms>, "list": [{"alan","bas","metin"}]}`
- Produces: `oneri_satiri(veri) -> str` (boş string = ekleme yok)
- `gonder(saat, ad, dilim, tur, subs, gizli, gun_anahtari, oneri="")`

**Global Constraints hatırlatması:** Actions log'u herkese açık. Öneri METNİ log'a **basılmaz** — yalnızca eklenip eklenmediği.

- [ ] **Step 1: Testi yaz (kırmızı)**

```bash
cat > "$SCRATCHPAD/t-push.py" <<'T6'
import importlib.util, sys, time, os
spec = importlib.util.spec_from_file_location("pf", os.path.expanduser("~/panel/push_feed.py"))
pf = importlib.util.module_from_spec(spec); spec.loader.exec_module(pf)

simdi = time.time() * 1000
def veri(t_ms, liste):
    return {"data": {"d:oneri": {"t": t_ms, "list": liste}}}

oneri = [{"alan": "spor", "bas": "Protein günde ort. 22 g eksik", "metin": "…"}]
hata = 0
def kontrol(ad, gercek, beklenen):
    global hata
    if gercek == beklenen:
        print("  ✓", ad)
    else:
        print(f"  ✗ {ad}\n    beklenen: {beklenen!r}\n    gerçek:   {gercek!r}"); hata = 1

print("oneri_satiri:")
kontrol("veri yokken boş", pf.oneri_satiri({}), "")
kontrol("liste boşken boş", pf.oneri_satiri(veri(simdi, [])), "")
kontrol("damga yokken boş", pf.oneri_satiri({"data": {"d:oneri": {"list": oneri}}}), "")
kontrol("taze öneri döner", pf.oneri_satiri(veri(simdi, oneri)), "Protein günde ort. 22 g eksik")
kontrol("23 saatlik hâlâ taze", pf.oneri_satiri(veri(simdi - 23*3600*1000, oneri)),
        "Protein günde ort. 22 g eksik")
kontrol("25 saatlik bayat, boş", pf.oneri_satiri(veri(simdi - 25*3600*1000, oneri)), "")
kontrol("bozuk yapı çökmez", pf.oneri_satiri({"data": {"d:oneri": "abc"}}), "")
sys.exit(hata)
T6
python3 "$SCRATCHPAD/t-push.py"
```
Beklenen: `AttributeError: module 'pf' has no attribute 'oneri_satiri'`. **Kırmızı.**

- [ ] **Step 2: `oneri_satiri()`'yi yaz**

`push_feed.py`'de `def gonder(` fonksiyonunun ÜSTÜNE:

```python
ONERI_TAZE_SAAT = 24


def oneri_satiri(veri):
    """Panelin yazdığı en öncelikli öneriyi döndürür; bayatsa boş string.

    Kurallar tarayıcıda çalışıyor (bkz. tasarım notu): panel açılmadan
    d:oneri güncellenmiyor. İki günlük bir öneriyi taze gibi göstermek
    "her gösterge gerçek veriye bağlı" kuralını çiğner, o yüzden 24 saatten
    eskisi bildirime hiç girmiyor.
    """
    try:
        o = ((veri or {}).get("data") or {}).get("d:oneri") or {}
        liste = o.get("list") or []
        damga = o.get("t") or 0
        if not liste or not damga:
            return ""
        yas_saat = (time.time() * 1000 - float(damga)) / 3600000
        if yas_saat > ONERI_TAZE_SAAT:
            return ""
        return str((liste[0] or {}).get("bas") or "").strip()
    except (AttributeError, TypeError, ValueError):
        return ""
```

- [ ] **Step 3: Testi çalıştır (yeşil)**

```bash
python3 "$SCRATCHPAD/t-push.py"
```
Beklenen: yedi satır da `✓`.

- [ ] **Step 4: `gonder()`'e bağla**

İmzayı değiştir:

```python
def gonder(saat, ad, dilim, tur, subs, gizli, gun_anahtari, oneri=""):
```

Gövde satırını değiştir:

```python
        "body": f"{saat} · başladın mı?" + (f" · {oneri}" if oneri else ""),
```

Sonundaki özet satırına, **öneri metnini basmadan**, yalnızca eklenip eklenmediğini yaz:

```python
    print(f"{ad} ({saat}) — {basarili}/{len(subs)} cihaza gönderildi."
          + (f" ölü abonelik: {len(olu)}" if olu else "")
          + (" · öneri eklendi" if oneri else ""))
```

- [ ] **Step 5: `main()`'deki çağrılara geçir**

`main()` içinde `veri` çözüldükten sonra (yani `veri = json.loads(veri_ham) if veri_ham else {}` satırının ardına):

```python
    oneri = oneri_satiri(veri)
```

ve `gonder(...)` çağrılarının hepsine son argüman olarak `oneri` ekle.

```bash
cd ~/panel && grep -n "gonder(" push_feed.py
```
Her çağrının `oneri` aldığından emin ol.

- [ ] **Step 6: Python sözdizimi + kuru koşum**

```bash
cd ~/panel && python3 -m py_compile push_feed.py && echo "derleme OK"
cd ~/panel && PANEL_GIST_TOKEN= VAPID_PRIVATE= python3 push_feed.py
```
İkincisi `secret tanımlı değil: … — atlandı.` yazıp 0 dönmeli — secret olmadan çökmemeli.

- [ ] **Step 7: Kişisel veri + log taraması**

```bash
cd ~/panel && grep -n "print(" push_feed.py | grep -i "oneri\|öneri"
```
Beklenen: yalnızca `" · öneri eklendi"` — öneri **metnini** basan bir satır olmamalı.

```bash
cd ~/panel && grep -rInE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(\+90|0)5[0-9]{9}|gh[pousr]_[A-Za-z0-9]{20,}|sk-ant-" index.html *.py
```
(`VAPID_SUB_VARSAYILAN` içindeki mailto adresi zaten repoda ve kullanıcının değil — yeni bir eşleşme çıkmamalı.)

- [ ] **Step 8: Commit**

```bash
cd ~/panel && git add push_feed.py && git commit -m "Bildirim gövdesine öneri satırı: taze ise ekler, bayatsa eklemez

Ayrı bildirim ve ayrı cron YOK — dış zamanlayıcı (DEVAM.md A1) kurulmadan
zamanlama zaten güvenilmez, ikinci bir akış riski ikiye katlardı. Öneri
mevcut yoklama bildiriminin gövdesine giriyor.

Kurallar tarayıcıda çalıştığı için panel açılmadan d:oneri güncellenmiyor;
24 saatten eski öneri bildirime hiç girmiyor. Bayat öneriyi taze göstermek
'her gösterge gerçek veriye bağlı' kuralını çiğnerdi.

Actions log'u herkese açık: log'a öneri METNİ değil, yalnızca eklenip
eklenmediği yazılıyor. Öneri metni harcama ve başvuru bilgisi taşıyabilir.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Uçtan uca doğrulama, DEVAM.md, canlıya alma

**Files:**
- Modify: `DEVAM.md`
- Test: tarayıcı, iki tema, 7 gün, canlı sayfa

- [ ] **Step 1: Bütün testleri son kez koştur**

```bash
for t in kcal spor para is susma; do node "$SCRATCHPAD/t-$t.mjs" || exit 1; done && python3 "$SCRATCHPAD/t-push.py" && echo "HEPSİ GEÇTİ"
```

- [ ] **Step 2: Boş veri senaryosu**

Yeni bir tarayıcı profilinde (ya da gizli pencerede) paneli aç — hiçbir `d:` anahtarı yokken:
- Bant görünmemeli.
- Konsolda hata olmamalı.
- Hiçbir kural sayı uydurmamalı.

- [ ] **Step 3: Yedi günü de gez**

Antrenman ve program güne göre değişiyor. Konsolda sahte gün kurup her gün için bandı kontrol et; `hareket-tikandi` kuralı `programHareketleri()` üzerinden bütün haftayı zaten geziyor, ama render'ın günden bağımsız çalıştığı doğrulanmalı.

- [ ] **Step 4: İki temayı da gez**

`data-theme` = `almanak` ve `hud`. Bandın kenar çizgisi, etiketi ve `[×]`'i ikisinde de okunur olmalı; sabit renk kullanılmadığı için ikisinde de değişkenlerden gelmeli.

- [ ] **Step 5: Mobil genişlik**

640 px altında `.oneri-et` etiketi gizleniyor. Dar ekranda başlık ve metin taşmamalı.

- [ ] **Step 6: `DEVAM.md`'yi güncelle**

Şunları yaz:
- Bölüm 1'e: sabit şeridin üstünde **Öneri Bandı**, veri kaynağı "aşağıdaki kartların türevi + `d:oneriKapali`".
- Bölüm 1'in anahtar listesine: `d:oneri`, `d:oneriKapali`.
- Bölüm 2 C1'e (faz anahtarı): hüküm mantığı artık `hdHukum()`'da, cut için çevrilecek **tek yer** orası.
- Bölüm 3'e (verilmiş kararlar) yeni satır:
  **"Öneri motoru modelsiz — kurallar `index.html`'de, deterministik."** Gerekçe: LLM kararıyla tutarlı, anahtarsız, çevrimdışı. Bedeli bilerek kabul edildi: panel açılmadan öneri güncellenmiyor, 24 saatten eski öneri bildirime girmiyor. Kuralları Python'a kopyalama **önerilmesin**.
- Bölüm 5'e (tuzaklar) yeni madde: **kural `id`'leri kararlıdır** — değişirse kullanıcının susturması sessizce kaybolur.
- Bölüm 7'ye oturum satırı.

- [ ] **Step 7: Kişisel veri taraması (push öncesi, 1. kural)**

```bash
cd ~/panel && grep -rInE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(\+90|0)5[0-9]{9}|gh[pousr]_[A-Za-z0-9]{20,}|sk-ant-" index.html *.py docs/
```

- [ ] **Step 8: Commit ve push**

```bash
cd ~/panel && git add DEVAM.md && git commit -m "DEVAM.md: öneri bandı, yeni anahtarlar, modelsiz kararı

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
cd ~/panel && git fetch && git rebase origin/main && git push origin main
```

- [ ] **Step 9: Canlıda doğrula**

`LC_ALL=C` şart (`DEVAM.md` §6 — Türkçe karakterde "character not in range" verip sessizce eşleşmiyor):

```bash
until curl -s "https://dogukandurukan.github.io/panel/index.html?cb=$(date +%s)" | LC_ALL=C grep -q "oneriBox"; do sleep 10; done; echo "canlıda"
```

Sonra telefondan aç: bant görünüyor mu, `[×]` çalışıyor mu, senkron sonrası Mac'te de susmuş mu.

- [ ] **Step 10: Scratchpad testlerini bırak**

Test dosyaları repoya **girmiyor**. Doğrulandı:

```bash
cd ~/panel && git status --porcelain && echo "temiz olmalı"
```

---

## Self-review notu

Spec'in her bölümü bir göreve bağlı:

| Spec bölümü | Görev |
|---|---|
| Yerleşim (`#oneriBox`, hidden) | 2 |
| Yapı (`ONERI`, `ctx`, tek toplama) | 2 |
| Kural 1 + `hdHukum()` ayrıştırma | 1, 3 |
| Kural 2, 3, 4 | 5 |
| Kural 5, 6 (pencere eşitliği, sabit gider) | 6 |
| Kural 7, 8 | 7 |
| Susturma (`d:oneriKapali`, 7 gün) | 4 |
| Bildirim (`d:oneri`, 24 saat tazelik) | 2 (yazma), 8 (okuma) |
| İki tema | 2 (CSS), her görevin tarayıcı adımı |
| Doğrulama listesi | 9 |
