# Lead Backend — Production Log

**Tarih:** 2026-05-27
**Sprint:** 7

---

## Deploy Durumu

```
$ curl -sI https://tradiaturkey.com/api/health
HTTP/2 404
```

**Backend henüz deploy edilmemiş.** `/api/health` ve `/api/lead` GitHub Pages tarafından servis ediliyor (404/405 dönüşü Pages davranışı). Workers route aktif değil.

**Önkoşul (Ahmet eylemi):**
1. `npm i -g wrangler` (yoksa)
2. `wrangler login` (Cloudflare hesabı ile)
3. `cd workers && wrangler d1 create tradia_leads_v1`
   → çıktıdaki `database_id` UUID'sini `wrangler.toml` içindeki placeholder ile değiştir
4. `wrangler d1 execute tradia_leads_v1 --file=d1_schema.sql --remote`
5. `wrangler secret put HASH_SALT` (random 32 byte hex)
6. `wrangler secret put ADMIN_KEY` (random 32 byte hex)
7. `wrangler secret put NOTIFY_WEBHOOK` (opsiyonel — Telegram için `tg:BOTTOKEN:CHATID`)
8. `wrangler deploy`

Detaylı: [workers/DEPLOY.md](../workers/DEPLOY.md) 8-adım rehber.

---

## Smoke Test — DEPLOY SONRASI BEKLENEN ÇIKTI

Backend canlandığında `workers/test_curl_commands.sh` çalıştırılacak. Beklenen sonuç:

```
=== 0. Health check ===
  ✓ PASS: /api/health → 200

=== 1. /api/lead POST — 4 dilde 4 persona ===
  ✓ PASS: TR Arnavutköy rapor → 200
  ✓ PASS: EN Bursa city_report → 200
  ✓ PASS: RU Antalya waitlist → 200
  ✓ PASS: DE Mudanya rapor → 200

=== 2. /api/yorum POST — Mudanya 4 mahalle ===
  ✓ PASS: yorum mudanya-burgaz (yukseliste) → 200
  ✓ PASS: yorum mudanya-mirza (stabil) → 200
  ✓ PASS: yorum mudanya-yeni (dususte) → 200
  ✓ PASS: yorum mudanya-celepkoy (stabil) → 200

=== 3. Rate limit — 6. istek 429 olmalı ===
  istek 1 → HTTP 200
  ...
  istek 5 → HTTP 200
  istek 6 → HTTP 429
  ✓ PASS: Rate limit doğru

=== 4. KVKK opt-in eksikse 400 ===
  ✓ PASS: kvkk_onay:false → 400
  ✓ PASS: kvkk_onay eksik → 400

=== 5. KVKK silme — Article 7 ===
  ✓ PASS: kvkk-sil → 200

Pass: 12 / 12
```

---

## Sprint 7 Eklenen Kod (Deploy Bekleniyor)

### Admin Dashboard

- **Dosya:** [workers/admin-handler.js](../workers/admin-handler.js)
- **Endpoint:** `GET /admin` (HTML dashboard), `GET /admin/leads` (JSON stats), `GET /admin/leads/export` (full dump), `GET /admin/yorumlar`
- **Auth:** `X-Admin-Key` header veya `Authorization: Bearer <ADMIN_KEY>`
- **Deploy:** `wrangler.toml`'a yeni route eklenir:
  ```toml
  [[routes]]
  pattern = "tradiaturkey.com/admin/*"
  zone_name = "tradiaturkey.com"
  ```
  ya da ayrı worker olarak:
  ```bash
  wrangler deploy --config workers/wrangler-admin.toml
  ```

### Notify Webhook (Telegram/Email)

- **Dosya:** [workers/notify-webhook.js](../workers/notify-webhook.js)
- **Yapı:** `notify(env, lead)` çağrısı lead-handler.js'in `ctx.waitUntil()` içinde tetiklenir
- **Modlar:**
  - `NOTIFY_WEBHOOK=tg:BOTTOKEN:CHATID` → Telegram Bot
  - `NOTIFY_WEBHOOK=email:placeholder` → Cloudflare Email Routing (mailchannels)
  - `NOTIFY_WEBHOOK=https://hooks.slack.com/...` → generic webhook
- **KVKK:** lead'in kendisi e-posta almaz; sadece Ahmet uyarılır
- **lead-handler.js entegrasyonu (Sprint 8'de uygulanır):**
  ```js
  import { notify } from './notify-webhook.js';
  ...
  ctx.waitUntil(notify(env, leadKaydi));
  ```

---

## Sprint 8 Görevi (deploy sonrası)

- [ ] Ahmet → DEPLOY.md 8 adım
- [ ] `./workers/test_curl_commands.sh` çalıştır, 12/12 pass bekle
- [ ] `https://tradiaturkey.com/admin` Bearer auth ile aç, dashboard görüntüle
- [ ] Notify webhook test (`POST /notify-test` ile mock lead)
- [ ] Bu log'a "PRODUCTION LIVE — YYYY-MM-DD" notu düş
- [ ] Frontend `/map/`'teki `sendLead()` → backend gerçek yanıt verir mi kontrol et
- [ ] Lansman dalga 1 için ilk 24h lead izlemesi

---

*Hazırlayan: CC-Site Sprint 7. Backend canlandığında bu log post-mortem ile güncellenecek.*
