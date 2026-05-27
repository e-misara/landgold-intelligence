-- ============================================================================
-- Tradia Lead Backend — D1 Admin Queries (Sprint 6)
-- Wrangler ile çalıştır: wrangler d1 execute tradia_leads_v1 --command "..."
-- veya SQL dosyasını: wrangler d1 execute tradia_leads_v1 --file=this.sql
-- ============================================================================

-- ============================================================================
-- 1. RAPOR SORGULARI
-- ============================================================================

-- Toplam lead sayısı + tip dağılımı
SELECT tip, COUNT(*) AS sayi
FROM leads
GROUP BY tip
ORDER BY sayi DESC;

-- Dil dağılımı (i18n etkisi gözlem)
SELECT dil, COUNT(*) AS sayi
FROM leads
GROUP BY dil
ORDER BY sayi DESC;

-- Son 24 saatlik aktivite
SELECT id, ts, tip, dil, email, il, mahalle, kaynak
FROM leads
WHERE ts >= datetime('now','-24 hours')
ORDER BY ts DESC;

-- Son 7 günlük günlük lead sayısı
SELECT DATE(ts) AS gun, COUNT(*) AS lead_sayisi
FROM leads
WHERE ts >= datetime('now','-7 days')
GROUP BY gun
ORDER BY gun DESC;

-- En çok talep alan iller (TOP 10)
SELECT il, COUNT(*) AS sayi
FROM leads
WHERE il IS NOT NULL
GROUP BY il
ORDER BY sayi DESC
LIMIT 10;

-- En çok talep alan mahalleler (Bursa Mudanya odak)
SELECT mahalle, COUNT(*) AS sayi
FROM leads
WHERE mahalle IS NOT NULL
GROUP BY mahalle
ORDER BY sayi DESC
LIMIT 15;

-- Yorum trend dağılımı (Mudanya 4 mahalle)
SELECT mahalle_slug, trend, COUNT(*) AS sayi
FROM comments
GROUP BY mahalle_slug, trend
ORDER BY mahalle_slug, sayi DESC;

-- KVKK silme log (Article 7 audit trail)
SELECT id, ts, email, silinen_lead_sayisi, silinen_yorum_sayisi
FROM kvkk_silme
ORDER BY ts DESC
LIMIT 50;


-- ============================================================================
-- 2. RATE LIMIT MONITORING
-- ============================================================================

-- Aktif rate limit kovaları (son 5 dk)
SELECT ip_hash, bucket_min, count, endpoint
FROM rate_limit
WHERE bucket_min >= strftime('%Y%m%d%H%M','now','-5 minutes')
ORDER BY count DESC;

-- 5/min limit aşan IP'ler (suspicious)
SELECT ip_hash, bucket_min, count, endpoint
FROM rate_limit
WHERE count >= 5
ORDER BY bucket_min DESC, count DESC
LIMIT 50;


-- ============================================================================
-- 3. KVKK COMPLIANCE
-- ============================================================================

-- Opt-in olmayanları bul (olmamalı, KVKK ihlali sinyali)
SELECT id, ts, email, dil, kvkk_onay
FROM leads
WHERE kvkk_onay = 0 OR kvkk_onay IS NULL
LIMIT 100;

-- Bir email için tüm kayıtları çek (Article 15 — veri erişim hakkı)
-- Email'i parametre olarak değiştir
SELECT 'lead' AS tip, id, ts, tip AS lead_tip, email, il, mahalle, dil, kaynak
FROM leads WHERE email = 'XXXXX@XXXXX.com'
UNION ALL
SELECT 'yorum' AS tip, id, ts, trend AS lead_tip, NULL AS email, il, ilce AS mahalle, NULL AS dil, mahalle_slug AS kaynak
FROM comments WHERE 1=0  -- yorumlar emaile bağlı değil
ORDER BY ts DESC;


-- ============================================================================
-- 4. TEMİZLİK (test verisi sil, audit korunur)
-- ============================================================================

-- Test verisini sil (kaynak LIKE 'test_%')
DELETE FROM leads WHERE kaynak LIKE 'test_%';
DELETE FROM comments WHERE body LIKE 'Test yorumu%';
DELETE FROM rate_limit WHERE bucket_min < strftime('%Y%m%d%H%M','now','-1 hour');

-- 90 günden eski rate limit kayıtları (KVKK retention)
DELETE FROM rate_limit WHERE bucket_min < strftime('%Y%m%d%H%M','now','-90 days');

-- ÖNEMLİ: kvkk_silme tablosu SİLİNMEZ (audit log).


-- ============================================================================
-- 5. BACKUP DUMP (CSV export için)
-- ============================================================================
-- wrangler d1 export tradia_leads_v1 --output=backup.sql --remote
-- veya selective:
-- SELECT * FROM leads;  → JSON çıktı → manuel kayıt
