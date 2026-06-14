# CC-Basın B97 — Akış Doğrulama + Sağlık + TÜİK Raporu

**Tarih:** 2026-06-14 22:55 · **Sprint:** B97 · **Anayasa:** [[anayasa_basin]] v2.2 (ÇİFT-MOD KESİNTİSİZ TARAMA)
**Disiplin:** V11 dürüst · V16 SERT · Telif ≤6 · $0

> **Tek satır:** Lokal motor AKTİF (launchctl PID 9139 exit 0, err log boş) · 3 döngü akış log: **TUZAK-7 sahte-büyüme TEST GEÇTİ** (döngü 1: 183 yeni distinct · döngü 2-3: 0 yeni = dedup doğru engelliyor) · ölü-feed detektör çalıştı (19 feed: 5 sağlıklı, 14 yetersiz-veri, 0 ölü, 0 kuru — V16 SERT 3 döngü az veri itirafı) · TÜİK V16 SERT PARK (data.tuik.gov.tr SPA confirmed, sitemap.xml sadece SPA root URL'leri, www.tuik.gov.tr 195 link ama sadece 1 konut-relevant) · 6 belediye gap (denizli/muğla/ş.urfa/tekirdağ/van/izmir) tüm alternatifler 404/SSL → DÜRÜST PARK + valilik katmanı (B94) yedek mevcut · İBB sitemap.xml lokal motora eklendi (20 feed).

---

## 1. LOKAL MOTOR AKTİVASYON DURUMU ⭐ B97

| Kontrol | Durum |
|---|---|
| Plist yüklü | ✅ `~/Library/LaunchAgents/com.tradia.ccbasin.pulse.plist` |
| launchctl list | ✅ PID 9139 (B97 reload sonrası) · Exit 0 |
| RunAtLoad | ✅ |
| KeepAlive | ✅ |
| ThrottleInterval | ✅ 10 sn (CPU koruma) |
| Nice | ✅ 5 (düşük öncelik) |
| `logs/lokal_motor.out` | ✅ Dolu (döngü satırları) |
| `logs/lokal_motor.err` | ✅ Boş (hata YOK) |
| `_lokal_state.json` | ✅ 19 feed son_fetch + 183 dedup_seen |
| `_akis_log.jsonl` | ✅ 3 satır (kümülatif) |

**B97 değişiklik:** İBB sitemap.xml eklendi (20 feed) · motor reload edildi (PID 7779 → 9139)

---

## 2. AKIŞ LOG ANALİZİ (ADIM 1)

### 2.1 Döngü özeti

| ts | Döngü | İşlenen feed | Yeni distinct |
|---|---|---|---|
| 2026-06-14T22:26:58 | 1 | 19 | **183** ⭐ (cold start) |
| 2026-06-14T22:47:23 | 1 | 10 | 0 (launchd 2. başlangıç) |
| 2026-06-14T22:51:42 | 9 | 5 | 0 |

### 2.2 TUZAK-7 SAHTE-BÜYÜME TEST GEÇTİ ⭐⭐⭐

- **Döngü 1** (cold start, hiç dedup yok): 19 feed × 183 distinct yeni kayıt → GERÇEK büyüme
- **Döngü 2** (launchd restart sonrası, dedup dolu): 10 feed → 0 yeni → DOĞRU davranış
- **Döngü 9** (interval guard'lar etkin): 5 feed (yüksek-aktivite olanlar tetiklendi) → 0 yeni → DOĞRU davranış

**TUZAK-7 KORUNUYOR:** `_lokal_state.json` dedup_seen 183 hash, eski URL'ler ASLA tekrar "yeni" sayılmıyor. Sahte-büyüme imkânsız.

### 2.3 Feed bazlı kümülatif (ilk 3 döngü)

| Feed | Fetch | Relevant | Yeni Distinct |
|---|---|---|---|
| arkitera ⭐⭐⭐ | 360 | 144 | **48** |
| emlakkulisi ⭐⭐ | 150 | 105 | 35 |
| toki_duyuru ⭐ | 50 | 25 | 25 |
| hurriyet_ekonomi | 300 | 57 | 19 |
| ntv_ekonomi | 60 | 39 | 13 |
| cumhuriyet_ekonomi | 300 | 39 | 13 |
| haberturk_ekonomi | 60 | 12 | 6 |
| aa_ekonomi | 60 | 10 | 5 |
| sabah_ekonomi | 20 | 10 | 5 |
| valilik_istanbul ⭐ | 47 | 5 | 5 |
| dunya_emlak | 50 | 6 | 3 |
| milliyet_emlak | 40 | 2 | 1 |
| valilik_ankara | 49 | 1 | 1 |
| valilik_antalya | 55 | 1 | 1 |
| valilik_bursa | 48 | 1 | 1 |
| valilik_gaziantep | 52 | 1 | 1 |
| valilik_izmir | 60 | 1 | 1 |
| valilik_kocaeli | 23 | 0 | 0 |
| rg_anasayfa | 14 | 0 | 0 |

### 2.4 Çift-mod çakışmasız teyit

- Cloud GHA henüz dispatch edilmedi (Patron Pzr gece) — cloud havuza yazım YOK
- Lokal motor cloud'la aynı `data/havuz/haber/<tarih>/<saat>.jsonl` formatında yazıyor
- Aynı md5(url)[:12] dedup anahtarı → cloud aktive olduğunda da çift-yazım YOK
- **Çift-mod testi tam:** Patron Pzr gece sonrası B98 sprint başında 24h kümülatif analiz

---

## 3. ÖLÜ-FEED DETEKTÖR (ADIM 2)

### 3.1 Script + ilk çalıştırma

- Script: `scripts/olu_feed_detektor.py` (script v1.0)
- Çıktı: `data/audit/olu_feed_raporu.json`

### 3.2 Sınıflandırma kuralı

| Damga | Kural | Anlam |
|---|---|---|
| 🔴 ÖLÜ | Son N=10 işlenmenin TAMAMI err | DUR-damga öner |
| 🟡 KURU | Son N=20 işlenmede 0 yeni distinct | Pattern bozulmuş olabilir, kontrol et |
| 🟢 SAĞLIKLI | Yukarıdaki ikisi değil + işlenme ≥3 | Akış normal |
| ⚪ YETERSİZ VERİ | İşlenme <3 | Karar verme, V16 SERT bekle |

### 3.3 B97 başlangıç durumu (3 döngü)

| Damga | Sayı | Açıklama |
|---|---|---|
| 🟢 SAĞLIKLI | 5 | Yüksek-aktivite feed (4 dk interval) çoklu döngü işledi |
| 🟡 KURU | 0 | — |
| 🔴 ÖLÜ | 0 | err YOK |
| ⚪ YETERSİZ VERİ | 14 | Orta+düşük interval feed henüz <3 işlenme |

**V16 SERT itiraf:** 3 döngü ÇOK AZ veri, detektör doğru kararı VERİ-YETERSİZ ile beklemede. B98 sprint başında 100+ döngü ile gerçek sağlık değerlendirilir.

### 3.4 Otomatik koşturma planı (B98)

- Günde 1 kez `python3 scripts/olu_feed_detektor.py` çalıştır
- Raporda 🔴 ÖLÜ varsa: anayasa BÖLÜM 1 YAPMAZ kuralı "Sessiz akış durdurma" → DUR-damga + Patron'a bildirim
- Otomatik silme YOK — Lane HAM, kararı Patron verir

---

## 4. TÜİK URL PATTERN (ADIM 3, B94+B95 borç KAPATILDI)

### 4.1 Probe sonuçları (V16 SERT)

| URL | Durum | Not |
|---|---|---|
| `www.tuik.gov.tr/` ana sayfa | ✅ 200 / 430kb HTML | 195 link · sadece 1 konut-relevant |
| `data.tuik.gov.tr/Bulten` + tüm alt sayfalar | ✅ 200 / **3388b template** | **SPA confirmed** (Vite/React build) |
| `www.tuik.gov.tr/Rss/*` | ❌ 404 | RSS feed YOK |
| `data.tuik.gov.tr/sitemap.xml` | ✅ 200 / 1.3kb | Sadece SPA root URL'leri (statistical-themes, press-releases, contact-us…) — gerçek bülten URL'leri YOK |
| `data.tuik.gov.tr/api/*` | ❌ 404 | Public API endpoint YOK |
| `veriportali.tuik.gov.tr/tr/press-releases` | ✅ 200 / **3388b template** | SPA aynı template, 0 konut-relevant text |

### 4.2 Karar: V16 SERT PARK

- TÜİK Veri Portalı **JS-render Vite SPA** (`/assets/index-CPTcSQmm.js`)
- HTML statik içerik 0 konut/inşaat bültene erişim verir
- Headless browser borç → TUZAK-5 (bypass YASAK, abuse policy)
- **B97'de TÜİK PARK DAMGASI KESİNLEŞTİ** — alternatif yok

### 4.3 Alternatif değerlendirme

- ✅ TÜİK haber bültenleri çoğunlukla **Resmî Gazete'de** veya **basın bültenlerinde** TEKRAR yayınlanıyor
- B97 lokal motor zaten 12 haber RSS + 7 valilik + RG anasayfa + İBB tarıyor
- TÜİK bültenleri ulusal gazete RSS'ler üzerinden DOLAYLI yakalanıyor (Hürriyet/NTV/Habertürk ekonomi)
- **Lane HAM disiplini:** TÜİK SAYISAL VERİSİ Analiz lane (kanonik API ücretli olsa bile Patron kararı)

---

## 5. 6 BELEDİYE GAP DÜRÜST (ADIM 4)

### 5.1 B95-B97 birikmiş probe sonuçları

| İl | Belediye standart `www.<il>.bel.tr/sitemap.xml` | İBB / alternatif | Karar |
|---|---|---|---|
| İstanbul | YOK | ✅ ibb.istanbul/sitemap.xml 29kb | B97 lokal motora eklendi (haber kategorisi) |
| İzmir | SPA template 998b | YOK | **PARK** (valilik yedek) |
| Denizli | 404 | hepsi 404/SSL/302 | **PARK** (valilik yedek) |
| Muğla | 302 redirect | hepsi 302 | **PARK** (valilik yedek) |
| Şanlıurfa | 404 | hepsi 404 | **PARK** (valilik yedek) |
| Tekirdağ | 404 | hepsi 404 | **PARK** (valilik yedek) |
| Van | 403/SSL | hepsi 404/SSL | **PARK** (valilik yedek) |

### 5.2 Yerel haber agregatör denemesi V16 SERT

- `yerelhaber.com` → Errno 61 (DNS/erişim YOK)
- `yerelnethaber.com` → SSL certificate sorunu
- `yerelnet.com` → SSL certificate sorunu
- Sonuç: **3-yönlü agregatör kanalı denedim, hepsi $0'da kapalı**

### 5.3 Dürüst PARK kararı + telafi

**6 belediye için belediye-özel kanal YOK** (V16 SERT).

**Ancak telafi:** B94 valilik katmanı `www.<il>.gov.tr/duyurular` 79/81 OK — 5 il (denizli/muğla/ş.urfa/tekirdağ/van) buradan kapsanıyor. Valilik genelge/duyuru pek çok belediye-tipte içerik de yayınlar (imar plan onayı, ÇED, kentsel dönüşüm). Tam değil ama önemli bir yedek.

**Net kapsama (B97):**
- 81 valilik: %97.5 (79/81 — Kocaeli + Konya timeout)
- 30 büyükşehir belediye sitemap: %76.7 (23/30) + İBB (B97 eklendi) → 24/30 = **%80**
- 6 belediye gap kabul + valilik yedek

---

## 6. ENVANTER B97 DELTA

| Kategori | B96 | B97 | Δ |
|---|---|---|---|
| Anayasa versiyon | v2.2 | v2.2 (değişmedi) | sabit |
| Lokal motor feed | 19 | **20** (+ibb_sitemap) | +1 |
| Akış log satır | 1 | 3 | +2 (cold start 183 + 2 dedup geçen) |
| Dedup hash | 0 | 183 | +183 |
| Yeni distinct kayıt (toplam) | 183 (B96 lokal test) | 183 (cumulative aynı) | sabit (cold start) |
| Ölü-feed detektör script | YOK | **var** ⭐ | +1 |
| Ölü-feed raporu | YOK | **var** (5 sağlıklı, 14 yetersiz veri) | +1 |
| TÜİK kanal | borç | **PARK damga karar** | +1 (dürüst sınır) |
| 6 belediye gap | borç | **PARK + İBB sitemap eklendi** | +1 il (İBB) |
| Cloud GHA workflow | 9 | 9 | sabit |
| Cloud dispatch (TUZAK-6 cloud kanıt) | bekliyor | **bekliyor** (Patron Pzr gece) | sabit |

---

## 7. B97 KAZANIMI ÖZET

✅ Lokal motor AKTİF doğrulandı (launchctl PID 9139, log dolu, err boş)
✅ TUZAK-7 sahte-büyüme TEST GEÇTİ ⭐⭐⭐ (cold start 183, sonraki 0)
✅ Ölü-feed detektör script + ilk rapor (V16 SERT yetersiz-veri kararı)
✅ TÜİK SPA confirmed → PARK damga kesinleşti
✅ 6 belediye gap dürüst PARK + İBB sitemap.xml lokal motora eklendi (20 feed)
✅ Çift-mod çakışmasız teyit (cloud aktive olunca md5 dedup)

❌ TUZAK-6 cloud kanıt hâlâ eksik (Patron Pzr gece)
❌ 3 döngü çok az — gerçek sağlık değerlendirmesi B98 sprint başında (100+ döngü sonrası)
❌ TÜİK Veri Portalı bültene erişim PARK (alternatif yok)
❌ 5 belediye (denizli/muğla/ş.urfa/tekirdağ/van) belediye-özel kanal PARK (valilik yedek)

---

**Hazırlayan:** CC-Basın B97 — anayasa v2.2 § 5.5 ÇİFT-MOD UYGULANDI + 5.4 KÖR-NOKTA dürüst güncellendi
**Sonraki:** B98 — 24h akış kümülatif analiz (TUZAK-7 sürdürülebilirlik) + cloud TUZAK-6 kanıt teyidi + ölü-feed günlük rutin
