"""
Haftalık bülten + projeksiyon güncelleme.
Pazartesi gece 23:00 UTC = Salı 02:00 TR çalışır.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.append_signal import append_signal

TR = ZoneInfo("Europe/Istanbul")


def run_weekly_pipeline() -> dict:
    """
    Haftalık pipeline. Salı sabahı çalışır.
    Returns: {"success": bool, "stages": {...}, "errors": [...]}
    """
    bugun = datetime.now(TR)
    sonuc = {
        "started_at": bugun.isoformat(),
        "stages": {},
        "errors": [],
    }

    # AŞAMA 1: Tüm projeksiyonları yenile
    try:
        update_all_projections()
        sonuc["stages"]["projections"] = {"status": "ok"}
        append_signal("weekly_stage", stage="projections")
    except Exception as e:
        sonuc["stages"]["projections"] = {"status": "error", "message": str(e)}
        sonuc["errors"].append({"stage": "projections", "error": str(e)})

    # AŞAMA 2: Bülten üret
    try:
        from agents.ceo_agent import CEOAgent
        ceo = CEOAgent()
        bulletin_result = ceo.generate_weekly_bulletin()
        sonuc["stages"]["bulletin"] = {"status": "ok", **bulletin_result}
        append_signal(
            "weekly_bulletin_generated",
            public_path=bulletin_result["public_bulletin"],
            top5=bulletin_result["top5_ilceler"],
        )
    except Exception as e:
        sonuc["stages"]["bulletin"] = {"status": "error", "message": str(e)}
        sonuc["errors"].append({"stage": "bulletin", "error": str(e)})

    sonuc["finished_at"] = datetime.now(TR).isoformat()
    sonuc["success"] = len(sonuc["errors"]) == 0
    return sonuc


def update_all_projections() -> None:
    """Tüm ilçeler için fiyat projeksiyonu yenile"""
    from services.price_projector import PriceProjector

    proj = PriceProjector()
    db_path = Path("data/research/turkiye_il_ilce.json")

    if not db_path.exists():
        raise FileNotFoundError(f"İlçe DB bulunamadı: {db_path}")

    ilceler = json.loads(db_path.read_text(encoding="utf-8"))
    proj_data: dict = {}
    hatalar = 0

    for il_kodu, il_info in ilceler.get("iller", {}).items():
        for ilce in il_info.get("ilceler", []):
            kod = f"{il_kodu}-{ilce}"
            try:
                proj_data[kod] = {
                    "3_ay": proj.project(kod, 3),
                    "12_ay": proj.project(kod, 12),
                }
            except Exception:
                hatalar += 1

    out_path = Path("data/havuz/ilce_projeksiyon.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(proj_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"✅ {len(proj_data)} ilçe projektısyonu güncellendi, {hatalar} hata")


if __name__ == "__main__":
    sonuc = run_weekly_pipeline()
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    sys.exit(0 if sonuc["success"] else 1)
