from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode, urljoin

import anthropic
import requests
from bs4 import BeautifulSoup

from core.config import Config
from .base_agent import BaseAgent
from services.heat_calculator import HeatCalculator
from services.price_projector import PriceProjector

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

_EXCHANGE_URL = "https://api.exchangerate-api.com/v4/latest/USD"

_PROPERTY_TYPES = {"land", "apartment", "villa", "commercial", "industrial"}


class PropertyAgent(BaseAgent):
    """Scrapes property listings, converts prices to USD, and persists raw data."""

    DATA_SOURCES: list[dict[str, str]] = [
        {"name": "sahibinden",    "base_url": "https://www.sahibinden.com",    "type": "scrape"},
        {"name": "emlakjet",      "base_url": "https://www.emlakjet.com",       "type": "scrape"},
        {"name": "hurriyetemlak", "base_url": "https://www.hurriyetemlak.com", "type": "scrape"},
    ]

    SCORECARD_CRITERIA: dict[str, dict] = {
        "location_score":          {"weight": 0.20, "rule": False, "description": "City tier, district growth potential, neighborhood demand"},
        "zoning_score":            {"weight": 0.15, "rule": True,  "description": "Current zoning + projection upside"},
        "legal_cleanliness":       {"weight": 0.15, "rule": True,  "description": "Title deed status, no mortgage/injunction/annotation"},
        "infrastructure_proximity":{"weight": 0.12, "rule": True,  "description": "Distance to highway, airport, logistics hub"},
        "price_value_ratio":       {"weight": 0.12, "rule": True,  "description": "Price vs district average per m2 (USD)"},
        "rental_yield_potential":  {"weight": 0.10, "rule": False, "description": "Estimated gross rental yield %"},
        "growth_projection_5yr":   {"weight": 0.08, "rule": False, "description": "5-year value appreciation estimate"},
        "liquidity_score":         {"weight": 0.05, "rule": False, "description": "How easy to resell"},
        "gov_signal_score":        {"weight": 0.02, "rule": False, "description": "Active gov infrastructure or zoning signals nearby"},
        "news_context_score":      {"weight": 0.01, "rule": False, "description": "Recent news sentiment for this district"},
    }

    _DISTRICT_BASELINE_USD_M2: dict[str, float] = {
        "istanbul": 2500.0,
        "ankara":   1200.0,
        "izmir":    1800.0,
        "İzmir":    1800.0,
    }
    _DEFAULT_BASELINE_USD_M2 = 1000.0

    _ZONING_SCORES: dict[str, float] = {
        "commercial":   90.0,
        "land":         80.0,
        "industrial":   70.0,
        "villa":        65.0,
        "residential":  60.0,
        "apartment":    55.0,
        "agricultural": 40.0,
    }

    _REPORT_SYSTEM = (
        "You are a senior real estate advisor at Tradia Turkey Intelligence, "
        "advising high-net-worth foreign investors on Turkish property. "
        "Write a professional investment brief in English. "
        "Structure:\n"
        "1) Executive Summary (2 sentences)\n"
        "2) Key Strengths (3 bullet points)\n"
        "3) Risk Factors (2 bullet points)\n"
        "4) Investment Recommendation: BUY / WATCH / PASS with one sentence rationale.\n\n"
        "Then append EXACTLY these structured fields (no deviation from format):\n"
        "HIGHLIGHTS:\n- [key selling point 1]\n- [key selling point 2]\n- [key selling point 3]\n"
        "RISKS:\n- [risk 1]\n- [risk 2]\n"
        "IDEAL_FOR: [concise investor profile — e.g. 'Dubai-based investor seeking yield']\n\n"
        "Be specific, use the data provided, avoid generic language."
    )

    _MARKET_SUMMARY_SYSTEM = (
        "You are a senior market analyst at LandGold Intelligence. "
        "Write one concise paragraph (4-5 sentences) summarizing the current Turkish real estate "
        "market conditions based on the portfolio data provided. "
        "Focus on actionable insights for foreign investors. English only."
    )

    _SCORING_SYSTEM = (
        "You are a real estate scoring AI for LandGold, a Turkish property investment firm. "
        "Given a property listing and a scoring criterion, return a score from 0 to 100. "
        "Reply ONLY in this exact format:\n"
        "SCORE: <integer 0-100>\n"
        "REASON: <one sentence>\n"
        "Be strict, data-driven, and consistent."
    )

    # ── Search param → URL path for each source ────────────────────────────
    _SOURCE_PATHS: dict[str, str] = {
        "sahibinden":    "/satilik-arazi",
        "emlakjet":      "/satilik/arazi",
        "hurriyetemlak": "/satilik-arazi",
    }

    def __init__(self, name: str = "property", role: str = "Parcel Analyst", ceo_callback=None) -> None:
        super().__init__(name=name, role=role, ceo_callback=ceo_callback)
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._usd_rate: float | None = None
        self._parcels_analysed: int = 0
        self._llm = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.heat = HeatCalculator()
        self.proj = PriceProjector()

    # ── Currency ───────────────────────────────────────────────────────────

    def fetch_usd_rate(self) -> float:
        try:
            resp = self._session.get(_EXCHANGE_URL, timeout=Config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            rate = float(data["rates"]["TRY"])
            self._usd_rate = rate
            self.log(f"USD/TRY rate: {rate}")
            return rate
        except Exception as exc:
            self.log(f"Exchange rate error: {exc} — using fallback 32.0")
            self._usd_rate = 32.0
            return self._usd_rate

    def try_to_usd(self, amount_try: float) -> float:
        if self._usd_rate is None:
            self.fetch_usd_rate()
        return round(amount_try / self._usd_rate, 2)

    # ── Parsing ────────────────────────────────────────────────────────────

    def parse_listing(self, html: str, source_name: str) -> list[dict[str, Any]]:
        """
        Extract property dicts from a search-results HTML page.
        Each source has a different DOM — we attempt common patterns and fall
        back to None for any field that cannot be found.  Never raises.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return []

        listings: list[dict[str, Any]] = []
        cards = _find_cards(soup, source_name)

        for card in cards:
            try:
                prop = _build_empty_property()
                prop["id"]          = str(uuid.uuid4())
                prop["fetched_at"]  = datetime.now(timezone.utc).isoformat()

                prop["title"]       = _safe_text(card, _SELECTORS[source_name]["title"])
                prop["listing_url"] = _safe_href(card, _SELECTORS[source_name]["url"], source_name)
                prop["raw_description"] = _safe_text(card, _SELECTORS[source_name].get("desc", ""))

                price_raw = _safe_text(card, _SELECTORS[source_name]["price"])
                prop["price_try"] = _parse_price(price_raw)
                if prop["price_try"] is not None:
                    prop["price_usd"] = self.try_to_usd(prop["price_try"])

                area_raw = _safe_text(card, _SELECTORS[source_name].get("area", ""))
                prop["area_m2"] = _parse_area(area_raw)

                loc_raw = _safe_text(card, _SELECTORS[source_name].get("location", ""))
                prop["location"] = _parse_location(loc_raw)

                listings.append(prop)
            except Exception:
                continue  # never crash on a single bad card

        return listings

    def fetch_listings(
        self,
        source_name: str,
        search_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        source = next((s for s in self.DATA_SOURCES if s["name"] == source_name), None)
        if source is None:
            self.log(f"Unknown source: {source_name!r}")
            return []

        path   = self._SOURCE_PATHS.get(source_name, "")
        qs     = _build_query(source_name, search_params)
        url    = source["base_url"] + path + ("?" + urlencode(qs) if qs else "")

        self.log(f"Fetching {source_name}: {url}")
        try:
            resp = self._session.get(url, timeout=Config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:
            self.log(f"Fetch error {source_name}: {exc}")
            return []

        listings = self.parse_listing(html, source_name)

        # Post-filter by search_params client-side (site may ignore unknown QS)
        max_usd    = search_params.get("max_price_usd")
        min_area   = search_params.get("min_area_m2")
        prop_type  = search_params.get("property_type")

        filtered: list[dict[str, Any]] = []
        for p in listings:
            if max_usd is not None and p["price_usd"] is not None:
                if p["price_usd"] > max_usd:
                    continue
            if min_area is not None and p["area_m2"] is not None:
                if p["area_m2"] < min_area:
                    continue
            if prop_type is not None and p["property_type"] is not None:
                if p["property_type"] != prop_type:
                    continue
            p["source"] = source_name
            filtered.append(p)

        self.log(f"{source_name}: {len(filtered)}/{len(listings)} listings after filter")
        return filtered

    # ── Persistence ────────────────────────────────────────────────────────

    def save_listings(self, listings: list[dict[str, Any]]) -> None:
        Config.ensure_dirs()
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = Config.PROPERTIES_DIR / f"raw_{date}.json"

        existing: list[dict] = []
        if path.exists():
            with path.open(encoding="utf-8") as f:
                existing = json.load(f)

        merged = _dedup_listings(existing + listings)
        if not merged:
            self.log("No listings to save — skipping file write")
            return
        with path.open("w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        self.log(f"Saved {len(merged)} listings → {path.name}")

    # ── Scoring ────────────────────────────────────────────────────────────

    def score_criterion(self, prop: dict[str, Any], criterion: str) -> float:
        """Returns 0-100 float for one criterion. Rule-based where possible, AI otherwise."""
        meta = self.SCORECARD_CRITERIA.get(criterion, {})

        # ── Rule-based ─────────────────────────────────────────────────────
        if criterion == "legal_cleanliness":
            if not prop.get("has_title_deed"):
                return 0.0
            issues = prop.get("title_deed_issues") or []
            return max(0.0, 100.0 - 20.0 * len(issues))

        if criterion == "zoning_score":
            zoning = (prop.get("zoning") or prop.get("property_type") or "").lower()
            return self._ZONING_SCORES.get(zoning, 50.0)

        if criterion == "infrastructure_proximity":
            km = prop.get("highway_distance_km")
            if km is None:
                return 40.0
            if km < 1:
                return 100.0
            if km < 5:
                return 70.0
            if km < 20:
                return 40.0
            return 10.0

        if criterion == "price_value_ratio":
            price_usd = prop.get("price_usd")
            area_m2   = prop.get("area_m2")
            if not price_usd or not area_m2:
                return 50.0
            city      = ((prop.get("location") or {}).get("city") or "").lower()
            baseline  = self._DISTRICT_BASELINE_USD_M2.get(city, self._DEFAULT_BASELINE_USD_M2)
            ratio     = (price_usd / area_m2) / baseline
            return max(0.0, min(100.0, 120.0 - ratio * 70.0))

        # ── AI-scored ──────────────────────────────────────────────────────
        return self._ai_score(prop, criterion, meta.get("description", ""))

    def _ai_score(self, prop: dict[str, Any], criterion: str, description: str) -> float:
        """Call claude-sonnet-4-6 to score one criterion. Returns 50.0 on failure."""
        compact = {
            "title":     prop.get("title"),
            "city":      (prop.get("location") or {}).get("city"),
            "district":  (prop.get("location") or {}).get("district"),
            "type":      prop.get("property_type"),
            "area_m2":   prop.get("area_m2"),
            "price_usd": prop.get("price_usd"),
            "zoning":    prop.get("zoning"),
        }
        user = (
            f"Criterion: {criterion}\n"
            f"Description: {description}\n\n"
            f"Property:\n{json.dumps(compact, ensure_ascii=False, indent=2)}"
        )
        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=128,
                system=[{"type": "text", "text": self._SCORING_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
            )
            raw = resp.content[0].text.strip()
            for line in raw.splitlines():
                if line.upper().startswith("SCORE:"):
                    return max(0.0, min(100.0, float(line.split(":", 1)[1].strip())))
        except Exception as exc:
            self.log(f"AI score error [{criterion}]: {exc}")
        return 50.0

    def calculate_total_score(self, prop: dict[str, Any]) -> dict[str, Any]:
        criteria_breakdown: dict[str, dict[str, float]] = {}
        for criterion, meta in self.SCORECARD_CRITERIA.items():
            raw      = self.score_criterion(prop, criterion)
            weighted = round(raw * meta["weight"], 4)
            criteria_breakdown[criterion] = {"raw_score": round(raw, 2), "weighted": weighted}

        total = round(sum(v["weighted"] for v in criteria_breakdown.values()), 2)
        total = max(0.0, min(100.0, total))

        if total >= 80:
            grade = "A"
        elif total >= 65:
            grade = "B"
        elif total >= 50:
            grade = "C"
        else:
            grade = "D"

        ranked = sorted(criteria_breakdown.items(), key=lambda x: x[1]["weighted"], reverse=True)
        return {
            "total":              total,
            "grade":              grade,
            "criteria_breakdown": criteria_breakdown,
            "strengths":          [c for c, _ in ranked[:3]],
            "weaknesses":         [c for c, _ in ranked[-3:]],
        }

    def score_all_listings(self, listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for i, prop in enumerate(listings):
            self.log(f"Scoring {i+1}/{len(listings)}: {(prop.get('title') or 'unknown')[:50]!r}")
            prop["scorecard"] = self.calculate_total_score(prop)
        return listings

    # ── Scored persistence ─────────────────────────────────────────────────

    def _load_latest_raw(self) -> tuple[list[dict[str, Any]], None]:
        candidates = sorted(Config.PROPERTIES_DIR.glob("raw_*.json"), reverse=True)
        for candidate in candidates:
            with candidate.open(encoding="utf-8") as f:
                data = json.load(f)
            if data:
                return data, candidate
        return [], None

    def _save_scored(self, listings: list[dict[str, Any]]) -> "Path":
        from pathlib import Path
        Config.ensure_dirs()
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = Config.PROPERTIES_DIR / f"scored_{date}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(listings, f, ensure_ascii=False, indent=2)
        self.log(f"Saved {len(listings)} scored listings → {path.name}")
        return path

    # ── Report generation ──────────────────────────────────────────────────

    def _load_latest_scored(self) -> list[dict[str, Any]]:
        candidates = sorted(Config.PROPERTIES_DIR.glob("scored_*.json"), reverse=True)
        if not candidates:
            return []
        with candidates[0].open(encoding="utf-8") as f:
            return json.load(f)

    def generate_property_report(self, prop: dict[str, Any]) -> dict[str, Any]:
        """Call LLM to produce multilingual investment briefs for one scored property."""
        sc = prop.get("scorecard", {})
        loc = prop.get("location") or {}

        _LANGS = {
            "en": "English",
            "ru": "Russian",
            "ar": "Arabic",
            "tr": "Turkish",
        }

        briefs: dict[str, str] = {}
        recommendation = "WATCH"

        for lang_code, lang_name in _LANGS.items():
            prompt = (
                f"You are a senior real estate advisor at Tradia Turkey.\n"
                f"Write a professional 3-sentence investment brief in {lang_name} ONLY.\n"
                f"Never mix languages.\n\n"
                f"Property: {prop.get('title')}\n"
                f"Location: {loc.get('city')} - {loc.get('district')}\n"
                f"Price: ${prop.get('price_usd', 0):,.0f} USD\n"
                f"Area: {prop.get('area_m2')} m²\n"
                f"Score: {sc.get('total', 0):.1f}/100\n"
                f"Grade: {sc.get('grade', 'C')}\n"
                f"Strengths: {sc.get('strengths', [])}\n\n"
                f"Write: 1 sentence executive summary, 1 sentence key strength, "
                f"1 sentence recommendation.\n"
                f"End with: VERDICT: BUY or WATCH or PASS"
            )
            try:
                resp = self._llm.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}],
                )
                text    = resp.content[0].text.strip().replace("**", "")
                verdict = "WATCH"
                if "VERDICT: BUY"  in text: verdict = "BUY"
                elif "VERDICT: PASS" in text: verdict = "PASS"
                briefs[f"brief_{lang_code}"] = text.split("VERDICT:")[0].strip()
                if lang_code == "en":
                    recommendation = verdict
            except Exception as exc:
                self.log(f"generate_property_report({lang_code}) error: {exc}")
                briefs[f"brief_{lang_code}"] = ""

        return {
            **briefs,
            "brief":          briefs.get("brief_en", ""),  # backwards compat
            "recommendation": recommendation,
            "highlights":     [],
            "risks":          [],
            "ideal_for":      "",
        }

    def build_top_opportunities(self, n: int = 5) -> list[dict[str, Any]]:
        """Load scored listings, keep A/B grades, sort by score, enrich top-n with reports."""
        all_scored = self._load_latest_scored()
        eligible = [
            p for p in all_scored
            if (p.get("scorecard") or {}).get("grade") in ("A", "B")
        ]
        eligible.sort(
            key=lambda p: (p.get("scorecard") or {}).get("total", 0),
            reverse=True,
        )
        top = eligible[:n]
        for prop in top:
            self.log(f"Generating report: {(prop.get('title') or 'unknown')[:50]!r}")
            prop["report"] = self.generate_property_report(prop)
        return top

    def generate_ceo_report(self) -> dict[str, Any]:
        """Build full portfolio report, save to disk, forward to CEO."""
        all_scored = self._load_latest_scored()

        grades = [p.get("scorecard", {}).get("grade", "D") for p in all_scored]
        grade_counts = {g: grades.count(g) for g in ("A", "B", "C", "D")}
        avg_score = (
            round(sum((p.get("scorecard") or {}).get("total", 0) for p in all_scored) / len(all_scored), 1)
            if all_scored else 0.0
        )

        top_opportunities = self.build_top_opportunities(n=5)

        market_summary = ""
        if all_scored:
            portfolio_snapshot = {
                "total_listings": len(all_scored),
                "grade_distribution": grade_counts,
                "avg_score": avg_score,
                "sample_cities": list({
                    (p.get("location") or {}).get("city")
                    for p in all_scored[:20]
                    if (p.get("location") or {}).get("city")
                })[:5],
            }
            try:
                resp = self._llm.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=256,
                    system=[{"type": "text", "text": self._MARKET_SUMMARY_SYSTEM,
                             "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content":
                               "Portfolio data:\n" + json.dumps(portfolio_snapshot, indent=2)}],
                )
                market_summary = resp.content[0].text.strip()
            except Exception as exc:
                self.log(f"Market summary error: {exc}")

        report: dict[str, Any] = {
            "date":            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "agent":           self.name,
            "total_analyzed":  len(all_scored),
            "grade_a_count":   grade_counts["A"],
            "grade_b_count":   grade_counts["B"],
            "avg_score":       avg_score,
            "top_opportunities": [
                {
                    "title":          p.get("title"),
                    "location":       p.get("location"),
                    "price_usd":      p.get("price_usd"),
                    "area_m2":        p.get("area_m2"),
                    "photo_url":      p.get("photo_url"),
                    "score":          (p.get("scorecard") or {}).get("total"),
                    "grade":          (p.get("scorecard") or {}).get("grade"),
                    "recommendation": (p.get("report") or {}).get("recommendation", "WATCH"),
                    "brief":          (p.get("report") or {}).get("brief", ""),
                    "brief_en":       (p.get("report") or {}).get("brief_en", ""),
                    "brief_ru":       (p.get("report") or {}).get("brief_ru", ""),
                    "brief_ar":       (p.get("report") or {}).get("brief_ar", ""),
                    "brief_tr":       (p.get("report") or {}).get("brief_tr", ""),
                    "highlights":     (p.get("report") or {}).get("highlights", []),
                    "risks":          (p.get("report") or {}).get("risks", []),
                    "ideal_for":      (p.get("report") or {}).get("ideal_for", ""),
                }
                for p in top_opportunities
            ],
            "market_summary":  market_summary,
        }

        Config.ensure_dirs()
        date_str = report["date"]
        out_path = Config.REPORTS_DIR / f"property_report_{date_str}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        self.log(f"CEO report saved → {out_path.name}")

        self.report_to_ceo({
            "action":          "property_report_ready",
            "date":            date_str,
            "total_analyzed":  report["total_analyzed"],
            "grade_a_count":   report["grade_a_count"],
            "grade_b_count":   report["grade_b_count"],
            "avg_score":       report["avg_score"],
            "top_count":       len(top_opportunities),
            "priority":        "high" if grade_counts["A"] > 0 else "normal",
        })
        return report

    # ── Orchestration ──────────────────────────────────────────────────────

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "fetch")
        params = task.get("params", {})

        if action == "status_report":
            return {
                "status":            "READY",
                "priority":          "normal",
                "parcels_analysed":  self._parcels_analysed,
                "usd_rate":          self._usd_rate,
            }

        if action in ("fetch", "analyse"):
            self.fetch_usd_rate()
            all_listings: list[dict[str, Any]] = []
            for source in self.DATA_SOURCES:
                results = self.fetch_listings(source["name"], params)
                all_listings.extend(results)

            merged = _dedup_listings(all_listings)
            self.save_listings(merged)
            self._parcels_analysed += len(merged)

            self.report_to_ceo({
                "action":   "fetch_complete",
                "count":    len(merged),
                "sources":  [s["name"] for s in self.DATA_SOURCES],
                "priority": "normal",
            })
            return {"status": "OK", "count": len(merged)}

        if action == "score":
            raw, raw_path = self._load_latest_raw()
            if not raw:
                self.log("No raw listings found — run 'fetch' first")
                return {"status": "NO_DATA", "action": action}

            scored   = self.score_all_listings(raw)
            out_path = self._save_scored(scored)

            grades   = [p["scorecard"]["grade"] for p in scored]
            dist     = {g: grades.count(g) for g in ("A", "B", "C", "D")}
            avg_score = round(sum(p["scorecard"]["total"] for p in scored) / len(scored), 1)

            self.report_to_ceo({
                "action":    "score_complete",
                "count":     len(scored),
                "avg_score": avg_score,
                "grades":    dist,
                "file":      str(out_path),
                "priority":  "normal",
            })
            return {"status": "OK", "count": len(scored), "avg_score": avg_score, "grades": dist}

        if action == "report":
            if not self._load_latest_scored():
                self.log("No scored listings found — run 'score' first")
                return {"status": "NO_DATA", "action": action}
            report = self.generate_ceo_report()
            return {
                "status":         "OK",
                "total_analyzed": report["total_analyzed"],
                "grade_a_count":  report["grade_a_count"],
                "grade_b_count":  report["grade_b_count"],
                "avg_score":      report["avg_score"],
                "top_count":      len(report["top_opportunities"]),
            }

        if action == "full":
            # fetch → score_all → generate_ceo_report
            self.fetch_usd_rate()
            all_listings: list[dict[str, Any]] = []
            for source in self.DATA_SOURCES:
                results = self.fetch_listings(source["name"], params)
                all_listings.extend(results)

            merged = _dedup_listings(all_listings)
            self.save_listings(merged)          # merges with seed data in raw file
            self._parcels_analysed += len(merged)

            # Score the full raw file (seed + any freshly fetched), not just merged
            raw_full, _ = self._load_latest_raw()
            scored   = self.score_all_listings(raw_full)
            self._save_scored(scored)

            report = self.generate_ceo_report()
            return {
                "status":         "OK",
                "fetched":        len(merged),
                "scored":         len(scored),
                "grade_a_count":  report["grade_a_count"],
                "grade_b_count":  report["grade_b_count"],
                "avg_score":      report["avg_score"],
                "top_count":      len(report["top_opportunities"]),
            }

        return {"status": "UNKNOWN_ACTION", "action": action}

    # ── İlçe istihbarat servisi ────────────────────────────────────────────

    def get_ilce_intel(self, ilce_kodu: str) -> dict:
        """
        Bir ilçenin tüm istihbarat verisini topla.
        Kontrat: docs/havuz/ADIM-2-ISI-PROJEKSIYON-V1.md
        """
        from zoneinfo import ZoneInfo
        TR = ZoneInfo("Europe/Istanbul")
        try:
            temp = self.heat.get_temperature(ilce_kodu)
            proj_3 = self.proj.project(ilce_kodu, 3)
            proj_12 = self.proj.project(ilce_kodu, 12)
            events = self.heat.get_active_events(ilce_kodu)

            return {
                "ilce": ilce_kodu,
                "isi_son_6_ay": temp["mevcut_isi"],
                "tarihsel_ortalama": temp["tarihsel_ortalama"],
                "sicaklik_orani": temp["sicaklik_orani"],
                "seviye": temp["seviye"],
                "projeksiyon_3_ay": proj_3,
                "projeksiyon_12_ay": proj_12,
                "aktif_olaylar": events,
                "guncelleme_zamani": datetime.now(TR).isoformat(),
            }
        except Exception as e:
            return {
                "ilce": ilce_kodu,
                "hata": str(e),
                "guncelleme_zamani": datetime.now(TR).isoformat(),
            }

    # ── Legacy stubs (kept for CEO orchestration compatibility) ────────────

    def analyse(self, parcel: dict[str, Any]) -> dict[str, Any]:
        return parcel

    def calculate_roi(self, parcel: dict, gov_signal: str) -> dict:
        pass

    def score_risk(self, constraints: list[str], proximity_m: float, road_type: str) -> dict:
        pass


# ── Source-specific CSS selectors ─────────────────────────────────────────────
# These represent best-effort patterns; sites change layouts frequently.
_SELECTORS: dict[str, dict[str, str]] = {
    "sahibinden": {
        "title":    ".classifiedTitle",
        "price":    ".price",
        "area":     ".size",
        "location": ".cityArea",
        "url":      "a.classifiedTitle",
        "desc":     ".classifiedDescription",
    },
    "emlakjet": {
        "title":    ".listing-card__title",
        "price":    ".listing-card__price",
        "area":     ".listing-card__area",
        "location": ".listing-card__location",
        "url":      "a.listing-card__link",
        "desc":     ".listing-card__description",
    },
    "hurriyetemlak": {
        "title":    ".listing-text--title",
        "price":    ".listing-price",
        "area":     ".listing-text--metrekare",
        "location": ".listing-text--location",
        "url":      "a.listing-item-link",
        "desc":     ".listing-text--description",
    },
}

_CARD_SELECTORS: dict[str, str] = {
    "sahibinden":    ".searchResultsItem",
    "emlakjet":      ".listing-card",
    "hurriyetemlak": ".listing-item",
}


def _find_cards(soup: BeautifulSoup, source_name: str) -> list:
    sel = _CARD_SELECTORS.get(source_name, "article")
    cards = soup.select(sel)
    if not cards:
        # generic fallback
        cards = soup.find_all(["article", "li"], class_=lambda c: c and "listing" in c.lower())
    return cards[:50]


# ── Field extractors ──────────────────────────────────────────────────────────

def _safe_text(node: Any, selector: str) -> str:
    if not selector:
        return ""
    try:
        el = node.select_one(selector)
        return el.get_text(" ", strip=True) if el else ""
    except Exception:
        return ""


def _safe_href(node: Any, selector: str, source_name: str) -> str | None:
    if not selector:
        return None
    try:
        el    = node.select_one(selector)
        href  = el.get("href", "") if el else ""
        if href and not href.startswith("http"):
            base = next(s["base_url"] for s in PropertyAgent.DATA_SOURCES if s["name"] == source_name)
            href = urljoin(base, href)
        return href or None
    except Exception:
        return None


def _parse_price(raw: str) -> float | None:
    try:
        cleaned = "".join(c for c in raw if c.isdigit() or c == ".")
        cleaned = cleaned.replace(".", "")
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def _parse_area(raw: str) -> float | None:
    try:
        import re
        match = re.search(r"[\d.,]+", raw.replace(",", "."))
        return float(match.group().replace(".", "").replace(",", ".")) if match else None
    except Exception:
        return None


def _parse_location(raw: str) -> dict[str, str | None]:
    parts = [p.strip() for p in raw.replace("/", ",").split(",") if p.strip()]
    return {
        "city":         parts[0] if len(parts) > 0 else None,
        "district":     parts[1] if len(parts) > 1 else None,
        "neighborhood": parts[2] if len(parts) > 2 else None,
    }


def _build_empty_property() -> dict[str, Any]:
    return {
        "id":                  None,
        "title":               None,
        "price_try":           None,
        "price_usd":           None,
        "area_m2":             None,
        "location":            {"city": None, "district": None, "neighborhood": None},
        "property_type":       None,
        "zoning":              None,
        "road_type":           None,
        "highway_distance_km": None,
        "has_title_deed":      None,
        "title_deed_issues":   [],
        "listing_url":         None,
        "raw_description":     None,
        "fetched_at":          None,
        "source":              None,
    }


def _dedup_listings(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen:   set[str] = set()
    unique: list[dict[str, Any]] = []
    for p in listings:
        title = (p.get("title") or "").lower().strip()
        city  = (p.get("location") or {}).get("city") or ""
        key   = f"{title}|{city.lower()}"
        if key and key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _build_query(source_name: str, params: dict[str, Any]) -> dict[str, str]:
    city      = params.get("city", "")
    prop_type = params.get("property_type", "")
    max_price = params.get("max_price_usd")

    if source_name == "sahibinden":
        q: dict[str, str] = {}
        if city:
            q["searchText"] = city
        return q

    if source_name == "emlakjet":
        q = {}
        if city:
            q["city"] = city
        return q

    if source_name == "hurriyetemlak":
        q = {}
        if city:
            q["where"] = city
        return q

    return {}
