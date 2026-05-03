# TRADIA HABER HAVUZU — ADIM 2: ISI PUANI VE FİYAT PROJEKSİYONU

**Versiyon:** 1.0
**Tarih:** 3 Mayıs 2026
**Hedef:** Tradia için ısı puanı + fiyat projeksiyon matematiği
**Bağımlılık:** Adım 1 sınıflandırıcı çıktısı (ilce_haber_havuzu.jsonl)
**Hesaplama:** Saf matematik, API çağrısı yok
**Test:** 5 senaryo, hepsi otomatik ve hızlı

---

## 1. SİSTEM AKIŞI (BÜTÜN RESİM)

```
Adım 1 çıktısı (sınıflandırılmış haberler)
        ↓
ilce_haber_havuzu.jsonl
        ↓
        ├─→ ISI HESAPLAYICI (services/heat_calculator.py)
        │     ├─ Per haber: agirlik × kategori_carpani × kaynak_carpani × tazelik
        │     ├─ İlçe toplam ısı (son 6 ay)
        │     └─ Sıcaklık oranı = mevcut / tarihsel_ortalama
        │
        ├─→ FİYAT PROJEKTÖRÜ (services/price_projector.py)
        │     ├─ Bugünkü m² (kaynak: Endeksa veya tahmin)
        │     ├─ × (1 + TÜFE)
        │     ├─ × (1 + nüfus_artışı × 3)
        │     ├─ × (1 - inşaat_artışı × 0.5)
        │     ├─ × (1 + olay_etkisi)
        │     └─ × (1 + log(sıcaklık_oranı) × 0.05)
        │
        └─→ İlçe profili güncelleme (data/ilce_profil/{kod}.json)
              ├─ ısı_son_6_ay: 87
              ├─ sıcaklık_oranı: 3.5
              ├─ projeksiyon_3_ay: 41.000 TL/m²
              ├─ projeksiyon_12_ay: 51.500 TL/m²
              └─ kaynak_etiketi: "tahmin-v1"
```

---

## 2. ISI PUANI FORMÜLÜ

### 2.1 Tek haber için ısı katkısı

```
haber_isi = agirlik_puani × kategori_carpani × kaynak_carpani × tazelik_carpani
```

Her bileşen ayrı:

#### 2.1.1 Ağırlık puanı
Adım 1 sınıflandırıcısından gelir. 0-10 arası tam sayı.

#### 2.1.2 Kategori çarpanı

Bazı kategoriler diğerlerinden daha fazla fiyat etkisi yapar. Çarpan ile ayarlıyoruz:

```python
KATEGORI_CARPANLARI = {
    "mega-proje": 2.0,          # En güçlü etki
    "ulasim-iyilestirme": 1.8,
    "saglik-tesisi": 1.6,
    "yargi-karari": 1.5,        # Negatif yön de güçlü
    "sanayi-yatirim": 1.5,
    "imar-degisikligi": 1.3,
    "kamulastirma": 1.3,
    "donusum-ilani": 1.4,
    "egitim-tesisi": 1.2,
    "ekonomik-karar": 1.2,      # Genel etki ama ilçe-bazlı küçük
    "yatirim-tesvik": 1.1,
    "ihale-ilani": 1.0,         # Baseline (henüz olmamış proje)
    "yabanci-satis": 1.0,
    "vergi-harc-degisikligi": 1.0,
    "turizm-yatirim": 1.0,
    "dogal-afet": 1.5,          # Akut etki
    "dogal-olay": 0.9,
    "sosyal-tesis": 0.7,
    "demografik-haber": 0.8,
    "guvenlik-suc": 0.8,
    "BELIRSIZ": 0.0,            # Havuza eklenmez zaten
}
```

**Mantık**: Mega proje 2x çarpan çünkü 10 puanlık bir mega proje haberi 5 puanlık imar değişikliğine eşdeğer ısı yapar (5×2 = 10×1).

#### 2.1.3 Kaynak çarpanı

```python
KAYNAK_CARPANLARI = {
    "resmi": 1.0,         # Resmi Gazete, bakanlık, KAP — tam ağırlık
    "yari-resmi": 0.85,   # AA, İHA, büyük gazete — yüksek güven
    "haber": 0.6,         # Yerel/sektör — orta güven
    "soylenti": 0.3,      # Doğrulanmamış — düşük güven
}
```

**Mantık**: Söylentiler havuza giriyor (gelecek sinyali olarak), ama 0.3 çarpan ile etkisi sınırlı. Eğer söylenti **resmi açıklamayla doğrulanırsa** yeni bir haber girer (1.0 çarpan), üst üste birikir.

