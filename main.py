from __future__ import annotations
import sys
import argparse
import time
sys.path.insert(0, ".")

import schedule
from colorama import init as colorama_init, Fore, Style

from core.config import Config
from core.logger import configure_root
from core.message_bus import MessageBus
from agents.ceo_agent      import CEOAgent
from agents.news_agent     import NewsAgent
from agents.property_agent import PropertyAgent
from agents.outreach_agent import OutreachAgent
from agents.dev_agent      import DevAgent
from agents.research_agent import ResearchAgent

colorama_init(autoreset=True)

GOLD  = Fore.YELLOW
DIM   = Style.DIM
BOLD  = Style.BRIGHT
RESET = Style.RESET_ALL


def _banner(text: str) -> None:
    width = 60
    line  = "═" * width
    print(f"\n{GOLD}{line}")
    print(f"  {BOLD}{text}")
    print(f"{GOLD}{line}{RESET}\n")


def _section(label: str, data: dict) -> None:
    print(f"{GOLD}┌─ {BOLD}{label}{RESET}")
    for k, v in data.items():
        print(f"{GOLD}│{RESET}  {DIM}{k:<22}{RESET} {v}")
    print(f"{GOLD}└{'─'*50}{RESET}")


# ── System factory ─────────────────────────────────────────────────────────────

def _build_system() -> CEOAgent:
    """Instantiate and wire all agents; return the CEO."""
    configure_root()
    Config.ensure_dirs()

    ceo      = CEOAgent()
    news     = NewsAgent()
    prop     = PropertyAgent()
    outreach = OutreachAgent()
    dev      = DevAgent()
    research = ResearchAgent()

    for agent in (news, prop, outreach, dev, research):
        ceo.register_agent(agent)

    return ceo


# ── Agent runner ───────────────────────────────────────────────────────────────

def run_agent(agent_name: str, task: str) -> int:
    ceo = _build_system()
    _banner(f"LandGold — {agent_name.upper()} → {task}")

    if agent_name == "ceo":
        result = ceo.run_task({"action": task})
        if isinstance(result, dict):
            _section(f"ceo / {task}", {k: str(v)[:120] for k, v in result.items()
                                        if k not in ("briefing", "report", "decision", "actions", "checks")})
        return 0

    agent = ceo._agents.get(agent_name)
    if agent is None:
        print(f"Unknown agent: {agent_name!r}. Choose from: news property outreach dev ceo research")
        return 1

    result = agent.run_task({"action": task})
    _section(f"{agent_name} / {task}", {k: str(v)[:120] for k, v in result.items()})
    return 0


# ── Scheduler ──────────────────────────────────────────────────────────────────

