# CC-Basın Pzt Launch Dürüst Durum Raporu — 2026-06-15

**Tarih:** 2026-06-15 02:30 TR (Pzt sabahın erken saatleri, launch günü)
**Sprint:** B98 sonu kapanış · **Anayasa:** [[anayasa_basin]] v2.3
**Disiplin:** V11 dürüst · V16 SERT · A04 · $0

> **Tek satır:** 🚨 **V16 SERT KRİTİK BULGU**: B93/B94'te yazdığım 5 yeni workflow ve 3 yeni script git'e EKLENMEDİ → cloud'da HİÇ YOK. B97/B98 raporlarında "cloud workflow 9" varsaydım, gerçek: cloud'da yalnız 4 commit'li workflow (B86+B88). TUZAK-3 (cloud "çalışıyor" karinesi) ihlali itiraf. POZİTİF: Lokal motor 81 döngü ⭐ TUZAK-7 GEÇTİ + Pzt 09:45 TR CSB workflow ZATEN COMMIT'Lİ ve cloud cron'da → TOKİ launch eş-pencere kanal HAZIR.

---

## 1. V16 SERT İTİRAF — B93-B98 ZİNCİR HATASI

### Hata zinciri
- **B86 commit:** `primer-monitor.yml` + script git'e eklendi, push edildi → cloud ✅
- **B88 commit:** 3 İhale workflow (rg/csb/dsi) git'e eklendi, push edildi → cloud ✅
- **B93 yazıldı:** `haber-pulse-saatlik.yml` + `piyasa-monitor-aylik.yml` + 2 script → **commit YAPILMADI, push YAPILMADI**
- **B94 yazıldı:** 3 valilik workflow + `valilik_pulse_81il.py` → **commit YAPILMADI, push YAPILMADI**
- **B96-B98 yazıldı:** lokal motor + sağlık plist + sınıflandırıcı + Cross-CC → **lokal**, git önemli değil
- **B97 raporu:** "Cloud GHA 9 workflow … Pzr gece dispatch bekliyor" → **YANILGI**
- **B98 raporu:** "Cloud workflow 9 (değişmedi)" → **YANILGI**

### Kök neden — TUZAK-3 ihlali
> *"GitHub Actions workflow push edilmiş olması cloud'da çalıştığı anlamına GELMEZ."*

Tersi de geçerli: **Workflow dosyası yerelde olması push edildiği anlamına GELMEZ.** B93-B94 sprintlerinde `git add` + `commit` + `push` yapmadım, lokal dosyaları cloud-aktif sandım.

### Bulgu kaynağı
- `git status` — 5 workflow `??` (untracked)
- GitHub API `actions/runs` son 30 run: primer-monitor 2, ihale-rg 1, sync-vezir 25 failure (CC-Basın değil), pages 2 — yenilerin 0 run'ı YOK

---

## 2. CLOUD GERÇEK DURUM (V16 SERT — API teyitli)

| Workflow | Git | Cloud çalıştı mı? | Son başarılı |
|---|---|---|---|
| `primer-monitor.yml` | ✅ commit (B86) | ✅ 2 run / 2 success | 2026-06-14 09:21 |
| `ihale-rg-gunluk.yml` | ✅ commit (B88) | ✅ 1 run / 1 success | 2026-06-14 10:01 |
| `ihale-csb-haftalik.yml` Pzt 09:45 ⭐ | ✅ commit (B88) | ⏳ Pzt vakit gelmedi | henüz - bugün 09:45 |
| `ihale-dsi-haftalik.yml` Salı 09:50 | ✅ commit (B88) | ⏳ Salı | yarın |
| `haber-pulse-saatlik.yml` B93 | ❌ untracked | ❌ cloud'da YOK | hiç |
| `piyasa-monitor-aylik.yml` B93 | ❌ untracked | ❌ cloud'da YOK | hiç |
| `valilik-pulse-metro.yml` B94 | ❌ untracked | ❌ cloud'da YOK | hiç |
| `valilik-pulse-buyuksehir.yml` B94 | ❌ untracked | ❌ cloud'da YOK | hiç |
| `valilik-pulse-kalan.yml` B94 | ❌ untracked | ❌ cloud'da YOK | hiç |
| `sync-vezir.yml` | ✅ commit | ❌ 25 run / 25 failure (CC-Vezir, Basın değil) | 0 success — sekreter sorunu |

**Net:** Cloud'da aktif 4 workflow (sadece 2'si zaten çalıştı, 2'si Pzt-Salı tetiklenir). 5 yeni workflow cloud'da YOK.

---

## 3. TOKİ LAUNCH PZT 09:45 — POZİTİF

**`ihale-csb-haftalik.yml` ZATEN COMMIT'Lİ (B88) + cloud cron'a kayıtlı:**
```yaml
- cron: "45 6 * * 1"   # Pzt 09:45 TR ⭐ TOKİ launch eş-pencere
```

**Yani:** TOKİ launch kritik kanalı bugün 09:45 TR'de **kendiliğinden tetiklenecek** (B86/B88 commit'leri gerçek). Patron Pzr gece elle dispatch ETMESİ DAHİ GEREKMİYORDU bu workflow için.

**Eylem:** Bugün 09:46 TR'de `gh run list` (anonim API) ile teyit. Audit cloud commit beklenir.

---

## 4. LOKAL MOTOR (B96-B98) — TAM AKTİF ⭐

