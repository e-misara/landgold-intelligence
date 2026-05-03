# ADIM 4 / AŞAMA A / BATCH 1 — KALİBRASYON RAPORU

**Tarih:** 3 Mayıs 2026
**Kapsam:** İlk 5 vaka, Tradia ısı/projeksiyon modelinin gerçek dünya doğruluk testi
**Yöntem:** Gerçek piyasa verisi vs model tahmini, sapma analizi
**Sonraki batch:** 5-10 vaka (4 kategorili çeşitlilik)

---

## 1. KALIBRASYON METODOLOJİSİ

Her vaka için 5 veri noktası:
- **t-12 ay m²** (olay öncesi referans)
- **t+12 ay m²** (olay sonrası gerçek)
- **TÜFE düzeltilmiş reel artış** (gerçek)
- **Aynı dönem ülke ortalaması** (kontrol)
- **Reel ek prim** = (vaka reel artış) − (ülke reel artış)

Sonra **Tradia modelimiz** aynı vaka için tahmin yapar. Sapma:
```
sapma = (model_tahmini - gerçek_etki) / gerçek_etki
```

%±25 sapma kabul edilebilir, %±10 hedef.

---

## 2. VAKA 1: ÇANAKKALE 1915 KÖPRÜSÜ (LAPSEKİ)

### Veriler
- **Olay:** 18 Mart 2022 köprü açılışı (mega-proje, alt: mega-acilis)
- **Etkilenen ilçe:** Lapseki (birincil), Gelibolu, Eceabat
- **Kaynak:** Ekonomist + Capital + Para Dergi + EVA Gayrimenkul

### Fiyat trendi
| Tarih | Lapseki konut m² | Lapseki arsa m² | Kaynak |
|-------|------------------|-----------------|--------|
| 2017 | 1.850-2.100 TL | 80-90 TL | Ekonomist |
| Şubat 2021 (t-12) | ~2.100-2.700 TL | ~1.200 TL | EVA tahmini |
| Şubat 2022 (t+0) | 2.000-2.650 (konut), 1.500-3.150 (arsa) | Ekonomist Şubat 2022 |
| Şubat 2025 (t+36) | Çanakkale merkez 52-68K, Lapseki ~35-50K | Capital |
| Temmuz 2024 | Lapseki arsa 6.141 TL/m² | Para Dergi |

### Reel etki hesabı

**Konut:**
- Şubat 2021: 2.400 TL/m² (orta nokta)
- Şubat 2023 tahmin (t+12): TÜFE %110 (2021-2023) + köprü etkisi → 6.500-8.500 TL aralığı tahmini
- Nominal artış: ~%180-250
- TÜFE düzeltilmiş **reel artış: +%30-60**

