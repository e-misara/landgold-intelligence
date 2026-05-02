"""
Watchdog — Katman 1 İzleyici

Her saat çalışır. API çağrısı YOK, $0 maliyet.
Dosya yaşı ve HTTP kontrolü yapar.
Değişiklik varsa Orchestrator'ı tetikler.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

import requests
_PYTHON   = str(_BASE_DIR / ".venv" / "bin" / "python")


class WatchdogAgent:

    def __init__(self) -> None:
        self.triggers: list[tuple[str, str]] = []
        self.timestamp = datetime.now()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _file_age_hours(self, *glob_patterns: str) -> float:
        files: list[Path] = []
        for pattern in glob_patterns:
            files.extend(_BASE_DIR.glob(pattern))
        if not files:
            return 999.0
        latest = max(files, key=lambda f: f.stat().st_mtime)
        return (datetime.now().timestamp() - latest.stat().st_mtime) / 3600

    # ── Checks ─────────────────────────────────────────────────────────────

    def check_news_freshness(self) -> tuple[str, str] | None:
        age = self._file_age_hours("data/news/analyzed_*.json", "data/news/raw_*.json")
        if age > 12:
            return ("news", f"Son haber dosyası {age:.0f} saat eski")
        return None

    def check_property_freshness(self) -> tuple[str, str] | None:
        age = self._file_age_hours("data/properties/scored_*.json", "data/properties/raw_*.json")
        if age > 18:
            return ("property", f"Son property listing {age:.0f} saat eski")
        return None

    def check_site_health(self) -> tuple[str, str] | None:
        try:
            r = requests.head("https://tradiaturkey.com", timeout=10)
            if r.status_code != 200:
                return ("health", f"Site HTTP {r.status_code}")
            if r.elapsed.total_seconds() * 1000 > 3000:
                return ("health", f"Site yavaş: {r.elapsed.total_seconds()*1000:.0f}ms")
        except Exception as exc:
            return ("health", f"Site ulaşılamıyor: {exc}")
        return None

    def check_lead_pipeline(self) -> tuple[str, str] | None:
        leads_file = _BASE_DIR / "data" / "leads" / "leads.json"
        if not leads_file.exists():
            return None
        try:
            data = json.loads(leads_file.read_text(encoding="utf-8"))
            leads = data if isinstance(data, list) else data.get("leads", [])
            today = datetime.now().strftime("%Y-%m-%d")
            new_today = sum(1 for l in leads if str(l.get("created_date", "")).startswith(today))
            if new_today > 0:
                return ("outreach", f"{new_today} yeni lead bugün")
        except Exception:
            pass
        return None

    def check_pending_deploy(self) -> tuple[str, str] | None:
        marker = _BASE_DIR / "data" / "last_deploy.txt"
        if not marker.exists():
            return ("deploy", "Deploy hiç yapılmamış")
        try:
            last_deploy = datetime.fromisoformat(marker.read_text().strip())
            content_files = list((_BASE_DIR / "data").rglob("*.json"))
            new_count = sum(
                1 for f in content_files
                if datetime.fromtimestamp(f.stat().st_mtime) > last_deploy
            )
            if new_count > 3:
                return ("deploy", f"{new_count} dosya deploy bekliyor")
        except Exception:
            pass
        return None

    # ── Core ───────────────────────────────────────────────────────────────

    def run(self) -> list[tuple[str, str]]:
        checks = [
            self.check_news_freshness,
            self.check_property_freshness,
            self.check_site_health,
            self.check_lead_pipeline,
            self.check_pending_deploy,
        ]

        for check in checks:
            try:
                result = check()
                if result:
                    self.triggers.append(result)
            except Exception as exc:
                print(f"[WATCHDOG] Check hatası {check.__name__}: {exc}")

        # Log
        log_dir = _BASE_DIR / "logs" / "watchdog"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{self.timestamp.strftime('%Y-%m-%d')}.jsonl"
        entry = {
            "ts":            self.timestamp.isoformat(),
            "triggers":      self.triggers,
            "trigger_count": len(self.triggers),
        }
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

        if self.triggers:
            print(f"⚡ Watchdog {self.timestamp.strftime('%H:%M')} — {len(self.triggers)} tetikleme:")
            for kind, reason in self.triggers:
                print(f"   [{kind}] {reason}")
            self._invoke_orchestrator()
        else:
            print(f"✅ Watchdog {self.timestamp.strftime('%H:%M')} — değişiklik yok")

        return self.triggers

    def _invoke_orchestrator(self) -> None:
        trigger_str = ",".join(f"{k}:{v}" for k, v in self.triggers)
        try:
            subprocess.Popen(
                [_PYTHON, "-m", "agents.orchestrator",
                 "--triggered-by", "watchdog",
                 "--triggers",     trigger_str],
                cwd=str(_BASE_DIR),
            )
        except Exception as exc:
            print(f"[WATCHDOG] Orchestrator tetiklenemedi: {exc}")


if __name__ == "__main__":
    agent = WatchdogAgent()
    triggers = agent.run()
    sys.exit(0 if not triggers else 2)
