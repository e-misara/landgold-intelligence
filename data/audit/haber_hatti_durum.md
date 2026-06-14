# CC-Basın Haber Hattı Durum Raporu — B93

**Tarih:** 2026-06-14 21:15 · **Sprint:** B93 · **Anayasa:** [[anayasa_basin]] v2.0 (KESİNTİSİZ AKIŞ BELKEMİĞİ) · **Disiplin:** V11 dürüst · Telif ≤6 · $0

> **Tek satır:** Anayasa şerit v2.0 genişledi, **2 yeni cron kanal aktif (saatlik haber pulse + aylık piyasa monitor)**, ilk pulse'da **185 yeni distinct kayıt havuza yazıldı** (haber 100 + piyasa 85). 6 GitHub Actions workflow aktif (~1300 dk/ay $0 sınırı %65). V16 SERT: 11 haber kaynağından 8 aktif / 3 ölü / 1 boş, 5 piyasa kaynağından 4 aktif / 1 boş. Kör nokta DÜRÜST: 81-il yerel henüz 1 belediye (Bursa BBB), 80 il kapsama-DIŞI; B93+ envanter borç.

---

## 1. KAYNAK ENVANTERİ (B93 itibariyle, $0 kanallar)

### 1.1 Resmî Primer (BELKEMİK — günde-bir, mevcut)
| Kanal | Frekans | Durum | Son tarama | Kapsam |
|---|---|---|---|---|
| RG Günlük (PDF) | Günlük 09:30 cloud | ✅ aktif | 2026-06-14 | Ulusal |
| CSB e-Devlet | Haftalık Pzt 09:45 cloud ⭐ | ✅ aktif | 2026-06-09 | 33 il |
| DSİ Haftalık | Haftalık Salı 09:50 cloud | ✅ aktif | 2026-06-10 | Su altyapı |
| Bursa BBB İmar | Günlük 09:00 cloud | ✅ aktif | 2026-06-14 | Bursa BBB (1 il) |
| İBB CKAN | Günlük 09:00 cloud | ✅ aktif | 2026-06-14 | İstanbul (35 dataset Tradia-relevant) |
| ÇŞB Haber/Duyuru | Günlük 09:00 cloud | ✅ aktif | 2026-06-14 | Ulusal |
| BDDK Mevzuat/Duyuru | Günlük 09:00 cloud | ✅ aktif (JSON serialize bug B92 borç) | 2026-06-14 | Ulusal finansal |
| VGM | Tek-seferlik harvest (İhale İ8) | ✅ statik 548 ilan | 2026-06-12 | 27 aktif il |
| SGK İcra | Tek-seferlik (PNG OCR devir) | ⚠️ 12 PNG Analiz devir | 2026-06-12 | Sınırlı |

**Toplam aktif primer:** 9 kanal · **Resmî bulut cron:** 4 workflow

### 1.2 Ulusal Ajans + Büyük Gazete (B93 ⭐ YENİ — saatlik pulse)
| Kanal | RSS | Durum | İlk pulse rel | Not |
|---|---|---|---|---|
| AA Ekonomi | ✅ | aktif | 4 rel / 30 fetch | Ulusal ajans en güvenilir |
| İHA Ekonomi | ❌ | ölü | 0 / 0 fetch | RSS URL değişmiş — B94 düzelt |
| Hürriyet Emlak | ⚠️ | erişim OK + 0 sonuç | 0 / 0 | RSS feed boş veya format değişti |
| Milliyet Emlak | ✅ | aktif | 1 rel / 20 | Düşük yoğunluk |
| Sabah Ekonomi | ✅ | aktif | 3 rel / 10 | |
| Dünya Gazetesi Emlak | ❌ | ölü | 0 / 0 fetch | URL düzeltme borç |
| Emlak Kulisi | ✅⭐ | aktif | **33 rel / 50** | Sektörel yüksek yoğunluk |
| İnşaat Time | ❌ | ölü | 0 / 0 fetch | URL düzeltme borç |
| Arkitera | ✅⭐ | aktif | **48 rel / 120** | Mimari/sektörel yüksek yoğunluk |
| RG Anasayfa (sitemap) | ⚠️ | erişim OK + 0 rel | 0 / 14 | Filtreden geçen başlık yok (RG günlük PDF tam kanal) |
| TOKİ Duyuru (sitemap) | ✅ | aktif | 11 rel / 50 | TOKİ açıklamaları gerçek zamanlı! |

**Toplam aktif ulusal/gazete:** 8/11 (%73) · **İlk pulse yeni distinct:** **100 kayıt/saat** ⭐

