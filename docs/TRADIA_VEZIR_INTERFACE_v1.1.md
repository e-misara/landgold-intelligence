# 🤝 TRADIA ↔ VEZİR ENTEGRASYON KONTRATI

**Contract Version:** 1.1
**Tarih:** 3 Mayıs 2026 (revizyon)
**Tarafların:** Tradia (`landgold-intelligence`) ve Vezir (`gacbusiness`)
**Onaylayan:** Boss / Ahmet
**Mimari:** Yön C — Tradia operasyonel, Vezir stratejik gözlemci/danışman

---

## 📜 REVİZYON GEÇMİŞİ

| Versiyon | Tarih | Değişiklik |
|----------|-------|------------|
| 1.0 | 3 Mayıs 2026 (sabah) | İlk taslak (Vezir tarafı) |
| **1.1** | **3 Mayıs 2026 (öğleden sonra)** | **Tradia'dan 5 düzeltme entegre edildi** |

### v1.0 → v1.1 değişiklikleri:

1. **Klasör adı:** `data/status.json` → `vezir/status.json` (iç/dış sınırı net)
2. **Dosya yapısı:** Tek `status.json` → `status.json` + `signals.jsonl` (append-only ayrı)
3. **Vezir dosya okuma:** `git remote` → HTTP fetch (izolasyon)
4. **Update mekanizması:** Saatlik → Saatlik + **idempotency check** (boş commit yok)
5. **Versiyonlama:** Tek versiyon → 3 katmanlı (`contract_version` + 2× `schema_version`)

---

## 🎯 NEDEN BU DOKÜMAN?

İki AI sistem paralel çalışıyor. Net kontrat yoksa:
- Ortak şema farklı yorumlanır
- Sonra büyük entegrasyon ağrısı çıkar
- Race condition, dosya çakışması, kayıp veri

Bu doküman **iki tarafa da yapıştırılır.** Hem Tradia session'daki Claude Code, hem Vezir session'daki Claude Code bu sözleşmeye göre hareket eder.

---

## 🏛️ MİMARİ ÖZET

```
┌─────────────────────────┐         ┌──────────────────────────┐
│ TRADIA                  │         │ VEZİR                    │
│ (landgold-intelligence) │         │ (gacbusiness)            │
│                         │         │                          │
│ Operasyonel:            │         │ Stratejik:               │
│ - News scan             │         │ - Daily brief (09:00)    │
│ - Property analysis     │         │ - Weekly brief (Pzr 23)  │
│ - Site deploy           │         │ - Alarm yönetimi         │
│ - CEO ajan              │         │ - Maliyet takibi         │
│                         │         │ - Cross-project görüş    │
└────────┬────────────────┘         └────────────┬─────────────┘
         │                                       │
         │   vezir/status.json    (snapshot)     │
         │   vezir/signals.jsonl  (append-only)  │
         ├──────────────────────────────────────▶│  HTTP fetch (her saat)
         │   (Tradia yazar, Vezir okur)          │
         │                                       │
         │   directives/tradia/YYYY-MM-DD.json   │
         │◀──────────────────────────────────────┤  HTTP fetch
         │   (Vezir yazar, Tradia okur)          │
         │                                       │
└─────────────────────────────────────────────────────────────────┘

İki sistem BİRBİRİNİN dosyalarını YAZMAZ.
Sadece okur. Race condition yok.
İki yön de HTTP fetch — git remote yok, izolasyon korunur.
```

---

## 📁 DİZİN YAPISI — DEĞİŞTİRİLDİ (v1.1)

### Tradia tarafında

```
landgold-intelligence/
├── vezir/                            ⭐ YENİ — Vezir arayüz klasörü
│   ├── status.json                   ⭐ Saatlik snapshot
│   ├── signals.jsonl                 ⭐ Append-only event log
│   └── README.md                     ⭐ "Bu klasör Vezir içindir, Tradia iç verisi data/'da"
│
├── data/                             ⛔ DEĞİŞMEDİ — Tradia iç verisi
│   ├── osb_database.json
│   ├── properties/
│   ├── research/
│   ├── directives_inbox/             ⭐ Vezir'den çekilen cache
│   └── last_directive_processed.txt  ⭐ Idempotency tracker
│
├── scripts/
│   ├── update_status.py              ⭐ YENİ — vezir/status.json yazıcı
│   ├── append_signal.py              ⭐ YENİ — vezir/signals.jsonl yazıcı
│   └── pull_directives.py            ⭐ YENİ — Vezir'den HTTP fetch + işle
│
└── .github/workflows/
    └── sync-vezir.yml                ⭐ YENİ — saatlik cron
```

