-- Tradia Lead Backend D1 SQLite Schema
-- Cloudflare D1: Worker'a bind edilir, ücretsiz tier 5 GB / 5M okuma/ay

-- ───────────────────────────────────────────────────────────────
-- Tablo 1: leads — rapor talepleri + waitlist + şehir raporu
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              TEXT    NOT NULL DEFAULT (datetime('now')),
  dil             TEXT    NOT NULL,                                          -- tr/en/ru/de/ar/fa/zh
  tip             TEXT    NOT NULL CHECK (tip IN ('rapor','sehir_raporu','waitlist','city_report')),
  email           TEXT    NOT NULL,
  ad              TEXT,                                                       -- opsiyonel
  mahalle         TEXT,                                                       -- rapor talebi için
  il              TEXT,                                                       -- sehir_raporu için
  kaynak          TEXT    NOT NULL DEFAULT 'map',                            -- map / landing-tr / landing-en / landing-XX
  user_agent      TEXT,
  ip_hash         TEXT,                                                       -- KVKK: ham IP saklanmaz, SHA-256(ip+salt)
  referer         TEXT,
  kvkk_onay       INTEGER NOT NULL DEFAULT 1                                  -- 1=onaylı (form submit edildi)
);

CREATE INDEX IF NOT EXISTS idx_leads_ts ON leads(ts DESC);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_dil_tip ON leads(dil, tip);

-- ───────────────────────────────────────────────────────────────
-- Tablo 2: comments — mahalle yorumları (yükselişte / stabil / düşüşte)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS comments (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              TEXT    NOT NULL DEFAULT (datetime('now')),
  mahalle         TEXT    NOT NULL,
  il              TEXT,
  ilce            TEXT,
  trend           TEXT    NOT NULL CHECK (trend IN ('yukseliste','stabil','dususte')),
  body            TEXT    CHECK (length(body) <= 280),                       -- 280 karakter limit
  ip_hash         TEXT,                                                       -- spam koruma + KVKK anonim
  user_agent      TEXT,
  onayli          INTEGER NOT NULL DEFAULT 1,                                 -- moderasyon flag (0=spam, 1=görünür)
  dil             TEXT
);

CREATE INDEX IF NOT EXISTS idx_comments_mahalle ON comments(mahalle);
CREATE INDEX IF NOT EXISTS idx_comments_ts ON comments(ts DESC);
CREATE INDEX IF NOT EXISTS idx_comments_trend ON comments(trend);

-- ───────────────────────────────────────────────────────────────
-- Tablo 3: rate_limit — IP başına dakika başı request sayacı
-- (Workers KV alternatifi: küçük ölçekte D1 yeterli)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rate_limit (
  ip_hash         TEXT    NOT NULL,
  minute_bucket   TEXT    NOT NULL,                                           -- "2026-05-27T12:34"
  count           INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (ip_hash, minute_bucket)
);

CREATE INDEX IF NOT EXISTS idx_rate_bucket ON rate_limit(minute_bucket);

-- ───────────────────────────────────────────────────────────────
-- Tablo 4: kvkk_silme — KVKK Madde 7 silme talepleri (audit log)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kvkk_silme (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              TEXT    NOT NULL DEFAULT (datetime('now')),
  email           TEXT    NOT NULL,
  silinen_kayit   INTEGER NOT NULL DEFAULT 0,                                 -- silinen satır sayısı
  ip_hash         TEXT,
  not_metni       TEXT                                                        -- talep gerekçesi (opsiyonel)
);

-- ───────────────────────────────────────────────────────────────
-- Cron temizlik: 60 dakikadan eski rate_limit kayıtları sil (haftalık)
-- (Wrangler cron trigger ile çalıştırılır)
-- DELETE FROM rate_limit WHERE minute_bucket < datetime('now', '-1 hour');
-- ───────────────────────────────────────────────────────────────
