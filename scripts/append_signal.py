"""
Append a single event line to vezir/signals.jsonl.

Usage (from any agent or script):
    from scripts.append_signal import append_signal
    append_signal("deploy", status="success", url="https://...")
    append_signal("agent_run", agent="news_agent", output_count=23, duration_s=12)
    append_signal("error", agent="property_agent", message="sahibinden 403")

Thread-safe: uses file-level append (atomic on POSIX).
"""

from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TR = ZoneInfo("Europe/Istanbul")
SIGNALS_PATH = Path(__file__).parent.parent / "vezir" / "signals.jsonl"

VALID_TYPES = {
    "deploy", "agent_run", "error",
    "directive_received", "directive_processed",
    "data_ingested", "status_updated",
}


def append_signal(event_type: str, **fields) -> None:
    """Append one event line to vezir/signals.jsonl. Silently skips on error."""
    if event_type not in VALID_TYPES:
        print(f"[append_signal] unknown type '{event_type}', skipping", file=sys.stderr)
        return

    ts = datetime.now(TR).isoformat(timespec="seconds")
    entry = {"ts": ts, "type": event_type, **fields}

    try:
        SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SIGNALS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[append_signal] write failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    # Quick smoke test
    append_signal("agent_run", agent="test", output_count=0, duration_s=0)
    print(f"Signal written to {SIGNALS_PATH}")
    print("Last line:", SIGNALS_PATH.read_text(encoding="utf-8").strip().split("\n")[-1])
