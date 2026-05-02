from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import anthropic

from core.config import Config
from core.logger import get_logger
from .base_agent import BaseAgent

PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2, "low": 3}

PRIORITY_RULES: list[dict[str, Any]] = [
    {
        "id":        "escalate_news",
        "condition": "any report has critical_count > 0",
        "action":    "escalate_news",
        "priority":  1,
        "agent":     "news",
    },
    {
        "id":        "escalate_dev",
        "condition": "site health == critical",
        "action":    "escalate_dev",
        "priority":  1,
        "agent":     "dev",
    },
    {
        "id":        "push_opportunities",
        "condition": "grade_a_count > 0 in property report",
        "action":    "push_opportunities",
        "priority":  2,
        "agent":     "property",
    },
    {
        "id":        "batch_followup",
        "condition": "followups_needed > 3 in outreach report",
        "action":    "batch_followup",
        "priority":  2,
        "agent":     "outreach",
    },
    {
        "id":        "trigger_dev",
        "condition": "pending high features > 0",
        "action":    "trigger_dev",
        "priority":  3,
        "agent":     "dev",
    },
    {
        "id":        "review_outreach",
        "condition": "conversion_rate < 10",
        "action":    "review_outreach",
        "priority":  3,
        "agent":     "outreach",
    },
]

_INVESTOR_REPORT_SYSTEM = (
    "You are the CEO of LandGold Intelligence writing a weekly investor newsletter. "
    "Audience: high-net-worth foreign investors interested in Turkish real estate.\n\n"
    "Structure:\n"
    "1. MARKET PULSE (2 paragraphs): key regulatory and market developments this week\n"
    "2. TOP OPPORTUNITIES (3 bullet points): best scored properties with grade and location\n"
    "3. REGULATORY WATCH (1 paragraph): important law/tax changes affecting foreign buyers\n"
    "4. PIPELINE UPDATE (1 paragraph): market momentum and timing recommendation\n"
    "5. CALL TO ACTION: one sentence inviting them to landgold-intelligence.com\n\n"
    "Tone: professional, confident, data-driven. USD denominated. Under 400 words."
)

_BRIEFING_SYSTEM = (
    "You are the CEO of LandGold Intelligence. "
    "Based on the agent reports provided, write a concise executive daily briefing. "
    "Structure:\n"
    "SITUATION: 2 sentences on overall system status\n"
    "OPPORTUNITIES: top 2 property or market opportunities right now\n"
    "RISKS: top 1-2 risks or issues needing attention\n"
    "TODAY'S PRIORITIES: numbered list of 3 actions\n"
    "INVESTOR PIPELINE: one sentence on lead status\n"
    "Keep it under 200 words. Be decisive and specific."
)

_CONFLICT_SYSTEM = (
    "You are the CEO of LandGold Intelligence, a Turkish real estate advisory firm. "
    "Two AI agents have conflicting priorities. Make a clear, decisive call. "
    "Return ONLY valid JSON with keys: "
    "decision (str), reasoning (str), action_for_agent_a (str), action_for_agent_b (str)."
)


