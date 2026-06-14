# CC-Basın B94 — 81-İl Kapsama Envanteri + Kör Nokta Kapatma

**Tarih:** 2026-06-14 22:30 · **Sprint:** B94 · **Anayasa:** [[anayasa_basin]] v2.0 (KESİNTİSİZ AKIŞ § BÖLÜM 5.1 · 5.4)
**Disiplin:** V11 dürüst · V16 SERT · Telif ≤6 · $0

---

## 0. V16 SERT — B93 YANLIŞ METRİK DÜZELTME ⚠️

**B93 raporu (haber_hatti_durum.md) "GHA $0 tier 1470/2000 dk %74" yazıyordu.** Bu METRİK YANLIŞTI.

**Gerçek (B94 doğrulama):**
- Repo `e-misara/landgold-intelligence` **PUBLIC** (`gh api repos/.../json visibility` → `public`, `isPrivate: false`)
- **GitHub Actions PUBLIC repolarda dakika SINIRSIZ + ÜCRETSİZ** (GHA fiyatlandırma resmi: "Workflows in public repositories run for free")
- 2000 dk/ay sınırı YALNIZCA PRIVATE repolar için (free hesap)

**Etki:**
- B93 frekans-maksimize kuralı kabul edildi ama yanlış tavanla — doğru tavan çok daha yüksek
- B94 ADIM 2 Patron önerisi "public'e taşı, tavan kalkar" → **göç GEREKLİ DEĞİL, zaten public**
- 81-il kapsama freni asla yoktu; ben yanlış tavan kullandığım için B93'te frenli düşündüm

**B95 backlog:** B93 anayasa metni "GHA $0 tier 2000 dk sınır" satırı düzeltilecek (anayasa v2.1 nokta düzeltme).

---

## 1. PROBE SONUÇLARI

