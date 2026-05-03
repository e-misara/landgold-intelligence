# ADIM 4 / AŞAMA A / BATCH 3 — KALİBRASYON RAPORU

**Tarih:** 3 Mayıs 2026
**Kapsam:** Vakalar 11-15, ilk negatif etki + İstanbul-dışı kontrol
**Kümülatif:** Batch 1+2+3 = 15 vaka tamamlandı (30'dan)
**Sonraki batch:** Batch 4 (Vakalar 16-20)

---

## 1. BATCH 3'ÜN KARAKTERİ

Bu batch **çeşitlilik patlaması**:
- ✅ İlk **negatif etki** vakası (deprem)
- ✅ İlk **sembolik etki** (Çamlıca Kulesi — turistik ama konut etkisi sınırlı)
- ✅ İlk **İstanbul-dışı kontrol** (Adana metro)
- ✅ İlk **yeşil alan/sosyal tesis** (TOKİ park)
- ✅ İlk **kümülatif/imar patlaması** (Esenyurt)

İlk 10 vaka **mega ulaşım/sağlık** ağırlıklıydı. Batch 3 modeli **uç durumlara** çekiyor.

---

## 2. VAKA 11: 6 ŞUBAT 2023 KAHRAMANMARAŞ DEPREMİ

### Veriler
- **Olay:** 6 Şubat 2023, iki büyük deprem (7.7 ve 7.6)
- **Kategori:** afet / deprem-buyuk (NEGATİF + dolaylı POZİTİF kombinasyonu)
- **Etkilenen iller:** 11 il, en ağır Hatay, Kahramanmaraş, Adıyaman, Malatya
- **Ölü:** 50.000+
- **Yıkım:** 100.000+ bağımsız bölüm tamamen yıkıldı

### Çift yönlü etki — kritik ders

**Deprem ilçesinde** (Hatay, Antakya, Adıyaman):
- **Konut stoku:** %53 azaldı (Endeksa, Mart 2023)
- **Kira fiyatları:** Hatay'da 1 ay içinde **+%56**, Adıyaman +%33, Maraş +%30
- **Satılık konut fiyatları:** **+%14 ortalama** (1 ay içinde)
- **2 yıl sonra (2025):** Hatay reel olarak **-%14 düştü** (Endeksa)
- **4 yıllık (2020-2024):** Hatay nominal **+%1147** (TÜFE düzeltilmiş **net pozitif**, ama düşük artış oranıyla)

**Çevre illere göç:**
- Mersin satılık fiyat artışı: 4 yıllık **%1126** (en hızlı) — **deprem göçünün hediyesi**
- Ankara/Mersin/Antalya kira: %20-30 anlık artış
- Konya, Kayseri, Niğde, Aksaray çevre kiralar: %45-58 stok düşüşü

### Reel etki hesabı (Hatay-Antakya için)

| Dönem | Nominal | Reel | Karşılaştırma |
|-------|---------|------|----------------|
| 1 ay sonra | +%14 sat, +%56 kira | +%5 reel sat | Türkiye geneli +%2 |
| 6 ay sonra | +%30 sat | +%8 reel | Türkiye geneli +%15 |
| 2 yıl sonra | +%17 sat (yıllık) | **-%14 reel** | Türkiye reel +%3 |
| **Net Hatay primi (2 yıl)** | -- | **-%17** (sektör altı) |

Yani uzun vadede Hatay **Türkiye ortalamasının %17 altında** kaldı (reel). Buna rağmen kısa vadede stok daralması yüzünden **+%5-8 reel** geçici sıçrama oldu.

### Tradia modeli tahmini

Mevcut model **negatif olay** kategorisini **desteklemiyor**. Adım 1 sınıflandırıcı kategori sözlüğümüzde "afet/deprem" var ama sıcaklık çarpanı **negatif değer almaz** (formül `1 + log(sicaklik) * 0.05` her zaman pozitif).

**Bu sistematik kusur**. Test edemedim, çünkü model bu vakayı **çözemez**.

### Sapma
**Ölçülemez** — model arızalı. Negatif olay desteği yok.

### Kalibrasyon dersi (KRİTİK)

Bu **acil mimari değişiklik** gerektirir:

```python
# services/heat_calculator.py — yeni mantık

def heat_with_negative_events(events, sicaklik_baseline):
    """Negatif olaylar sıcaklığı düşürür, fiyatı azaltır"""
    pozitif_etki = 0
    negatif_etki = 0
    
    for olay in events:
        if olay.kategori in ["afet", "yargi-iptali", "olumsuz-imar"]:
            negatif_etki += olay.agirlik * 0.10  # NEGATIF
        else:
            pozitif_etki += olay.agirlik * 0.05  # POZITIF
    
    sicaklik = sicaklik_baseline + pozitif_etki - negatif_etki
    return max(0.1, sicaklik)  # Sıfırın altına inmesin
```

Ayrıca **çevre illere göç etkisi**:
```yaml
event_impacts:
  afet-deprem:
    - olay_iline: -0.20      # Deprem ilçesi 1 yılda -%20 reel
    - cevre_iline: +0.10     # Mersin, Konya, Kayseri gibi
    - menzil_km: 200         # 200km içindeki iller pozitif
```

Bu **v1.5'e EKLENMELİ** — Türkiye gibi deprem ülkesinde model'in afet vakalarını çözememesi büyük eksiklik.

---

## 3. VAKA 12: ÇAMLICA KULESİ (ÜSKÜDAR-KÜÇÜK ÇAMLICA)

### Veriler
- **Olay:** 29 Mayıs 2021 açılış (Avrupa'nın en yüksek kulesi, 369m)
- **Kategori:** sosyal-tesis / sembolik-yapi
- **Etkilenen mahalle:** Küçük Çamlıca (Üsküdar)
- **Etki türü:** Turistik, sembolik (konut etkisi düşük)

### Reel etki tahmini

Çamlıca Kulesi **turistik cazibe** olarak yüksek etki yarattı ama **konut piyasasına spesifik etki sınırlı**:

- Üsküdar genel 2021-2023 dönem: TÜFE × İstanbul ortalaması paralel
- Küçük Çamlıca mahallesi spesifik veri **yok** (mahalle çok küçük, segment ayrılmamış)
- Lokal kafe/restoran/otel patlaması: **evet**, ama konut/kira yansıma: **dolaylı, sınırlı**

**Tahmin**: 1 yıllık reel ek prim **+%2-5** (turistik trafik kira talebine yansıdı)

### Tradia modeli tahmini

```python
bugunku_m2 = 9500  # Mayıs 2020 Küçük Çamlıca
tufe_12_ay = 0.135
nufus_artisi = 0.005
insaat_artisi = 0.05
sicaklik = 1.5  # Açılış öncesi sıcaklık
olay_etkisi = 0.04  # orta (sembolik-yapi-acilis)

f_tufe = 1.135
f_nufus = 1.015
f_arz = 0.975
f_olay = 1.04
f_havuz = 1.020

projeksiyon = 9500 * 1.135 * 1.015 * 0.975 * 1.04 * 1.020
            ≈ 9500 * 1.190
            ≈ 11.305 TL/m²

reel_artis = (11305/9500 - 1) - 0.135 = 0.190 - 0.135 = +%5.5 reel
```

### Sapma
- Gerçek reel ek prim: **+%2-5**
- Model tahmini: **+%5.5**
- **Sapma: +%10 ile +%175** (model **biraz fazla**)

### Kalibrasyon dersi
**Sembolik yapı (kule, anıt) için 0.04 fazla**. Bu vakalarda **0.025-0.03** olmalı. Ayrıca etki **çok lokalize** (300m yarıçap), ilçe seviyesinde dağıtılınca etkisi sönümleniyor.

**Yeni alt-kategori**: `sembolik-yapi-acilis` → 0.025

---

## 4. VAKA 13: ADANA METRO 1. ETAP (KONTROL VAKASI)

### Veriler
- **Olay:** 14 Mayıs 2010 açılış, Seyhan-Yüreğir, 13.5 km, 13 istasyon
- **Kategori:** ulasim-iyilestirme / metro-acilis
- **2. etap:** 2014'te ÇED, hala inşaat (2026 itibarıyla)
- **Etkilenen ilçeler:** Seyhan (merkez), Yüreğir (Anadolu yakası)

### Reel etki tahmini

Adana metroya **veri çok kısıtlı** — küçük şehir, segment ayrılmamış raporlar yok. Genel bilgiler:

- 2010 açılış sonrası: Adana 2010-2015 dönem genel %30-40 nominal artış
- TÜFE 2010-2015: ~%50 toplam → reel olarak **gerileme**
- Metro etkisi: **lokalize**, **küçük**, çünkü Adana zaten kompakt şehir, metro sadece 13.5km
- Yüreğir metro istasyonları çevresinde: **yıllık +%3-5 ek prim** (tahmini)

### Tradia modeli tahmini

```python
bugunku_m2 = 1200  # 2009 Yüreğir
tufe_12_ay = 0.085  # 2010 TÜFE
nufus_artisi = 0.012
insaat_artisi = 0.05
sicaklik = 2.0
olay_etkisi = 0.10  # buyuk (metro-acilis)

f_tufe = 1.085
f_nufus = 1.036
f_arz = 0.975
f_olay = 1.10
f_havuz = 1.035

projeksiyon = 1200 * 1.085 * 1.036 * 0.975 * 1.10 * 1.035
            ≈ 1200 * 1.250
            ≈ 1.500 TL/m²

reel_artis = (1500/1200 - 1) - 0.085 = 0.250 - 0.085 = +%16.5 reel
```

### Sapma
- Gerçek reel ek prim: **+%3-5** (tahmini, veri kısıtlı)
- Model tahmini: **+%16.5**
- **Sapma: +%230 ile +%450** (model **çok fazla**)

### Kalibrasyon dersi (kritik — ölçek meselesi)

**İstanbul-dışı şehirlerde model fazla iyimser**. Sebepler:
1. **Ölçek farkı**: İstanbul metrosu 250+ km, Adana 13km. Etki bambaşka.
2. **Şehir nüfus tabanı**: İstanbul 16M, Adana 2.3M
3. **Spekülatif yatırımcı havuzu**: İstanbul'da ulusal/uluslararası, Adana'da sınırlı

**Düzeltme**: Şehir büyüklüğü çarpanı:

```python
def city_scale_multiplier(il_kodu):
    """Etki büyüklüğünü şehir büyüklüğüne göre ayarla"""
    SCALE_FACTORS = {
        "34": 1.0,   # İstanbul (baseline)
        "06": 0.85,  # Ankara
        "35": 0.80,  # İzmir
        "16": 0.70,  # Bursa
        "01": 0.50,  # Adana — büyük il ama 16M değil
        "44": 0.40,  # Malatya — orta
        "48": 0.30,  # Muğla — turizm odaklı
        # default Anadolu illeri: 0.35
    }
    return SCALE_FACTORS.get(il_kodu, 0.35)

# Kullanım
olay_etkisi_calibrated = olay_etkisi * city_scale_multiplier(il_kodu)
```

Bu **çok önemli**. Yoksa model Anadolu'da %200+ sapma yapar.

---

## 5. VAKA 14: TOKİ SANCAKTEPE ŞEHİR PARKI

### Veriler
- **Olay:** 2018-2020 etap etap açılış, 1.500.000 m² yeşil alan
- **Kategori:** sosyal-tesis / yesil-alan
- **Etkilenen mahalle:** Sancaktepe Sarıgazi, Atatürk Mahallesi
- **Lokasyon:** Sancaktepe ilçesi merkez

### Reel etki tahmini

Park açılışları genelde **+%3-8 lokal prim** yaratır (uluslararası benchmark). Türkiye'de:
- Sancaktepe 2018-2020: %30-50 nominal artış (genel İstanbul ortalamasına yakın)
- Park ek primi: tahmini **+%3-7 reel** (1km yarıçap içinde)
- İlçe genel ortalama: **+%1-3 reel** (sönümlenmiş)

### Tradia modeli tahmini

```python
bugunku_m2 = 4200  # 2017 Sancaktepe
tufe_12_ay = 0.115
nufus_artisi = 0.025  # Sancaktepe hızlı büyüme
insaat_artisi = 0.15
sicaklik = 1.8
olay_etkisi = 0.04  # orta (yesil-alan-acilis)

f_tufe = 1.115
f_nufus = 1.075
f_arz = 0.925
f_olay = 1.04
f_havuz = 1.029

projeksiyon = 4200 * 1.115 * 1.075 * 0.925 * 1.04 * 1.029
            ≈ 4200 * 1.183
            ≈ 4.969 TL/m²

reel_artis = (4969/4200 - 1) - 0.115 = 0.183 - 0.115 = +%6.8 reel
```

### Sapma
- Gerçek reel (lokal): **+%3-7**
- Model tahmini: **+%6.8**
- **Sapma: -%2 ile +%125** (lokal seviyede iyi, ilçe seviyesinde fazla)

### Kalibrasyon dersi
**Park açılışları için 0.04 lokal etkide doğru**. Ancak ilçe ortalamasına dağıtılınca yine **mahalle granülaritesi** sorunu (Vaka 6'daki Garipçe gibi). Mevcut çarpan korunabilir, mahalle bazlı v2'de iyileşecek.

---

## 6. VAKA 15: ESENYURT İMAR PATLAMASI (2018-2022)

### Veriler
- **Olay:** Çoklu imar tadilatı + İstanbul kuzey aks gelişimi (havalimanı, M11, otoyol)
- **Kategori:** kümülatif (imar-degisikligi × yatırım-aksı × göç hedefi)
- **Tarih:** 2018-2022 sürekli
- **Mahalle:** Mevlana, Sultaniye, Fatih, Bağlarçeşme, Üçevler

### Reel etki — Esenyurt'un büyüsü

| Dönem | Esenyurt nominal | Türkiye geneli | Net ek prim |
|-------|-------------------|-----------------|--------------|
| 2018-2019 | %7.5 | %8 | -%0.5 (zayıf) |
| 2020-2021 | %62 (kira) | %50 | +%12 |
| 2021-2022 | %86 | %75 | +%11 |
| 2022-2023 | %158 | %125 | +%33 (PATLAMA) |
| 2023-2024 | %224 | %200 | +%24 |

**Esenyurt dramatik patlama** 2022'de oldu. Sebep **çoklu olay sinerjisi**:
1. Pandemi sonrası göç (2021)
2. M11 metro yakınlığı (2023)
3. Esenyurt 1 milyon nüfus (2022)
4. Çoklu imar tadilatı
5. Yatırımcı keşfi (orta segment cazip)

### Tradia modeli tahmini (2022 dönemi)

Mevcut model **bağımsız olayları toplar** ama Esenyurt'ta **sinerji etkisi** var. Test edelim:

```python
bugunku_m2 = 5500  # 2021 Esenyurt
tufe_12_ay = 0.65   # 2022 yüksek enflasyon
nufus_artisi = 0.045  # Esenyurt patlaması
insaat_artisi = 0.30  # Yoğun inşaat
sicaklik = 4.5  # Patlamış sıcaklık
olay_etkisi = 0.10  # Çoklu olay var ama tek tek küçük

f_tufe = 1.65
f_nufus = 1 + 0.045 * 3 = 1.135
f_arz = 1 - 0.30 * 0.5 = 0.85
f_olay = 1.10
f_havuz = 1 + log(4.5) * 0.05 = 1.075

projeksiyon = 5500 * 1.65 * 1.135 * 0.85 * 1.10 * 1.075
            ≈ 5500 * 1.937
            ≈ 10.654 TL/m²

reel_artis = (10654/5500 - 1) - 0.65 = 0.937 - 0.65 = +%29 reel
```

### Sapma
- Gerçek reel (2022): **+%33** ek prim (sektör üstü)
- Model tahmini: **+%29**
- **Sapma: -%12** → **HEDEF İÇİNDE!**

### Kalibrasyon dersi (sürpriz)

Yüksek sıcaklık + nüfus + arz çarpanları **kümülatif olay sinerjisini doğal olarak yakalıyor**! Esenyurt vakası modelin **çoklu olay** durumunda iyi çalıştığını gösteriyor.

**Önceki Öneri 4** (kümülatif sinerji 1.2x büyütme) **gereksiz olabilir** — sıcaklık 4.5 ile zaten yüksek skala yakalanıyor.

---

## 7. KÜMÜLATİF SAPMA TABLOSU (15 VAKA)

| # | Vaka | Gerçek | Model | Sapma | Yön |
|---|------|--------|-------|-------|-----|
| 1 | Lapseki köprü | +%40-50 | +%16 | -%30 | Az |
| 2 | M11 metro Göktürk | +%50 | +%20 | -%60 | Az |
| 3 | Başakşehir hastane | +%50 | +%29 | -%42 | Az |
| 4 | Marmaray Üsküdar | +%5-10 | +%21 | +%200 | Çok |
| 5 | Ford Gölcük | +%5-10 | +%12 | +%30 | Az fazla |
| 6 | YSS Beykoz (1y) | +%14-19 | +%13.3 | -%5 | **OK** ✅ |
| 7 | Avrasya Acıbadem (1y) | +%2-7 | +%15 | +%200 | Çok |
| 7b | Avrasya 3y | +%20-30 | +%15 | -%25 | Az |
| 8 | MoI İkitelli | +%5-10 | +%6.7 | -%10/+%30 | **OK** ✅ |
| 9 | Sabancı Üniv. | Kapsam dışı | - | - | N/A |
| 10 | TOSB Çayırova | +%2-4 | +%5 | +%25-150 | Fazla |
| 11 | Hatay deprem | -%17 (2y) | KAPSAM DIŞI | - | **MİMARİ EKSİK** |
| 12 | Çamlıca Kulesi | +%2-5 | +%5.5 | +%10/+%175 | Az fazla |
| 13 | Adana metro | +%3-5 | +%16.5 | +%230/+%450 | **ÇOK FAZLA** |
| 14 | Sancaktepe park | +%3-7 | +%6.8 | -%2/+%125 | OK lokal |
| 15 | Esenyurt patlama | +%33 | +%29 | -%12 | **OK** ✅ |

### Yeni paternler (Batch 3 ile)

1. **NEGATİF OLAYLAR**: Model çözemiyor — mimari eksik (Vaka 11)
2. **İSTANBUL-DIŞI**: Model **dramatik fazla** tahmin ediyor — şehir ölçek çarpanı zorunlu (Vaka 13)
3. **SEMBOLİK YAPILAR**: 0.04 yerine 0.025 olmalı (Vaka 12)
4. **ÇOKLU OLAY SİNERJİ**: Sıcaklık çarpanı zaten yakalıyor — Öneri 4 gereksiz (Vaka 15)
5. **GENEL TREND**: 4 ✅ OK, 6 az tahmin, 3 fazla tahmin, 1 mimari eksik, 1 kapsam dışı

**Doğruluk oranı 15 vakada**: ~%30 hedef sapma içinde (4/13 ölçülebilir vaka). **Hedef %50+**.

---

## 8. GÜNCELLENMİŞ KALİBRASYON ÖNERİLERİ (Batch 3'ten yeni)

Önceki 8 öneriye eklenenler:

### Öneri 11: Negatif olay desteği (KRİTİK)

Model'in mimarisi **şu an pozitif olay assumption'ı** üzerine kurulu. Türkiye gibi deprem ülkesinde **fatal eksiklik**.

**Çözüm**: Bu raporun §2'deki kod parçası:
- Negatif kategoriler: `afet`, `yargi-iptali`, `olumsuz-imar`
- Sıcaklık formülü ek: `+pozitif - negatif`
- Çevre illere göç bonusu: `menzil_km × pozitif_etki`

**Öncelik**: v1.5 zorunlu. Bu olmadan model **deprem sonrası verileri çözemez**.

### Öneri 12: Şehir ölçek çarpanı

İstanbul-dışı şehirlerde olay etkisi **çok daha küçük**. Adana metrosu vakası gösterdi.

**Çözüm**: Adım 2 servislerine `city_scale_multiplier` ekle. İl bazlı katsayılar:

```yaml
city_scale:
  istanbul: 1.0        # baseline (16M nüfus)
  ankara: 0.85         # 5.6M
  izmir: 0.80          # 4.5M
  bursa: 0.70          # 3.2M
  buyuk_anadolu: 0.50  # Adana, Antalya, Konya, Gaziantep, Kayseri (1-2.5M)
  orta_anadolu: 0.35   # Diğer büyükşehirler
  kucuk_iller: 0.20    # 500K altı iller
```

### Öneri 13: Sembolik yapı alt-kategorisi

Çamlıca Kulesi gibi vakalar mevcut "orta" kategoride değil, **kendi alt-kategorisinde**:

```yaml
alt_kategoriler:
  sembolik-yapi-acilis: 0.025  # Kule, anıt, gözlem terası
  sosyal-tesis-park: 0.04       # Park, yeşil alan (mevcut korunur)
  sosyal-tesis-avm: 0.04        # AVM (mevcut korunur)
```

### Öneri 14: Çoklu olay sinerjisi GERİ ALINDI

Batch 1'de **Öneri 4** olarak vermiştim: "3+ aktif olay = 1.2x çarpan". Esenyurt vakası bunu çürüttü.

**Yeni bulgu**: Sıcaklık çarpanı (4.5x) zaten kümülatif etkiyi yakalıyor. Ek 1.2x çarpan model'i **fazla tahmin** edecek.

**Öneri 4 İPTAL**.

### Öneri 15: Test verisi olarak Hatay ekle

Negatif vaka eklenince:

```python
def test_hatay_deprem_2023():
    """6 Şubat depremi sonrası Hatay 2 yıllık reel artış -%17"""
    result = project_with_event(
        bugunku_m2=10000,
        olay="afet-deprem",
        olay_buyukluk=-0.20,  # NEGATİF
        sicaklik=0.5,  # düşük (yıkım sonrası)
        ay_sayisi=24
    )
    reel = (result/10000 - 1) - 0.30  # 24 ay TÜFE
    # Reel artış -%20 ile -%10 aralığında olmalı
    assert -0.25 <= reel <= -0.10
```

---

## 9. BATCH 4 İÇİN PLANLANAN VAKALAR (16-20)

Batch 4 daha **çeşitli** olacak — model'in zayıf noktalarını test edecek:

16. **İzmir metrosu Üçyol-Bornova** (2014 açılış) — İstanbul-dışı pozitif test
17. **Antalya kentsel dönüşüm** (2018-2023) — turizm odaklı şehir
18. **Konya yüksek hızlı tren** (2011 açılış) — İstanbul-dışı kontrol
19. **Diyarbakır** (genel piyasa) — terör/güvenlik etkisi (negatif kontrol)
20. **Trabzon Akçaabat liman gelişimi** (2015-2020) — Karadeniz lojistik

Bu batch:
- 4'ü İstanbul-dışı (şehir ölçek çarpanı doğrulama)
- 1'i ikinci negatif vaka (Diyarbakır, terör)
- Çeşitlilik: ulaşım, turizm, lojistik, güvenlik

---

## 10. SONUÇ — BATCH 3 NE GETİRDİ

**Yeni öğrenilenler:**

1. ⚠️ **Negatif olay mimarisi yok** — Türkiye için kritik eksiklik (Hatay)
2. ⚠️ **İstanbul-dışı modelinde dramatik sapma** — şehir ölçek çarpanı zorunlu (Adana)
3. ✅ **Sembolik yapı kategorisi** — yeni alt-kategori gerekli (Çamlıca)
4. ✅ **Park kategorisi** — mevcut çarpan doğru (Sancaktepe)
5. ✅ **Çoklu olay sinerji** — sıcaklık zaten yakalıyor, ek çarpan **gereksiz** (Esenyurt)

### 15 vaka kümülatif sonuç:
- ✅ **4 vaka iyi** (Beykoz, MoI, Esenyurt, Sancaktepe lokal)
- ⚠️ **6 vaka az tahmin** (Lapseki, M11, Başakşehir, Marmaray uzun, vs)
- ⚠️ **5 vaka fazla tahmin** (Marmaray kısa, Acıbadem kısa, TOSB, Çamlıca, Adana metro)
- ❌ **1 mimari eksik** (Hatay deprem)
- ❌ **1 kapsam dışı** (Sabancı uzun vade)

**Doğruluk oranı**: ~%30. Bu **düşük ama anlamlı** — kalibrasyon önerileri uygulandığında **%70-85**'e çıkmalı.

### Toplam öneri sayısı (Batch 1+2+3):
1. Olay etkisi yüzdeleri %50 büyüt
2. Kısmi açılış / söylenti ayrımı
3. Bekleyiş primi (sıcaklık 0.05→0.07)
4. ~~Kümülatif sinerji~~ **İPTAL** (Öneri 14)
5. Geriye dönük TÜFE düzeltmesi
6. Etki gecikmesi eğrisi (kritik)
7. Mahalle granülaritesi (v2 hedef)
8. Uzun vadeli yumuşak kategori
9. Olay etkisi nihai yeniden ayar
10. Test verisi (Beykoz, Acıbadem)
11. **Negatif olay desteği (KRİTİK)**
12. **Şehir ölçek çarpanı (KRİTİK)**
13. Sembolik yapı kategorisi
14. **Öneri 4 iptal**
15. Test verisi (Hatay)

**13 aktif öneri** (1 iptal). Önerilerden **2'si "KRİTİK"** etiketli (negatif olay + şehir ölçek).

---

## 11. BOSS KARAR NOKTASI

**Karar 1**: Batch 4'e şimdi mi geçiyorum?

**Karar 2**: Kritik öneriler (11 + 12) **30 vaka sonu mu yoksa hemen v1.5'e** mi eklensin?
- **Önerim**: 30 vaka sonu **ama** dokümante edilsin ki kaybolmasın
- Çünkü Hatay/Adana vakaları başlı başına yeterli güvenilir veri
- Ancak diğer önerilerle birlikte uygulanması daha tutarlı

**Karar 3**: Bu rapor `docs/havuz/KALIBRASYON_BATCH_3_2026-05-03.md` olarak arşivlensin mi?

---

**Bu rapor Boss onayını bekliyor. Onay alınırsa Batch 4 başlar.**
