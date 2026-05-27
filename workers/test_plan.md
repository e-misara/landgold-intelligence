# Lead Backend Production Test Planı

**Tarih:** 2026-05-27
**Sprint:** 6 (Sprint 5 backend deploy sonrası)
**Hedef:** `tradiaturkey.com/api/*` üretim doğrulaması

---

## Önkoşullar

- [ ] `workers/DEPLOY.md` 8 adımı tamamlanmış olmalı (Ahmet)
- [ ] `wrangler deploy` başarılı, `https://tradiaturkey.com/api/health` dönüşü 200 + `{ ok: true }`
- [ ] D1 database `tradia_leads_v1` aktif, schema yüklü (4 tablo: leads, comments, rate_limit, kvkk_silme)
- [ ] Secrets set: `HASH_SALT`, `ADMIN_KEY`, `NOTIFY_WEBHOOK` (opsiyonel Telegram)
- [ ] `curl` + `jq` kurulu (`brew install jq` macOS)

---

## Test 1 — /api/lead POST, 4 dilde 4 persona

Her dil ayrı bir gerçekçi persona ile gönder. Backend `kaynak: "test_sprint6"` etiketi yaz, sonradan temizle.

### TR — İstanbul rapor talebi
```bash
curl -X POST https://tradiaturkey.com/api/lead \
  -H "Content-Type: application/json" \
  -H "Origin: https://tradiaturkey.com" \
  -d '{
    "tip": "rapor",
    "email": "ahmet.testtr@gmail.com",
    "ad": "Ahmet Yılmaz",
    "il": "İstanbul",
    "mahalle": "Arnavutköy",
    "dil": "tr",
    "kaynak": "test_sprint6",
    "kvkk_onay": true
  }'
```
**Beklenen:** `{ "ok": true, "id": <int>, "msg": "..." }` HTTP 200.

### EN — Bursa city report
```bash
curl -X POST https://tradiaturkey.com/api/lead \
  -H "Content-Type: application/json" \
  -H "Origin: https://tradiaturkey.com" \
  -d '{
    "tip": "city_report",
    "email": "john.testen@example.com",
    "ad": "John Smith",
    "il": "Bursa",
    "dil": "en",
    "kaynak": "test_sprint6",
    "kvkk_onay": true
  }'
```
**Beklenen:** HTTP 200, `id` döner.

### RU — Antalya waitlist
```bash
curl -X POST https://tradiaturkey.com/api/lead \
  -H "Content-Type: application/json" \
  -H "Origin: https://tradiaturkey.com" \
  -d '{
    "tip": "waitlist",
    "email": "ivan.testru@example.ru",
    "ad": "Иван Иванов",
    "il": "Antalya",
    "dil": "ru",
    "kaynak": "test_sprint6",
    "kvkk_onay": true
  }'
```

### DE — Mudanya rapor
```bash
curl -X POST https://tradiaturkey.com/api/lead \
  -H "Content-Type: application/json" \
  -H "Origin: https://tradiaturkey.com" \
  -d '{
    "tip": "rapor",
    "email": "hans.testde@example.de",
    "ad": "Hans Müller",
    "il": "Bursa",
    "mahalle": "Mudanya / Burgaz",
    "dil": "de",
    "kaynak": "test_sprint6",
    "kvkk_onay": true
  }'
```

**Doğrulama:** D1 sorgu
```bash
wrangler d1 execute tradia_leads_v1 --command \
  "SELECT id, ts, tip, dil, email, il, kvkk_onay FROM leads WHERE kaynak='test_sprint6';"
```
4 satır görmelisin.

---

## Test 2 — /api/yorum POST, Mudanya 4 mahalle simülasyonu

Mudanya'nın 4 mahallesi için trend yorumu gönder.

```bash
for slug in "mudanya-burgaz" "mudanya-mirza" "mudanya-yeni" "mudanya-celepkoy"; do
  trend=$(echo "$slug" | grep -oE 'burgaz|mirza|yeni|celepkoy' | awk '{ if($1=="burgaz") print "yukseliste"; else if($1=="mirza") print "stabil"; else if($1=="yeni") print "dususte"; else print "stabil"; }')
  curl -X POST https://tradiaturkey.com/api/yorum \
    -H "Content-Type: application/json" \
    -H "Origin: https://tradiaturkey.com" \
    -d "{
      \"mahalle_slug\": \"${slug}\",
      \"il\": \"Bursa\",
      \"ilce\": \"Mudanya\",
      \"trend\": \"${trend}\",
      \"body\": \"Test yorumu — Sprint 6 simulation. Mahalle ${slug}.\",
      \"kvkk_onay\": true
    }"
  echo ""
  sleep 1
done
```

**Doğrulama:**
```bash
wrangler d1 execute tradia_leads_v1 --command \
  "SELECT mahalle_slug, trend, substr(body,1,40) FROM comments WHERE body LIKE 'Test yorumu%';"
```
4 satır, trend dağılımı yukseliste/stabil/dususte/stabil.

---

## Test 3 — Rate limit 5/min/IP (6. istek 429)