#### 2.1.4 Tazelik çarpanı (zaman bozulması)

Eski haberler unutulur. Exponential decay kullanıyoruz:

```python
import math

def tazelik_carpani(haber_tarihi, bugun, kategori):
    gun_sayisi = (bugun - haber_tarihi).days
    yarilanma = YARILANMA_OMRU.get(kategori, 60)  # default 60 gün
    return math.exp(-gun_sayisi * math.log(2) / yarilanma)

YARILANMA_OMRU = {  # Gün cinsinden
    "mega-proje": 120,           # 4 ay yarılanır, uzun yaşar
    "ulasim-iyilestirme": 90,
    "saglik-tesisi": 90,
    "egitim-tesisi": 90,
    "donusum-ilani": 75,
    "sanayi-yatirim": 60,
    "imar-degisikligi": 45,
    "yargi-karari": 60,
    "kamulastirma": 45,
    "ihale-ilani": 30,           # 1 ay yarılanır, hızlı eskir
    "ekonomik-karar": 30,
    "yatirim-tesvik": 60,
    "yabanci-satis": 45,
    "vergi-harc-degisikligi": 45,
    "turizm-yatirim": 60,
    "dogal-afet": 90,            # Etki uzun
    "dogal-olay": 45,
    "sosyal-tesis": 30,
    "demografik-haber": 30,
    "guvenlik-suc": 14,          # 2 hafta, hızlı unutulur
}
```

**Örnek**: Mega proje haberi 120 gün yarılanma →
- 0 gün sonra: çarpan 1.0
- 60 gün sonra: çarpan 0.71
- 120 gün sonra: çarpan 0.5
- 240 gün sonra: çarpan 0.25
- 365 gün sonra: çarpan ~0.12

**v1 sınırlaması**: Etki gecikmesini (etki_gecikmesi_ay_min/max) henüz kullanmıyoruz. v2'de eklenecek (örn: hastane temeli atıldı haberi, etki 12 ay sonra zirve yapacak).

### 2.2 İlçe toplam ısı (son N ay)

```python
def ilce_isisi(ilce_kodu, gun_sayisi=180):
    """Bir ilçenin son 6 ay (180 gün) ısı puanı"""
    bugun = datetime.now()
    cutoff = bugun - timedelta(days=gun_sayisi)

    haberler = havuz.filter(
        ilce=ilce_kodu,
        tarih__gte=cutoff,
        kategori__ne="BELIRSIZ"
    )

    toplam_isi = 0
    for h in haberler:
        kategori_c = KATEGORI_CARPANLARI.get(h.kategori, 0)
        kaynak_c = KAYNAK_CARPANLARI.get(h.guvenilirlik, 0.5)
        tazelik = tazelik_carpani(h.tarih, bugun, h.kategori)

        haber_isi = h.agirlik_puani * kategori_c * kaynak_c * tazelik
        toplam_isi += haber_isi

    return round(toplam_isi, 2)
```

### 2.3 Sıcaklık oranı (sıcak/soğuk göstergesi)

```python
def sicaklik_orani(ilce_kodu, mevcut_isi):
    """Bu ilçenin tarihsel ortalama ile karşılaştırması"""
    tarihsel = tarihsel_ortalama_isi(ilce_kodu)

    if tarihsel < 1:  # Çok soğuk ilçe (Bingöl-Genç gibi)
        tarihsel = 1  # Bölme hatası önle

    return round(mevcut_isi / tarihsel, 2)
```

#### Sıcaklık seviyeleri

| Oran | Etiket | Anlam |
|------|--------|-------|
| < 0.5 | "donmus" | Aktivite çok düşük, dikkat gerekmez |
| 0.5 - 0.8 | "soguk" | Normalin altı |
| 0.8 - 1.5 | "normal" | Tipik aktivite |
| 1.5 - 2.5 | "sicak" | Kayda değer aktivite, izle |
| 2.5 - 4.0 | "cok-sicak" | **Bültende vurgula** |
| > 4.0 | "patlamis" | **Acil dikkat, derin analiz** |

### 2.4 Tarihsel ortalama hesaplama

**Sorun**: İlk gün veri yok. Soğuk başlangıç problemi.

**Çözüm: 3 katmanlı strateji**

#### Katman A — Bootstrap (geriye dönük 6 ay)

İlk kurulum: News agent'ı **6 ay geriye** çalıştır, RSS arşivlerinden + Google haber arşivinden 6 aylık haber çek, sınıflandır, havuza ekle.