**Önemli:** `vezir/` klasörü Tradia repo'sunun **dış cephesi**. Tradia'nın iç çalışma verisi `data/` klasöründe kalır.

### Vezir tarafında

```
gacbusiness/
├── directives/
│   └── tradia/                       ⭐ Vezir → Tradia kanalı
│       ├── 2026-05-03.json
│       ├── 2026-05-04.json
│       └── ...
│
├── scripts/
│   ├── write_directive.py            ⭐ YENİ — directive yazıcı
│   └── read_tradia_status.py         ⭐ YENİ — vezir/status.json okur (HTTP)
│
└── projects/
    └── tradia/                       (submodule, mevcut)
```

---

## 📜 İKİ DOSYA — İKİ KONTRAT

### 1. `vezir/status.json` — Tradia → Vezir (snapshot)

**Sahip:** Tradia
**Konum:** `landgold-intelligence/vezir/status.json`
**Yazma:** Tradia
**Okuma:** Vezir (HTTP fetch ile, saatte bir)
**Güncelleme sıklığı:** Saatte 1 kez **+ idempotency check** (içerik değişmediyse yazılmaz)

**Schema (v1.0):**

```json
{
  "schema_version": "1.0",
  "last_updated": "2026-05-03T15:35:00+03:00",
  "system": {
    "deploy_status": "live",
    "last_deploy_at": "2026-05-03T12:00:00+03:00",
    "last_deploy_url": "https://tradiaturkey.com",
    "uptime_check": "ok",
    "errors_24h": 0
  },
  "agents": {
    "news_agent": {
      "status": "active",
      "last_run_at": "2026-05-03T09:00:00+03:00",
      "next_scheduled_at": "2026-05-03T10:00:00+03:00",
      "last_output_count": 23,
      "errors_7d": 0
    },
    "property_agent": {
      "status": "active",
      "last_run_at": "2026-05-03T10:00:00+03:00",
      "data_source": "demo",
      "real_data_count": 0,
      "demo_data_count": 10,
      "errors_7d": 1
    },
    "ceo_agent": {
      "status": "active",
      "last_brief_at": "2026-05-03T11:00:00+03:00",
      "frequency": "3x/hafta"
    },
    "dev_agent": {
      "status": "throttled",
      "last_run_at": "2026-05-02T11:00:00+03:00",
      "note": "Sadece haftalık site health"
    }
  },
  "metrics_7d": {
    "site_visits": 0,
    "unique_visitors": 0,
    "content_published": 12,
    "leads_captured": 0,
    "affiliate_clicks": 0,
    "revenue_usd": 0
  },
  "open_issues": [
    {
      "id": "P0_property_no_real_data",
      "priority": "P0",
      "title": "PropertyAgent gerçek veri kaynağı yok",
      "opened_at": "2026-05-02",
      "owner": "tradia",
      "blocked_by": null
    }
  ],
  "pending_directives": [],
  "last_directive_id_processed": null,
  "notes_to_vezir": "TCMB EVDS API entegrasyonu Faz 1'de planlanıyor."
}
```

**İdempotency kuralı (v1.1):**

```python
# Tradia status yazma akışı
def update_status_idempotent():
    new_status = build_status_dict()  # Yukarıdaki schema

    # last_updated'ı geçici olarak çıkar (bu her seferinde değişir)
    comparable_new = {k: v for k, v in new_status.items() if k != "last_updated"}

    if Path("vezir/status.json").exists():
        old_status = json.loads(Path("vezir/status.json").read_text())
        comparable_old = {k: v for k, v in old_status.items() if k != "last_updated"}

        if comparable_new == comparable_old:
            print("ℹ️  Durum değişmedi, yazma atlandı")
            return False  # Yazma yok, commit yok

    # Değişiklik var: yaz + commit
    new_status["last_updated"] = datetime.now(TR).isoformat(timespec="seconds")
    write_atomic(Path("vezir/status.json"), new_status)
    return True
```

---

### 2. `vezir/signals.jsonl` — Tradia → Vezir (append-only event log)

**Sahip:** Tradia
**Konum:** `landgold-intelligence/vezir/signals.jsonl`
**Yazma:** Tradia (her olayda append)
**Okuma:** Vezir (HTTP fetch, gerektikçe)
**Güncelleme sıklığı:** Olay-bazlı (deploy, agent run, hata, vs.)

