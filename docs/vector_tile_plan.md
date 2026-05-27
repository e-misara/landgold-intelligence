# Tradia Maps — Vector Tile Geçişi · Sprint 7 Plan Belgesi

**Tarih:** 2026-05-27
**Sprint:** 6 (hazırlık) → Sprint 7 (uygulama)
**Hedef:** /map/ sayfasındaki 50 MB GeoJSON yükünü ~5 MB Mapbox Vector Tile (MVT/PBF) zemine taşımak.

---

## 1. Mevcut Durum (Sprint 6 sonu)

| Katman | Format | Boyut | Yükleme |
|---|---|---|---|
| iller.geojson | GeoJSON | 7.6 MB | hemen |
| ilceler.geojson | GeoJSON | 27 MB | lazy buton (~3 MB gzip) |
| mahalleler.geojson | GeoJSON | 15 MB | lazy buton + zoom≥12 (~2 MB gzip) |
| mega.geojson | GeoJSON | 16 KB | hemen |
| osb.geojson | GeoJSON | 108 KB | hemen |
| kisitli.geojson | GeoJSON | 12 KB | hemen |
| **Toplam** | | **~50 MB** | ~5 MB gzip transfer |

**Sorunlar:**
- Git repo bloat (50 MB GeoJSON history'de kalıcı)
- İlçeler katmanı yüklendiğinde tarayıcı RAM ~120 MB sıçrar
- Mobile cihazda mahalleler katmanı (3.797 feature) renderlama 800ms+ gecikme
- Zoom out edildiğinde Leaflet tüm polygonları tek tek SVG çizer

**Hedef:**
- Repo'dan büyük GeoJSON çıkarılır (git-filter-repo Sprint 7 sonu)
- Vector tile (MVT) → tile başına ~5 KB, zoom seviyesine göre çağrılır
- Mobile RAM <30 MB, scroll 60 fps

---

## 2. Tippecanoe — Üretim Komutu

[tippecanoe](https://github.com/felt/tippecanoe) Felt fork'u (eski Mapbox repo'sundan miras): GeoJSON → MBTiles vector tile dönüşümü için endüstri standardı.

### Kurulum (macOS)
```bash
brew install tippecanoe
tippecanoe --version  # 2.x+
```

### Komut · iller katmanı

```bash
cd ~/LandGold/docs/map/data
tippecanoe \
  --output=tiles/iller.mbtiles \
  --layer=iller \
  --minimum-zoom=0 --maximum-zoom=10 \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  --simplification=15 \
  --no-tile-compression \
  iller.geojson
```

**Açıklama:**
- `--minimum-zoom=0` → Türkiye tamamı zoom 0'da görünür
- `--maximum-zoom=10` → 10'un üstünde detay azalır (mahalle katmanı devralır)
- `--drop-densest-as-needed` → zoom düştükçe complex polygon basitleştirilir
- `--simplification=15` → Douglas-Peucker tolerance
- `--no-tile-compression` → çıktı gzip değil (Cloudflare zaten gzipliyor)

### Komut · ilçeler

```bash
tippecanoe \
  --output=tiles/ilceler.mbtiles \
  --layer=ilceler \
  --minimum-zoom=7 --maximum-zoom=12 \
  --drop-densest-as-needed \
  --simplification=10 \
  ilceler.geojson
```

### Komut · mahalleler

```bash
tippecanoe \
  --output=tiles/mahalleler.mbtiles \
  --layer=mahalleler \
  --minimum-zoom=11 --maximum-zoom=15 \
  --drop-densest-as-needed \
  --simplification=7 \
  --cluster-distance=2 \
  mahalleler.geojson
```

### Komut · birleşik (3 katman tek MBTiles)

```bash
tippecanoe \
  --output=tiles/tradia.mbtiles \
  -L iller:iller.geojson \
  -L ilceler:ilceler.geojson \
  -L mahalleler:mahalleler.geojson \
  --minimum-zoom=0 --maximum-zoom=15 \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  --simplification=12
```

Tahmini çıktı boyutu: ~5-7 MB MBTiles → ~5 MB serve.

### MBTiles → /tiles/{z}/{x}/{y}.pbf statik export

GitHub Pages MBTiles serve edemez (binary SQLite). İki yol:

**Yol A:** `mb-util` ile statik PBF dizinine export.
```bash
pip install mbutil
mb-util tiles/tradia.mbtiles docs/map/tiles --image_format=pbf
```
Çıktı: `docs/map/tiles/<z>/<x>/<y>.pbf` — Cloudflare gzip otomatik.

**Yol B:** MapTiler/Mapbox Studio'ya MBTiles upload, CDN URL al, frontend `mapboxgl.Map`'e ver.

---

## 3. MapTiler vs Self-host Karşılaştırması

| Kriter | MapTiler Cloud | Self-host (GitHub Pages) | Cloudflare R2 |
|---|---|---|---|
| **Setup** | Hesap aç, MBTiles upload | mbutil export, push | wrangler r2 create, upload |
| **Free tier** | 100K istek/ay (~5K kullanıcı) | sınırsız | 10 GB depolama + 1M GET/ay |
| **CDN** | Global (40+ POP) | global ama GH Pages yavaş | Cloudflare global |
| **Cache TTL** | 7 gün edge | belirsiz | 7 gün edge (Workers controlled) |
| **Custom domain** | $25/ay Plus plan | tradiaturkey.com hazır | tradiaturkey.com hazır |
| **API key gerekir mi?** | evet (kısıtlama+izleme) | hayır | gerekirse Workers ile |
| **MBTiles destek** | doğrudan | hayır (statik PBF dir) | hayır (statik PBF dir) |
| **Style customization** | Mapbox GL Style spec | local | local |
| **Aylık maliyet (10K aktif kullanıcı)** | $0 free tier | $0 | $0 (10 GB altında) |
| **Aylık maliyet (100K aktif kullanıcı)** | ~$25-40 | $0 | $0.36 (Class B 1M GET'in altında) |

### Önerilen yol (Sprint 7)

**1. faz · Self-host GitHub Pages:**
- `tippecanoe` → `mb-util` → `docs/map/tiles/`
- 3 katman, ~5 MB statik PBF
- Frontend `maplibre-gl` ya da `leaflet.vectorgrid` plugin
- Maliyet $0, sınırsız.

**2. faz (lansman dalga 2, kullanıcı >10K) · Cloudflare R2:**
- Workers ile tile router (`/tiles/{z}/{x}/{y}.pbf` → R2 fetch)
- Edge cache 7 gün
- Maliyet aylık <$1.

**MapTiler'a geç sadece:** Custom Mapbox Studio style + 3D building gerekirse. Şu an gereksinim yok.

---

## 4. Frontend Dönüşümü (Sprint 7)

### Leaflet → Maplibre GL (önerilen)

Leaflet'in MVT desteği yoktur (sadece plugin: `Leaflet.VectorGrid` deneysel). Maplibre native MVT renderer.

```html
<script src="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.css" rel="stylesheet">

<script>
const map = new maplibregl.Map({
  container: 'map',
  style: {
    version: 8,
    sources: {
      'osm': {
        type: 'raster',
        tiles: ['https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png'],
        tileSize: 256,
      },
      'tradia': {
        type: 'vector',
        tiles: ['https://tradiaturkey.com/map/tiles/{z}/{x}/{y}.pbf'],
        minzoom: 0, maxzoom: 15,
      },
    },
    layers: [
      { id: 'osm', type: 'raster', source: 'osm' },
      {
        id: 'iller-fill', type: 'fill', source: 'tradia', 'source-layer': 'iller',
        paint: {
          'fill-color': ['match', ['get', 'kapsama_renk'],
            'red', '#7f1d1d', 'yellow', '#854d0e', 'green', '#065f46', '#475569'],
          'fill-opacity': 0.45,
        },
      },
      { id: 'iller-line', type: 'line', source: 'tradia', 'source-layer': 'iller',
        paint: { 'line-color': '#94a3b8', 'line-width': 1 } },
      { id: 'ilceler-fill', type: 'fill', source: 'tradia', 'source-layer': 'ilceler',
        minzoom: 7, paint: { 'fill-color': '#64748b', 'fill-opacity': 0.12 } },
      { id: 'mahalleler-fill', type: 'fill', source: 'tradia', 'source-layer': 'mahalleler',
        minzoom: 11, paint: { 'fill-color': '#3b82f6', 'fill-opacity': 0.08 } },
    ],
  },
  center: [35.0, 39.2], zoom: 6,
  maxBounds: [[25, 35], [45.5, 43]],
});
</script>
```

Bursa Mudanya 4 mahalle vurgu marker'ı GeoJSON source olarak ayrı eklenir (eskisi gibi).

### Olası riskler

- Maplibre v4 → Leaflet'ten DOM event API farkı (popup, marker)
- Sprint 5 lead magnet modallarını taşımak gerekir (yeniden bağlama, fonk. değişmez)
- Mobile Safari'de WebGL crash raporları (Maplibre GL #4421); fallback Leaflet+GeoJSON tutulur

---

## 5. Storage Tahmini

### Cloudflare R2 (alternatif)

| Item | Sayı | Boyut |
|---|---|---|
| iller (z 0-10) | ~80 tile | ~400 KB |
| ilceler (z 7-12) | ~400 tile | ~1.8 MB |
| mahalleler (z 11-15) | ~600 tile | ~2.5 MB |
| **Toplam tile** | ~1.080 | **~4.7 MB** |

R2 fiyatlandırma:
- 0-10 GB depolama → ÜCRETSİZ
- Class A (write): 1M/ay ücretsiz
- Class B (read): 10M/ay ücretsiz

4.7 MB · 10.000 kullanıcı/ay · ortalama 50 tile = 500K read → ÜCRETSİZ.

### GitHub Pages (önerilen 1. faz)

- 1.080 küçük PBF dosya = repo ~5 MB ek
- GitHub Pages hard limit 1 GB site, 100K istek/ay yumuşak (gerçekte sıkıştırıyor değil)
- Cloudflare proxy önünde gzip aktif

**Karar:** Sprint 7'de GitHub Pages + self-host. Sprint 10+ ölçeklenince R2'ye taşı.

---

## 6. Sprint 7 — TODO Listesi

- [ ] `brew install tippecanoe` (ya da Docker `felt/tippecanoe`)
- [ ] `tippecanoe -L … --maximum-zoom=15 …` ile birleşik MBTiles üret
- [ ] `mb-util` ile `docs/map/tiles/<z>/<x>/<y>.pbf` export
- [ ] `docs/map/index.html` → maplibre-gl version (Leaflet kodu `index-leaflet-backup.html` olarak sakla)
- [ ] popup + lead magnet modallarını Maplibre event handler'larına bağla
- [ ] Mobile QA — iOS Safari, Android Chrome
- [ ] `docs/map/data/{ilceler,mahalleler}.geojson` → repo'dan kaldır (mega/osb/kisitli/iller GeoJSON KALIR, küçükler)
- [ ] Lighthouse skorunu yeniden ölç (hedef Performance ≥90)
- [ ] `git filter-repo --path docs/map/data/ilceler.geojson --invert-paths` ile history bloat'ı temizle (force push GEREK — Ahmet onayı)
- [ ] `docs/vector_tile_plan.md` → `docs/vector_tile_uygulama.md` (post-mortem)

---

## 7. Geri Dönüş Planı

Vector tile bozulursa:
1. `docs/map/index-leaflet-backup.html` dosyasını `index.html` adına geri yükle.
2. `docs/map/data/*.geojson` git tag `v6-pre-vector` üzerinden geri al.
3. Sprint 7 issue'sunu reopen et.

**Risk seviyesi:** orta. Frontend büyük rewrite ama veri kaybı yok (kaynak GeoJSON `~/landgold-agents/data/maps/` altında her zaman mevcut).

---

## 8. Referanslar

- Tippecanoe docs: <https://github.com/felt/tippecanoe>
- Maplibre GL Style spec: <https://maplibre.org/maplibre-style-spec/>
- Cloudflare R2 pricing: <https://www.cloudflare.com/products/r2/>
- MapTiler Cloud: <https://www.maptiler.com/cloud/>
- mb-util: <https://github.com/mapbox/mbutil>

---

*Hazırlayan: Sprint 6 (Tradia / CC-Site). Onay: Sprint 7 başında Ahmet.*
