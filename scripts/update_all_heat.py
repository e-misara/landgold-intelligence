"""
Tüm ilçeler için ısı + projeksiyon yeniden hesapla.
Günlük çalışır (08:15 TR).
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.heat_calculator import HeatCalculator
from services.price_projector import PriceProjector

TR = ZoneInfo("Europe/Istanbul")


def main() -> None:
    heat = HeatCalculator()
    proj = PriceProjector()

    db_path = Path("data/research/turkiye_il_ilce.json")
    if not db_path.exists():
        print(f"❌ {db_path} bulunamadı")
        sys.exit(1)

    with db_path.open("r", encoding="utf-8") as f:
        ilceler = json.load(f)

    isi_data: dict = {}
    proj_data: dict = {}
    sayac = 0
    hatalar = 0

    for il_kodu, il_info in ilceler.get("iller", {}).items():
        for ilce in il_info.get("ilceler", []):
            kod = f"{il_kodu}-{ilce}"

            try:
                temp = heat.get_temperature(kod)
                isi_data[kod] = {
                    "isi": temp["mevcut_isi"],
                    "tarihsel_ort": temp["tarihsel_ortalama"],
                    "sicaklik": temp["sicaklik_orani"],
                    "seviye": temp["seviye"],
                }
                proj_data[kod] = {
                    "3_ay": proj.project(kod, 3),
                    "12_ay": proj.project(kod, 12),
                }
                sayac += 1
            except Exception as e:
                hatalar += 1
                if hatalar <= 5:  # İlk 5 hatayı yazdır
                    print(f"⚠️  {kod}: {e}")

    output_dir = Path("data/havuz")
    output_dir.mkdir(parents=True, exist_ok=True)

    isi_path = output_dir / "ilce_isi_son_6_ay.json"
    isi_path.write_text(
        json.dumps(isi_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    proj_path = output_dir / "ilce_projeksiyon.json"
    proj_path.write_text(
        json.dumps(proj_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"✅ {sayac} ilçe güncellendi")
    print(f"⚠️  {hatalar} hata")
    print(f"📁 {isi_path}")
    print(f"📁 {proj_path}")
    print(f"🕐 {datetime.now(TR).isoformat()}")


if __name__ == "__main__":
    main()
