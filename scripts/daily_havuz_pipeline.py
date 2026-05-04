"""
Tradia Havuz Pipeline — Günlük Akış

Sıra:
1. Yeni haberleri çek (NewsAgent)
2. Sınıflandır + havuza yaz (ResearchAgent)
3. Isı hesapla (HeatCalculator)
4. Havuz özet yaz (havuz_summary.json)
5. Signal log

Hata toleransı: her aşama bağımsız try/except
"""
import json
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.append_signal import append_signal

TR = ZoneInfo("Europe/Istanbul")


def run_daily_pipeline(dry_run: bool = False) -> dict:
    """
    Ana pipeline. Günde 1 kez çalışır.
    Returns: {"success": bool, "stages": {...}, "errors": [...]}
    """
    from agents.news_agent import NewsAgent
    from agents.research_agent import ResearchAgent

    bugun = datetime.now(TR)
    sonuc = {
        "started_at": bugun.isoformat(),
        "dry_run": dry_run,
        "stages": {},
        "errors": [],
    }

    # AŞAMA 1: Haber çekme
    new_news = []
    try:
        news_agent = NewsAgent()
        new_news = news_agent.fetch_today()
        sonuc["stages"]["fetch"] = {"status": "ok", "count": len(new_news)}
        append_signal("pipeline_stage", stage="fetch", count=len(new_news))
    except Exception as e:
        sonuc["stages"]["fetch"] = {"status": "error", "message": str(e)}
        sonuc["errors"].append({"stage": "fetch", "error": str(e)})
        new_news = []

    # AŞAMA 2: Sınıflandırma (sadece dry_run=False ve haber varsa)
    if new_news and not dry_run:
        try:
            research = ResearchAgent()
            classified_result = research.process_news_pool(new_news)
            sonuc["stages"]["classify"] = {"status": "ok", **classified_result}
            append_signal(
                "pipeline_stage",
                stage="classify",
                classified=classified_result["classified"],
            )
        except Exception as e:
            sonuc["stages"]["classify"] = {"status": "error", "message": str(e)}
            sonuc["errors"].append({
                "stage": "classify",
                "error": str(e),
                "trace": traceback.format_exc()[:500],
            })

    # AŞAMA 3: Isı hesabı
    try:
        from scripts.update_all_heat import main as update_heat_main
        if not dry_run:
            update_heat_main()
        sonuc["stages"]["heat"] = {"status": "ok"}
        append_signal("pipeline_stage", stage="heat")
    except Exception as e:
        sonuc["stages"]["heat"] = {"status": "error", "message": str(e)}
        sonuc["errors"].append({"stage": "heat", "error": str(e)})

    # AŞAMA 4: Havuz özet (status.json için ham veri)
    try:
        if not dry_run:
            write_havuz_summary()
        sonuc["stages"]["summary"] = {"status": "ok"}
    except Exception as e:
        sonuc["stages"]["summary"] = {"status": "error", "message": str(e)}
        sonuc["errors"].append({"stage": "summary", "error": str(e)})

    # Kapanış
    sonuc["finished_at"] = datetime.now(TR).isoformat()
    sonuc["success"] = len(sonuc["errors"]) == 0

    duration = (datetime.now(TR) - bugun).total_seconds()
    if sonuc["success"]:
        append_signal(
            "pipeline_complete",
            stages_ok=len(sonuc["stages"]),
            duration_s=round(duration, 1),
        )
    else:
        append_signal(
            "pipeline_partial",
            errors_count=len(sonuc["errors"]),
            stages_ok=sum(
                1 for s in sonuc["stages"].values() if s.get("status") == "ok"
            ),
        )

    return sonuc


def write_havuz_summary() -> None:
    """
    En sıcak 5 ilçe + son 24h haber sayısı.
    update_status.py bu dosyayı okuyup status.json'a entegre eder.
    """
    isi_path = Path("data/havuz/ilce_isi_son_6_ay.json")
    summary_path = Path("data/havuz/havuz_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    top5 = []
    if isi_path.exists():
        isi_data = json.loads(isi_path.read_text(encoding="utf-8"))
        sorted_ilceler = sorted(
            isi_data.items(),
            key=lambda x: x[1].get("sicaklik", 0),
            reverse=True,
        )
        top5 = [
            {
                "ilce": kod,
                "sicaklik": data.get("sicaklik"),
                "seviye": data.get("seviye"),
            }
            for kod, data in sorted_ilceler[:5]
        ]

    summary = {
        "schema_version": "1.0",
        "guncellenme": datetime.now(TR).isoformat(),
        "toplam_haber": count_total_news(),
        "son_24h_haber": count_recent_news(hours=24),
        "en_sicak_5_ilce": top5,
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def count_recent_news(hours: int = 24) -> int:
    """Son N saat içinde havuza eklenen haber sayısı"""
    havuz_path = Path("data/havuz/ilce_haber_havuzu.jsonl")
    if not havuz_path.exists():
        return 0

    cutoff = datetime.now(TR) - timedelta(hours=hours)
    count = 0
    with havuz_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                h = json.loads(line)
                ts_str = h.get("siniflandirma_zamani") or h.get("tarih_referansi")
                if not ts_str:
                    continue
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=TR)
                if ts > cutoff:
                    count += 1
            except (json.JSONDecodeError, ValueError):
                continue
    return count


def count_total_news() -> int:
    """Havuzdaki toplam haber sayısı"""
    havuz_path = Path("data/havuz/ilce_haber_havuzu.jsonl")
    if not havuz_path.exists():
        return 0
    with havuz_path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tradia günlük havuz pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Dosya yazma, simüle et")
    args = parser.parse_args()

    sonuc = run_daily_pipeline(dry_run=args.dry_run)
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    sys.exit(0 if sonuc["success"] else 1)