| Kontrol | Durum |
|---|---|
| launchctl com.tradia.ccbasin.pulse | ✅ PID 9139 / exit 0 (B97'den beri ~3.5 saat kesintisiz) |
| _akis_log.jsonl satır | **81** (B97'de 3 idi) |
| Döngü sayısı | 368+ döngü |
| Ortalama döngü süresi | ~2.7 dk (interval guard tetik) |
| TUZAK-7 sahte-büyüme | ✅ GEÇTİ ⭐⭐⭐ (cold start 183 → sonraki döngülerde 0-3 yeni, dedup engelliyor) |
| Ölü-feed (mantık düzeltildi) | 0 🔴 ÖLÜ · 0 🟡 KURU · 5 🟢 SAĞLIKLI · 15 ⚪ yetersiz-veri (8 saatte interval yetersiz) |
| Bugün havuz `2026-06-15` | data/havuz/haber/2026-06-15/00.jsonl (1221 byte) |
| Bugün sınıflama | 3 distinct · 0 il · 1 kategori (TCMB faiz manşeti gece) |
| Cross-Hat Analiz bridge | 1 sinyal · İhale kazanan 0 |

**B98 Patron-yapma:** Ölü-feed detektör mantığı düzeltildi (KURU artık `relevant=0 + fetch>0` şart; salt `yeni=0` yanlış-pozitif veriyordu — gece RSS feed'leri statik kalınca).

---

## 5. DİĞER BEKLEYEN PATRON BORÇLARI

| Borç | Durum |
|---|---|
| B92 damga 4-satır karar (Atatürk/Başak/Göztepe/Barbaros HP) | ⏳ B92-B98 boyunca ele alınmadı |
| com.tradia.ccbasin.saglik.plist yükleme | ⏳ B98 yazıldı, `launchctl load` Patron yapacak |
| 5 yeni workflow commit + push | ⏳ V16 SERT bu rapor itirafı — Patron'a sunulur |
| Pzt 08:50-10:00 launch live tepki + v3 sunum paylaş | ⏳ bugün ⭐ |
| BDDK JSON serialize bug | ⏳ |

---

## 6. ÖNERİ — PATRON KARARINA SUNULAN (V16 SERT)

### Öneri 1: 5 yeni workflow + 3 yeni script + plist commit + push
```
git add scripts/haber_pulse_saatlik.py scripts/piyasa_monitor_aylik.py \
        scripts/valilik_pulse_81il.py scripts/lokal_surekli_motor.py \
        scripts/haber_classifier.py scripts/havuz_siniflandir.py \
        scripts/cross_cc_besle.py scripts/olu_feed_detektor.py \
        scripts/_rg_parser_lib.py \
        .github/workflows/haber-pulse-saatlik.yml \
        .github/workflows/piyasa-monitor-aylik.yml \
        .github/workflows/valilik-pulse-metro.yml \
        .github/workflows/valilik-pulse-buyuksehir.yml \
        .github/workflows/valilik-pulse-kalan.yml \
        requirements.txt
git commit -m "feat(cc-basin/b93-b98): saatlik haber + valilik tier + piyasa + sınıflandırma + Cross-CC köprü"
git push
```

**Sonuç:** 4 cloud workflow → 9 cloud workflow ⭐ KESİNTİSİZ AKIŞ tamamlanır.

**Risk:** Public repo + bot commit'leri (haber-pulse her saat commit) repo'yu şişirir. **Mitigasyon:** sync-vezir benzer model zaten kullanılıyor.

### Öneri 2: data/devir/ ve data/havuz/ commit'ten HARİÇ TUT
- `data/havuz/` bot her saat commit eder, repo şişer
- `.gitignore` ekleme: `data/havuz/` + `data/devir/` + `data/audit/`
- Yalnız `data/audit/<key>_summary.json` (özet) commit'lensin

---

## 7. SONUÇ

✅ **POZİTİF**
- TOKİ launch 09:45 TR ⭐ kanal (CSB) ZATEN cloud-aktif (B88 commit'i gerçek)
- Lokal motor 81 döngü kesintisiz · TUZAK-7 sahte-büyüme TEST GEÇTİ
- B98 sınıflandırma + Cross-CC köprü lokal çalışıyor
- Ölü-feed detektör mantığı düzeltildi (gece kuru-pozitifi kalktı)

❌ **NEGATİF (V16 SERT)**
- 5 yeni workflow git'te değil → cloud'da yok
- B97/B98 raporlarında "cloud 9 workflow" YANILGI (gerçek 4)
- TUZAK-3 (cloud "çalışıyor" karinesi) bende ihlal edildi — B93/B94 sprintlerinde push doğrulanmadı

📋 **PATRON KARARLARI (4)**
1. 5 workflow + 8 script + plist commit + push **ONAY** mı?
2. `.gitignore` `data/havuz/` ekleme **ONAY** mı?
3. `com.tradia.ccbasin.saglik.plist` yükle (`launchctl load`) **EYLEM** kimde?
4. B92 damga 4-satır karar **bekliyor**

---

**Hazırlayan:** CC-Basın Pzt sabah dürüst durum
**Anayasa atfı:** v2.3 (TUZAK-3 + TUZAK-6 + TUZAK-7 + TUZAK-8 hepsi bu raporda uygulamada)
**Sonraki sprint:** B99 — Patron kararı (Öneri 1+2) sonrası commit + push + cloud doğrulama + 24h sürdürülebilirlik