def run_schedule() -> int:
    configure_root()
    Config.ensure_dirs()

    def _job(agent_name: str, task: str, label: str) -> None:
        print(f"\n{GOLD}[SCHEDULED]{RESET} {label}")
        try:
            if agent_name == "__deploy__":
                from deploy_to_site import deploy
                deploy()
            else:
                ceo = _build_system()
                if agent_name == "ceo":
                    ceo.run_task({"action": task})
                else:
                    agent = ceo._agents.get(agent_name)
                    if agent:
                        agent.run_task({"action": task})
        except Exception as exc:
            print(f"{Fore.RED}[SCHEDULE ERROR] {label}: {exc}{RESET}")

    # ── Reactive Architecture (3-Katman) aktif ──────────────────────────
    # Katman 1 (Watchdog) + Katman 2 (Orchestrator) Watchdog'u tetikler.
    # Ajanlar sadece Orchestrator kararıyla çalışır — burada schedule YOK.
    # Manuel tetikleme: python main.py --agent <name> --task full

    schedule.every().day.at("08:00").do(_job, "ceo",        "briefing",       "CEO Daily Briefing")
    schedule.every().day.at("09:00").do(_job, "news",       "full",           "News Full Cycle")
    schedule.every().day.at("10:00").do(_job, "property",   "full",           "Property Full Cycle")
    schedule.every().day.at("10:30").do(_job, "research",   "marmara",        "Research — Marmara Scan")
    schedule.every().day.at("10:45").do(_job, "research",   "ege",            "Research — Ege Scan")
    schedule.every().day.at("11:00").do(_job, "research",   "karadeniz",      "Research — Karadeniz Scan")
    schedule.every().day.at("11:15").do(_job, "research",   "ic_anadolu",     "Research — İç Anadolu Scan")
    schedule.every().day.at("11:45").do(_job, "research",   "guneydogu",      "Research — Güneydoğu Scan")
    schedule.every().day.at("11:30").do(_job, "outreach",   "full",           "Outreach Full Cycle")
    schedule.every().day.at("12:00").do(_job, "__deploy__", "",               "Deploy → GitHub Pages")
    schedule.every().day.at("14:00").do(_job, "dev",        "full",           "Dev Full Cycle")
    schedule.every().monday.at("07:00").do(_job, "ceo",      "investor_report", "Weekly Investor Report")
    schedule.every().monday.at("08:00").do(_job, "research", "osb_report",      "Research — Weekly OSB Report")

    W = 36
    next_job  = min(schedule.jobs, key=lambda j: j.next_run)
    next_name = next_job.job_func.args[2]
    next_time = next_job.next_run.strftime("%Y-%m-%d %H:%M")

    print("=" * W)
    print("LANDGOLD AGENT SYSTEM — SCHEDULER")
    print("=" * W)
    print(f"Jobs registered: {len(schedule.jobs)}")
    print("Sabit schedule (13 iş):")
    print("  08:00  CEO briefing")
    print("  09:00  News Agent — full scan")
    print("  10:00  Property Agent — full analysis")
    print("  10:30  Research Agent — Marmara scan")
    print("  10:45  Research Agent — Ege scan")
    print("  11:00  Research Agent — Karadeniz scan")
    print("  11:15  Research Agent — İç Anadolu scan")
    print("  11:30  Outreach Agent — lead pipeline")
    print("  11:45  Research Agent — Güneydoğu scan")
    print("  12:00  Deploy → GitHub Pages")
    print("  14:00  Dev Agent — health + features")
    print("  Mon 07:00  Weekly investor report")
    print("  Mon 08:00  Research — Weekly OSB Report")
    print("Manuel: python main.py --agent <news|property|outreach|dev> --task full")
    print("=" * W)
    print(f"Next run: {next_name} at {next_time}")
    print("Press Ctrl+C to stop.")
    print("=" * W + "\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print(f"\n{GOLD}Scheduler stopped.{RESET}")
    return 0


# ── Default run ────────────────────────────────────────────────────────────────

def main() -> int:
    ceo = _build_system()
    _banner("LandGold Intelligence — Agent System Boot")
    print(f"{GOLD}  Registered:{RESET} {', '.join(ceo._agents.keys())}\n")

    ceo.run_cycle()

    print(f"\n{GOLD}System ready. Use --schedule for automated runs.{RESET}")
    return 0


# ── Deploy ─────────────────────────────────────────────────────────────────────

def run_deploy() -> int:
    # Step 1: generate fresh data via CEO briefing
    _banner("LandGold — Pre-Deploy: CEO Briefing")
    ceo = _build_system()
    try:
        ceo.run_task({"action": "briefing"})
    except Exception as exc:
        print(f"{Fore.RED}[DEPLOY] Briefing error: {exc} — continuing with existing data{RESET}")

    # Step 2: run the deploy script
    _banner("LandGold — Deploying to Site")
    from deploy_to_site import deploy
    return deploy()


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_faz3() -> None:
    agent = PropertyAgent(name="PropertyAgent", role="property_advisor")
    dummy = {
        "id": "test-001",
        "title": "Test Arsa - Esenyurt",
        "price_try": 5000000,
        "price_usd": 160000,
        "area_m2": 500,
        "location": {"city": "Istanbul", "district": "Esenyurt", "neighborhood": "Merkez"},
        "property_type": "land",
        "zoning": "commercial",
        "road_type": "state_road",
        "highway_distance_km": 3.5,
        "has_title_deed": True,
        "title_deed_issues": [],
        "listing_url": "https://example.com",
        "raw_description": "Esenyurt merkez ticari arsa",
        "fetched_at": "2024-01-01T00:00:00",
    }
    score = agent.calculate_total_score(dummy)
    print("=== FAZ 3 TEST ===")
    print(f"Toplam skor: {score['total']:.1f}/100")
    print(f"Not: {score['grade']}")
    print(f"Güçlü yönler: {score['strengths']}")
    print(f"Zayıf yönler: {score['weaknesses']}")
    report = agent.generate_ceo_report()
    print(f"\nCEO Raporu alanları: {list(report.keys())}")
    print(f"Rapor tarihi: {report['date']}")
    print("=== TEST TAMAM ===")


def run_all_tests() -> int:
    configure_root()
    Config.ensure_dirs()
    _banner("LandGold — All Agent Tests")
    errors: list[str] = []

    try:
        test_faz3()
        print(f"{GOLD}✓ PropertyAgent test passed{RESET}")
    except Exception as exc:
        errors.append(f"PropertyAgent: {exc}")
        print(f"{Fore.RED}✗ PropertyAgent test FAILED: {exc}{RESET}")

    try:
        agent = OutreachAgent()
        lead  = {"name": "Test Lead", "platform": "linkedin", "segment": "Gulf Investor",
                 "language": "en", "estimated_budget_usd": 200000,
                 "contact_email": "test@test.com", "status": "identified"}
        score = agent.score_lead(lead)
        assert score == 85, f"expected 85, got {score}"
        stats = agent.get_pipeline_stats()
        assert "total_leads" in stats
        print(f"{GOLD}✓ OutreachAgent test passed{RESET}")
    except Exception as exc:
        errors.append(f"OutreachAgent: {exc}")
        print(f"{Fore.RED}✗ OutreachAgent test FAILED: {exc}{RESET}")

    try:
        agent   = DevAgent()
        pending = agent.get_pending_features(priority="high")
        assert len(pending) == 2, f"expected 2 high-priority features, got {len(pending)}"
        assert len(agent.generate_deploy_checklist()) == 6
        assert "uptime_percent" in agent.get_uptime_stats(24)
        print(f"{GOLD}✓ DevAgent test passed{RESET}")
    except Exception as exc:
        errors.append(f"DevAgent: {exc}")
        print(f"{Fore.RED}✗ DevAgent test FAILED: {exc}{RESET}")

    try:
        agent = NewsAgent()
        item  = {"title": "kamulaştırma kararı Ankara", "summary": "", "source": "test",
                 "url": "https://example.com", "published": "2024-01-01"}
        classified = agent.classify_item(item)
        assert classified["type"] in ("critical", "opportunity", "threat", "neutral")
        print(f"{GOLD}✓ NewsAgent test passed{RESET}")
    except Exception as exc:
        errors.append(f"NewsAgent: {exc}")
        print(f"{Fore.RED}✗ NewsAgent test FAILED: {exc}{RESET}")

    try:
        ceo = _build_system()
        mock_reports = {
            "news":     {"distribution": {"critical": 1, "opportunity": 2}},
            "property": {"grade_a_count": 1, "avg_score": 70.0},
            "outreach": {"followups_needed": 0, "pipeline": {"total_leads": 3, "conversion_rate": 8.0}},
            "dev":      {"site_health": {"overall": "ok"}, "uptime_24h": {"uptime_percent": 100.0},
                         "high_priority_features": [{"id": "feat-001"}]},
            "errors": [],
        }
        actions = ceo.evaluate_priorities(mock_reports)
        assert any(a["action"] == "escalate_news" for a in actions)
        assert any(a["action"] == "trigger_dev"   for a in actions)
        text = ceo.format_briefing(mock_reports, actions, [])
        assert len(text) > 50
        print(f"{GOLD}✓ CEOAgent test passed{RESET}")
    except Exception as exc:
        errors.append(f"CEOAgent: {exc}")
        print(f"{Fore.RED}✗ CEOAgent test FAILED: {exc}{RESET}")

    print()
    total = 5
    passed = total - len(errors)
    if errors:
        _banner(f"Tests: {passed}/{total} passed")
        return 1
    _banner(f"All {total} tests passed ✓")
    return 0


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LandGold Intelligence Agent System")
    parser.add_argument("--agent",    choices=["news", "property", "outreach", "dev", "ceo", "research"],
                        help="Agent to run")
    parser.add_argument("--task",     default="status_report",
                        help="Task action to execute (default: status_report)")
    parser.add_argument("--test",     action="store_true", help="Run all agent tests")
    parser.add_argument("--schedule", action="store_true", help="Run automated schedule loop")
    parser.add_argument("--deploy",   action="store_true", help="Generate fresh data and deploy to GitHub Pages")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_all_tests())
    elif args.schedule:
        sys.exit(run_schedule())
    elif args.deploy:
        sys.exit(run_deploy())
    elif args.agent:
        sys.exit(run_agent(args.agent, args.task))
    else:
        sys.exit(main())