class CEOAgent(BaseAgent):
    """Orchestrates all sub-agents: reports, priority evaluation, task routing, conflict resolution."""

    AGENT_REGISTRY: dict[str, BaseAgent] = {}

    def __init__(self) -> None:
        super().__init__(name="ceo", role="Chief Orchestrator")
        self._agents:        dict[str, BaseAgent]  = {}
        self._pending_tasks: list[dict[str, Any]]  = []
        self._alerts:        list[dict[str, Any]]  = []
        self._briefing_log:  list[dict[str, Any]]  = []
        self._llm = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    # ── Registry ───────────────────────────────────────────────────────────

    def register_agent(self, agent: BaseAgent) -> None:
        agent.ceo_callback = self._on_report
        self._agents[agent.name] = agent
        CEOAgent.AGENT_REGISTRY[agent.name] = agent
        self.log(f"Registered agent: {agent.name!r} ({agent.role})")

    def _on_report(self, report: dict[str, Any]) -> None:
        self._briefing_log.append(report)
        priority = report.get("summary", {}).get("priority", "normal")
        if priority in ("high", "critical"):
            self._alerts.append(report)

    # ── Full report collection ─────────────────────────────────────────────

    def collect_reports(self) -> dict[str, Any]:
        collected: dict[str, Any] = {}
        errors: list[str] = []

        report_methods = {
            "news":     "generate_ceo_report",
            "property": "generate_ceo_report",
            "outreach": "generate_ceo_report",
            "dev":      "generate_ceo_report",
        }

        for agent_name, method_name in report_methods.items():
            agent = self._agents.get(agent_name)
            if agent is None:
                errors.append(f"{agent_name}: not registered")
                continue
            try:
                report = getattr(agent, method_name)()
                collected[agent_name] = report
                self.log(f"Report collected: {agent_name}")
            except Exception as exc:
                errors.append(f"{agent_name}: {exc}")
                self.log(f"Report error [{agent_name}]: {exc}")

        return {
            **collected,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "errors":       errors,
        }

    # ── Priority evaluation ────────────────────────────────────────────────

    def evaluate_priorities(self, reports: dict[str, Any]) -> list[dict[str, Any]]:
        triggered: list[dict[str, Any]] = []

        news_report     = reports.get("news", {})
        property_report = reports.get("property", {})
        outreach_report = reports.get("outreach", {})
        dev_report      = reports.get("dev", {})

        # Rule: any report has critical_count > 0
        news_critical = (news_report.get("distribution") or {}).get("critical", 0)
        if news_critical > 0:
            triggered.append({
                "action":   "escalate_news",
                "priority": 1,
                "reason":   f"NewsAgent found {news_critical} critical item(s)",
                "agent":    "news",
            })

        # Rule: site health == critical
        site_overall = (dev_report.get("site_health") or {}).get("overall", "ok")
        if site_overall == "critical":
            triggered.append({
                "action":   "escalate_dev",
                "priority": 1,
                "reason":   "Site health is CRITICAL",
                "agent":    "dev",
            })

        # Rule: grade_a_count > 0 in property report
        grade_a = property_report.get("grade_a_count", 0)
        if grade_a > 0:
            triggered.append({
                "action":   "push_opportunities",
                "priority": 2,
                "reason":   f"PropertyAgent has {grade_a} grade-A opportunity(s)",
                "agent":    "property",
            })

        # Rule: followups_needed > 3 in outreach report
        followups = outreach_report.get("followups_needed", 0)
        if followups > 3:
            triggered.append({
                "action":   "batch_followup",
                "priority": 2,
                "reason":   f"OutreachAgent has {followups} stale leads needing follow-up",
                "agent":    "outreach",
            })

        # Rule: pending high features > 0
        high_feats = len(dev_report.get("high_priority_features") or [])
        if high_feats > 0:
            triggered.append({
                "action":   "trigger_dev",
                "priority": 3,
                "reason":   f"DevAgent has {high_feats} pending high-priority feature(s)",
                "agent":    "dev",
            })

        # Rule: conversion_rate < 10
        conv_rate = (outreach_report.get("pipeline") or {}).get("conversion_rate", 0.0)
        if conv_rate < 10:
            triggered.append({
                "action":   "review_outreach",
                "priority": 3,
                "reason":   f"Outreach conversion rate is {conv_rate}% (< 10% threshold)",
                "agent":    "outreach",
            })

        triggered.sort(key=lambda x: x["priority"])
        self.log(f"Priority evaluation: {len(triggered)} rule(s) triggered")
        return triggered

    # ── Task assignment ────────────────────────────────────────────────────

    def assign_tasks(self, priority_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        action_map: dict[str, tuple[str, str]] = {
            "escalate_news":    ("news",     "digest"),
            "escalate_dev":     ("dev",      "check"),
            "push_opportunities": ("property", "report"),
            "batch_followup":   ("outreach", "followups"),
            "trigger_dev":      ("dev",      "generate_features"),
            "review_outreach":  ("outreach", "stats"),
        }

        results: list[dict[str, Any]] = []
        for pa in priority_actions:
            action      = pa["action"]
            agent_name, task_name = action_map.get(action, (None, None))
            if agent_name is None:
                self.log(f"WARN: no handler for action {action!r}")
                continue

            agent = self._agents.get(agent_name)
            if agent is None:
                self.log(f"WARN: agent {agent_name!r} not registered for action {action!r}")
                continue

            started_at = datetime.now(timezone.utc).isoformat()
            try:
                result = agent.run_task({"action": task_name})
                self.log(
                    f"[{started_at}] Task assigned: {action} → {agent_name}.{task_name} "
                    f"→ {result.get('status', '?')}"
                )
                results.append({
                    "action":     action,
                    "agent":      agent_name,
                    "task":       task_name,
                    "started_at": started_at,
                    "result":     result,
                })
            except Exception as exc:
                self.log(f"Task error [{action}]: {exc}")
                results.append({
                    "action":     action,
                    "agent":      agent_name,
                    "task":       task_name,
                    "started_at": started_at,
                    "error":      str(exc),
                })

        return results

    # ── Conflict resolution ────────────────────────────────────────────────

    def resolve_conflict(self, conflict: dict[str, Any] | str, agent_b: str = "", topic: str = "") -> Any:
        # Accept both new dict form and legacy positional (agent_a, agent_b, topic)
        if isinstance(conflict, str):
            conflict = {"between": [conflict, agent_b], "topic": topic, "details": ""}

        agent_a_name = conflict.get("between", ["?", "?"])[0]
        agent_b_name = conflict.get("between", ["?", "?"])[-1]
        topic_str    = conflict.get("topic", "unknown")
        details      = conflict.get("details", "")

        self.log(f"CONFLICT: {agent_a_name} ↔ {agent_b_name} on '{topic_str}'")

        user_msg = (
            f"Agent A: {agent_a_name}\n"
            f"Agent B: {agent_b_name}\n"
            f"Topic: {topic_str}\n"
            f"Details: {details}"
        )

        decision: dict[str, Any]
        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=256,
                system=[{"type": "text", "text": _CONFLICT_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = "\n".join(
                    l for l in raw.splitlines()
                    if not l.strip().startswith("```")
                ).strip()
            decision = json.loads(raw)
        except Exception as exc:
            self.log(f"resolve_conflict API error: {exc} — using conservative fallback")
            decision = {
                "decision":          f"Proceed with conservative approach on '{topic_str}' pending human review.",
                "reasoning":         "API unavailable; defaulting to no-action to avoid data loss.",
                "action_for_agent_a": f"{agent_a_name}: pause until reviewed",
                "action_for_agent_b": f"{agent_b_name}: pause until reviewed",
            }

        self.log(f"DECISION: {decision.get('decision', '')}")
        self.send_message("*", {"conflict": topic_str, "decision": decision}, priority="high", msg_type="alert")
        return decision

    # ── Format briefing ────────────────────────────────────────────────────

    def format_briefing(
        self,
        reports: dict[str, Any],
        actions: list[dict[str, Any]],
        tasks:   list[dict[str, Any]],
    ) -> str:
        snapshot = {
            "news_critical":      (reports.get("news", {}).get("distribution") or {}).get("critical", 0),
            "news_opportunities": (reports.get("news", {}).get("distribution") or {}).get("opportunity", 0),
            "property_grade_a":   reports.get("property", {}).get("grade_a_count", 0),
            "property_avg_score": reports.get("property", {}).get("avg_score", 0),
            "outreach_total":     (reports.get("outreach", {}).get("pipeline") or {}).get("total_leads", 0),
            "outreach_conversion":(reports.get("outreach", {}).get("pipeline") or {}).get("conversion_rate", 0),
            "outreach_followups": reports.get("outreach", {}).get("followups_needed", 0),
            "site_health":        (reports.get("dev", {}).get("site_health") or {}).get("overall", "unknown"),
            "uptime_percent":     (reports.get("dev", {}).get("uptime_24h") or {}).get("uptime_percent", 100),
            "actions_triggered":  [a["action"] for a in actions],
            "tasks_completed":    len(tasks),
            "errors":             reports.get("errors", []),
        }

        user_msg = (
            "Generate the executive daily briefing based on this data:\n\n"
            + json.dumps(snapshot, indent=2)
        )

        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                system=[{"type": "text", "text": _BRIEFING_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_msg}],
            )
            return resp.content[0].text.strip()
        except Exception as exc:
            self.log(f"format_briefing API error: {exc}")
            lines = [
                "SITUATION: System operational. All agents running normally.",
                f"OPPORTUNITIES: {snapshot['property_grade_a']} grade-A properties identified.",
                f"RISKS: {len(snapshot['errors'])} collection error(s). "
                f"Outreach conversion at {snapshot['outreach_conversion']}%.",
                "TODAY'S PRIORITIES: 1. Review property opportunities. "
                "2. Follow up stale leads. 3. Deploy pending features.",
                f"INVESTOR PIPELINE: {snapshot['outreach_total']} leads tracked; "
                f"{snapshot['outreach_followups']} require follow-up.",
            ]
            return "\n".join(lines)

    # ── Daily briefing (full intelligence cycle) ───────────────────────────

    def daily_briefing(self) -> str:
        print("=== LANDGOLD CEO DAILY BRIEFING ===")

        reports = self.collect_reports()
        actions = self.evaluate_priorities(reports)
        tasks   = self.assign_tasks(actions)
        briefing_text = self.format_briefing(reports, actions, tasks)

        print(briefing_text)

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        Config.ensure_dirs()
        record = {
            "date":               date_str,
            "briefing_text":      briefing_text,
            "reports_collected":  [k for k in reports if k not in ("collected_at", "errors")],
            "actions_triggered":  actions,
            "tasks_completed":    len(tasks),
            "errors":             reports.get("errors", []),
        }
        out_path = Config.REPORTS_DIR / f"ceo_briefing_{date_str}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        self.log(f"Briefing saved → {out_path.name}")

        return briefing_text

    # ── Weekly investor report ─────────────────────────────────────────────

    def generate_investor_report(self) -> str:
        from pathlib import Path

        cutoff = datetime.now(timezone.utc).timestamp() - 7 * 86400
        patterns = {
            "news":     "news_report_*.json",
            "property": "property_report_*.json",
            "outreach": "outreach_report_*.json",
            "dev":      "dev_report_*.json",
        }

        weekly: dict[str, list[dict]] = {}
        for key, pattern in patterns.items():
            files = sorted(Config.REPORTS_DIR.glob(pattern), reverse=True)
            recent = []
            for f in files:
                if f.stat().st_mtime >= cutoff:
                    try:
                        with f.open(encoding="utf-8") as fh:
                            recent.append(json.load(fh))
                    except (json.JSONDecodeError, OSError):
                        pass
            weekly[key] = recent

        # compact aggregate for the prompt
        agg: dict[str, Any] = {
            "week_ending": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "news": {
                "reports_count":   len(weekly["news"]),
                "total_items":     sum(r.get("total_items", 0) for r in weekly["news"]),
                "critical_items":  sum((r.get("distribution") or {}).get("critical", 0) for r in weekly["news"]),
                "opportunities":   sum((r.get("distribution") or {}).get("opportunity", 0) for r in weekly["news"]),
                "top_summaries":   [
                    item.get("summary", "")
                    for r in weekly["news"]
                    for item in (r.get("top_items") or [])[:2]
                ][:6],
            },
            "property": {
                "reports_count":   len(weekly["property"]),
                "total_analyzed":  sum(r.get("total_analyzed", 0) for r in weekly["property"]),
                "grade_a_total":   sum(r.get("grade_a_count", 0) for r in weekly["property"]),
                "avg_score":       round(
                    sum(r.get("avg_score", 0) for r in weekly["property"]) / max(len(weekly["property"]), 1), 1
                ),
                "top_opportunities": [
                    opp for r in weekly["property"]
                    for opp in (r.get("top_opportunities") or [])[:2]
                ][:3],
            },
            "outreach": {
                "total_leads":     max(
                    ((r.get("pipeline") or {}).get("total_leads", 0) for r in weekly["outreach"]), default=0
                ),
                "conversion_rate": next(
                    ((r.get("pipeline") or {}).get("conversion_rate", 0) for r in weekly["outreach"]), 0
                ),
                "followups_needed": max(
                    (r.get("followups_needed", 0) for r in weekly["outreach"]), default=0
                ),
            },
            "site": {
                "uptime_avg": round(
                    sum((r.get("uptime_24h") or {}).get("uptime_percent", 100) for r in weekly["dev"])
                    / max(len(weekly["dev"]), 1), 1
                ),
                "incidents": sum(
                    len((r.get("uptime_24h") or {}).get("incidents", [])) for r in weekly["dev"]
                ),
            },
        }

        user_msg = (
            "Generate the weekly investor newsletter based on this weekly data:\n\n"
            + json.dumps(agg, ensure_ascii=False, indent=2)
        )

        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                system=[{"type": "text", "text": _INVESTOR_REPORT_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_msg}],
            )
            report_text = resp.content[0].text.strip()
        except Exception as exc:
            self.log(f"generate_investor_report API error: {exc}")
            grade_a = agg["property"]["grade_a_total"]
            leads   = agg["outreach"]["total_leads"]
            report_text = (
                f"MARKET PULSE\n"
                f"The Turkish real estate market continues to attract foreign investment with "
                f"{agg['property']['total_analyzed']} properties analyzed this week. "
                f"Grade-A opportunities totalled {grade_a} listings with an average score of "
                f"{agg['property']['avg_score']}/100.\n\n"
                f"TOP OPPORTUNITIES\n"
                f"• {grade_a} grade-A properties identified across monitored districts\n"
                f"• Average portfolio score: {agg['property']['avg_score']}/100\n"
                f"• {agg['news']['opportunities']} market opportunities flagged by news analysis\n\n"
                f"REGULATORY WATCH\n"
                f"{agg['news']['critical_items']} regulatory developments monitored this week. "
                f"Foreign buyer conditions remain stable.\n\n"
                f"PIPELINE UPDATE\n"
                f"{leads} investor leads tracked. "
                f"Conversion rate: {agg['outreach']['conversion_rate']}%. "
                f"Market timing remains favorable for entry.\n\n"
                f"CALL TO ACTION\n"
                f"Explore this week's top opportunities at landgold-intelligence.com"
            )

        Config.ensure_dirs()
        week_str = datetime.now(timezone.utc).strftime("%Y-W%V")
        json_path = Config.REPORTS_DIR / f"weekly_investor_report_{week_str}.json"
        txt_path  = Config.REPORTS_DIR / f"weekly_investor_report_{week_str}.txt"

        record = {
            "week":         week_str,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_text":  report_text,
            "data_summary": agg,
        }
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        txt_path.write_text(report_text, encoding="utf-8")
        self.log(f"Investor report saved → {json_path.name} + {txt_path.name}")

        return report_text

    # ── Task routing (single-agent, legacy) ───────────────────────────────

    def assign_task(self, agent_name: str, task: dict[str, Any]) -> dict[str, Any] | None:
        if agent_name not in self._agents:
            self.log(f"WARN: agent {agent_name!r} not registered — task queued")
            self._pending_tasks.append({"target": agent_name, "task": task})
            return None
        self.send_message(agent_name, task, priority=task.get("priority", "normal"), msg_type="task")
        result = self._agents[agent_name].run_task(task)
        self.log(f"Task → {agent_name}: {task.get('action','?')} → {result.get('status','?')}")
        return result

    def prioritize(self, reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(reports, key=lambda r: PRIORITY_RANK.get(r.get("priority", "normal"), 2))

    # ── Orchestration cycle ────────────────────────────────────────────────

    def run_cycle(self) -> dict[str, Any]:
        print("=== LANDGOLD AGENT SYSTEM STARTING ===")
        print(f"Registered agents: {list(CEOAgent.AGENT_REGISTRY.keys())}")

        briefing_text = self.daily_briefing()

        print("=== CYCLE COMPLETE ===")
        return {
            "status":   "OK",
            "briefing": briefing_text,
            "agents":   list(self._agents.keys()),
        }

    # ── BaseAgent abstract ─────────────────────────────────────────────────

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "")

        if action == "status_report":
            return {
                "status":   "OPERATIONAL",
                "priority": "normal",
                "agents":   list(self._agents.keys()),
                "pending":  len(self._pending_tasks),
            }

        if action in ("briefing", "full"):
            text = self.daily_briefing()
            return {"status": "OK", "briefing": text}

        if action == "cycle":
            return self.run_cycle()

        if action == "collect":
            return self.collect_reports()

        if action == "priorities":
            reports = self.collect_reports()
            actions = self.evaluate_priorities(reports)
            for a in actions:
                print(f"  [{a['priority']}] {a['action']:20} — {a['reason']}")
            return {"status": "OK", "actions": actions, "count": len(actions)}

        if action == "investor_report":
            text = self.generate_investor_report()
            print(text)
            return {"status": "OK", "report": text}

        if action == "conflicts":
            sample = {
                "between": ["news", "property"],
                "topic":   "Konya zoning classification",
                "details": (
                    "NewsAgent flagged a potential zoning freeze from Resmi Gazete. "
                    "PropertyAgent scored the same district as grade-A commercial opportunity."
                ),
            }
            decision = self.resolve_conflict(sample)
            print(f"Conflict Decision: {decision.get('decision', '')}")
            return {"status": "OK", "decision": decision}

        # Legacy: bare run_cycle without the new print wrapper
        return self.run_cycle()
