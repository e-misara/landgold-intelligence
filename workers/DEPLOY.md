# Tradia Lead Backend — Deploy Talimatı

**Süre:** ~30 dk · **Maliyet:** $0 (Cloudflare free tier)

## Önkoşul

- Cloudflare hesap (https://dash.cloudflare.com)
- Domain `tradiaturkey.com` Cloudflare'de yönetiliyor (DNS)
- Node.js 18+

## Adım 1 — Wrangler CLI kur

```bash
npm install -g wrangler
wrangler login   # Tarayıcıda Cloudflare hesap onayı
```

## Adım 2 — D1 veritabanı yarat

```bash
cd ~/LandGold/workers
wrangler d1 create tradia-leads
```

Çıktıdaki **database_id**'yi `wrangler.toml`'a yapıştır:
```toml
[[d1_databases]]
binding = "DB"
database_name = "tradia-leads"
database_id = "BURAYA_YAPISTIR"
```

## Adım 3 — Schema yükle

```bash
wrangler d1 execute tradia-leads --file=d1_schema.sql
wrangler d1 execute tradia-leads --command="SELECT name FROM sqlite_master WHERE type='table';"
# Beklenen: leads, comments, rate_limit, kvkk_silme
```

## Adım 4 — Secrets set

```bash
# Telegram bot için (önce @BotFather'dan token al)
wrangler secret put NOTIFY_WEBHOOK
# > https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=
# Veya basit webhook (örn. ntfy.sh):
# > https://ntfy.sh/tradia-leads-ahmet

# Admin stats key (rastgele uzun string)
wrangler secret put ADMIN_KEY
# > $(openssl rand -hex 32)

# IP hash salt
wrangler secret put HASH_SALT
# > $(openssl rand -hex 16)
```

## Adım 5 — Deploy

```bash
wrangler deploy
```

Çıktı: `https://tradia-lead-handler.<account>.workers.dev`
Route: `tradiaturkey.com/api/*` → Worker'a yönlendirilir.

## Adım 6 — Test

```bash
# Health check
curl https://tradiaturkey.com/api/health
# {"ok":true,"service":"tradia-lead-handler","version":"1.0.0"}

# Test lead
curl -X POST https://tradiaturkey.com/api/lead \
  -H "Content-Type: application/json" \
  -d '{"tip":"rapor","email":"ahmet.test@tradiaturkey.com","mahalle":"Mudanya Merkez","dil":"tr","kvkk_onay":true}'

# Telegram/webhook'a notification gelmeli
# Veritabanı kontrol:
wrangler d1 execute tradia-leads --command="SELECT * FROM leads ORDER BY id DESC LIMIT 5;"
```

## Adım 7 — Frontend güncelle

`docs/map/index.html` içinde `submitRapor` / `submitYorum`:
```js
// Eski:
console.log('[LEAD]', lead);

// Yeni:
fetch('https://tradiaturkey.com/api/lead', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({...lead, kvkk_onay: true}),
}).then(r => r.json()).then(...);
```

## Adım 8 — Admin Stats

```bash
curl "https://tradiaturkey.com/api/stats?admin_key=$ADMIN_KEY"
```

## Bakım

### KVKK silme talebi
Kullanıcı veri silme isterse:
```bash
curl -X POST https://tradiaturkey.com/api/kvkk-sil \
  -H "Content-Type: application/json" \
  -d '{"email":"silinecek@email.com","not_metni":"Kullanıcı talebi"}'
```

### D1 yedek
```bash
wrangler d1 export tradia-leads --output=backup-$(date +%Y%m%d).sql
```

### Rate limit cron temizlik
`wrangler.toml` içinde `crons = ["0 * * * *"]` (saatlik) — eski rate_limit kayıtları otomatik silinir.

## Free Tier Limits (CF)

- **Workers:** 100.000 req/gün ücretsiz
- **D1:** 5 GB depolama, 5M okuma + 100K yazma /gün
- **Bandwidth:** sınırsız

Tradia için bu limitler büyük yatırımcı trafiğine kadar yeterli (~50.000 günlük lead/yorum).
