"""
Orchestrator — Katman 2 Karar Verici

Watchdog tetiklerse veya manuel çağrılırsa çalışır.
Anthropic API ile sistem durumunu analiz eder.
Hangi ajanların çalışacağına karar verir ve tetikler.
Tek API çağrısı: ~$0.05/tetikleme.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

import anthropic
_PYTHON   = str(_BASE_DIR / ".venv" / "bin" / "python")
_MAIN     = str(_BASE_DIR / "main.py")

# Tahmini maliyet referansları (USD)
_AGENT_COSTS = {
    "news":     0.30,
    "property": 0.30,
    "outreach": 0.15,
    "deploy":   0.05,
}


class OrchestratorAgent:

    def __init__(self) -> None:
        from core.config import Config
        self._llm      = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.timestamp = datetime.now()
        self.executed: list[dict] = []

    # ── Context ────────────────────────────────────────────────────────────

    def gather_context(self, triggers: list[tuple[str, str]] | None = None) -> dict:
        context: dict = {
            "timestamp": self.timestamp.isoformat(),
            "triggers":  triggers or [],
            "data_status": {},
        }
        for folder in ("news", "properties", "leads"):
            path = _BASE_DIR / "data" / folder
            if path.exists():
                files = sorted(path.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
                if files:
                    context["data_status"][folder] = {
                        "file_count": len(files),
                        "latest_age_hours": round(
                            (datetime.now().timestamp() - files[0].stat().st_mtime) / 3600, 1
                        ),
                    }

        # Son deploy zamanı
        marker = _BASE_DIR / "data" / "last_deploy.txt"
        if marker.exists():
            try:
                last = datetime.fromisoformat(marker.read_text().strip())
                context["last_deploy_hours_ago"] = round(
                    (datetime.now().timestamp() - last.timestamp()) / 3600, 1
                )
            except Exception:
                context["last_deploy_hours_ago"] = 999
        else:
            context["last_deploy_hours_ago"] = 999

        return context

    # ── Decision ───────────────────────────────────────────────────────────

    def make_decision(self, context: dict) -> dict:
        triggers_text = "\n".join(
            f"  - [{k}] {v}" for k, v in context.get("triggers", [])
        ) or "  (yok — manuel çağrı)"

        prompt = f"""Sen landgold-agents sistemini yöneten orchestrator'sın.
Görev: Tetiklemeleri analiz et, hangi ajanların çalışması gerektiğine karar ver.

Watchdog tetiklemeleri:
{triggers_text}

Sistem durumu:
{json.dumps(context.get("data_status", {}), indent=2, ensure_ascii=False)}

Son deploy: {context.get("last_deploy_hours_ago", "?")} saat önce

Kullanılabilir ajanlar ve maliyetleri:
  - news:     Haber topla + analiz et    (~$0.30)
  - property: Mülk listele + skorla      (~$0.30)
  - outreach: Lead pipeline yönetimi     (~$0.15)
  - deploy:   tradiaturkey.com'a yükle   (~$0.05)

Kurallar:
1. Sadece gerçekten gerekli olanları seç, boşa harcama.
2. news veya property çalışıyorsa, sonra deploy da çalıştır.
3. outreach: sadece tetiklemede 'outreach' varsa.
4. Tetikleme yoksa (manuel çağrı): konservatif ol, her şeyi çalıştırma.

Cevap: sadece geçerli JSON, başka metin yok.
{{
  "decisions": {{
    "news":     {{"run": true/false, "reason": "..."}},
    "property": {{"run": true/false, "reason": "..."}},
    "outreach": {{"run": true/false, "reason": "..."}},
    "deploy":   {{"run": true/false, "reason": "..."}}
  }},
  "estimated_cost": 0.00,
  "summary": "Kısa özet"
}}"""

        resp = self._llm.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # JSON bloğunu temizle
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    # ── Execution ──────────────────────────────────────────────────────────

    def _run_agent(self, name: str) -> dict:
        """main.py üzerinden ajan çalıştır."""
        if name == "deploy":
            cmd = [_PYTHON, _MAIN, "--deploy"]
        else:
            cmd = [_PYTHON, _MAIN, "--agent", name, "--task", "full"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(_BASE_DIR),
            )
            status = "success" if result.returncode == 0 else "failed"
            if result.returncode != 0:
                print(f"  [ORCH] {name} HATA:\n{result.stderr[-400:]}")
            return {"agent": name, "status": status, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"agent": name, "status": "timeout"}
        except Exception as exc:
            return {"agent": name, "status": "error", "error": str(exc)}

    def execute_decisions(self, decision: dict) -> None:
        for name in ("news", "property", "outreach", "deploy"):
            agent_dec = decision["decisions"].get(name, {})
            if agent_dec.get("run"):
                print(f"  🚀 {name}: {agent_dec['reason']}")
                result = self._run_agent(name)
                self.executed.append(result)
                print(f"     → {result['status']}")
            else:
                print(f"  ⏭  {name}: {agent_dec.get('reason', 'atlandı')}")

    # ── Report ─────────────────────────────────────────────────────────────

    def write_report(self, decision: dict) -> dict:
        report = {
            "timestamp": self.timestamp.isoformat(),
            "decision":  decision,
            "executed":  self.executed,
        }
        report_dir = _BASE_DIR / "data" / "reports" / "orchestrator"
        report_dir.mkdir(parents=True, exist_ok=True)
        fname = self.timestamp.strftime("%Y-%m-%d_%H-%M") + ".json"
        (report_dir / fname).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (report_dir / "latest.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return report

    # ── Main ───────────────────────────────────────────────────────────────

    def run(self, triggers: list[tuple[str, str]] | None = None) -> dict:
        print(f"\n🎯 Orchestrator {self.timestamp.strftime('%H:%M')} — tetikleyici: watchdog")

        context  = self.gather_context(triggers)
        decision = self.make_decision(context)

        print(f"💡 Karar: {decision.get('summary','')}")
        print(f"💰 Tahmini maliyet: ${decision.get('estimated_cost', 0):.2f}")

        self.execute_decisions(decision)
        report = self.write_report(decision)

        ran    = [e["agent"] for e in self.executed if e["status"] == "success"]
        failed = [e["agent"] for e in self.executed if e["status"] != "success"]
        print(f"\n✅ Tamamlananlar: {ran or 'yok'}")
        if failed:
            print(f"❌ Başarısızlar: {failed}")

        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LandGold Orchestrator")
    parser.add_argument("--triggered-by", default="manual")
    parser.add_argument("--triggers",     default="", help="k:v,k:v formatında tetiklemeler")
    args = parser.parse_args()

    triggers: list[tuple[str, str]] = []
    if args.triggers:
        for item in args.triggers.split(","):
            if ":" in item:
                k, v = item.split(":", 1)
                triggers.append((k.strip(), v.strip()))

    orch = OrchestratorAgent()
    orch.run(triggers=triggers)
    sys.exit(0)
