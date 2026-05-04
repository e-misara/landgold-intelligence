"""
Write vezir/status.json with current system state.
Idempotent: only writes (and commits) when content changes.

Run:
    python scripts/update_status.py          # dry-run safe, no git
    python scripts/update_status.py --commit  # also git add + commit + push
"""

from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

TR = ZoneInfo("Europe/Istanbul")
BASE_DIR = Path(__file__).parent.parent
STATUS_PATH = BASE_DIR / "vezir" / "status.json"
DATA_PATH = BASE_DIR / "data"
LOGS_PATH = BASE_DIR / "logs"
DIRECTIVES_INBOX = DATA_PATH / "directives_inbox"
LAST_DIRECTIVE_FILE = DATA_PATH / "last_directive_processed.txt"


# ── Helpers ────────────────────────────────────────────────────────────────

def _latest_file(pattern: str) -> Path | None:
    files = sorted(glob.glob(str(DATA_PATH / pattern)))
    return Path(files[-1]) if files else None


def _mtime_dt(path: Path | None) -> str | None:
    if path and path.exists():
        return datetime.fromtimestamp(path.stat().st_mtime, tz=TR).isoformat(timespec="seconds")
    return None


def _errors_7d(agent_name: str) -> int:
    """Count lines with 'error' in the last 7 days of watchdog logs."""
    count = 0
    cutoff = datetime.now(TR) - timedelta(days=7)
    for log_file in sorted((LOGS_PATH / "watchdog").glob("*.jsonl")):
        try:
            date_str = log_file.stem  # 2026-05-03
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=TR)
            if file_date < cutoff:
                continue
            for line in log_file.read_text(encoding="utf-8").splitlines():
                if agent_name in line and "error" in line.lower():
                    count += 1
        except Exception:
            pass
    return count


def _site_uptime() -> tuple[str, str | None]:
    """Read last health log entry."""
    health_file = DATA_PATH / "dev" / "health_log.json"
    if not health_file.exists():
        return "unknown", None
    try:
        entries = json.loads(health_file.read_text(encoding="utf-8"))
        if isinstance(entries, list) and entries:
            last = entries[-1]
            return last.get("overall", "unknown"), last.get("checks", [{}])[0].get("checked_at")
        if isinstance(entries, dict):
            return entries.get("overall", "unknown"), None
    except Exception:
        pass
    return "unknown", None


def _last_deploy_at() -> str | None:
    """Infer last deploy time from scored property files or news files."""
    candidates = [
        _latest_file("properties/scored_*.json"),
        _latest_file("news/analyzed_*.json"),
    ]
    mtimes = [_mtime_dt(p) for p in candidates if p]
    return max(mtimes) if mtimes else None