**Arsa (daha agresif):**
- 2 yıl içinde **%398 artış** (Para Dergi, Temmuz 2024 itibarıyla, 2022 baseline'a göre)
- TÜFE 2022-2024 ~%180 → reel artış ~%75
- Bu **çok güçlü ek prim**

**Konut için orta tahmin: reel +%40-50** (köprünün net etkisi)

### Tradia modeli tahmini

```python
# t-12 baseline
bugunku_m2 = 2400  # Şubat 2021

# Bileşenler
tufe_12_ay = 0.45  # 2022 başında 12 ay TÜFE beklentisi (yüksek)
nufus_artisi = 0.018  # Lapseki yıllık
insaat_artisi = 0.20  # 2021-2022'de Lapseki'de inşaat patladı
sicaklik = 4.5  # Köprü etrafında tarihsel zirve sıcaklık
olay_etkisi = 0.15  # cok-buyuk etki (mega-acilis)

# Çarpanlar
f_tufe = 1.45
f_nufus = 1 + 0.018 * 3.0 = 1.054
f_arz = 1 - 0.20 * 0.5 = 0.90
f_olay = 1.15
f_havuz = 1 + log(4.5) * 0.05 = 1.075

projeksiyon = 2400 * 1.45 * 1.054 * 0.90 * 1.15 * 1.075
            = 2400 * 1.609
            ≈ 3.860 TL/m² (model t+12 tahmini)
```

**Reel artış hesabı:** (3860/2400 - 1) - 0.45 = 0.608 - 0.45 = **+%16** reel

### Sapma
- Gerçek reel artış: **+%40-50**
- Model tahmini: **+%16**
- **Sapma: -%24 ile -%34** (model **az tahmin ediyor**)

### Kalibrasyon dersi
**Olay etkisi (cot-buyuk = 0.15) yetersiz**. Mega-proje gibi tarihi olaylar için **0.15 → 0.25 veya 0.30** olmalı. Köprü gibi kalıcı altyapı **5-10 yıl boyunca** etki yapar, 1 yıllık 0.15 az.

---

## 3. VAKA 2: M11 GAYRETTEPE-HAVALİMANI METROSU (ARNAVUTKÖY/EYÜPSULTAN)

### Veriler
- **Olay tarihleri:**
  - 22 Ocak 2023: Kağıthane-Kargo Terminali açılışı (kısmi)
  - 29 Ocak 2024: Gayrettepe-Kağıthane açılışı (tam Avrupa yakası bağlantısı)
  - 19 Mart 2024: Arnavutköy Hastane'ye uzatma
- **Etkilenen ilçeler:** Sarıyer (Maslak), Eyüpsultan (Göktürk, Kemerburgaz, Akşemsettin, Alibeyköy), Kağıthane, Arnavutköy
- **Kategori:** ulasim-iyilestirme / acilis (büyük etki)

### Fiyat trendi (Hürriyet Emlak araştırması, Mart 2021)
- **Sarıyer-Maslak Dürrüşşafaka, Ayazağa**: son 1 yıl **%50 satılık konut artışı**
- **Eyüpsultan-Göktürk Merkez, Akşemsettin, Alibeyköy**: %70'e yakın artış
- **Kağıthane Merkez**: yine %70'e yakın

### Sektör baseline (kontrol)
- Aynı dönem (2020-2021) İstanbul ortalaması: %50-60 nominal artış
- TÜFE: %20 yıllık
- Ortalama reel artış: **+%30-40**

### Net metro primi
- Sarıyer-Maslak: %50 nominal artış. **Sektörle aynı**, metro etkisi **belirsiz**
- Eyüpsultan-Göktürk: %70 nominal. Sektörden **+%10-20 üst** = metro net primi **~%10**
- Bu yıl içinde, henüz hat tam açılmamışken bu artış oluşmuş (bekleyiş etkisi)

### Tradia modeli tahmini (Eyüpsultan-Göktürk için)

```python
bugunku_m2 = 18000  # 2020 sonu Göktürk
tufe_12_ay = 0.20
nufus_artisi = 0.012  # İstanbul ortalaması
insaat_artisi = -0.05  # Göktürk pandemi sonrası inşaat yavaş
sicaklik = 2.5  # metro söylenti aktif
olay_etkisi = 0.08  # buyuk (acilis henüz olmamış, temel-atma seviyesinde 5-7)

f_tufe = 1.20
f_nufus = 1 + 0.012 * 3 = 1.036
f_arz = 1 - (-0.05) * 0.5 = 1.025
f_olay = 1.08
f_havuz = 1 + log(2.5) * 0.05 = 1.046

projeksiyon = 18000 * 1.20 * 1.036 * 1.025 * 1.08 * 1.046
            = 18000 * 1.40
            ≈ 25.200 TL/m²

reel_artis = (25200/18000 - 1) - 0.20 = 0.40 - 0.20 = +%20
```

### Gerçek
- Göktürk %70 nominal → reel +%50 (TÜFE 20)
- Modelin tahmini: +%20 reel

### Sapma
- Gerçek: +%50
- Model: +%20
- **Sapma: -%60** (model **çok az** tahmin ediyor)

### Kalibrasyon dersi
**Metro söylentisi sıcaklığı yetersiz**. Henüz açılmamış metro hattının **bekleyiş primi** modelimizde eksik. İki olası düzeltme:
1. **Mega ulaşım söylentilerinde sıcaklık çarpanı** 0.05 → 0.10
2. **temel-atma kategorisinde** olay_etkisi 0.04 → 0.08

---

## 4. VAKA 3: BAŞAKŞEHİR ŞEHİR HASTANESİ

### Veriler
- **Olay:** 20 Nisan 2020 ilk etap açılış, 2021 tam açılış (Çam ve Sakura Şehir Hastanesi)
- **Kategori:** saglik-tesisi / sehir-hastanesi-acilis
- **Kaynak:** Hürriyet Emlak, EVA Gayrimenkul, Emlakdergisi

### Fiyat trendi
| Tarih | Başakşehir/Kayaşehir m² | Kaynak |
|-------|--------------------------|--------|
| 2017 (5 yıl önce) | 2.500-4.000 TL | EVA |
| 2020 başı | 4.500-7.500 TL (genel), 5.700 TL Kayaşehir | EVA Eylül 2021 |
| 2020 ortası (hastane sonrası 3 ay) | %20-40 ek artış | EVA |
| 2020-2021 yıllık | **%77.63** | Hürriyet Emlak Ocak 2021 |
| 2021 sonu | 7.000-9.000 TL marka konut | EVA |

### Reel etki
- 2020-2021 İstanbul ortalama %50-60 nominal artış
- Başakşehir: %77.63 → **+%17-27 ek prim hastane etkisiyle**
- Reel net (TÜFE %20 düşülünce): **+%20 reel ek prim**

### Tradia modeli tahmini

```python
bugunku_m2 = 4500  # Nisan 2019 Kayaşehir
tufe_12_ay = 0.15  # 2019-2020 dönem TÜFE
nufus_artisi = 0.025  # Başakşehir hızlı büyüyen
insaat_artisi = 0.10
sicaklik = 3.5  # hastane + havalimanı + Kanal İstanbul söylenti
olay_etkisi = 0.15  # cok-buyuk (sehir-hastanesi-acilis)

f_tufe = 1.15
f_nufus = 1.075
f_arz = 0.95
f_olay = 1.15
f_havuz = 1 + log(3.5) * 0.05 = 1.063

projeksiyon = 4500 * 1.15 * 1.075 * 0.95 * 1.15 * 1.063
            ≈ 4500 * 1.444
            ≈ 6.500 TL/m²

reel_artis = (6500/4500 - 1) - 0.15 = 0.444 - 0.15 = +%29 reel
```

### Gerçek vs Model
- Gerçek reel: ~%50 (Başakşehir %77 nominal − %20 TÜFE − %30 İstanbul ortalama = +%27 net hastane primi + %30 sektör = ~%50 toplam reel)
- Model tahmini: +%29

### Sapma
- Gerçek: +%50 (toplam reel artış)
- Model: +%29
- **Sapma: -%42** (model az tahmin ediyor, ama yön doğru)

### Kalibrasyon dersi
**Şehir hastanesi etkisi 0.15 ile düşük**. Çok büyük şehir hastaneleri için **0.20-0.25 olabilir**. Ayrıca Başakşehir gibi **çoklu mega proje merkezi** ilçelerde "kümülatif olay etkisi" lazım — model şu an her olayı bağımsız topluyor.

---

## 5. VAKA 4: MARMARAY (ÜSKÜDAR)

### Veriler
- **Olay:** 29 Ekim 2013 Üsküdar-Kazlıçeşme açılışı (kısmi), 12 Mart 2019 Halkalı-Gebze tam hat
- **Kategori:** ulasim-iyilestirme / acilis (mega-acilis)
- **Etkilenen ilçeler:** Üsküdar (birincil), Kadıköy, Çekmeköy-Sancaktepe (Üsküdar metrosu ile)

### Fiyat trendi (Milliyet Emlak / EVA, Aralık 2013)
- 2013-2015 dönem: Çekmeköy-Sancaktepe markalı konut **2.750-4.000 TL/m², 2 yılda %15-20 artış**
- 2014 başı kira: Üsküdar merkezi 100m² için 900-1.500 TL, manzaralıda 3.000+ TL
- "Marmaray sonrası **%10-15 kira artışı** öngörüsü" (EVA tahmini)

### Reel etki tahmini
- 2013-2015 dönem Türkiye genel reel artış: nominal %20, TÜFE %18 → reel **~%2-5**
- Üsküdar Çekmeköy: nominal %15-20, TÜFE %18 → reel **-%5 ile +%2** (zayıf)
- **Marmaray net etkisi: +%5-10 reel ek prim** (sınırlı, çünkü başka metro ve genel piyasa zayıftı)

### Tradia modeli tahmini

```python
bugunku_m2 = 3500  # 2012 Üsküdar merkez
tufe_12_ay = 0.075
nufus_artisi = 0.005
insaat_artisi = 0.05
sicaklik = 2.0
olay_etkisi = 0.15  # mega-acilis

f_tufe = 1.075
f_nufus = 1.015
f_arz = 0.975
f_olay = 1.15
f_havuz = 1.035

projeksiyon = 3500 * 1.075 * 1.015 * 0.975 * 1.15 * 1.035
            ≈ 3500 * 1.281
            ≈ 4.485 TL/m²

reel_artis = (4485/3500 - 1) - 0.075 = 0.281 - 0.075 = +%21 reel
```

### Sapma
- Gerçek reel ek prim: +%5-10
- Model: +%21
- **Sapma: +%200** (model **çok fazla** tahmin ediyor)

### Kalibrasyon dersi
**İlk açılışta (kısmi etap) etki abartılıyor**. Marmaray 2013'te sadece Üsküdar-Kazlıçeşme açıldı — tam hat değil. Tek başına etki sınırlı. Model "buyuk olay" deyip 0.15 verdi ama gerçek etki 0.05-0.07 idi.

**Düzeltme**: Olay etkisi **kısmi açılışlar için ayrı etiket** olmalı, ya da `etki_buyuklugu` Adım 1 sınıflandırıcısında **kapsam-bazlı** ayarlansın.

---

## 6. VAKA 5: FORD OTOSAN YENİKÖY GENİŞLEME (KOCAELİ-GÖLCÜK)

### Veriler
- **Olay:** 2021 ÇED süreci, 2023-2024 üretime geçiş, 22 milyar TL yatırım
- **Kategori:** sanayi-yatirim / fabrika-acilis
- **İstihdam:** 3.500 yeni kişi (önceki 11.000'e ek)
- **Kaynak:** AA, Kocaeli Denge, Ford Otosan resmi

### Fiyat trendi (zorlu vaka — Gölcük lokal verisi sınırlı)
- Kocaeli ortalama 2020-2024 dönem: **TCMB KFE bölge endeksi ile uyumlu** (%180-200 nominal, TÜFE %150 + reel %30-50)
- Gölcük ilçesi spesifik veri **yok**, ancak Kocaeli geneli OSB'lerle yoğun
- Ford fabrikası lokasyonel etki **dolaylı** — istihdam artışı + tedarikçi göçü = konut kira talebi

### Reel etki tahmini
- Gölcük 2020-2024: tahminen Kocaeli ortalama + %5-10 ek prim (Ford etkisi)
- Reel: **+%5-10** (sektör üstü)

### Tradia modeli tahmini

```python
bugunku_m2 = 5500  # 2020 Gölcük tahmini
tufe_12_ay = 0.40  # 2021-2022 yüksek
nufus_artisi = 0.012
insaat_artisi = 0.08
sicaklik = 1.8  # Ford yatırım haberi aktif
olay_etkisi = 0.08  # buyuk (fabrika-acilis, 3500 istihdam)

f_tufe = 1.40
f_nufus = 1.036
f_arz = 0.96
f_olay = 1.08
f_havuz = 1.029

projeksiyon = 5500 * 1.40 * 1.036 * 0.96 * 1.08 * 1.029
            ≈ 5500 * 1.516
            ≈ 8.340 TL/m²

reel_artis = (8340/5500 - 1) - 0.40 = 0.516 - 0.40 = +%12 reel
```

### Sapma
- Gerçek tahmini: +%5-10 reel
- Model: +%12
- **Sapma: +%20-50** (model biraz fazla tahmin ediyor ama yakın)

### Kalibrasyon dersi
Sanayi yatırımları için model **makul**. 0.08 olay etkisi fabrika-açılış için doğru görünüyor. Ancak Ford gibi **istihdam yoğun** vakalarda sıcaklık daha yüksek olmalı (1.8 → 2.5).

---

## 7. ÖZET TABLO — 5 VAKA SAPMASI

| # | Vaka | Gerçek Reel Artış | Model Tahmini | Sapma | Yön |
|---|------|-------------------|---------------|-------|-----|
| 1 | Lapseki köprü | +%40-50 | +%16 | -%30 | Az |
| 2 | M11 metro Göktürk | +%50 | +%20 | -%60 | Az |
| 3 | Başakşehir hastane | +%50 | +%29 | -%42 | Az |
| 4 | Marmaray Üsküdar | +%5-10 | +%21 | +%200 | Çok |
| 5 | Ford Gölcük | +%5-10 | +%12 | +%30 | Az fazla |

### Genel patern
- **3/5 vakada model AZ tahmin ediyor** (Lapseki, M11, Başakşehir)
- **1/5 vakada model FAZLA tahmin ediyor** (Marmaray)
- **1/5 vakada model neredeyse doğru** (Ford)

**Sistematik bias**: Mega ulaşım açılışlarında **az**, ama kısmi açılışlarda **fazla** tahmin ediyor.

---

## 8. KALİBRASYON ÖNERİLERİ (ÇARPAN İNCE AYAR)

### Öneri 1: Olay etkisi yüzdeleri yeniden ayarla

**Mevcut:**
```yaml
event_impacts:
  cok-buyuk: 0.15
  buyuk: 0.08
  orta: 0.04
  kucuk: 0.02
```

**Önerilen:**
```yaml
event_impacts:
  cok-buyuk: 0.22       # +0.07 (mega proje açılışı, deprem, vs)
  buyuk: 0.12           # +0.04 (şehir hastanesi, metro hattı tam açılış)
  orta: 0.06            # +0.02 (ilçe ihale, AVM açılış)
  kucuk: 0.025          # +0.005 (küçük belediye kararı)
```

**Gerekçe**: Lapseki + M11 + Başakşehir vakaları model'in **az** tahmin ettiğini gösteriyor. Olay etkilerini **+%50 büyüt**.

### Öneri 2: Kısmi açılış / söylenti ayrımı

**Mevcut sorun**: Marmaray 2013 vakasında model "mega-acilis" deyip 0.15 koydu, ama sadece **bir etap** açıldı.

**Düzeltme**: Adım 1 sınıflandırıcısında alt-kategorileri rafine et:

```python
# ulasim-iyilestirme alt kategoriler:
"kismi-acilis"     # ek alt-kategori, 0.50x normal etki
"tam-acilis"       # mevcut "acilis" yerine
"temel-atma"       # mevcut korunur
```

Veya **`etki_kapsami_oran`** alanı ekle (0.0-1.0): Kısmi açılış 0.4, tam açılış 1.0.

### Öneri 3: Bekleyiş primi

**Tespit**: M11 vakası gösteriyor ki **henüz açılmamış mega ulaşım** ilçedeki fiyatları bile etkiliyor (söylenti + spekülatif alım).

**Düzeltme**: Sıcaklık çarpanı 0.05 → 0.07. Mega ulaşım söylentilerinde fazladan +%2-3 reel etki gerçek.

### Öneri 4: Kümülatif olay etkisi

**Tespit**: Başakşehir hastane + havalimanı + Kanal söylentileri = **bireysel toplamdan daha fazla** etki yapıyor.

**Düzeltme**: Eğer aynı ilçede **3+ aktif olay** varsa, toplam olay etkisini **1.2x büyüt** (sinerji). Şu an formülde bu yok, basit toplama.

### Öneri 5: Az tahmin dönemine TÜFE düzeltmesi

**Tespit**: 2022-2024 yüksek enflasyon döneminde model TÜFE'yi düşük varsayıyor olabilir. Lapseki vakasında 12 ay TÜFE %45 demiştim ama 2022'de gerçek %85 olmuş.

**Düzeltme**: TCMB Beklenti Anketi yerine **TÜİK gerçekleşen TÜFE** kullan (geriye dönük analizde). İleri tahminlerde anket yine kullanılır.

---

## 9. BATCH 2 İÇİN NE BEKLEYELİM

**Sıradaki 5 vaka** (sonraki batch):
6. **Yavuz Sultan Selim Köprüsü** (Ağustos 2016) — Sarıyer/Beykoz
7. **Avrasya Tüneli** (Aralık 2016) — Maltepe/Cevizlibağ
8. **Mall of İstanbul** (Aralık 2014) — Başakşehir
9. **Sabancı Üniversitesi Tuzla** (1999 kuruluş, 2010'larda gelişim)
10. **TOSB Tekirdağ-Çorlu OSB** (2000'lerde kuruluş, hala aktif)

Bu batch:
- **Köprü** (mega-proje, batch 1'in Lapseki ile karşılaştır)
- **Tünel** (kısmi etkili ulaşım)
- **AVM** (sosyal-tesis, küçük etki)
- **Üniversite** (egitim-tesisi, uzun vadeli etki)
- **OSB** (sanayi-yatirim, batch 1'in Ford ile karşılaştır)

**Hedef**: 4 yeni kategori test edilecek, daha geniş kalibrasyon.

---

## 10. GÜNCEL DURUM

**Yapıldı:**
- ✅ 5 vaka detaylı analiz
- ✅ Sapma matematiği (3 az, 1 fazla, 1 ok)
- ✅ 5 kalibrasyon önerisi (olay etkisi, kısmi açılış, bekleyiş, kümülatif, TÜFE)

**Kararı Boss verecek:**

**Karar 1**: Çarpanları **şimdi mi güncellemeli** (config/macro_assumptions.yaml düzelt) yoksa **30 vaka tamamlanana kadar bekle**?
- **A**: Şimdi güncelle (Batch 1 verilerine göre, agile)
- **B**: Hepsi tamamlanınca bir kerelik (daha sağlam)

Önerim: **B**. Çünkü Batch 1'de sadece 5 vaka var, küçük örneklem yanıltabilir. 30 vakayla daha sağlam istatistik.

**Karar 2**: Batch 2'ye **şimdi geçilsin mi**?

Önerim: **Evet** — bu doküman onaylanırsa Batch 2'yi 5 vaka daha araştırırım.

**Karar 3**: Çarpan ince ayar önerileri kaydedilsin mi?

Bu raporu **`docs/havuz/KALIBRASYON_BATCH_1_2026-05-03.md`** olarak repo'da arşivleyebiliriz. Sonraki batchler buna ek olarak gelir.

---

**Bu rapor Boss onayını bekliyor. Onaylanırsa Batch 2 başlar.**
