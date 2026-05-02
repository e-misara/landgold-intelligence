from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic

from core.config import Config
from .base_agent import BaseAgent


class OutreachAgent(BaseAgent):
    """Manages investor leads: scoring, storage, filtering, and outreach status."""

    TARGET_PROFILES: dict[str, list[dict]] = {
        "segments": [
            {
                "name": "Gulf Investor",
                "languages": ["ar", "en"],
                "keywords": [
                    "real estate investment", "property turkey", "istanbul investment",
                    "عقارات تركيا", "استثمار اسطنبول", "dubai investor",
                ],
                "platforms": ["linkedin", "instagram"],
                "typical_budget_usd": 200000,
            },
            {
                "name": "European Diaspora",
                "languages": ["tr", "de", "en"],
                "keywords": [
                    "yatırım türkiye", "istanbul emlak", "türkiye gayrimenkul",
                    "türkei immobilien", "turkish property",
                ],
                "platforms": ["linkedin", "instagram", "facebook"],
                "typical_budget_usd": 100000,
            },
            {
                "name": "Russian/CIS Investor",
                "languages": ["ru", "en"],
                "keywords": [
                    "недвижимость турция", "стамбул инвестиции", "купить квартиру турция",
                    "turkey property", "antalya investment",
                ],
                "platforms": ["instagram", "linkedin"],
                "typical_budget_usd": 150000,
            },
            {
                "name": "UK/US HNW",
                "languages": ["en"],
                "keywords": [
                    "emerging market property", "turkey real estate", "istanbul apartment",
                    "overseas property investment", "golden visa turkey",
                ],
                "platforms": ["linkedin"],
                "typical_budget_usd": 300000,
            },
        ]
    }

    MESSAGE_TEMPLATES: dict[str, dict[str, str]] = {
        "linkedin_first_touch": {
            "en": (
                "Hi {name}, I came across your profile and noticed your interest in {interest_area}. \n"
                "I work with LandGold Intelligence — we help international investors identify high-yield "
                "property opportunities in Turkey, denominated in USD.\n"
                "We currently have {opportunity_count} analyzed opportunities scoring above 75/100 on our "
                "due diligence framework.\n"
                "Would you be open to a brief overview? landgold-intelligence.com"
            ),
            "ru": (
                "Здравствуйте, {name}! Увидел ваш профиль и ваш интерес к {interest_area}.\n"
                "Я работаю с LandGold Intelligence — мы помогаем международным инвесторам находить "
                "высокодоходную недвижимость в Турции в долларах США.\n"
                "Сейчас у нас {opportunity_count} проверенных объектов с оценкой выше 75/100.\n"
                "Хотели бы получить краткий обзор? landgold-intelligence.com"
            ),
            "ar": (
                "مرحباً {name}، اطلعت على ملفك الشخصي ولاحظت اهتمامك بـ {interest_area}.\n"
                "أعمل مع LandGold Intelligence — نساعد المستثمرين الدوليين في تحديد فرص العقارات "
                "عالية العائد في تركيا بالدولار الأمريكي.\n"
                "لدينا حالياً {opportunity_count} فرصة محللة بتقييم أعلى من 75/100.\n"
                "هل أنت مهتم بنظرة عامة مختصرة؟ landgold-intelligence.com"
            ),
        },
        "email_first_touch": {
            "en": (
                "Subject: High-yield Turkish property opportunities — LandGold Intelligence\n\n"
                "Dear {name},\n\n"
                "I hope this message finds you well. I'm reaching out because your investment profile "
                "aligns with opportunities we're currently tracking in the Turkish real estate market.\n\n"
                "LandGold Intelligence provides USD-denominated property analysis for international "
                "investors, covering zoning signals, legal due diligence, and 5-year ROI projections.\n\n"
                "Our current top opportunity scores {top_score}/100 on our 10-criterion framework, "
                "located in {top_location}.\n\n"
                "I'd welcome 15 minutes to walk you through our methodology and current pipeline.\n\n"
                "Best regards,\n"
                "LandGold Intelligence Team\n"
                "https://e-misara.github.io/landgold-intelligence/"
            ),
            "ru": (
                "Тема: Высокодоходная недвижимость в Турции — LandGold Intelligence\n\n"
                "Уважаемый(ая) {name},\n\n"
                "Обращаюсь к вам, поскольку ваш инвестиционный профиль соответствует возможностям, "
                "которые мы отслеживаем на турецком рынке недвижимости.\n\n"
                "LandGold Intelligence предоставляет анализ недвижимости в долларах США для "
                "международных инвесторов.\n\n"
                "Наша лучшая текущая возможность получила {top_score}/100 по нашей системе из "
                "10 критериев, расположена в {top_location}.\n\n"
                "С уважением,\n"
                "Команда LandGold Intelligence"
            ),
            "ar": (
                "الموضوع: فرص عقارية عالية العائد في تركيا — LandGold Intelligence\n\n"
                "عزيزي {name}،\n\n"
                "أتواصل معك لأن ملفك الاستثماري يتوافق مع الفرص التي نتابعها في سوق العقارات التركي.\n\n"
                "تقدم LandGold Intelligence تحليلاً عقارياً بالدولار الأمريكي للمستثمرين الدوليين.\n\n"
                "أفضل فرصة لدينا حصلت على {top_score}/100 وفق إطارنا المكون من 10 معايير، "
                "وتقع في {top_location}.\n\n"
                "مع أطيب التحيات،\n"
                "فريق LandGold Intelligence"
            ),
        },
    }

    _FOLLOWUP_SYSTEM = (
        "Write a short, non-pushy follow-up message for a real estate investor "
        "who hasn't responded to our initial outreach. "
        "Keep it under 3 sentences. Be warm, add a new data point or insight. "
        "Language: {language}"
    )

    _CEO_REC_SYSTEM = (
        "You are the outreach director at LandGold Intelligence. "
        "Given a pipeline summary, write ONE sentence recommending the CEO's top priority action. "
        "Be specific and actionable. English only."
    )

    _INTEREST_AREA_SYSTEM = (
        "You are an outreach assistant for LandGold Intelligence, a Turkish real estate firm. "
        "Given an investor segment name, return a short phrase (4-8 words) describing the investor's "
        "likely interest area for use in a personalised outreach message. "
        "Reply with ONLY the phrase, no punctuation, no explanation."
    )

    _SEGMENT_INTEREST_DEFAULTS: dict[str, str] = {
        "Gulf Investor":       "Turkish real estate and Gulf investment diversification",
        "European Diaspora":   "Turkish property and homeland investment",
        "Russian/CIS Investor": "overseas real estate and Turkish market opportunities",
        "UK/US HNW":           "emerging market property and portfolio diversification",
    }

    _VALID_PLATFORMS = {"linkedin", "instagram", "email", "referral", "facebook"}
    _VALID_STATUSES  = {"identified", "contacted", "responded", "qualified", "converted", "dead"}

    def __init__(self, name: str = "outreach", role: str = "Investor Relations", ceo_callback=None) -> None:
        super().__init__(name=name, role=role, ceo_callback=ceo_callback)
        self._approval_queue: list[dict] = []
        self._llm = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    # ── Lead scoring ───────────────────────────────────────────────────────

    def score_lead(self, lead: dict[str, Any]) -> int:
        score = 0
        if lead.get("contact_email"):
            score += 30
        if (lead.get("estimated_budget_usd") or 0) > 100_000:
            score += 20
        if lead.get("platform") == "linkedin":
            score += 20
        if lead.get("segment") in ("Gulf Investor", "UK/US HNW"):
            score += 15
        if lead.get("status") == "responded":
            score += 15
        return min(score, 100)

    # ── Persistence ────────────────────────────────────────────────────────

    def _leads_path(self):
        Config.ensure_dirs()
        return Config.LEADS_DIR / "leads.json"

    def load_leads(self) -> list[dict[str, Any]]:
        path = self._leads_path()
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def _save_leads(self, leads: list[dict[str, Any]]) -> None:
        path = self._leads_path()
        with path.open("w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)

    def add_lead(self, lead_dict: dict[str, Any]) -> dict[str, Any]:
        lead = _build_empty_lead()
        lead.update({k: v for k, v in lead_dict.items() if k in lead})

        if not lead["id"]:
            lead["id"] = str(uuid.uuid4())
        if not lead["created_at"]:
            lead["created_at"] = datetime.now(timezone.utc).isoformat()
        if lead["status"] not in self._VALID_STATUSES:
            lead["status"] = "identified"
        if lead["platform"] not in self._VALID_PLATFORMS:
            lead["platform"] = "referral"

        lead["score"] = self.score_lead(lead)

        existing = self.load_leads()
        existing.append(lead)
        self._save_leads(existing)
        self.log(f"Lead added: {lead['name']!r} [{lead['segment']}] score={lead['score']}")
        return lead

    def update_lead(self, lead_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        leads = self.load_leads()
        for lead in leads:
            if lead.get("id") == lead_id:
                lead.update({k: v for k, v in updates.items() if k in lead})
                lead["score"] = self.score_lead(lead)
                self._save_leads(leads)
                self.log(f"Lead updated: {lead_id} score={lead['score']}")
                return lead
        self.log(f"Lead not found: {lead_id}")
        return None

    # ── Filtering ──────────────────────────────────────────────────────────

    def filter_leads(
        self,
        status: str | None = None,
        min_score: int = 0,
        segment: str | None = None,
    ) -> list[dict[str, Any]]:
        leads = self.load_leads()
        result = []
        for lead in leads:
            if status is not None and lead.get("status") != status:
                continue
            if (lead.get("score") or 0) < min_score:
                continue
            if segment is not None and lead.get("segment") != segment:
                continue
            result.append(lead)
        return result

    # ── Template & personalisation ─────────────────────────────────────────

    def get_template(self, channel: str, language: str) -> str:
        channel_templates = self.MESSAGE_TEMPLATES.get(channel, {})
        return channel_templates.get(language) or channel_templates.get("en", "")

    def personalize_message(
        self,
        template: str,
        lead: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> str:
        ctx = dict(context or {})

        if "interest_area" not in ctx:
            segment = lead.get("segment", "")
            interest = self._SEGMENT_INTEREST_DEFAULTS.get(segment)
            if not interest:
                try:
                    resp = self._llm.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=32,
                        system=[{"type": "text", "text": self._INTEREST_AREA_SYSTEM,
                                 "cache_control": {"type": "ephemeral"}}],
                        messages=[{"role": "user", "content": f"Segment: {segment}"}],
                    )
                    interest = resp.content[0].text.strip()
                except Exception as exc:
                    self.log(f"interest_area inference error: {exc}")
                    interest = "real estate investment"
            ctx["interest_area"] = interest

        ctx.setdefault("name",             lead.get("name") or "Investor")
        ctx.setdefault("opportunity_count", "5")
        ctx.setdefault("top_score",        "82")
        ctx.setdefault("top_location",     "Istanbul")

        try:
            return template.format(**ctx)
        except KeyError as exc:
            self.log(f"Template key missing: {exc} — returning raw template")
            return template

    def draft_outreach(
        self,
        lead: dict[str, Any],
        channel: str = "linkedin_first_touch",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        language = lead.get("language") or "en"
        template  = self.get_template(channel, language)
        message   = self.personalize_message(template, lead, context)
        return {
            "lead_id":    lead.get("id"),
            "channel":    channel,
            "message":    message,
            "language":   language,
            "drafted_at": datetime.now(timezone.utc).isoformat(),
        }

    def draft_batch(
        self,
        leads_list: list[dict[str, Any]],
        channel: str = "linkedin_first_touch",
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        drafts: list[dict[str, Any]] = []
        for lead in leads_list:
            draft = self.draft_outreach(lead, channel=channel, context=context)
            drafts.append(draft)
            self.log(f"Drafted [{channel}] for {lead.get('name')!r} lang={draft['language']}")

        Config.ensure_dirs()
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = Config.LEADS_DIR / f"drafts_{date_str}.json"
        existing: list[dict] = []
        if out_path.exists():
            with out_path.open(encoding="utf-8") as f:
                existing = json.load(f)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(existing + drafts, f, ensure_ascii=False, indent=2)
        self.log(f"Saved {len(drafts)} drafts → {out_path.name}")
        return drafts

    # ── Contact logging ────────────────────────────────────────────────────

    def log_contact(self, lead_id: str, channel: str, message: str) -> dict[str, Any] | None:
        leads = self.load_leads()
        for lead in leads:
            if lead.get("id") == lead_id:
                lead["status"] = "contacted"
                lead["last_contact"] = datetime.now(timezone.utc).isoformat()
                lead.setdefault("contact_history", []).append({
                    "channel":         channel,
                    "message_preview": message[:100],
                    "sent_at":         lead["last_contact"],
                })
                lead["score"] = self.score_lead(lead)
                self._save_leads(leads)
                self.log(f"Contact logged: {lead_id} via {channel}")
                return lead
        self.log(f"log_contact: lead not found {lead_id}")
        return None

    # ── Pipeline analytics ─────────────────────────────────────────────────

    def get_pipeline_stats(self) -> dict[str, Any]:
        leads = self.load_leads()
        by_status: dict[str, int] = {s: 0 for s in self._VALID_STATUSES}
        by_segment: dict[str, int] = {}
        total_score = 0

        for lead in leads:
            s = lead.get("status", "identified")
            by_status[s] = by_status.get(s, 0) + 1
            seg = lead.get("segment") or "Unknown"
            by_segment[seg] = by_segment.get(seg, 0) + 1
            total_score += lead.get("score") or 0

        total = len(leads)
        avg_score = round(total_score / total, 1) if total else 0.0
        converted = by_status.get("converted", 0)
        conversion_rate = round(converted / total * 100, 1) if total else 0.0

        top_leads = sorted(leads, key=lambda l: l.get("score") or 0, reverse=True)[:5]

        return {
            "total_leads":     total,
            "by_status":       by_status,
            "by_segment":      by_segment,
            "avg_score":       avg_score,
            "conversion_rate": conversion_rate,
            "top_leads": [
                {"name": l.get("name"), "status": l.get("status"), "score": l.get("score")}
                for l in top_leads
            ],
        }

    # ── Lead qualification ─────────────────────────────────────────────────

    def qualify_lead(
        self,
        lead_id: str,
        budget_confirmed: float,
        timeline: str,
        notes: str = "",
    ) -> dict[str, Any] | None:
        leads = self.load_leads()
        for lead in leads:
            if lead.get("id") == lead_id:
                lead["status"] = "qualified"
                lead["qualification"] = {
                    "budget_confirmed": budget_confirmed,
                    "timeline":         timeline,
                    "notes":            notes,
                    "qualified_at":     datetime.now(timezone.utc).isoformat(),
                }
                lead["score"] = self.score_lead(lead)
                self._save_leads(leads)
                self.log(f"Lead qualified: {lead_id} budget=${budget_confirmed:,.0f} timeline={timeline!r}")
                return lead
        self.log(f"qualify_lead: lead not found {lead_id}")
        return None

    # ── Follow-up generation ───────────────────────────────────────────────

    def _stale_contacted_leads(self) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        result = []
        for lead in self.load_leads():
            if lead.get("status") != "contacted":
                continue
            last = lead.get("last_contact")
            if not last:
                result.append(lead)
                continue
            try:
                last_dt = datetime.fromisoformat(last)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                if last_dt <= cutoff:
                    result.append(lead)
            except ValueError:
                result.append(lead)
        return result

    def generate_followup(self, lead_id: str) -> str:
        leads = self.load_leads()
        lead = next((l for l in leads if l.get("id") == lead_id), None)
        if lead is None:
            self.log(f"generate_followup: lead not found {lead_id}")
            return ""

        language = lead.get("language") or "en"
        lang_label = {"en": "English", "ru": "Russian", "ar": "Arabic", "tr": "Turkish"}.get(language, "English")
        system_text = self._FOLLOWUP_SYSTEM.format(language=lang_label)

        context = (
            f"Lead name: {lead.get('name')}\n"
            f"Segment: {lead.get('segment')}\n"
            f"Last contact: {lead.get('last_contact')}\n"
            f"Platform: {lead.get('platform')}\n"
        )
        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=128,
                system=[{"type": "text", "text": system_text,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": context}],
            )
            followup = resp.content[0].text.strip()
        except Exception as exc:
            self.log(f"generate_followup error: {exc}")
            followup = f"Following up on our previous message — happy to share any new insights, {lead.get('name')}."

        self.log(f"Follow-up generated for {lead.get('name')!r}")
        return followup

    # ── CEO report ─────────────────────────────────────────────────────────

    def generate_ceo_report(self) -> dict[str, Any]:
        stats = self.get_pipeline_stats()
        stale = self._stale_contacted_leads()

        Config.ensure_dirs()
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        drafts_file = Config.LEADS_DIR / f"drafts_{date_str}.json"
        drafts_ready = 0
        if drafts_file.exists():
            with drafts_file.open(encoding="utf-8") as f:
                drafts_ready = len(json.load(f))

        recommendation = ""
        try:
            snapshot = json.dumps({
                "total_leads":     stats["total_leads"],
                "by_status":       stats["by_status"],
                "conversion_rate": stats["conversion_rate"],
                "followups_needed": len(stale),
                "drafts_ready":    drafts_ready,
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
            recommendation = "Review qualified leads and prioritise conversion follow-ups."

        report: dict[str, Any] = {
            "date":              date_str,
            "agent":             self.name,
            "pipeline":          stats,
            "drafts_ready":      drafts_ready,
            "followups_needed":  len(stale),
            "stale_lead_ids":    [l.get("id") for l in stale],
            "recommendation":    recommendation,
        }

        out_path = Config.REPORTS_DIR / f"outreach_report_{date_str}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        self.log(f"CEO report saved → {out_path.name}")

        self.report_to_ceo({
            "action":           "outreach_report_ready",
            "date":             date_str,
            "total_leads":      stats["total_leads"],
            "conversion_rate":  stats["conversion_rate"],
            "followups_needed": len(stale),
            "recommendation":   recommendation,
            "priority":         "high" if stale or stats["by_status"].get("qualified", 0) > 0 else "normal",
        })
        return report

    # ── Orchestration ──────────────────────────────────────────────────────

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "load")

        if action == "status_report":
            leads = self.load_leads()
            return {
                "status":           "READY",
                "priority":         "normal",
                "total_leads":      len(leads),
                "pending_approval": len(self._approval_queue),
            }

        if action == "load":
            leads = self.load_leads()
            status_dist: dict[str, int] = {}
            segment_dist: dict[str, int] = {}
            total_score = 0

            for lead in leads:
                s = lead.get("status", "unknown")
                status_dist[s] = status_dist.get(s, 0) + 1
                seg = lead.get("segment", "unknown")
                segment_dist[seg] = segment_dist.get(seg, 0) + 1
                total_score += lead.get("score") or 0

            avg_score = round(total_score / len(leads), 1) if leads else 0.0
            qualified = sum(1 for l in leads if l.get("status") in ("qualified", "converted"))

            self.log(f"Lead summary: {len(leads)} total, avg_score={avg_score}, qualified={qualified}")
            return {
                "status":        "OK",
                "total":         len(leads),
                "avg_score":     avg_score,
                "qualified":     qualified,
                "by_status":     status_dist,
                "by_segment":    segment_dist,
                "priority":      "high" if qualified > 0 else "normal",
            }

        if action == "add":
            lead = self.add_lead(task.get("lead", {}))
            return {"status": "OK", "lead_id": lead["id"], "score": lead["score"]}

        if action == "filter":
            results = self.filter_leads(
                status=task.get("status"),
                min_score=task.get("min_score", 0),
                segment=task.get("segment"),
            )
            return {"status": "OK", "count": len(results), "leads": results}

        if action == "draft":
            msg = self.draft_message(
                lead=task.get("lead", {}),
                analysis=task.get("analysis", {}),
                lang=task.get("lang", "en"),
            )
            return {"status": "PENDING_APPROVAL", "message": msg}

        if action == "draft_batch":
            channel = task.get("channel", "linkedin_first_touch")
            context = task.get("context")
            candidates = self.filter_leads(status="identified", min_score=50)
            if not candidates:
                self.log("draft_batch: no identified leads with score >= 50")
                return {"status": "NO_LEADS", "drafted": 0}

            drafts = self.draft_batch(candidates, channel=channel, context=context)

            self.report_to_ceo({
                "action":   "draft_batch_complete",
                "channel":  channel,
                "drafted":  len(drafts),
                "leads":    [d["lead_id"] for d in drafts],
                "priority": "normal",
            })
            return {"status": "OK", "drafted": len(drafts), "channel": channel}

        if action == "stats":
            stats = self.get_pipeline_stats()
            return {"status": "OK", **stats}

        if action == "followups":
            stale = self._stale_contacted_leads()
            results = []
            for lead in stale:
                msg = self.generate_followup(lead["id"])
                results.append({"lead_id": lead["id"], "name": lead.get("name"), "followup": msg})
            return {"status": "OK", "count": len(results), "followups": results}

        if action == "full":
            channel = task.get("channel", "linkedin_first_touch")
            context = task.get("context")

            new_leads = self.filter_leads(status="identified", min_score=50)
            drafted = 0
            if new_leads:
                drafted = len(self.draft_batch(new_leads, channel=channel, context=context))

            stale = self._stale_contacted_leads()
            followup_count = 0
            for lead in stale:
                self.generate_followup(lead["id"])
                followup_count += 1

            report = self.generate_ceo_report()
            return {
                "status":          "OK",
                "drafted":         drafted,
                "followups_sent":  followup_count,
                "total_leads":     report["pipeline"]["total_leads"],
                "conversion_rate": report["pipeline"]["conversion_rate"],
                "recommendation":  report["recommendation"],
            }

        return {"status": "UNKNOWN_ACTION", "action": action}

    # ── Legacy stubs ───────────────────────────────────────────────────────

    def draft_message(self, lead: dict, analysis: dict, lang: str) -> dict:
        return {
            "lead_id":  lead.get("id"),
            "lang":     lang,
            "segment":  lead.get("segment"),
            "status":   "PENDING_APPROVAL",
            "body":     None,
        }

    def select_persona(self, lang: str) -> str:
        mapping = {"ar": "Abdullah", "ru": "Dmitry", "tr": "Selim", "en": "James"}
        return mapping.get(lang, "James")

    def queue_for_approval(self, message: dict) -> None:
        message["status"] = "PENDING_APPROVAL"
        self._approval_queue.append(message)


# ── Empty lead factory ─────────────────────────────────────────────────────────

def _build_empty_lead() -> dict[str, Any]:
    return {
        "id":                   None,
        "name":                 "",
        "platform":             "referral",
        "profile_url":          None,
        "segment":              None,
        "language":             "en",
        "estimated_budget_usd": None,
        "contact_email":        None,
        "status":               "identified",
        "score":                0,
        "notes":                "",
        "created_at":           None,
        "last_contact":         None,
        "contact_history":      [],
    }