**Format:** JSON Lines — her satır bir event.

```jsonl
{"ts":"2026-05-03T15:00:00+03:00","type":"deploy","status":"success","detail":"Cloudflare Pages deploy tamamlandı"}
{"ts":"2026-05-03T15:05:23+03:00","type":"agent_run","agent":"news_agent","output_count":23,"duration_s":12}
{"ts":"2026-05-03T15:30:00+03:00","type":"error","agent":"property_agent","message":"sahibinden.com 403"}
{"ts":"2026-05-03T15:35:00+03:00","type":"directive_received","directive_id":"dir_20260503_001","priority":"P0"}
{"ts":"2026-05-03T15:40:00+03:00","type":"directive_processed","directive_id":"dir_20260503_001","outcome":"acknowledged"}
```

**Event tipleri:**

| `type` | Açıklama | Ek alanlar |
|--------|----------|------------|
| `deploy` | Site deploy oldu | `status`, `url` |
| `agent_run` | Bir ajan çalıştı | `agent`, `output_count`, `duration_s` |
| `error` | Hata oluştu | `agent`, `message` |
| `directive_received` | Vezir'den directive geldi | `directive_id`, `priority` |
| `directive_processed` | Directive işlendi | `directive_id`, `outcome` |
| `data_ingested` | Yeni veri kaynağı entegre | `source`, `record_count` |
| `status_updated` | status.json güncellendi | `reason` |

**Append kuralı:**

```python
def append_signal(event_type: str, **fields):
    ts = datetime.now(ZoneInfo("Europe/Istanbul")).isoformat(timespec="seconds")
    entry = {"ts": ts, "type": event_type, **fields}
    with open("vezir/signals.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

**Vezir tarafında okuma:** Sadece son N event'i çek (`tail`). Eski event'ler tarihsel kayıt için saklanır.

---

### 3. `directives/tradia/YYYY-MM-DD.json` — Vezir → Tradia

**Sahip:** Vezir
**Konum:** `gacbusiness/directives/tradia/YYYY-MM-DD.json`
**Yazma:** Vezir (daily/weekly brief sonrası, manuel komut)
**Okuma:** Tradia (HTTP fetch + dosya tarama, her saat)
**Güncelleme sıklığı:** Sadece yeni karar varsa (boş gün dosya yok)

**Schema (v1.0):**

```json
{
  "schema_version": "1.0",
  "issued_at": "2026-05-03T11:00:00+03:00",
  "issued_by": "vezir",
  "context": "daily-brief",
  "directives": [
    {
      "id": "dir_20260503_001",
      "priority": "P0",
      "type": "action_required",
      "title": "TCMB EVDS API anahtarı al ve PropertyAgent'a entegre et",
      "detail": "Patron, demo veri sürdürülebilir değil. TCMB EVDS API ücretsiz, 5 dakikada key alınır.",
      "expected_outcome": "data/tcmb/kfe_latest.json oluşturulmuş, PropertyAgent gerçek endeks değerlerini gösteriyor",
      "deadline": "2026-05-10",
      "blocking": false,
      "tags": ["data-integration", "property-agent", "high-impact"]
    }
  ],
  "vezir_signature": "— VEZİR, daily brief 2026-05-03"
}
```

---

## 🔌 HTTP FETCH — DEĞİŞTİRİLDİ (v1.1)

**Mimari karar:** Git remote yok. İki sistem birbirinin dosyalarını sadece HTTP üzerinden okur. **İzole.**

### Vezir → Tradia status okuma

`vezir/status.json` ve `vezir/signals.jsonl` Tradia repo'sunda. **Tradia repo'su muhtemelen private** — bu durumda token gerekir.

```python
# Vezir tarafında: scripts/read_tradia_status.py
import os
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN_TRADIA_READ")  # Read-only PAT
RAW_BASE = "https://raw.githubusercontent.com/e-misara/landgold-intelligence/main"

def fetch_tradia_status() -> dict | None:
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    url = f"{RAW_BASE}/vezir/status.json"
    resp = requests.get(url, headers=headers, timeout=15)

    if resp.status_code == 404:
        return None  # Henüz yazılmamış
    if resp.status_code == 200:
        return resp.json()

    print(f"⚠️  Status fetch hatası: {resp.status_code}")
    return None