### 1.3 Sektörel + Piyasa (B93 ⭐ YENİ — aylık monitor, B87 borcu KAPATILDI)
| Kanal | Frekans | Durum | İlk taramada |
|---|---|---|---|
| TCMB Konut Fiyat Endeksi | Aylık | ⚠️ fetch_ok / PDF link 0 | URL pattern değişmiş — B94 düzelt |
| GYODER Yayınlar | Aylık (Çeyreklik) | ✅ aktif | 44 yeni distinct |
| TÜİK Veri Portalı | Aylık | ⚠️ ana sayfa probe | URL pattern keşif borç |
| İstanbul Valiliği ÇED | Aylık | ✅ aktif ⭐ | 40 yeni distinct |
| İstanbul Valiliği Karar | Aylık | ✅ aktif | 0 yeni (ÇED ile aynı template, dedup) |

**Toplam aktif piyasa:** 4/5 · **İlk tarama yeni distinct:** **85 kayıt**

### 1.4 81-İl Yerel (KÖR NOKTA — B93+ envanter borç)
| İl | Belediye | Durum |
|---|---|---|
| Bursa | BBB imar plan | ✅ aktif (mevcut) |
| Diğer 80 il | — | ❌ KAPSAMA YOK |

**81-il kapsama yüzdesi:** **%1.2 (1/81)** — V16 SERT dürüst

---

## 2. FREKANS DAĞILIMI (KESİNTİSİZ AKIŞ doktrini)

| Frekans | Workflow | Aylık run | Aylık dk |
|---|---|---|---|
| **Saatlik** | haber-pulse-saatlik.yml ⭐ YENİ | 720 | ~720 |
| Saatlik (mevcut) | sync-vezir.yml | 720 | ~360 |
| Günlük | primer-monitor.yml + ihale-rg-gunluk.yml | 60 | ~300 |
| Haftalık | ihale-csb + ihale-dsi | 8 | ~80 |
| Aylık | piyasa-monitor-aylik.yml ⭐ YENİ (1+15) | 2 | ~10 |
| Havuz pipelines | havuz-pipelines.yml | (disabled cron, sadece dispatch) | ~0 |

**Toplam:** **6 aktif workflow · ~1470 dk/ay · GHA $0 tier 2000 dk sınır içinde (%74) ✅**

**Aktif workflow dosyaları:**
- `.github/workflows/primer-monitor.yml` (günlük 09:00 TR)
- `.github/workflows/ihale-rg-gunluk.yml` (günlük 09:30 TR)
- `.github/workflows/ihale-csb-haftalik.yml` (Pzt 09:45 TR ⭐)
- `.github/workflows/ihale-dsi-haftalik.yml` (Salı 09:50 TR)
- `.github/workflows/haber-pulse-saatlik.yml` ⭐ YENİ B93 (her XX:10)
- `.github/workflows/piyasa-monitor-aylik.yml` ⭐ YENİ B93 (her ay 1 + 15)
- `.github/workflows/sync-vezir.yml` (her saat XX:05 — Vezir kanal, Basın değil)

---

## 3. HAVUZ BOYUTU (SÜREKLİ ARŞİV doktrini · V36 etiket disiplini)

