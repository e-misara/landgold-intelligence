#!/usr/bin/env python3
"""
Mega proje görsellerini WebP olarak optimize et.

Girdi: ~/Desktop/tradia_gorsel_arsiv/01_mega_projeler/{slug}/*.png
Çıktı:
  docs/images/mega/{slug}/01-thumb.webp  (400×250, Q70)
  docs/images/mega/{slug}/01-full.webp   (max 1600px, Q80)

Sadece thumb ekli olarak liste ekler. Aynı projede birden fazla görsel varsa
01, 02, 03 olarak numaralandırılır.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
KAYNAK = Path.home() / "Desktop" / "tradia_gorsel_arsiv" / "01_mega_projeler"
KAYNAK_EXTRA = {
    "_genel/kolaj": Path.home() / "Desktop" / "tradia_gorsel_arsiv" / "06_bulten_kapak" / "20260519_mega_kolaj_01.png",
    "_genel/saglik": Path.home() / "Desktop" / "tradia_gorsel_arsiv" / "07_tematik" / "20260520_saglik_genel_01.png",
}
HEDEF = ROOT / "docs" / "images" / "mega"

THUMB_SIZE = (400, 250)
THUMB_QUALITY = 70
FULL_MAX = 1600
FULL_QUALITY = 80


def make_variants(src: Path, slug_dir: Path, idx: int, force: bool = False):
    """idempotent: thumb ve full hedef varsa ve kaynaktan yeniyse skip."""
    slug_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = slug_dir / f"{idx:02d}-thumb.webp"
    full_path = slug_dir / f"{idx:02d}-full.webp"
    src_mtime = src.stat().st_mtime
    if not force and thumb_path.exists() and full_path.exists():
        if thumb_path.stat().st_mtime >= src_mtime and full_path.stat().st_mtime >= src_mtime:
            return {
                "src": str(src.relative_to(Path.home())),
                "thumb": str(thumb_path.relative_to(ROOT / "docs")),
                "full":  str(full_path.relative_to(ROOT / "docs")),
                "thumb_size": thumb_path.stat().st_size,
                "full_size":  full_path.stat().st_size,
                "orig_size":  src.stat().st_size,
                "skipped":    True,
            }

    img = Image.open(src).convert("RGB")

    # Thumb: cover-fit 400x250
    thumb = img.copy()
    tw, th = THUMB_SIZE
    src_ratio = thumb.width / thumb.height
    tgt_ratio = tw / th
    if src_ratio > tgt_ratio:
        new_w = int(thumb.height * tgt_ratio)
        left = (thumb.width - new_w) // 2
        thumb = thumb.crop((left, 0, left + new_w, thumb.height))
    else:
        new_h = int(thumb.width / tgt_ratio)
        top = (thumb.height - new_h) // 2
        thumb = thumb.crop((0, top, thumb.width, top + new_h))
    thumb = thumb.resize(THUMB_SIZE, Image.Resampling.LANCZOS)
    thumb.save(thumb_path, "WEBP", quality=THUMB_QUALITY, method=6)

    # Full: max 1600px width
    full = img.copy()
    if full.width > FULL_MAX:
        new_h = int(full.height * FULL_MAX / full.width)
        full = full.resize((FULL_MAX, new_h), Image.Resampling.LANCZOS)
    full.save(full_path, "WEBP", quality=FULL_QUALITY, method=6)

    return {
        "src":        str(src.relative_to(Path.home())),
        "thumb":      str(thumb_path.relative_to(ROOT / "docs")),
        "full":       str(full_path.relative_to(ROOT / "docs")),
        "thumb_size": thumb_path.stat().st_size,
        "full_size":  full_path.stat().st_size,
        "orig_size":  src.stat().st_size,
        "skipped":    False,
    }


def main():
    import sys
    force = "--force" in sys.argv
    HEDEF.mkdir(parents=True, exist_ok=True)
    rapor = {"projeler": {}, "ozet": {}}

    toplam_orig = toplam_thumb = toplam_full = 0
    proje_count = 0
    yeni = atlanan = 0

    # Mega proje klasörleri
    for slug_dir_src in sorted(KAYNAK.iterdir()):
        if not slug_dir_src.is_dir():
            continue
        pngs = sorted(slug_dir_src.glob("*.png"))
        if not pngs:
            continue
        slug = slug_dir_src.name
        slug_dir = HEDEF / slug
        proje_kayit = []
        for i, png in enumerate(pngs, 1):
            v = make_variants(png, slug_dir, i, force=force)
            if v.get("skipped"):
                atlanan += 1
                print(f"  [{slug}] {png.name} → atlandı (güncel)", flush=True)
            else:
                yeni += 1
                print(f"  [{slug}] {png.name} → optimize edildi", flush=True)
            proje_kayit.append(v)
            toplam_orig += v["orig_size"]
            toplam_thumb += v["thumb_size"]
            toplam_full += v["full_size"]
        rapor["projeler"][slug] = proje_kayit
        proje_count += 1

    # Ekstra görseller (genel) — idempotent
    for hedef_alt, src in KAYNAK_EXTRA.items():
        if not src.exists():
            continue
        slug_dir = HEDEF / hedef_alt.split("/")[0]
        suffix = hedef_alt.split("/")[1]
        thumb_path = slug_dir / f"{suffix}-thumb.webp"
        full_path = slug_dir / f"{suffix}-full.webp"
        src_mtime = src.stat().st_mtime
        if not force and thumb_path.exists() and full_path.exists() \
           and thumb_path.stat().st_mtime >= src_mtime and full_path.stat().st_mtime >= src_mtime:
            atlanan += 1
            print(f"  [{hedef_alt}] {src.name} → atlandı (güncel)", flush=True)
            toplam_orig += src.stat().st_size
            toplam_thumb += thumb_path.stat().st_size
            toplam_full += full_path.stat().st_size
            continue
        yeni += 1
        print(f"  [{hedef_alt}] {src.name} → optimize edildi", flush=True)
        img = Image.open(src).convert("RGB")
        slug_dir.mkdir(parents=True, exist_ok=True)
        thumb = img.copy()
        tw, th = THUMB_SIZE
        src_ratio = thumb.width / thumb.height
        tgt_ratio = tw / th
        if src_ratio > tgt_ratio:
            new_w = int(thumb.height * tgt_ratio)
            left = (thumb.width - new_w) // 2
            thumb = thumb.crop((left, 0, left + new_w, thumb.height))
        else:
            new_h = int(thumb.width / tgt_ratio)
            top = (thumb.height - new_h) // 2
            thumb = thumb.crop((0, top, thumb.width, top + new_h))
        thumb = thumb.resize(THUMB_SIZE, Image.Resampling.LANCZOS)
        thumb.save(thumb_path, "WEBP", quality=THUMB_QUALITY, method=6)
        full = img.copy()
        if full.width > FULL_MAX:
            new_h = int(full.height * FULL_MAX / full.width)
            full = full.resize((FULL_MAX, new_h), Image.Resampling.LANCZOS)
        full.save(full_path, "WEBP", quality=FULL_QUALITY, method=6)
        toplam_orig += src.stat().st_size
        toplam_thumb += thumb_path.stat().st_size
        toplam_full += full_path.stat().st_size

    rapor["ozet"] = {
        "proje_sayisi": proje_count,
        "toplam_orig_byte": toplam_orig,
        "toplam_thumb_byte": toplam_thumb,
        "toplam_full_byte": toplam_full,
        "toplam_orig_mb": round(toplam_orig / 1024 / 1024, 2),
        "toplam_thumb_mb": round(toplam_thumb / 1024 / 1024, 2),
        "toplam_full_mb": round(toplam_full / 1024 / 1024, 2),
        "kazanc_orani": round(1 - (toplam_thumb + toplam_full) / toplam_orig, 3),
    }

    # Rapor dosyası
    rapor_path = ROOT / "data" / "site" / "gorsel_optimize_rapor.json"
    rapor_path.parent.mkdir(parents=True, exist_ok=True)
    rapor_path.write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("✓ Optimize tamam")
    print(f"  Proje sayısı     : {proje_count}")
    print(f"  Yeni optimize    : {yeni} dosya")
    print(f"  Atlandı (güncel) : {atlanan} dosya")
    print(f"  Toplam orijinal  : {rapor['ozet']['toplam_orig_mb']} MB")
    print(f"  Thumb toplamı    : {rapor['ozet']['toplam_thumb_mb']} MB")
    print(f"  Full toplamı     : {rapor['ozet']['toplam_full_mb']} MB")
    print(f"  Toplam yeni      : {round((toplam_thumb + toplam_full)/1024/1024, 2)} MB")
    print(f"  Kazanç oranı     : %{rapor['ozet']['kazanc_orani']*100:.1f}")
    print(f"  Rapor: {rapor_path}")


if __name__ == "__main__":
    main()
