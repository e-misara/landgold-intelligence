#!/bin/bash
# Tradia Maps — Tippecanoe MVT Build Script (Sprint 7)
# Önkoşul: tippecanoe + mb-util kurulu
#   macOS: brew install tippecanoe && pip install mbutil
#   Docker: docker pull klokantech/tippecanoe
#
# Kullanım:
#   ./scripts/build_mvt.sh        # native (tippecanoe in PATH)
#   USE_DOCKER=1 ./scripts/build_mvt.sh  # Docker fallback

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/docs/map/data"
OUT="$ROOT/docs/map/tiles"
TMP="$ROOT/docs/map/_mvt_tmp"

mkdir -p "$OUT" "$TMP"

renkli() { printf "\033[1;%sm%s\033[0m\n" "$1" "$2"; }
basla()  { renkli 36 "\n▸ $1"; }
ok()     { renkli 32 "  ✓ $1"; }
hata()   { renkli 31 "  ✗ $1"; exit 1; }

# ---------------------------------------------------------------------------
# Önkoşul kontrol
# ---------------------------------------------------------------------------
if [ "$USE_DOCKER" = "1" ]; then
  command -v docker >/dev/null || hata "docker bulunamadı (USE_DOCKER=1 modu)"
  TIP="docker run --rm -v $ROOT:/work klokantech/tippecanoe tippecanoe"
  MBU="docker run --rm -v $ROOT:/work --entrypoint mb-util klokantech/tippecanoe"
else
  command -v tippecanoe >/dev/null || hata "tippecanoe bulunamadı — brew install tippecanoe ya da USE_DOCKER=1"
  command -v mb-util    >/dev/null || hata "mb-util bulunamadı — pip install mbutil"
  TIP="tippecanoe"
  MBU="mb-util"
fi

# ---------------------------------------------------------------------------
# 1. Birleşik MBTiles üret (3 katman tek dosyada)
# ---------------------------------------------------------------------------
basla "Tippecanoe → birleşik tradia.mbtiles"

$TIP \
  --output="$TMP/tradia.mbtiles" \
  --force \
  -L iller:"$SRC/iller.geojson" \
  -L ilceler:"$SRC/ilceler.geojson" \
  -L mahalleler:"$SRC/mahalleler.geojson" \
  --minimum-zoom=0 --maximum-zoom=14 \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  --simplification=12 \
  --no-tile-compression

ok "MBTiles üretildi: $(du -h "$TMP/tradia.mbtiles" | cut -f1)"

# ---------------------------------------------------------------------------
# 2. MBTiles → /tiles/{z}/{x}/{y}.pbf statik export
# ---------------------------------------------------------------------------
basla "mb-util → static PBF dizini"

rm -rf "$OUT"
$MBU --image_format=pbf --silent "$TMP/tradia.mbtiles" "$OUT"

PBF_COUNT=$(find "$OUT" -name "*.pbf" | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "$OUT" | cut -f1)
ok "$PBF_COUNT tile dosyası, toplam $TOTAL_SIZE"

# ---------------------------------------------------------------------------
# 3. Cleanup + git ignore eski .geojson büyük dosyalar
# ---------------------------------------------------------------------------
basla "Sonraki adım (manuel)"
echo "  1. /map/index.html → maplibre-gl geçişi (vector_tile_plan.md adım 4)"
echo "  2. Test: python3 -m http.server 8080 -d $ROOT/docs  →  http://localhost:8080/map/"
echo "  3. Mobile QA (iOS Safari, Android Chrome)"
echo "  4. Onaylanırsa: git add docs/map/tiles/ && git rm docs/map/data/{iller,ilceler,mahalleler}.geojson"
echo "  5. Bütün katmanlar OK ise rm -rf $TMP"

renkli 32 "\n✓ MVT build tamam."