Tahmini hacim: 6 ay × 200 haber/hafta × ~50 haber/ilçe = ilçe başına ~1.000 haber arşivi
Maliyet: 5.000 haber × $0.003 = ~$15

#### Katman B — Nüfus-bazlı kaba tahmin (fallback)

Bootstrap olmadan da bir başlangıç gerekirse:

```python
def kaba_tarihsel_ortalama(ilce_kodu):
    """Nüfus + büyükşehir durumuna göre tahmin"""
    ilce = il_ilce_db[ilce_kodu]
    nufus = ilce["nufus"]

    if ilce["buyuksehir_merkez"]:
        baseline = nufus / 5000
    elif ilce["il_merkez"]:
        baseline = nufus / 8000
    else:
        baseline = nufus / 12000

    return max(baseline, 0.5)  # Minimum 0.5
```

**Örnekler**:
- Şişli (270K, BB merkez): 270.000/5000 = 54 puan
- Çankaya (910K): 182 puan
- Lapseki (24K, ilçe): 24.000/12000 = 2 puan
- Bingöl-Genç (35K): 35.000/12000 = ~3 puan

#### Katman C — Yuvarlanan ortalama (canlı sistem)

Sistem 6+ ay çalıştıktan sonra gerçek tarihsel ortalama hesaplanır.

---

## 3. FİYAT PROJEKSİYON FORMÜLÜ

### 3.1 Ana formül

```
gelecek_m2(N_ay) = bugunku_m2 ×
                   (1 + TUFE_N_ay) ×
                   (1 + nufus_artisi_yillik × 3 × N_ay/12) ×
                   (1 - insaat_artisi_yillik × 0.5 × N_ay/12) ×
                   (1 + olay_etkisi_aktif) ×
                   (1 + log(max(sicaklik_orani, 1)) × 0.05)
```

### 3.2 Bileşenler

- **TÜFE**: TCMB Beklenti Anketi (manuel config fallback)
- **Nüfus × 3**: %1 nüfus artışı → %3 talep etkisi
- **İnşaat × 0.5**: %10 inşaat artışı → %5 arz baskısı
- **Olay etkisi**: Büyük olaylar (agirlik ≥ 8), ±%30 sınır
- **Havuz ısısı**: log(sicaklik_orani) × 0.05 — logaritmik etki

### 3.3 Güven aralığı

±%20 (Endeksa entegrasyonu öncesi v1 için)

Hedef:
- v1: ±%25 sapma, %75 doğruluk
- Kalibrasyon sonrası: ±%15 sapma, %85 doğruluk
- Endeksa sonrası: ±%10, %90+

---

## 4. LAPSEKI VE ŞİŞLİ REFERANS HESAPLARI

### Lapseki (12 ay)

| Bileşen | Değer | Çarpan |
|---------|-------|--------|
| TÜFE 12 ay | %35 | 1.35 |
| Nüfus artışı %1.8 × 3 | %5.4 | 1.054 |
| İnşaat artışı %12 × 0.5 | -%6 | 0.94 |
| Olay etkisi | %0 | 1.0 |
| Sıcaklık 1.5x | log(1.5)×0.05 = +%2 | 1.02 |

```
Projeksiyon = 40.000 × 1.35 × 1.054 × 0.94 × 1.0 × 1.02 ≈ 54.300 TL/m²
Nominal: %35.7 | Reel: %+0.7
```

### Şişli (12 ay)

```
Projeksiyon = 200.000 × 1.35 × 1.009 × 1.025 × 1.0 × 1.055 ≈ 294.500 TL/m²
Nominal: %47.3 | Reel: %+12.3
```

---

## 5. YENİ DOSYALAR

```
services/
├── heat_calculator.py        ⭐ YENİ
├── price_projector.py        ⭐ YENİ
└── __init__.py

config/
└── macro_assumptions.yaml    ⭐ YENİ

scripts/
└── update_all_heat.py        ⭐ YENİ (günlük cron)

tests/
└── test_heat_calculator.py   ⭐ YENİ (5 test)
```

---

## 6. BİLİNEN SINIRLAR (v1)

1. Çarpanlar henüz kalibre edilmemiş (30 vaka analizi bekleniyor)
2. TÜFE manuel config — TCMB API entegrasyonu yok
3. TÜİK inşaat verisi 3-6 ay gecikmeli
4. Bootstrap haber yok — ilk 3 ay Katman B fallback
5. Endeksa aboneliği olmadan bugünkü m² kaba tahmin

Her projeksiyonda `kaynak: "tahmin-v1"` etiketi zorunlu.

---

**Bu doküman 1.0 son.**