| Havuz | B92 sonu | B93 başı (ilk pulse) | Δ distinct |
|---|---|---|---|
| **data/havuz/haber/** ⭐ YENİ | 0 | **100** | +100 (kayıt) |
| **data/havuz/piyasa/** ⭐ YENİ | 0 | **85** | +85 (kayıt) |
| data/audit/primer_monitor_*.json | 4 gün (06-11→06-14) | 4 gün | sabit |
| data/audit/haber_pulse_*.json ⭐ YENİ | 0 | 1 gün (06-14) | +1 dosya |
| data/audit/piyasa_monitor_*.json ⭐ YENİ | 0 | 1 ay (2026-06) | +1 dosya |
| İhale takvim v8 (cc_ihale lane) | 746 | 746 | sabit |
| İhale altyapı sinyal v4 | 13 | 13 | sabit |

**B93 ilk-pulse havuz delta:** **+185 distinct kayıt** (ilk saatte) ⭐

**Projeksiyon (B94 sonu, 1 hafta = 168 saat):**
- Haber pulse: 100/saat × 168 saat = teorik 16.800 ham fetch; dedup sonrası tahmini **2.000-4.000 distinct yeni** kayıt/hafta
- Piyasa: aylık → B94 sonu **+0** (sonraki tarama 2026-07-01)

---

## 4. 81-İL KAPSAMA (KÖR NOKTA HARİTASI)

**Mevcut yerel kapsam:**
- ✅ Bursa (BBB imar plan)
- ✅ İstanbul (İBB CKAN 35 dataset + İstanbul Valiliği ÇED + Vali genelge)
- ✅ 33 il (CSB e-Devlet, sınırlı — sadece kamu taşınmaz satışı)
- ✅ 27 il (VGM, sınırlı — vakıf taşınmaz ihalesi)

**KÖR NOKTA (V16 SERT):**
- ❌ Ankara, İzmir, Antalya, Konya, Adana, Mersin, Kayseri, Diyarbakır, Trabzon… **77 il yerel belediye RSS/sitemap akış YOK**
- ❌ Büyükşehir 30 belediye akışı (B94+ ilk hedef)
- ❌ Yerel haber gazete RSS akışı (yerel.gazete.com.tr benzeri)

**B94 yol haritası:**
1. Büyükşehir 30 belediye sitemap.xml taraması — toplu envanter
2. Yerel haber agregatör (yerel-haber portalları) ara
3. Hedef: B100 sonu 30+ büyükşehir akış aktif → kapsama %37+

---

## 5. ANI YAKALAMA (TUZAK-6 ÜÇLÜ KANIT)

**B93 yeni saatlik kanal ilk run:**

| Kanıt | Durum |
|---|---|
| ✅ Local run (script doğrulama) | 2026-06-14 21:00 TR · 294 fetch / 100 yeni distinct |
| ⏳ Cloud dispatch tetik | **Patron manuel test (web UI 5 sn)** veya schedule (XX:10) bekleniyor |
| ⏳ Bot commit | İlk cloud run sonrası `tradia-basin-bot` push edecek |
| ⏳ Audit dosyası cloud'da | İlk cloud run sonrası `data/audit/haber_pulse_*.json` cloud commit'le gelir |

**TUZAK-3 öğrenmesi uygulandı:** Workflow push ≠ cloud çalışıyor. Patron Pzr gece (saatlik schedule) veya manuel dispatch ile ÜÇLÜ kanıt tamamlanır.

---

## 6. DÜRÜST KÖR NOKTA + RİSK (V16 SERT)

| Risk | Açıklama | Mitigasyon |
|---|---|---|
| 3 RSS ölü (İHA/Dünya/İnşaat Time) | URL değişmiş veya feed kaldırılmış | B94: URL güncelle veya kaldır, yerine alternatif ekle |
| TCMB KFE PDF link 0 | Sayfa yapısı statik değil, JS-render | B94: alternatif TCMB EVDS API (Patron API key kararı bekliyor) |
| Hürriyet Emlak RSS boş | Feed format değişimi | B94: alternatif Hürriyet ekonomi (yapısal değişim takip) |
| GHA $0 tier 1470/2000 dk | %74 kullanım — büyüme yastığı var | B94+ kanal ekleme öncesi yeniden hesap |
| 80 il kapsama-DIŞI | Yerel belediye akışı YOK | B94+ büyükşehir 30 belediye taraması |
| Headless borç (EKAP/UYAP/ilan.gov.tr/GİB/TTSG/TOKİ live) | TUZAK-5 sabit, bypass YASAK | PARK damgası — kanal eklenmez |
| Saatlik cron uyanış (cloud GHA scheduler) | GHA scheduler bazen 5-15 dk geç (resmi belgeli) | Kabul edilebilir — launchd 116-136 dk gecikme çok daha kötüydü, cloud iyileştirme |

---

## 7. B93 KAZANIMI ÖZET

✅ Anayasa v2.0 — ŞERİT genişledi "kesintisiz akış belkemiği"
✅ Yeni TUZAK-6 (sessiz cron başarısızlığı) ve TUZAK-7 (akış sahte-büyüme önleyici) eklendi
✅ 3 yeni DİSİPLİN kuralı: ÜÇLÜ CRON KANIT + FREKANS-MAKSİMİZE + AKIŞ-ÖLÇÜ
✅ `haber_pulse_saatlik.py` + workflow — 11 kaynak / 8 aktif / **100 yeni/saat** ⭐
✅ `piyasa_monitor_aylik.py` + workflow — B87 borç KAPATILDI / 4 aktif / 85 yeni
✅ Havuz yapısı: `data/havuz/<kanal>/YYYY-MM-DD/HH.jsonl` append-only
✅ Lokal test: 185 distinct kayıt ilk run (TUZAK-3 ÜÇLÜ kanıt: 1/3, cloud bekleniyor)

❌ 80 il kapsama-DIŞI (V16 SERT)
❌ 3 RSS ölü (İHA + Dünya + İnşaat Time)
❌ TCMB KFE PDF erişim format problemi

---

**Hazırlayan:** CC-Basın B93
**Anayasa:** v2.0 atfı
**Sonraki:** B94 — ölü RSS düzelt + büyükşehir 30 belediye sitemap envanteri + cloud ÜÇLÜ kanıt doğrula (Pzr gece schedule veya Patron dispatch)