def _pending_directives() -> tuple[list[str], str | None]:
    """Scan directives_inbox for IDs not yet processed."""
    last_processed = None
    if LAST_DIRECTIVE_FILE.exists():
        last_processed = LAST_DIRECTIVE_FILE.read_text(encoding="utf-8").strip() or None

    pending: list[str] = []
    if not DIRECTIVES_INBOX.exists():
        return pending, last_processed

    for f in sorted(DIRECTIVES_INBOX.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            for d in payload.get("directives", []):
                did = d.get("id", "")
                if did and did != last_processed:
                    pending.append(did)
        except Exception:
            pass
    return pending, last_processed


# ── Build status dict ──────────────────────────────────────────────────────

def build_status() -> dict:
    uptime_status, _ = _site_uptime()
    pending_dirs, last_dir = _pending_directives()

    news_file    = _latest_file("news/analyzed_*.json")
    prop_file    = _latest_file("properties/scored_*.json")
    leads_file   = _latest_file("leads/leads.json")

    # Agent output counts
    news_count = 0
    if news_file and news_file.exists():
        try:
            items = json.loads(news_file.read_text(encoding="utf-8"))
            news_count = len(items) if isinstance(items, list) else 0
        except Exception:
            pass

    prop_count = 0
    if prop_file and prop_file.exists():
        try:
            items = json.loads(prop_file.read_text(encoding="utf-8"))
            prop_count = len(items) if isinstance(items, list) else 0
        except Exception:
            pass

    return {
        "schema_version": "1.0",
        # last_updated filled at write time
        "system": {
            "deploy_status": "live" if uptime_status == "ok" else uptime_status,
            "last_deploy_at": _last_deploy_at(),
            "last_deploy_url": "https://e-misara.github.io/landgold-intelligence/",
            "uptime_check": uptime_status,
            "errors_24h": 0,
        },
        "agents": {
            "news_agent": {
                "status": "active" if news_file else "unknown",
                "last_run_at": _mtime_dt(news_file),
                "next_scheduled_at": None,
                "last_output_count": news_count,
                "errors_7d": _errors_7d("news"),
            },
            "property_agent": {
                "status": "active" if prop_file else "unknown",
                "last_run_at": _mtime_dt(prop_file),
                "data_source": "demo",
                "real_data_count": 0,
                "demo_data_count": prop_count,
                "errors_7d": _errors_7d("property"),
            },
            "ceo_agent": {
                "status": "active",
                "last_brief_at": _mtime_dt(_latest_file("reports/briefing_*.json")),
                "frequency": "daily",
            },
            "outreach_agent": {
                "status": "active" if leads_file else "unknown",
                "last_run_at": _mtime_dt(leads_file),
                "errors_7d": _errors_7d("outreach"),
            },
            "dev_agent": {
                "status": "active",
                "last_run_at": _mtime_dt(DATA_PATH / "dev" / "health_log.json"),
                "note": "",
            },
            "research_agent": {
                "status": "active",
                "last_run_at": None,
                "errors_7d": _errors_7d("research"),
            },
        },
        "metrics_7d": {
            "site_visits": 0,
            "unique_visitors": 0,
            "content_published": news_count,
            "leads_captured": 0,
            "affiliate_clicks": 0,
            "revenue_usd": 0,
        },
        "open_issues": [
            {
                "id": "P0_property_no_real_data",
                "priority": "P0",
                "title": "PropertyAgent gerçek veri kaynağı yok",
                "opened_at": "2026-05-02",
                "owner": "tradia",
                "blocked_by": None,
            }
        ],
        "pending_directives": pending_dirs,
        "last_directive_id_processed": last_dir,
        "notes_to_vezir": "",
    }

    # Havuz özet entegrasyonu — daily_havuz_pipeline.py tarafından üretilir
    havuz_summary_path = DATA_PATH / "havuz" / "havuz_summary.json"
    if havuz_summary_path.exists():
        try:
            havuz = json.loads(havuz_summary_path.read_text(encoding="utf-8"))
            status["havuz"] = {
                "toplam_haber": havuz.get("toplam_haber", 0),
                "son_24h_haber": havuz.get("son_24h_haber", 0),
                "en_sicak_5_ilce": havuz.get("en_sicak_5_ilce", []),
                "guncellenme": havuz.get("guncellenme"),
            }
        except Exception as e:
            import sys
            print(f"⚠️  Havuz summary okuma hatası: {e}", file=sys.stderr)

    return status


# ── Idempotent write ───────────────────────────────────────────────────────

def write_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def status_changed(new: dict) -> bool:
    """Return True if status content changed (ignores last_updated)."""
    if not STATUS_PATH.exists():
        return True
    try:
        old = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        def strip_ts(d: dict) -> dict:
            return {k: v for k, v in d.items() if k != "last_updated"}
        return strip_ts(new) != strip_ts(old)
    except Exception:
        return True


def update_status(do_commit: bool = False) -> bool:
    """Build + maybe write status. Returns True if written."""
    new_status = build_status()

    if not status_changed(new_status):
        print("ℹ️  Durum değişmedi, yazma atlandı")
        return False

    new_status["last_updated"] = datetime.now(TR).isoformat(timespec="seconds")
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(STATUS_PATH, new_status)
    print(f"✓ vezir/status.json güncellendi ({new_status['last_updated']})")

    try:
        from scripts.append_signal import append_signal
        append_signal("status_updated", deploy_status=new_status["system"]["deploy_status"])
    except Exception:
        pass

    if do_commit:
        _git_commit()

    return True


def _git_commit() -> None:
    try:
        subprocess.run(["git", "add", "vezir/status.json", "vezir/signals.jsonl"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", "status: hourly update [skip ci]"],
            cwd=BASE_DIR, capture_output=True, text=True,
        )
        if result.returncode == 0:
            subprocess.run(["git", "push"], cwd=BASE_DIR, check=True, capture_output=True)
            print("✓ git commit + push")
        else:
            print("ℹ️  git commit: nothing to commit")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  git error: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="git add + commit + push after write")
    args = parser.parse_args()
    sys.exit(0 if update_status(do_commit=args.commit) else 0)
