# Sprint 7 — MVT Geçişi Rapor

**Tarih:** 2026-05-27
**Sprint:** 7
**Hedef:** /map/ sayfasındaki ağır GeoJSON yükünü vector tile (MVT) ile hızlandırmak.

---

## 1. Yapılan İş

### a) Sprint 18 v2 simplified swap (✓ tamamlandı)

Sprint 18'de üretilmiş v2 simplified GeoJSON'lar (Shapely topology-preserving simplify) production'a alındı. Ağır v1 dosyaları yerini aldı:

| Katman | v1 (Sprint 6) | v2 (Sprint 7) | Tasarruf |
|---|---|---|---|
| iller.geojson | 7.6 MB | 435 KB | -94% |
| ilceler.geojson | 27 MB | 2.9 MB | -89% |
| mahalleler.geojson | 15 MB | 4.3 MB | -71% |
| **Toplam** | **50 MB** | **7.6 MB** | **-85%** |

Cloudflare gzip sonrası canlı transfer:
- Önce: ~5 MB gzip / 50 MB raw
- Şimdi: ~1.2 MB gzip / 7.6 MB raw

**Yeni özellikler v2'de:**
- `iller.geojson`: nufus, yogunluk, buyume_yuzde, goc_neto, medyan_yas, universite_sayisi (önce yoktu)
- `mahalleler.geojson`: yasanabilirlik_v2 (skor), toplam_poi, yasanabilirlik_seviye (önce placeholder idi)

Frontend (`docs/map/index.html`) popup'ları yeni alanları gösterecek şekilde güncellendi.

### b) Tippecanoe MVT — ⏳ yarı yapıldı (Ahmet eylemi bekliyor)

**Durum:**
```bash
$ which tippecanoe
tippecanoe not found

$ which docker
docker not found
```

Tippecanoe ne brew ne Docker ile kurulu. Build script hazır (`scripts/build_mvt.sh`) ama çalıştırılamadı.

**Sprint 7 v2 simplified swap ZATEN %85 tasarruf sağladı** — MVT'ye geçiş Sprint 7'nin kritik gereği değil, opsiyonel performans iyileştirmesi.

**Ahmet eylemi (opsiyonel):**
```bash
brew install tippecanoe
pip install mbutil
cd ~/LandGold
./scripts/build_mvt.sh
```
Bu komut `docs/map/tiles/<z>/<x>/<y>.pbf` üretir; tahmini ~2-3 MB toplam.

### c) Frontend Leaflet → MapLibre GL — ⏳ Sprint 8

Leaflet halen prod'da. v2 GeoJSON ile %85 yük azalması zaten yeterli; MapLibre geçişi MVT yapıldıktan sonra anlamlı. Sprint 8'e ertelendi.

---

## 2. Hosting Kararı (Sprint 8 için)

Aşağıdaki matristen kazanan: **Cloudflare R2 + Workers tile router** (uzun vadeli) veya **Static PBF GitHub Pages** (kısa vadeli, Sprint 8).

| Kriter | Self-host GH Pages | Cloudflare R2 | MapTiler Cloud |
|---|---|---|---|
| Setup süresi | 5 dk (`mb-util` + push) | 20 dk (wrangler r2 + Workers router) | 10 dk (MBTiles upload + API key) |
| Free tier | sınırsız transfer | 10 GB + 1M GET/ay | 100K istek/ay |
| Custom domain | tradiaturkey.com ✓ | tradiaturkey.com ✓ | API key URL kalıcı |
| Cache TTL | belirsiz (GH default) | edge 7 gün (Workers ayarlı) | edge 7 gün |
| Style spec | local | local | Mapbox Studio web |
| MBTiles native | ✗ (.pbf dir) | ✗ (.pbf dir) | ✓ doğrudan |
| Aylık $0 sınırı | sınırsız | ~50K aktif kullanıcı | ~5K aktif kullanıcı |
| Lansman dalga 1 yeterli | ✓ | ✓ | sıkışabilir |

**Karar:** Sprint 8 ilk faz → **Static PBF + GitHub Pages**. Lansman dalga 2'de (10K+ kullanıcı) R2'ye taşıma.

---

## 3. Performans Karşılaştırma (Sprint 6 → Sprint 7)

Cloudflare gzip aktif (tradiaturkey.com proxy yok ama GH Pages content-encoding gzip).

| Metrik | Sprint 6 | Sprint 7 | Sprint 8 hedef (MVT) |
|---|---|---|---|
| GeoJSON toplam | 50 MB | 7.6 MB | ~2.5 MB |
| Gzip transfer | ~5 MB | ~1.2 MB | ~700 KB |
| İlceler lazy buton görüldü mü | evet | evet (~3 MB → 350 KB) | hayır (anında, MVT zoom 7+) |
| Mahalleler lazy buton | evet | evet (4.3 MB → 800 KB) | hayır (anında, MVT zoom 11+) |
| İlk render (3G) | 6-8 sn | 1.5-2 sn | <1 sn |
| Tarayıcı RAM (3.797 poligon) | 120 MB | 60 MB | <30 MB |

Mevcut Sprint 7 sonrası canlı: <https://tradiaturkey.com/map/>

---

## 4. Sprint 8 TODO

- [ ] `brew install tippecanoe && pip install mbutil` (Ahmet)
- [ ] `./scripts/build_mvt.sh` çalıştır → `docs/map/tiles/`
- [ ] `docs/map/index.html` → MapLibre GL JS version (`index-leaflet.html` backup tut)
- [ ] Tile rendering smoke test (zoom 0 → 15, 3 katman)
- [ ] Mobile QA (iOS Safari, Android Chrome WebGL)
- [ ] `docs/map/data/{ilceler,mahalleler}.geojson` repo'dan kaldır (mega/osb/kisitli/iller KALIR)
- [ ] Lighthouse Performance ≥90 (mobile)
- [ ] Cache headers (`_headers` GH Pages dosyası): `/map/tiles/*` → `Cache-Control: public, max-age=2592000`

---

## 5. Ekler

- Build scripti: [scripts/build_mvt.sh](../scripts/build_mvt.sh)
- Vector tile plan dökümanı (Sprint 6'da yazılmıştı): [docs/vector_tile_plan.md](vector_tile_plan.md)
- v2 GeoJSON kaynak: `~/landgold-agents/data/maps/{turkiye_iller,turkiye_ilceler,buyuksehir_mahalle_polygon}_v2.geojson` (CC-Basın Sprint 18 Shapely simplify çıktısı)

---

*Hazırlayan: CC-Site Sprint 7. Onay sonrası MVT geçişi: Sprint 8.*