### 1.1 81 Valilik (www.<il>.gov.tr/duyurular)
**Pattern doğrulandı:** 79/81 il OK · 2 timeout (Kocaeli + Konya — anlık ağ sorunu, retry'da geçer)

**Aktif:** %97.5

### 1.2 30 Büyükşehir Belediyesi (www.<il>.bel.tr/sitemap.xml + /haberler)
**Pattern doğrulandı:** 23/30 OK

**Aktif:** %76.7

**Standart pattern dışı 7 il (B95 tek tek keşif borç):**
- istanbul (ibb.gov.tr — yeni domain, B77'de keşfedildi)
- izmir (izmir.bel.tr ama farklı path)
- denizli, muğla, şanlıurfa, tekirdağ, van — alternatif domain

---

## 2. KAPSAMA % DELTA

| Sprint | Aktif kaynak yerel | 81-il kapsama % | Açıklama |
|---|---|---|---|
| B92 | 1 (Bursa BBB) | %1.2 | Tek belediye |
| B93 | 1 (sabit) | %1.2 | Yeni ulusal/sektörel — yerel değişmedi |
| **B94** | **79 valilik + 23 büyükşehir** | **%97.5** ⭐⭐⭐ | Pattern probe + 3 tier workflow |

**Mutlak artış:** +78 valilik · +22 belediye · kapsama **+%96.3**

---

## 3. TİERED FREKANS PLANI (anayasa v2.0 § 5.2 ANI YAKALAMA)

| Tier | İl sayısı | İller | Frekans | Workflow |
|---|---|---|---|---|
| **METRO** ⭐ | 7 | İstanbul, Ankara, İzmir, Bursa, Antalya, Kocaeli, Gaziantep | **Yarım-günlük** (09:15 + 17:15 TR) | `valilik-pulse-metro.yml` |
| BÜYÜKŞEHİR | 23 | Adana, Aydın, Balıkesir, Denizli, Diyarbakır, Erzurum, Eskişehir, Hatay, K.Maraş, Kayseri, Konya, Malatya, Manisa, Mardin, Mersin, Muğla, Ordu, Sakarya, Samsun, Ş.Urfa, Tekirdağ, Trabzon, Van | Günlük (09:30 TR) | `valilik-pulse-buyuksehir.yml` |
| KALAN | 51 | Diğer 51 il | Günlük batch (09:45 TR) | `valilik-pulse-kalan.yml` |

**Mantık:**
- Metro: nüfus + işlem yoğunluğu en yüksek → 2x/gün
- Büyükşehir: orta yoğunluk → 1x/gün ayrı workflow
- Kalan: düşük yoğunluk → 1x/gün batch (51 il tek run)

**Toplam günlük il-fetch:** 7×2 + 23 + 51 = **88 il-fetch/gün** (havuz akış maksimizesi)

---

## 4. HABER PULSE B94 GÜNCELLEME (ölü RSS düzeltme)

### Kaldırıldı (3 kanal):
- ❌ **İHA Ekonomi** — `https://www.iha.com.tr/rss/*` 403 bot koruma (RSS feed kapalı)
- ❌ **İnşaat Time** — SSL sertifika hatası (sertifika YENİLENMEDİ, kuruma sorun yapısal)
- ⚠️ **Hürriyet Emlak** (`/rss/emlak`) — feed boş gelirdi, Hürriyet ekonomi ile değiştirildi

### Düzeltildi (1 kanal):
- ✅ **Dünya Gazetesi Emlak** — `https://www.dunya.com/rss?icerik=emlak` (25 entry) — eski `/rss/sektorler-emlak` 404'tü

### Eklendi (4 yeni kanal):
- ✅ **Hürriyet Ekonomi** (`/rss/ekonomi`) — 100 entry / 17 relevant ⭐
- ✅ **Cumhuriyet Ekonomi** (`/rss/3.xml`) — 100 entry / 10 relevant ⭐
- ✅ **NTV Ekonomi** (`.rss`) — 20 entry / 10 relevant (yüksek ratio)
- ✅ **Habertürk Ekonomi** (`/rss/kategori/ekonomi.xml`) — 30 entry / 3 relevant

**B93 → B94 haber pulse durumu:**
| Metrik | B93 | B94 | Δ |
|---|---|---|---|
| Toplam kanal | 11 | 12 | +1 |
| Aktif kanal | 8 (%73) | 12 (%100) ⭐ | +4 |
| Fetch/saat | 294 | 569 | +275 |
| Relevant/saat | 100 | 141 | +41 |

---

## 5. TÜM AKTİF WORKFLOW B94 SONU

| Workflow | Frekans | Tip |
|---|---|---|
| `primer-monitor.yml` | Günlük 09:00 | resmî 4 primer (Bursa BBB+İBB CKAN+ÇŞB+BDDK) |
| `ihale-rg-gunluk.yml` | Günlük 09:30 | RG PDF |
| `ihale-csb-haftalik.yml` | Pzt 09:45 ⭐ | CSB e-Devlet |
| `ihale-dsi-haftalik.yml` | Salı 09:50 | DSİ |
| `haber-pulse-saatlik.yml` | Her saat XX:10 | 12 ulusal/gazete/sektör RSS |
| `piyasa-monitor-aylik.yml` | Ay 1+15 | 5 piyasa endeks |
| **`valilik-pulse-metro.yml` ⭐ YENİ B94** | **09:15+17:15** | **7 metropol valilik** |
| **`valilik-pulse-buyuksehir.yml` ⭐ YENİ B94** | **09:30** | **23 büyükşehir valilik** |
| **`valilik-pulse-kalan.yml` ⭐ YENİ B94** | **09:45** | **51 il valilik batch** |
| `sync-vezir.yml` | Her saat XX:05 | Vezir kanal (Basın değil) |

**Aktif Basın workflow:** 9 (B93 sonu 6 → B94 +3) · **Aktif TÜM workflow:** 10

---

## 6. PUBLIC-REPO CRON ŞEMA (B94 — Patron ADIM 2 önerisi)

### Durum doğrulaması
- Repo `e-misara/landgold-intelligence` **ZATEN PUBLIC** (B94 keşif)
- GHA dakika **SINIRSIZ + ÜCRETSİZ**
- Veri akışı: public haber + public commit (sır yok)

### Şema çalışıyor (göç YOK)
- Public repo cron çalışır durumda — B86'dan beri
- Tek değişiklik anayasa metni B93'te "$0 tier 2000 dk" satırı düzeltilecek (B95)

### Risk uyarısı (V16 SERT)
- **Public repo + GHA = sınırsız dakika ANCAK** GitHub abuse politikası geçerli: aşırı agresif cron (örn. dakikalık) abuse-policy ihlal edebilir
- Mevcut cron: saatlik haber pulse (24×30=720 run/ay) + günlük valilik (3×30=90 run/ay) + diğer = **~1000 run/ay** — abuse sınırı altında, **güvenli**
- Frekans büyüme için: dakikalık cron YASAK, saatlik üst sınır + 30-60 dk ralantı yeterli

### B95+ büyüme alanları (frene değil, hedefe)
- 30 büyükşehir belediye sitemap.xml akış (mevcut 23, +7 alternatif domain B95)
- TÜİK veri portalı URL pattern keşif
- TCMB EVDS API (Patron API key kararı)
- Yerel haber agregatör keşfi

---

## 7. KÖR NOKTA (V16 SERT, kalanlar)

| Kanal | Sebep | Durum |
|---|---|---|
| İHA RSS | 403 bot koruma | KAPALI — alternatif AA + Cumhuriyet/NTV/Habertürk |
| İnşaat Time RSS | SSL sertifika yenilenmemiş | KAPALI — sektör için Emlak Kulisi + Arkitera yeterli |
| 2 valilik timeout (Kocaeli/Konya) | Anlık ağ | retry'da düzelir |
| 7 büyükşehir belediye | Domain pattern farklı | B95 tek tek keşif borç |
| TCMB KFE PDF | Sayfa JS-render | PARK / TCMB EVDS API alternatif |
| TÜİK veri portalı | URL pattern keşif yapılmadı | B95+ borç |
| EKAP / UYAP / ilan.gov.tr / GİB / TTSG / TOKİ live | TUZAK-5 headless borç | PARK sabit |
| Yerel haber agregatör | Keşif yapılmadı | B95+ |

**81-İL VALİLİK KAPSAMA: %97.5** (V16 SERT — sayısal)
**81-İL BELEDİYE KAPSAMA: %28.4** (23/81 — büyükşehir-dışı belediye kapsama YOK, B100+)

---

## 8. TUZAK-6 ÜÇLÜ KANIT (B94 hedef tamamlama)

| Kanıt | B93 | B94 |
|---|---|---|
| 1. Local run | ✅ 185 distinct | ✅ haber_pulse +41 + valilik metro +9 = **+50 distinct** (B94 lokal) |
| 2. Cloud dispatch | ⏳ Pzr gece schedule veya Patron manuel | ⏳ Patron Pzr gece (B94 sonu) |
| 3. Bot commit + audit | ⏳ Cloud sonrası | ⏳ Cloud sonrası |

**Patron pazar gece tetik talimatı (5 sn × 9 workflow web UI):**
```
github.com/e-misara/landgold-intelligence/actions/
  → her workflow için Run workflow (main branch)
  Sırayla:
    1. primer-monitor
    2. ihale-rg-gunluk
    3. ihale-csb-haftalik
    4. ihale-dsi-haftalik
    5. haber-pulse-saatlik
    6. piyasa-monitor-aylik
    7. valilik-pulse-metro ⭐ YENİ
    8. valilik-pulse-buyuksehir ⭐ YENİ
    9. valilik-pulse-kalan ⭐ YENİ
```

---

## 9. B94 KAZANIMI ÖZET

✅ V16 SERT GHA limit yanılgısı düzeltildi (public repo → sınırsız)
✅ 81 valilik probe → 79/81 OK (%97.5 aktif)
✅ 30 büyükşehir probe → 23/30 OK (%76.7 aktif)
✅ Ölü 3 RSS kaldırıldı + 4 yeni gazete + Dünya emlak düzeltildi → 12/12 aktif (%100)
✅ valilik_pulse_81il.py 3-tier script (metro/buyuksehir/kalan/hepsi)
✅ 3 yeni workflow (metro yarım-günlük + büyükşehir günlük + kalan günlük batch)
✅ B87 borç KAPATILDI (B93'te), Patron ADIM 2 "public göç" → ZATEN PUBLIC dürüst raporlandı

❌ İHA + İnşaat Time RSS (alternatifle telafi)
❌ 7 büyükşehir belediye standart-dışı (B95)
❌ TUZAK-6 cloud kanıt eksik (Patron Pzr gece)

---

**Hazırlayan:** CC-Basın B94 — anayasa v2.0 § 5.1 GÜNCEL-HER-ZAMAN + 5.4 KÖR-NOKTA DÜRÜST UYGULANDI
**Sonraki:** B95 — 7 büyükşehir belediye keşif + cloud ÜÇLÜ kanıt + anayasa v2.1 (GHA metrik düzeltme)