Aynı IP'den 6 lead arka arkaya gönder; 6. istek 429 dönmeli.

```bash
for i in 1 2 3 4 5 6; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST https://tradiaturkey.com/api/lead \
    -H "Content-Type: application/json" \
    -H "Origin: https://tradiaturkey.com" \
    -d "{\"tip\":\"rapor\",\"email\":\"rl${i}@test.com\",\"il\":\"İstanbul\",\"dil\":\"tr\",\"kaynak\":\"test_ratelimit\",\"kvkk_onay\":true}")
  echo "İstek $i: HTTP $STATUS"
done
```

**Beklenen çıktı:**
```
İstek 1: HTTP 200
İstek 2: HTTP 200
İstek 3: HTTP 200
İstek 4: HTTP 200
İstek 5: HTTP 200
İstek 6: HTTP 429
```

**Temizlik (10 dakika sonra rate window otomatik temizler, ya da):**
```bash
wrangler d1 execute tradia_leads_v1 --command "DELETE FROM rate_limit;"
wrangler d1 execute tradia_leads_v1 --command "DELETE FROM leads WHERE kaynak='test_ratelimit';"
```

---

## Test 4 — KVKK opt-in eksikse 400 reddi

`kvkk_onay: false` ya da hiç gönderilmemişse backend kayıt yapmamalı.

```bash
echo "== kvkk_onay: false =="
curl -s -X POST https://tradiaturkey.com/api/lead \
  -H "Content-Type: application/json" \
  -H "Origin: https://tradiaturkey.com" \
  -d '{
    "tip": "rapor",
    "email": "nokvkk@test.com",
    "il": "İstanbul",
    "dil": "tr",
    "kvkk_onay": false
  }' | jq

echo "== kvkk_onay alanı yok =="
curl -s -X POST https://tradiaturkey.com/api/lead \
  -H "Content-Type: application/json" \
  -H "Origin: https://tradiaturkey.com" \
  -d '{
    "tip": "rapor",
    "email": "nokvkk2@test.com",
    "il": "İstanbul",
    "dil": "tr"
  }' | jq
```

**Beklenen:** Her iki istekte de HTTP 400 + `{ "ok": false, "err": "kvkk_onay_required" }` veya benzeri.

**Doğrulama:** DB'de bu iki email kaydı OLMAMALI.
```bash
wrangler d1 execute tradia_leads_v1 --command \
  "SELECT * FROM leads WHERE email IN ('nokvkk@test.com','nokvkk2@test.com');"
```
0 satır.

---

## Test 5 — /api/kvkk-sil endpoint (Article 7)

Test verisi sil. ADMIN_KEY gerekli.

```bash
ADMIN_KEY="<DEPLOY.md adım 5'te set ettiğin değer>"

curl -X POST https://tradiaturkey.com/api/kvkk-sil \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{
    "email": "ahmet.testtr@gmail.com"
  }' | jq
```

**Beklenen:** `{ "ok": true, "silinen": <int>, "audit_id": <int> }`.

**Doğrulama:**
```bash
wrangler d1 execute tradia_leads_v1 --command \
  "SELECT * FROM leads WHERE email='ahmet.testtr@gmail.com';"
# 0 satır olmalı

wrangler d1 execute tradia_leads_v1 --command \
  "SELECT * FROM kvkk_silme WHERE email='ahmet.testtr@gmail.com';"
# 1 audit satırı olmalı
```

---

## Test 6 — Son 24 saatlik leads dump

```bash
wrangler d1 execute tradia_leads_v1 --command \
  "SELECT id, ts, tip, dil, email, il, mahalle, kaynak FROM leads
   WHERE ts >= datetime('now','-24 hours')
   ORDER BY ts DESC;"
```

Tüm Test 1 + Test 2 satırlarını görmelisin (Test 5 sildiyse o satır eksik olur).

---

## Temizlik (testler bittikten sonra)

```bash
wrangler d1 execute tradia_leads_v1 --command "DELETE FROM leads WHERE kaynak LIKE 'test_%';"
wrangler d1 execute tradia_leads_v1 --command "DELETE FROM comments WHERE body LIKE 'Test yorumu%';"
wrangler d1 execute tradia_leads_v1 --command "DELETE FROM rate_limit WHERE bucket_min < strftime('%Y%m%d%H%M','now','-1 hour');"
```

Audit log (`kvkk_silme`) silinmesin — KVKK compliance gereği saklı.

---

## Pass/Fail Kriterleri

| Test | Pass koşulu |
|---|---|
| 1 | 4 lead kaydı, 4 farklı dil, ip_hash dolu |
| 2 | 4 yorum kaydı, trend kolonu doğru CHECK uyuyor |
| 3 | 6. istek HTTP 429 |
| 4 | kvkk_onay eksik/false → HTTP 400, DB'de kayıt yok |
| 5 | Lead silindi, audit kaydı oluştu |
| 6 | Son 24h dump → tüm test verisi görünüyor |

Hepsi pass ise: Sprint 7 → vector tiles + Sayı 6 lansman.
