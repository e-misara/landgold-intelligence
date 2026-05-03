"""
Migrate refah_endeksi.json to a single unified schema.

Old schema (il 0-32):
  gelir, istihdam, egitim, saglik, altyapi, guvenlik, cevre,
  sosyal_katilim, konut, yasam_memnuniyeti, kira_getiri_yuzde, grade

New schema (il 33-80):
  gelir_endeksi, egitim_endeksi, altyapi_endeksi, istihdam_endeksi,
  kira_getiri_endeksi, yatirim_cezbediciligi

Target (unified — new schema field names, ASCII only):
  il, refah_endeksi,
  gelir_endeksi, istihdam_endeksi, egitim_endeksi, altyapi_endeksi,
  kira_getiri_endeksi, yatirim_cezbediciligi
  + extra old-schema fields kept as supplementary: saglik, guvenlik,
    cevre, sosyal_katilim, konut, yasam_memnuniyeti

Idempotent: running twice produces the same result.
"""

from __future__ import annotations
import json
import shutil
from pathlib import Path

SOSYAL_DIR = Path(__file__).parent.parent / "data" / "research" / "sosyal"
SRC = SOSYAL_DIR / "refah_endeksi.json"
BAK = SOSYAL_DIR / "refah_endeksi.json.bak"

# Old name → new name mapping
RENAME_MAP = {
    "gelir":            "gelir_endeksi",
    "istihdam":         "istihdam_endeksi",
    "egitim":           "egitim_endeksi",
    "altyapi":          "altyapi_endeksi",
    "altyapı_endeksi":  "altyapi_endeksi",   # Turkish ı → ASCII i
    "kira_getiri_yuzde":"kira_getiri_endeksi",
    "grade":            "yatirim_cezbediciligi",
}

# Fields that belong to the unified core schema
CORE_FIELDS = {
    "il", "refah_endeksi",
    "gelir_endeksi", "istihdam_endeksi", "egitim_endeksi", "altyapi_endeksi",
    "kira_getiri_endeksi", "yatirim_cezbediciligi",
}

# Extra fields from old schema kept as supplementary (never deleted)
SUPPLEMENTARY = {"saglik", "guvenlik", "cevre", "sosyal_katilim", "konut", "yasam_memnuniyeti"}


def migrate_record(rec: dict) -> tuple[dict, list[str]]:
    """Return (migrated_record, list_of_changes)."""
    changes: list[str] = []
    out = dict(rec)

    for old, new in RENAME_MAP.items():
        if old in out:
            if new not in out:
                out[new] = out[old]
                changes.append(f"{old} → {new}")
            else:
                changes.append(f"{old} already covered by {new} (skipped)")
            del out[old]

    return out, changes


def validate(iller: list[dict]) -> list[str]:
    """Return list of validation errors."""
    errors: list[str] = []
    required = {"il", "refah_endeksi", "gelir_endeksi", "istihdam_endeksi",
                "egitim_endeksi", "altyapi_endeksi", "kira_getiri_endeksi",
                "yatirim_cezbediciligi"}
    for il in iller:
        missing = required - set(il.keys())
        if missing:
            errors.append(f"{il.get('il','?')}: missing {missing}")
        # Check no Turkish ı in any field name
        for k in il.keys():
            if "ı" in k:
                errors.append(f"{il.get('il','?')}: Turkish ı in field '{k}'")
    return errors


def main() -> None:
    print("=== refah_endeksi.json schema migration ===\n")

    # Backup
    shutil.copy2(SRC, BAK)
    print(f"Backup: {BAK}")

    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    iller = data["iller"]
    total = len(iller)
    print(f"Toplam il: {total}\n")

    converted = 0
    already_ok = 0
    all_changes: list[str] = []

    for i, rec in enumerate(iller):
        new_rec, changes = migrate_record(rec)
        iller[i] = new_rec
        if changes:
            converted += 1
            all_changes.append(f"  {rec.get('il','?')}: {', '.join(changes)}")
        else:
            already_ok += 1

    print(f"Dönüştürülen: {converted} il")
    print(f"Zaten doğru:  {already_ok} il")
    if all_changes:
        print("\nDeğişiklikler:")
        for line in all_changes:
            print(line)

    # Validate
    print("\n--- Validasyon ---")
    errors = validate(iller)
    if errors:
        print(f"HATA: {len(errors)} sorun bulundu:")
        for e in errors:
            print(f"  ! {e}")
        print("\nDosya kaydedilmedi — backup geri yüklenecek")
        shutil.copy2(BAK, SRC)
        raise SystemExit(1)
    else:
        print(f"OK — tüm {total} il standart şemaya uyuyor")

    # Update gostergeler to reflect new schema
    data["gostergeler"] = [
        "gelir_endeksi", "istihdam_endeksi", "egitim_endeksi", "altyapi_endeksi",
        "kira_getiri_endeksi", "yatirim_cezbediciligi"
    ]
    data["last_updated"] = "2026-05-03"

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nDosya güncellendi: {SRC}")

    # Show one sample record from each group
    print("\n--- Örnek kayıt (eski şemadan — Ankara) ---")
    for il in iller:
        if il["il"] == "Ankara":
            print(json.dumps(il, ensure_ascii=False, indent=2))
            break

    print("\n--- Örnek kayıt (yeni şemadan — Ağrı) ---")
    for il in iller:
        if il["il"] == "Ağrı":
            print(json.dumps(il, ensure_ascii=False, indent=2))
            break

    print("\n=== Migration tamamlandı ===")


if __name__ == "__main__":
    main()
