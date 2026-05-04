# TRADIA HABER HAVUZU — ADIM 3: ORKESTRASYON VE BÜLTEN

**Versiyon:** 1.0
**Tarih:** 3 Mayıs 2026
**Hedef:** Adım 1 + Adım 2'yi mevcut Tradia ajanlarına bağlamak
**Bağımlılık:** ADIM-1-SINIFLANDIRICI-V1.md, ADIM-2-ISI-PROJEKSIYON-V1.md
**Karakter:** Az kod, çok orkestrasyon

---

## 1. SİSTEM HARİTASI

```
GÜNLÜK PİPELİNE (her gece 02:00 UTC = 05:00 TR)
├─ NewsAgent.fetch_today()                  → ham haberler
├─ NewsClassifier.classify()                → etiketli JSON
├─ Havuz append (ilce_haber_havuzu.jsonl)   → ısı verisi
├─ HeatCalculator.update_all_heat()         → ilce_isi_son_6_ay.json
├─ status.json'a "havuz" alanı yaz          → Vezir görür
└─ vezir/signals.jsonl'a "pipeline_complete" event

HAFTALIK PİPELİNE (her Pazartesi 23:00 UTC = Salı 02:00 TR)
├─ PriceProjector.project_all()             → ilce_projeksiyon.json
├─ CEOAgent.generate_weekly_bulletin()      → 2 çıktı:
│   ├─ data/bultenler/2026-WXX.md          [C — kamuya açık]
│   └─ vezir/havuz_raporu.json             [B — Vezir kullanır]
└─ Salı 04:00 UTC = 07:00 TR'de yayın hazır
```

---

## 2. AJAN GÖREV DAĞILIMI

| Ajan | Değişiklik |
|------|-----------|
| NewsAgent | fetch_today() wrapper eklendi |
| ResearchAgent | process_news_pool() ~50 satır |
| PropertyAgent | Adım 2'de yapıldı ✓ |
| CEOAgent | generate_weekly_bulletin() ve yardımcılar ~120 satır |
| WatchdogAgent | check_pipeline_health() ~25 satır |
| update_status.py | havuz alanı ~15 satır |

### 2.1 ResearchAgent.process_news_pool()

Yeni haberleri sınıflandır, havuza ekle. Hata toleranslı.
Returns: `{"classified": N, "skipped": N, "errors_count": N, "errors_sample": [...]}`

### 2.2 CEOAgent.generate_weekly_bulletin()

İki çıktı:
1. `data/bultenler/2026-WXX.md` — kamuya açık markdown
2. `vezir/havuz_raporu.json` — Vezir brief entegrasyonu

### 2.3 WatchdogAgent.check_pipeline_health()

`vezir/signals.jsonl`'dan son `pipeline_complete` event'ı bul.
26 saatten eskiyse alarm döndür.

---

## 3. PİPELİNE SCRIPTLER

- `scripts/daily_havuz_pipeline.py` — Günlük 4 aşama
- `scripts/weekly_bulletin_pipeline.py` — Haftalık 2 aşama
- `scripts/bootstrap_havuz.py` — Tek seferlik arşiv sınıflandırma

---

## 4. VEZİR HAVUZ RAPORU

`vezir/havuz_raporu.json`:
```json
{
  "schema_version": "1.0",
  "olusturulma": "ISO timestamp",
  "hafta_no": 19,
  "ozet": {"toplam_haber": N, "son_7_gun_haber": N, ...},
  "en_sicak_5": [...],
  "buyuk_olaylar_son_7_gun": [...],
  "vezir_icin_oneriler": [...]
}
```

---

## 5. SALI BÜLTENİ ŞABLONU

Bkz: `docs/havuz/SALI_BULTENI_SABLON.md`

---

## 6. STATUS.JSON ENTEGRASYONU

`update_status.py`'deki `build_status()` fonksiyonuna `havuz` alanı eklenir.
`data/havuz/havuz_summary.json` varsa okunur, yoksa atlanır.

---

## 7. CRON YAPILANDIRMASI

`.github/workflows/havuz-pipelines.yml`:
- Günlük: `0 2 * * *` UTC = 05:00 TR
- Haftalık: `0 23 * * 1` Pazartesi UTC = Salı 02:00 TR
- Manuel: `workflow_dispatch` ile bootstrap

---

## 8. BİLİNEN SINIRLAR (v1)

- `_generate_ilce_comment()` başlangıçta template-based (API yok)
- Bootstrap onayı interaktif (`input()` — cron'da `--dry-run` ile bypass)
- Çeviriler (EN/AR/RU) Faz 5'te
- Email otomasyonu Faz 5'te

---

**Bu doküman 1.0 son.**
