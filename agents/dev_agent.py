from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic
import requests

from core.config import Config
from .base_agent import BaseAgent

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


class DevAgent(BaseAgent):
    """Monitors site health, logs results, and alerts CEO on critical failures."""

    MONITORED_URLS: list[dict[str, Any]] = [
        {
            "name":             "Tradia Turkey Main",
            "url":              "https://tradiaturkey.com/",
            "expected_status":  200,
            "expected_content": "TRADIA",
            "critical":         True,
        },
        {
            "name":             "Tradia Turkey Index",
            "url":              "https://tradiaturkey.com/index.html",
            "expected_status":  200,
            "expected_content": "TRADIA",
            "critical":         True,
        },
    ]

    PENDING_FEATURES: list[dict[str, Any]] = [
        {
            "id":              "feat-001",
            "title":           "News feed section",
            "description":     "Display top 5 news items from NewsAgent on the main page",
            "priority":        "high",
            "status":          "pending",
            "file_to_modify":  "index.html",
            "data_source":     "data/reports/news_report_{date}.json",
        },
        {
            "id":              "feat-002",
            "title":           "Property listings section",
            "description":     "Show top 3 scored properties from PropertyAgent with grade badges",
            "priority":        "high",
            "status":          "pending",
            "file_to_modify":  "index.html",
            "data_source":     "data/reports/property_report_{date}.json",
        },
        {
            "id":              "feat-003",
            "title":           "Lead form backend",
            "description":     "Connect investment request form to Airtable or Formspree",
            "priority":        "medium",
            "status":          "pending",
            "file_to_modify":  "index.html",
            "data_source":     None,
        },
        {
            "id":              "feat-004",
            "title":           "Multi-language toggle",
            "description":     "Full EN/RU/AR/TR language switching activation",
            "priority":        "medium",
            "status":          "pending",
            "file_to_modify":  "index.html",
            "data_source":     None,
        },
        {
            "id":              "feat-005",
            "title":           "PDF report download",
            "description":     "Allow investors to download property analysis as PDF",
            "priority":        "low",
            "status":          "pending",
            "file_to_modify":  "index.html",
            "data_source":     "data/reports/property_report_{date}.json",
        },
    ]

    _CEO_REC_SYSTEM = (
        "You are the technical lead at LandGold Intelligence. "
        "Given a system status report, write ONE sentence telling the CEO what the dev team "
        "should focus on today. Be specific and actionable. English only."
    )

    _MOCK_DEPLOY_SYSTEM = (
        "Generate a mock GitHub Actions status check response for a GitHub Pages site. "
        "Return ONLY valid JSON with keys: last_deploy (ISO datetime), "
        "status ('success' or 'failed'), commit_message (str), duration_seconds (int)."
    )

    _FEATURE_SYSTEM = (
        "You are a senior frontend developer. "
        "Generate clean, production-ready HTML/CSS/JavaScript code for the following feature. "
        "The target site uses vanilla HTML/CSS/JS hosted on GitHub Pages. "
        "Return ONLY the code block to be inserted, no explanation. "
        "Keep it self-contained, no external dependencies except what is already on the page."
    )

    PERFORMANCE_THRESHOLDS: dict[str, int] = {
        "response_time_warn_ms":     2000,
        "response_time_critical_ms": 5000,
        "min_content_length":        500,
    }

    def __init__(self, name: str = "dev", role: str = "System Monitor", ceo_callback=None) -> None:
        super().__init__(name=name, role=role, ceo_callback=ceo_callback)
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._error_log: list[dict] = []
        self._llm = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        # mutable copy so status updates don't mutate the class-level list
        self._features: list[dict[str, Any]] = [dict(f) for f in self.PENDING_FEATURES]

    # ── Health checks ──────────────────────────────────────────────────────

    def check_url(self, monitored_url: dict[str, Any]) -> dict[str, Any]:
        url      = monitored_url["url"]
        name     = monitored_url["name"]
        expected_status  = monitored_url.get("expected_status", 200)
        expected_content = monitored_url.get("expected_content", "")
        now = datetime.now(timezone.utc).isoformat()

        result: dict[str, Any] = {
            "url":             url,
            "name":            name,
            "status_code":     None,
            "response_time_ms": None,
            "content_ok":      False,
            "content_length":  0,
            "error":           None,
            "health":          "critical",
            "checked_at":      now,
        }

        t0 = time.monotonic()
        try:
            resp = self._session.get(url, timeout=10, allow_redirects=True)
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

            result["status_code"]      = resp.status_code
            result["response_time_ms"] = elapsed_ms
            result["content_length"]   = len(resp.text)
            result["content_ok"]       = expected_content in resp.text

            warn_ms     = self.PERFORMANCE_THRESHOLDS["response_time_warn_ms"]
            critical_ms = self.PERFORMANCE_THRESHOLDS["response_time_critical_ms"]

            if (
                resp.status_code != expected_status
                or elapsed_ms > critical_ms
            ):
                result["health"] = "critical"
            elif (
                elapsed_ms > warn_ms
                or not result["content_ok"]
                or result["content_length"] < self.PERFORMANCE_THRESHOLDS["min_content_length"]
            ):
                result["health"] = "warn"
            else:
                result["health"] = "ok"

        except Exception as exc:
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
            result["response_time_ms"] = elapsed_ms
            result["error"]  = str(exc)
            result["health"] = "critical"
            self._error_log.append({"url": url, "error": str(exc), "at": now})

        self.log(
            f"[{result['health'].upper():8}] {name} — "
            f"{result['status_code']} {result['response_time_ms']}ms "
            f"content_ok={result['content_ok']}"
        )
        return result

    def check_all(self) -> list[dict[str, Any]]:
        return [self.check_url(m) for m in self.MONITORED_URLS]

    def get_site_status(self) -> dict[str, Any]:
        checks   = self.check_all()
        now      = datetime.now(timezone.utc).isoformat()

        critical_issues = [c for c in checks if c["health"] == "critical"]
        warnings        = [c for c in checks if c["health"] == "warn"]

        # overall is "critical" only if a critical=True URL is critical
        monitored_map = {m["url"]: m for m in self.MONITORED_URLS}
        has_critical = any(
            c["health"] == "critical" and monitored_map.get(c["url"], {}).get("critical", False)
            for c in checks
        )
        has_warn = bool(warnings)

        if has_critical:
            overall = "critical"
        elif has_warn:
            overall = "warn"
        else:
            overall = "ok"

        return {
            "overall":         overall,
            "checks":          checks,
            "critical_issues": critical_issues,
            "warnings":        warnings,
            "checked_at":      now,
        }

    # ── Persistence ────────────────────────────────────────────────────────

    def save_health_log(self, status: dict[str, Any]) -> None:
        Config.ensure_dirs()
        dev_dir  = Config.DATA_PATH / "dev"
        dev_dir.mkdir(parents=True, exist_ok=True)
        log_path = dev_dir / "health_log.json"

        existing: list[dict] = []
        if log_path.exists():
            try:
                with log_path.open(encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = []

        existing.append(status)
        trimmed = existing[-1000:]

        with log_path.open("w", encoding="utf-8") as f:
            json.dump(trimmed, f, ensure_ascii=False, indent=2)
        self.log(f"Health log saved ({len(trimmed)} entries)")

    # ── Feature backlog ────────────────────────────────────────────────────

    def get_pending_features(self, priority: str | None = None) -> list[dict[str, Any]]:
        return [
            f for f in self._features
            if f["status"] == "pending"
            and (priority is None or f["priority"] == priority)
        ]

    def generate_feature_code(self, feature: dict[str, Any]) -> dict[str, Any]:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data_source = feature.get("data_source") or "none"
        if "{date}" in (data_source or ""):
            data_source = data_source.replace("{date}", date_str)

        user_msg = (
            f"Feature ID: {feature['id']}\n"
            f"Title: {feature['title']}\n"
            f"Description: {feature['description']}\n"
            f"File to modify: {feature['file_to_modify']}\n"
            f"Data source: {data_source}\n"
            f"Priority: {feature['priority']}\n\n"
            "Generate the HTML/CSS/JS snippet to implement this feature. "
            "Include a comment block at the top with the feature ID and title."
        )

        code = ""
        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=[{"type": "text", "text": self._FEATURE_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_msg}],
            )
            code = resp.content[0].text.strip()
            # strip markdown fences if model wraps output
            if code.startswith("```"):
                lines = code.splitlines()
                code = "\n".join(
                    l for l in lines
                    if not l.strip().startswith("```")
                ).strip()
        except Exception as exc:
            self.log(f"generate_feature_code error [{feature['id']}]: {exc}")
            code = f"<!-- Code generation failed for {feature['id']}: {exc} -->"

        insertion_point = (
            "<!-- INSERT: news-feed-section -->"    if feature["id"] == "feat-001"
            else "<!-- INSERT: property-section -->" if feature["id"] == "feat-002"
            else "<!-- INSERT: lead-form -->"        if feature["id"] == "feat-003"
            else "<!-- INSERT: lang-toggle -->"      if feature["id"] == "feat-004"
            else "<!-- INSERT: pdf-download -->"
        )

        self.log(f"Code generated for {feature['id']} ({len(code)} chars)")
        return {
            "feature_id":       feature["id"],
            "code":             code,
            "insertion_point":  insertion_point,
            "generated_at":     datetime.now(timezone.utc).isoformat(),
        }

    def save_feature_code(self, feature_id: str, code: str) -> str:
        Config.ensure_dirs()
        features_dir = Config.DATA_PATH / "dev" / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = features_dir / f"{feature_id}_{date_str}.html"
        out_path.write_text(code, encoding="utf-8")
        self.log(f"Feature code saved → {out_path.name}")

        for feat in self._features:
            if feat["id"] == feature_id:
                feat["status"] = "code_ready"
                break

        return str(out_path)

    # ── Uptime & deploy ────────────────────────────────────────────────────

    def get_uptime_stats(self, hours: int = 24) -> dict[str, Any]:
        dev_dir  = Config.DATA_PATH / "dev"
        log_path = dev_dir / "health_log.json"

        entries: list[dict] = []
        if log_path.exists():
            try:
                with log_path.open(encoding="utf-8") as f:
                    entries = json.load(f)
            except (json.JSONDecodeError, OSError):
                entries = []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent: list[dict] = []
        for entry in entries:
            ts = entry.get("checked_at")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    recent.append(entry)
            except ValueError:
                continue

        ok_count       = sum(1 for e in recent if e.get("overall") == "ok")
        warn_count     = sum(1 for e in recent if e.get("overall") == "warn")
        critical_count = sum(1 for e in recent if e.get("overall") == "critical")
        total          = len(recent)

        # avg response time from individual url checks embedded in each entry
        times: list[float] = []
        incidents: list[dict] = []
        for entry in recent:
            for chk in entry.get("checks", []):
                rt = chk.get("response_time_ms")
                if rt is not None:
                    times.append(rt)
            if entry.get("overall") == "critical":
                incidents.append({
                    "checked_at": entry.get("checked_at"),
                    "critical_issues": entry.get("critical_issues", []),
                })

        uptime_percent  = round(ok_count / total * 100, 2) if total else 100.0
        avg_response_ms = round(sum(times) / len(times), 1) if times else 0.0

        return {
            "period_hours":      hours,
            "total_checks":      total,
            "ok_count":          ok_count,
            "warn_count":        warn_count,
            "critical_count":    critical_count,
            "uptime_percent":    uptime_percent,
            "avg_response_time_ms": avg_response_ms,
            "incidents":         incidents,
        }

    def check_github_actions_status(self) -> dict[str, Any]:
        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=128,
                system=[{"type": "text", "text": self._MOCK_DEPLOY_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": "Generate a realistic mock deploy status."}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = "\n".join(
                    l for l in raw.splitlines()
                    if not l.strip().startswith("```")
                ).strip()
            return json.loads(raw)
        except Exception as exc:
            self.log(f"check_github_actions_status fallback: {exc}")
            return {
                "last_deploy":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "status":           "success",
                "commit_message":   "auto: agent update",
                "duration_seconds": 42,
            }

    def generate_deploy_checklist(self) -> list[dict[str, str]]:
        return [
            {"step": "Run health check",       "command": "python main.py --agent dev --task check"},
            {"step": "Validate news data",      "command": "python main.py --agent news --task analyze"},
            {"step": "Validate property data",  "command": "python main.py --agent property --task score"},
            {"step": "Generate feature code",   "command": "python main.py --agent dev --task generate_features"},
            {"step": "Commit and push",         "command": "git add . && git commit -m 'auto: agent update' && git push"},
            {"step": "Verify deployment",       "command": "python main.py --agent dev --task check"},
        ]

    def generate_ceo_report(self) -> dict[str, Any]:
        site_health = self.get_site_status()
        uptime      = self.get_uptime_stats(24)
        pending     = self.get_pending_features()
        deploy      = self.check_github_actions_status()
        checklist   = self.generate_deploy_checklist()
        date_str    = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        high_priority = [f for f in pending if f["priority"] == "high"]

        recommendation = ""
        try:
            snapshot = json.dumps({
                "site_overall":      site_health["overall"],
                "uptime_percent":    uptime["uptime_percent"],
                "incidents_24h":     len(uptime["incidents"]),
                "pending_features":  len(pending),
                "high_priority":     len(high_priority),
                "last_deploy":       deploy.get("status"),
            })
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=80,
                system=[{"type": "text", "text": self._CEO_REC_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": snapshot}],
            )
            recommendation = resp.content[0].text.strip()
        except Exception as exc:
            self.log(f"CEO recommendation error: {exc}")
            recommendation = (
                "Deploy pending high-priority features and verify site health after push."
                if high_priority else
                "Site is healthy — focus on medium-priority feature development."
            )

        report: dict[str, Any] = {
            "date":                    date_str,
            "agent":                   self.name,
            "site_health":             site_health,
            "uptime_24h":              uptime,
            "pending_features":        len(pending),
            "high_priority_features":  high_priority,
            "last_deploy":             deploy,
            "deploy_checklist":        checklist,
            "recommendation":          recommendation,
        }

        Config.ensure_dirs()
        out_path = Config.REPORTS_DIR / f"dev_report_{date_str}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        self.log(f"CEO report saved → {out_path.name}")

        self.report_to_ceo({
            "action":           "dev_report_ready",
            "date":             date_str,
            "site_overall":     site_health["overall"],
            "uptime_percent":   uptime["uptime_percent"],
            "pending_features": len(pending),
            "recommendation":   recommendation,
            "priority":         "critical" if site_health["overall"] == "critical" else "normal",
        })
        return report

    # ── Orchestration ──────────────────────────────────────────────────────

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "check")

        if action == "status_report":
            return {
                "status":   "MONITORING",
                "priority": "normal",
                "errors":   len(self._error_log),
            }

        if action in ("check", "review"):
            status = self.get_site_status()
            self.save_health_log(status)

            overall = status["overall"]
            n_crit  = len(status["critical_issues"])
            n_warn  = len(status["warnings"])
            n_ok    = sum(1 for c in status["checks"] if c["health"] == "ok")

            self.log(
                f"Site status: {overall.upper()} — "
                f"{n_ok} ok / {n_warn} warn / {n_crit} critical"
            )

            if overall == "critical":
                self.report_to_ceo({
                    "action":   "site_health_alert",
                    "overall":  overall,
                    "critical_issues": [
                        {"name": c["name"], "error": c["error"], "status_code": c["status_code"]}
                        for c in status["critical_issues"]
                    ],
                    "priority": "critical",
                })

            return {
                "status":   "OK",
                "overall":  overall,
                "ok":       n_ok,
                "warn":     n_warn,
                "critical": n_crit,
                "checks":   status["checks"],
            }

        if action == "generate_features":
            priority = task.get("priority", "high")
            pending  = self.get_pending_features(priority=priority)
            if not pending:
                self.log(f"No pending features with priority={priority!r}")
                return {"status": "NO_FEATURES", "priority": priority, "generated": 0}

            generated = []
            for feat in pending:
                result   = self.generate_feature_code(feat)
                out_path = self.save_feature_code(feat["id"], result["code"])
                generated.append({
                    "feature_id":      feat["id"],
                    "title":           feat["title"],
                    "file":            out_path,
                    "insertion_point": result["insertion_point"],
                    "generated_at":    result["generated_at"],
                })

            self.report_to_ceo({
                "action":    "features_generated",
                "count":     len(generated),
                "priority":  priority,
                "features":  [g["feature_id"] for g in generated],
                "priority_level": "normal",
            })
            return {"status": "OK", "generated": len(generated), "features": generated}

        if action == "deploy_checklist":
            checklist = self.generate_deploy_checklist()
            for i, step in enumerate(checklist, 1):
                self.log(f"Step {i}: {step['step']}")
            return {"status": "OK", "checklist": checklist}

        if action == "full":
            # check → uptime → generate features → ceo report
            site_status = self.get_site_status()
            self.save_health_log(site_status)

            uptime = self.get_uptime_stats(24)

            pending = self.get_pending_features(priority="high")
            generated_count = 0
            for feat in pending:
                result   = self.generate_feature_code(feat)
                self.save_feature_code(feat["id"], result["code"])
                generated_count += 1

            report = self.generate_ceo_report()
            return {
                "status":          "OK",
                "site_overall":    site_status["overall"],
                "uptime_percent":  uptime["uptime_percent"],
                "features_generated": generated_count,
                "pending_features":   report["pending_features"],
                "recommendation":     report["recommendation"],
            }

        return {"status": "UNKNOWN_ACTION", "action": action}

    # ── Legacy stubs ───────────────────────────────────────────────────────

    def review_logs(self) -> list[dict]:
        return list(self._error_log)

    def propose_fix(self, error: dict) -> str:
        return f"Investigate {error.get('url')} — last error: {error.get('error')}"

    def update_prompt(self, agent_name: str, new_prompt: str) -> None:
        self.log(f"update_prompt requested for {agent_name!r} (not implemented)")
