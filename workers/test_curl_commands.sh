#!/bin/bash
# Tradia Lead Backend — Test Curl Commands
# Sprint 6 — copy-paste ready test suite
# Önkoşul: workers/DEPLOY.md tamamlanmış, /api/health 200 dönüyor
#
# Kullanım:
#   chmod +x test_curl_commands.sh
#   export ADMIN_KEY="<DEPLOY.md adım 5'teki değer>"
#   ./test_curl_commands.sh

set -e

BASE="https://tradiaturkey.com/api"
ORIGIN="https://tradiaturkey.com"
PASS=0
FAIL=0

renkli() { printf "\033[1;%sm%s\033[0m\n" "$1" "$2"; }
pass()  { renkli 32 "  ✓ PASS: $1"; PASS=$((PASS+1)); }
fail()  { renkli 31 "  ✗ FAIL: $1"; FAIL=$((FAIL+1)); }
basla() { renkli 36 "\n=== $1 ==="; }

# ---------------------------------------------------------------------------
basla "0. Health check"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health")
[ "$HEALTH" = "200" ] && pass "/api/health → 200" || fail "/api/health → $HEALTH"

# ---------------------------------------------------------------------------
basla "1. /api/lead POST — 4 dilde 4 persona"

leadtest() {
  local label="$1" payload="$2"
  HTTP=$(curl -s -o /tmp/lead_resp.json -w "%{http_code}" \
    -X POST "$BASE/lead" \
    -H "Content-Type: application/json" -H "Origin: $ORIGIN" \
    -d "$payload")
  if [ "$HTTP" = "200" ]; then
    pass "$label → 200 ($(cat /tmp/lead_resp.json))"
  else
    fail "$label → $HTTP ($(cat /tmp/lead_resp.json))"
  fi
}

leadtest "TR Arnavutköy rapor"  '{"tip":"rapor","email":"ahmet.testtr@gmail.com","ad":"Ahmet Yılmaz","il":"İstanbul","mahalle":"Arnavutköy","dil":"tr","kaynak":"test_sprint6","kvkk_onay":true}'
leadtest "EN Bursa city_report" '{"tip":"city_report","email":"john.testen@example.com","ad":"John Smith","il":"Bursa","dil":"en","kaynak":"test_sprint6","kvkk_onay":true}'
leadtest "RU Antalya waitlist"  '{"tip":"waitlist","email":"ivan.testru@example.ru","ad":"Иван Иванов","il":"Antalya","dil":"ru","kaynak":"test_sprint6","kvkk_onay":true}'
leadtest "DE Mudanya rapor"     '{"tip":"rapor","email":"hans.testde@example.de","ad":"Hans Müller","il":"Bursa","mahalle":"Mudanya / Burgaz","dil":"de","kaynak":"test_sprint6","kvkk_onay":true}'

# ---------------------------------------------------------------------------
basla "2. /api/yorum POST — Mudanya 4 mahalle"

yorumtest() {
  local slug="$1" trend="$2"
  HTTP=$(curl -s -o /tmp/y_resp.json -w "%{http_code}" \
    -X POST "$BASE/yorum" \
    -H "Content-Type: application/json" -H "Origin: $ORIGIN" \
    -d "{\"mahalle_slug\":\"$slug\",\"il\":\"Bursa\",\"ilce\":\"Mudanya\",\"trend\":\"$trend\",\"body\":\"Test yorumu — Sprint 6 sim. $slug.\",\"kvkk_onay\":true}")
  [ "$HTTP" = "200" ] && pass "yorum $slug ($trend) → 200" || fail "yorum $slug → $HTTP"
  sleep 1
}

yorumtest "mudanya-burgaz"   "yukseliste"
yorumtest "mudanya-mirza"    "stabil"
yorumtest "mudanya-yeni"     "dususte"
yorumtest "mudanya-celepkoy" "stabil"

# ---------------------------------------------------------------------------
basla "3. Rate limit — 6. istek 429 olmalı"

rl_pass=true
for i in 1 2 3 4 5 6; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/lead" \
    -H "Content-Type: application/json" -H "Origin: $ORIGIN" \
    -d "{\"tip\":\"rapor\",\"email\":\"rl${i}@test.com\",\"il\":\"İstanbul\",\"dil\":\"tr\",\"kaynak\":\"test_ratelimit\",\"kvkk_onay\":true}")
  echo "  istek $i → HTTP $STATUS"
  if [ "$i" -le 5 ] && [ "$STATUS" != "200" ]; then rl_pass=false; fi
  if [ "$i" = "6" ] && [ "$STATUS" != "429" ]; then rl_pass=false; fi
done
$rl_pass && pass "Rate limit doğru: ilk 5 → 200, 6. → 429" || fail "Rate limit beklenmedik davranış"

# ---------------------------------------------------------------------------
basla "4. KVKK opt-in eksikse 400"

HTTP1=$(curl -s -o /tmp/kvkk1.json -w "%{http_code}" -X POST "$BASE/lead" \
  -H "Content-Type: application/json" -H "Origin: $ORIGIN" \
  -d '{"tip":"rapor","email":"nokvkk@test.com","il":"İstanbul","dil":"tr","kvkk_onay":false}')
[ "$HTTP1" = "400" ] && pass "kvkk_onay:false → 400" || fail "kvkk_onay:false → $HTTP1 (beklenen 400)"

HTTP2=$(curl -s -o /tmp/kvkk2.json -w "%{http_code}" -X POST "$BASE/lead" \
  -H "Content-Type: application/json" -H "Origin: $ORIGIN" \
  -d '{"tip":"rapor","email":"nokvkk2@test.com","il":"İstanbul","dil":"tr"}')
[ "$HTTP2" = "400" ] && pass "kvkk_onay eksik → 400" || fail "kvkk_onay eksik → $HTTP2 (beklenen 400)"

# ---------------------------------------------------------------------------
basla "5. KVKK silme (/api/kvkk-sil) — Article 7"

if [ -z "$ADMIN_KEY" ]; then
  fail "ADMIN_KEY env yok — Test 5 atlandı (export ADMIN_KEY=...)"
else
  HTTP=$(curl -s -o /tmp/sil.json -w "%{http_code}" -X POST "$BASE/kvkk-sil" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Key: $ADMIN_KEY" \
    -d '{"email":"ahmet.testtr@gmail.com"}')
  if [ "$HTTP" = "200" ]; then
    pass "kvkk-sil → 200 ($(cat /tmp/sil.json))"
  else
    fail "kvkk-sil → $HTTP ($(cat /tmp/sil.json))"
  fi
fi

# ---------------------------------------------------------------------------
basla "6. /api/stats — son 24h sayım"

curl -s "$BASE/stats" -H "X-Admin-Key: $ADMIN_KEY" | head -c 500
echo ""

# ---------------------------------------------------------------------------
basla "ÖZET"
renkli 32 "Pass: $PASS"
renkli 31 "Fail: $FAIL"

[ "$FAIL" = "0" ] && exit 0 || exit 1
