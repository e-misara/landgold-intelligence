"""
Mevcut Tradia haber arşivini havuza al.
Bir kerelik bootstrap. Vezir tetikleyebilir veya manuel.

CLI:
    python scripts/bootstrap_havuz.py --assess-only
    python scripts/bootstrap_havuz.py --limit 5
    python scripts/bootstrap_havuz.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TR = ZoneInfo("Europe/Istanbul")

# Eski haber arşivi — NewsAgent'ın çıktısı
_ARCHIVE_PATH = Path("data/news/news_archive.json")

# İçerik uzunluğu eşiği: altı → başlık-only kabul
_MIN_CONTENT_LEN = 100


def assess_old_news() -> dict:
    """Eski haberleri tara: tam metin var mı, başlık-only mı?"""
    if not _ARCHIVE_PATH.exists():
        return {"error": f"Eski haber arşivi yok: {_ARCHIVE_PATH}"}

    try:
        raw = json.loads(_ARCHIVE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse hatası: {e}"}

    # Liste veya dict kabul
    eski = list(raw.values()) if isinstance(raw, dict) else raw

    with_full = [
        h for h in eski
        if len(h.get("metin") or h.get("content") or h.get("body") or "") >= _MIN_CONTENT_LEN
    ]
    title_only = [h for h in eski if h not in with_full]

    return {
        "toplam": len(eski),
        "tam_metin": len(with_full),
        "sadece_baslik": len(title_only),
        "ornekler": eski[:3],
    }


def classify_old_news(limit: Optional[int] = None, dry_run: bool = False) -> None:
    """
    Eski haberleri sınıflandır, havuza ekle.

    Args:
        limit: Max kaç haber işlensin (None = tümü)
        dry_run: True ise dosyaya yazma
    """
    from agents.news_classifier import NewsClassifier

    print("📋 Önce değerlendirme...")
    assessment = assess_old_news()
    print(json.dumps(assessment, ensure_ascii=False, indent=2))

    if assessment.get("error"):
        print(f"❌ {assessment['error']}")
        return

    if assessment["sadece_baslik"] > 0:
        print(
            f"⚠️  {assessment['sadece_baslik']} haber sadece başlık içeriyor "
            "(sınıflandırma kalitesi düşük olacak)"
        )

    raw = json.loads(_ARCHIVE_PATH.read_text(encoding="utf-8"))
    eski = list(raw.values()) if isinstance(raw, dict) else raw

    if limit:
        eski = eski[:limit]

    if not dry_run:
        onay = input(
            f"\n{len(eski)} haber işlenecek (~${len(eski) * 0.003:.2f}). Devam? [y/N]: "
        )
        if onay.strip().lower() != "y":
            print("İptal")
            return

    classifier = NewsClassifier()
    havuz_path = Path("data/havuz/ilce_haber_havuzu.jsonl")
    havuz_path.parent.mkdir(parents=True, exist_ok=True)

    classified = skipped = errors = 0

    for i, haber in enumerate(eski):
        if (i + 1) % 25 == 0:
            print(f"  İşleniyor: {i + 1}/{len(eski)}")

        # Alanları NewsClassifier formatına normalize et
        normalized = {
            "baslik": haber.get("baslik") or haber.get("title") or "",
            "kaynak": haber.get("kaynak") or haber.get("source") or "",
            "tarih": haber.get("tarih") or haber.get("date") or "",
            "metin": haber.get("metin") or haber.get("content") or haber.get("body") or "",
        }

        try:
            labeled = classifier.classify_news(normalized)

            if labeled.get("kategori") == "BELIRSIZ":
                skipped += 1
                continue
            if not labeled.get("ilce"):
                skipped += 1
                continue

            if not dry_run:
                with havuz_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(labeled, ensure_ascii=False) + "\n")

            classified += 1

        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  ⚠️  Hata ({i}): {e}")

    print(f"\n✅ Bootstrap tamamlandı:")
    print(f"   Sınıflandırılan: {classified}")
    print(f"   Atlanan (BELIRSIZ/ilçesiz): {skipped}")
    print(f"   Hata: {errors}")
    if not dry_run:
        print(f"   Tahmini maliyet: ~${len(eski) * 0.003:.2f}")
    else:
        print("   Dry-run: dosyaya yazılmadı")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tradia havuz bootstrap")
    parser.add_argument("--assess-only", action="store_true", help="Sadece değerlendir")
    parser.add_argument("--limit", type=int, help="Max kaç haber işlensin")
    parser.add_argument("--dry-run", action="store_true", help="Yazma yapma")
    args = parser.parse_args()

    if args.assess_only:
        result = assess_old_news()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        classify_old_news(limit=args.limit, dry_run=args.dry_run)
