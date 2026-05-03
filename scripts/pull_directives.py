"""
Fetch Vezir directives from GitHub (HTTP, no git remote).
Processes new directives and logs them to vezir/signals.jsonl.

Run:
    python scripts/pull_directives.py            # fetch + process, no git
    python scripts/pull_directives.py --days 14  # look back 14 days
    python scripts/pull_directives.py --dry-run  # fetch only, no write

Requires (optional — graceful without):
    GITHUB_TOKEN_VEZIR_READ  env var (read-only PAT for gacbusiness repo)
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

TR = ZoneInfo("Europe/Istanbul")
BASE_DIR = Path(__file__).parent.parent
INBOX_PATH = BASE_DIR / "data" / "directives_inbox"
LAST_PROCESSED_FILE = BASE_DIR / "data" / "last_directive_processed.txt"

VEZIR_RAW_BASE = "https://raw.githubusercontent.com/e-misara/gacbusiness/main"
DIRECTIVES_PATH_TEMPLATE = "directives/tradia/{date}.json"


# ── HTTP fetch ─────────────────────────────────────────────────────────────

def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN_VEZIR_READ")
    return {"Authorization": f"Bearer {token}"} if token else {}


def fetch_directive(date_str: str) -> dict | None:
    """Fetch one day's directive file. Returns None if 404 or no token needed."""
    try:
        import requests
    except ImportError:
        print("⚠️  requests not installed", file=sys.stderr)
        return None

    url = f"{VEZIR_RAW_BASE}/{DIRECTIVES_PATH_TEMPLATE.format(date=date_str)}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=15)
        if resp.status_code == 404:
            return None
        if resp.status_code in (401, 403):
            print(f"⚠️  Auth error {resp.status_code} for {date_str} — check GITHUB_TOKEN_VEZIR_READ",
                  file=sys.stderr)
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"⚠️  Fetch error for {date_str}: {exc}", file=sys.stderr)
        return None


def fetch_recent(days_back: int = 7) -> list[dict]:
    today = datetime.now(TR).date()
    results = []
    for i in range(days_back):
        d = today - timedelta(days=i)
        payload = fetch_directive(d.strftime("%Y-%m-%d"))
        if payload:
            results.append(payload)
            print(f"  ✓ {d} — {len(payload.get('directives', []))} directive(s)")
        else:
            print(f"  · {d} — boş")
    return results


# ── Process ────────────────────────────────────────────────────────────────

def _last_processed() -> str | None:
    if LAST_PROCESSED_FILE.exists():
        val = LAST_PROCESSED_FILE.read_text(encoding="utf-8").strip()
        return val or None
    return None


def _save_last_processed(directive_id: str) -> None:
    LAST_PROCESSED_FILE.write_text(directive_id, encoding="utf-8")


def process_payloads(payloads: list[dict], dry_run: bool = False) -> int:
    """Process new directives. Returns count of new ones."""
    last_id = _last_processed()
    new_count = 0

    try:
        from scripts.append_signal import append_signal
        has_signal = True
    except Exception:
        has_signal = False

    # Flatten all directives, sorted by ID (chronological)
    all_directives: list[tuple[str, dict]] = []
    for payload in payloads:
        for d in payload.get("directives", []):
            did = d.get("id", "")
            if did:
                all_directives.append((did, d))

    all_directives.sort(key=lambda x: x[0])

    for did, d in all_directives:
        if last_id and did <= last_id:
            continue  # already processed

        priority = d.get("priority", "P2")
        title    = d.get("title", "")
        d_type   = d.get("type", "info")

        print(f"  [{priority}] {did}: {title[:60]}")

        if not dry_run:
            # Save to inbox
            INBOX_PATH.mkdir(parents=True, exist_ok=True)
            date_str = did[4:12]  # dir_20260503_001 → 20260503
            inbox_file = INBOX_PATH / f"{date_str}.json"
            existing = []
            if inbox_file.exists():
                try:
                    existing = json.loads(inbox_file.read_text(encoding="utf-8"))
                    if not isinstance(existing, list):
                        existing = [existing]
                except Exception:
                    existing = []
            existing.append(d)
            inbox_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                                  encoding="utf-8")

            if has_signal:
                append_signal("directive_received", directive_id=did, priority=priority)

            # Priority handling
            if priority == "P0":
                print(f"  🚨 P0 DIRECTIVE: {title}")
            elif priority == "P1":
                print(f"  ⚠️  P1 directive queued")

            if has_signal:
                append_signal("directive_processed", directive_id=did,
                              outcome="acknowledged", type=d_type)

            _save_last_processed(did)

        new_count += 1

    return new_count


# ── Main ───────────────────────────────────────────────────────────────────

def main(days_back: int = 7, dry_run: bool = False) -> None:
    token = os.environ.get("GITHUB_TOKEN_VEZIR_READ")
    if not token:
        print("ℹ️  GITHUB_TOKEN_VEZIR_READ yok — public repo veya token olmadan deneniyor")

    print(f"Son {days_back} gün Vezir directive fetch ediliyor...")
    payloads = fetch_recent(days_back)

    if not payloads:
        print("Yeni directive yok.")
        return

    print(f"\n{len(payloads)} gün directive bulundu. İşleniyor...")
    new = process_payloads(payloads, dry_run=dry_run)
    print(f"\n✓ {new} yeni directive işlendi.")
    if dry_run:
        print("(dry-run: dosya yazılmadı)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Kaç gün geriye bakılsın")
    parser.add_argument("--dry-run", action="store_true", help="Fetch et ama yazma")
    args = parser.parse_args()
    main(days_back=args.days, dry_run=args.dry_run)