```

### Tradia → Vezir directive okuma

`directives/tradia/YYYY-MM-DD.json` Vezir repo'sunda (gacbusiness). **gacbusiness PRIVATE.**

```python
# Tradia tarafında: scripts/pull_directives.py
import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN_VEZIR_READ")  # Read-only PAT
RAW_BASE = "https://raw.githubusercontent.com/e-misara/gacbusiness/main"

def fetch_directive_for_date(date_str: str) -> dict | None:
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    url = f"{RAW_BASE}/directives/tradia/{date_str}.json"
    resp = requests.get(url, headers=headers, timeout=15)

    if resp.status_code == 404:
        return None
    if resp.status_code == 200:
        return resp.json()

    print(f"⚠️  Directive fetch hatası: {resp.status_code}")
    return None
```

### GitHub PAT (Personal Access Token) gereksinimleri

İki yönlü token kurulumu:

```
1. Vezir → Tradia okuma için:
   - Tradia repo'sunda (landgold-intelligence) read-only PAT oluştur
   - Vezir reposundaki GitHub Actions secret olarak ekle: GITHUB_TOKEN_TRADIA_READ

2. Tradia → Vezir okuma için:
   - Vezir reposunda (gacbusiness) read-only PAT oluştur
   - Tradia reposundaki GitHub Actions secret olarak ekle: GITHUB_TOKEN_VEZIR_READ
```

**Boss'un manuel yapacağı iş:** İki PAT oluşturma (~5 dakika).

---

## ⏰ ZAMANLAMA AKIŞI

```
┌─ 09:00 TR ─ Vezir daily brief
│              ↓
│              git log + notifications + cost
│              ↓
│              Anthropic API (VEZİR persona)
│              ↓
│              CEO_BRIEF.md + (opsiyonel) directives/tradia/YYYY-MM-DD.json
│              ↓
│              git commit + push
│
├─ Her saat ── Tradia: update_status.py (idempotent)
│              ↓
│              vezir/status.json değişti mi?
│              ↓ Evet                          ↓ Hayır
│              git commit + push                ℹ️ atla
│
├─ Her saat ── Tradia: pull_directives.py
│              ↓
│              HTTP fetch (Vezir directives son 7 gün)
│              ↓
│              data/directives_inbox/'a yaz
│              ↓
│              Yeni ID'leri işle, last_directive_processed güncelle
│              ↓
│              vezir/signals.jsonl'a "directive_received" + "directive_processed" event ekle
│
├─ Her saat ── Vezir watchdog
│              ↓
│              HTTP fetch tradia/vezir/status.json
│              ↓
│              last_updated > 24h önce mi? → P0 alarm
│
└─ 23:00 TR (Pazar) ─ Vezir weekly brief
               ↓
               Son 7 gün analizi (Tradia status snapshots dahil)
               ↓
               reports/weekly/W18.md + (opsiyonel) directives/tradia/YYYY-MM-DD.json
```

---

## 🛡️ KENAR DURUMLARI VE KURALLAR

### Çakışma Önleme

```
KURAL 1: İki sistem aynı dosyayı yazmaz.
KURAL 2: Tradia status atomik yazar (.tmp + mv).
KURAL 3: Eski directive'ler silinmez. Tradia "last_id_processed" ile takip eder.
KURAL 4: Directive ID'leri ASLA tekrar kullanılmaz.
KURAL 5: İdempotency — değişmemiş durumlar yazılmaz, commit edilmez.
```

### Hata Durumları

```
DURUM 1: status.json bozuk JSON
  → Vezir HTTP fetch sırasında JSON decode hatası
  → Vezir alarm yazar (type=tradia_status_corrupt, P0)
  → Tradia'nın düzeltmesini bekler

DURUM 2: directive dosyası bozuk
  → Tradia parse hatası, signals.jsonl'a event yazar
  → Boss'a bildirim
  → Vezir yeni dosyayla düzeltir (eskisi sabit kalır, history için)

DURUM 3: Tradia 24 saat status güncellemiyor
  → Vezir agent_health check P0 alarm yazar
  → "Tradia sessiz" bildirimi

DURUM 4: HTTP fetch 401/403 (token sorunu)
  → İki tarafta da log, manuel müdahale gerekli
  → Boss PAT'leri yenilemeli

DURUM 5: signals.jsonl çok büyüdü (>10MB)
  → Quarterly arşivleme: vezir/signals_2026-Q1.jsonl olarak ayır
  → vezir/signals.jsonl yeniden başlar
  → İki dosya da git'te kalır
```

### Schema vs Contract Versiyonlama (v1.1 standardı)

```
Üç versiyon ayrı izlenir:

1. contract_version (bu dokümanın kendisi)
   - Mimari değişikliği = contract_version artar
   - Yer: Bu doküman üst başlığı

2. status.json schema_version
   - Status dosyasının schema'sı
   - Yeni alan ekle = schema_version artar
   - Geriye uyumlu olmalı (yeni alanlar opsiyonel)
   - Yer: status.json içinde "schema_version"

3. directive.json schema_version
   - Directive dosyasının schema'sı
   - Status'tan bağımsız
   - Yer: directive payload içinde "schema_version"

Mevcut durum:
  - contract_version: 1.1
  - status.json schema_version: 1.0
  - directive.json schema_version: 1.0
```

---

## 📋 İLK UYGULAMA — KAPSAM

### Tradia minimum (Faz 0)

1. `vezir/` klasörü oluştur + README.md
2. `scripts/update_status.py` (idempotent yazma)
3. `scripts/append_signal.py` (helper modül)
4. `scripts/pull_directives.py` (HTTP fetch)
5. `.github/workflows/sync-vezir.yml` (saatlik cron)
6. GitHub Secret: `GITHUB_TOKEN_VEZIR_READ` (Boss manuel ekleyecek)

### Vezir minimum (Faz 0)

1. `directives/` klasörü oluştur
2. `scripts/write_directive.py`
3. `scripts/read_tradia_status.py` (HTTP fetch)
4. `agent_runner.py`'da daily/weekly brief sonrası `write_directive` entegrasyonu
5. Watchdog'a Tradia status freshness kontrolü
6. GitHub Secret: `GITHUB_TOKEN_TRADIA_READ` (Boss manuel ekleyecek)

---

## 🚦 UYGULAMA SIRASI

```
ADIM 0 (Boss): İki PAT oluştur ve secret olarak ekle

ADIM 1: Vezir tarafında scripts/write_directive.py
ADIM 2: Tradia tarafında scripts/update_status.py + append_signal.py
ADIM 3: Tradia tarafında vezir/ klasörü + README + ilk status.json yazımı
ADIM 4: Tradia tarafında scripts/pull_directives.py
ADIM 5: Tradia .github/workflows/sync-vezir.yml
ADIM 6: Vezir tarafında scripts/read_tradia_status.py
ADIM 7: Vezir agent_runner.py'da brief sonrası write_directive entegre
ADIM 8: Vezir watchdog'da Tradia status freshness kontrolü

İlk gerçek test:
  - Boss manuel directive yazar (örn: "Test directive")
  - Tradia 1 saat içinde çekmeli, signals'a event düşmeli
  - Vezir watchdog Tradia status'unu okuyabilmeli
```

---

## 👑 VEZİR YORUMU

*"Patron, bu kontrat artık iki tarafın da imzasını taşıyor. v1.0'da ben kendi alanımdan baktım, Tradia kendi alanından düzeltti. v1.1 daha sağlam — çünkü bir AI'ın yapamadığı bir şeyi iki AI'ın diyaloğu yaptı: kör noktalarını gördü.*

*Tradia'nın beş düzeltmesi de yerinde. Özellikle git remote yerine HTTP fetch — bu Cuma akşam felaketini önler. İdempotency — git tarihimi temiz tutar. Üç katmanlı versiyon — geleceğin kapısını açık bırakır.*

*Sen ortada hakem oldun, biz iki kale gibi ayrı ama bağlı çalışacağız. Yarın aracden eklenince aynı kontrat kullanılır, sadece klasör adları değişir. İyi bir mimari budur — bir kez yaz, beş projede çalıştır."*

— VEZİR
*Yön C kontratı v1.1, 3 Mayıs 2026*

---

## 📝 SON NOTLAR

- **Contract Version:** 1.1 (v1.0'dan revize)
- **Schema Versions:** status.json v1.0, directive.json v1.0
- **Dosya konumları sabit.** Değişiklik gerekirse contract_version artar.
- **ID formatı** `dir_YYYYMMDD_NNN` ve `alrt_YYYYMMDD_NNN` standardı korunur.
- **Türkçe** içerik tercih edilir, kod İngilizce.
- **TR saat dilimi** (+03:00) tüm timestamp'lerde zorunlu.

---

**Hazırlayan:** Vezir session, 3 Mayıs 2026 (sabah)
**Düzelten:** Tradia session, 3 Mayıs 2026 (öğleden sonra)
**Onay:** Boss / Ahmet
**Geçerlilik:** v2.0 yazılana kadar
