"""
ResearchAgent — Mega-project intelligence and property target generation.

Tracks 8 Marmara mega-projects, fetches & classifies news signals per project,
produces property target profiles. No scheduled run — triggered by orchestrator
or manually via: python main.py --agent research --task marmara|full|project:<id>
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
import feedparser
import requests
from bs4 import BeautifulSoup

from core.config import Config
from .base_agent import BaseAgent

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Cache-Control":   "no-cache",
}

RESEARCH_DIR = Config.DATA_PATH / "research"


class ResearchAgent(BaseAgent):

    MEGA_PROJECTS: list[dict[str, Any]] = [
        {
            "id":               "kanal-istanbul",
            "name":             "Kanal İstanbul",
            "region":           "Marmara",
            "districts":        ["Arnavutköy", "Başakşehir", "Küçükçekmece", "Avcılar"],
            "status":           "planning",
            "keywords_tr":      ["kanal istanbul", "yenişehir imar", "sazlıbosna", "kanal güzergah"],
            "keywords_en":      ["istanbul canal", "canal project istanbul", "new istanbul waterway"],
            "impact_radius_km": 15,
            "tradia_score":     92,
        },
        {
            "id":               "kuzey-marmara-otoyolu",
            "name":             "Kuzey Marmara Otoyolu",
            "region":           "Marmara",
            "districts":        ["Arnavutköy", "Çatalca", "Silivri", "Kırklareli"],
            "status":           "active",
            "keywords_tr":      ["kuzey marmara otoyolu", "kmo", "otoyol arnavutköy", "kuzey çevre"],
            "keywords_en":      ["north marmara highway", "istanbul ring road", "northern bypass"],
            "impact_radius_km": 10,
            "tradia_score":     85,
        },
        {
            "id":               "istanbul-havalimani",
            "name":             "İstanbul Havalimanı Bölgesi",
            "region":           "Marmara",
            "districts":        ["Arnavutköy", "Eyüpsultan", "Başakşehir"],
            "status":           "active",
            "keywords_tr":      ["istanbul havalimanı", "havalimanı bölgesi", "iata ist", "arnavutköy metro"],
            "keywords_en":      ["istanbul airport", "IST airport zone", "airport district development"],
            "impact_radius_km": 20,
            "tradia_score":     90,
        },
        {
            "id":               "gebze-oiz",
            "name":             "Gebze Organize Sanayi Bölgesi Genişlemesi",
            "region":           "Marmara",
            "districts":        ["Gebze", "Dilovası", "Darıca"],
            "status":           "active",
            "keywords_tr":      ["gebze osb", "gebze sanayi", "dilovası", "kocaeli organize sanayi"],
            "keywords_en":      ["gebze industrial zone", "kocaeli OIZ", "marmara industrial"],
            "impact_radius_km": 8,
            "tradia_score":     82,
        },
        {
            "id":               "cerkezkoy-trakya",
            "name":             "Çerkezköy-Trakya Sanayi Aksı",
            "region":           "Marmara",
            "districts":        ["Çerkezköy", "Tekirdağ", "Muratlı", "Çorlu"],
            "status":           "active",
            "keywords_tr":      ["çerkezköy osb", "trakya sanayi", "çorlu tekstil", "tekirdağ lojistik"],
            "keywords_en":      ["thrace industrial", "cerkezkoy OIZ", "trakya logistics corridor"],
            "impact_radius_km": 12,
            "tradia_score":     78,
        },
        {
            "id":               "bursa-nilufer",
            "name":             "Bursa Nilüfer Teknoloji ve Sanayi Bölgesi",
            "region":           "Marmara",
            "districts":        ["Nilüfer", "Osmangazi", "Gemlik"],
            "status":           "active",
            "keywords_tr":      ["bursa osb", "nilüfer teknoloji", "bursa otomotiv", "uludağ osb"],
            "keywords_en":      ["bursa technology zone", "bursa automotive", "nilüfer OIZ"],
            "impact_radius_km": 10,
            "tradia_score":     83,
        },
        {
            "id":               "yavuz-sultan-selim-koprusu",
            "name":             "Yavuz Sultan Selim Köprüsü Etki Bölgesi",
            "region":           "Marmara",
            "districts":        ["Sarıyer", "Beykoz", "Garipçe", "Poyrazköy"],
            "status":           "active",
            "keywords_tr":      ["3. köprü", "yavuz sultan selim", "kuzey istanbul", "garipçe"],
            "keywords_en":      ["third bridge istanbul", "yavuz sultan selim bridge", "northern istanbul"],
            "impact_radius_km": 15,
            "tradia_score":     80,
        },
        {
            "id":               "osmangazi-koprusu",
            "name":             "Osmangazi Köprüsü — Gemlik Körfezi Aksı",
            "region":           "Marmara",
            "districts":        ["Gemlik", "Orhangazi", "İznik", "Yalova"],
            "status":           "active",
            "keywords_tr":      ["osmangazi köprüsü", "gemlik liman", "orhangazi", "yalova gelişim"],
            "keywords_en":      ["osmangazi bridge", "gemlik port", "gulf of izmit development"],
            "impact_radius_km": 20,
            "tradia_score":     79,
        },
    ]

    SEARCH_SOURCES: list[dict] = [
        {"name": "AA Ekonomi",        "url": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",        "type": "rss", "priority": 1},
        {"name": "BİK Resmi İlanlar", "url": "https://bik.gov.tr/rss",                                  "type": "rss", "priority": 1},
        {"name": "Hürriyet Gündem",   "url": "https://www.hurriyet.com.tr/rss/gundem",                  "type": "rss", "priority": 2},
        {"name": "NTV Gündem",        "url": "https://www.ntv.com.tr/gundem.rss",                       "type": "rss", "priority": 2},
        {"name": "Sabah Ekonomi",     "url": "https://www.sabah.com.tr/rss/ekonomi.xml",                "type": "rss", "priority": 2},
        {"name": "Dünya Gazetesi",    "url": "https://www.dunya.com/rss",                               "type": "rss", "priority": 2},
        {"name": "Yeni Şafak",        "url": "https://www.yenisafak.com/rss",                           "type": "rss", "priority": 3},
        {"name": "Cumhuriyet",        "url": "https://www.cumhuriyet.com.tr/rss/son_dakika.xml",        "type": "rss", "priority": 3},
    ]

    def __init__(
        self,
        name: str = "research",
        role: str = "Regional Intelligence",
        ceo_callback=None,
    ) -> None:
        super().__init__(name=name, role=role, ceo_callback=ceo_callback)
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._llm = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _fetch_rss(self, url: str) -> list[dict[str, str]]:
        try:
            resp = self._session.get(url, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            self.log(f"RSS error {url}: {exc}")
            return []

        items = []
        for entry in feed.entries:
            items.append({
                "title":     entry.get("title", "").strip(),
                "link":      entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary":   BeautifulSoup(
                    entry.get("summary", ""), "html.parser"
                ).get_text(" ", strip=True)[:500],
            })
        return items

    def _keyword_match(self, text: str, keywords: list[str]) -> bool:
        t = text.lower()
        return any(kw.lower() in t for kw in keywords)

    def _parse_price_signal(self, text: str) -> float:
        """Extract numeric % from strings like '+15%' or '-5%'. Returns 0.0 on failure."""
        m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", str(text))
        return float(m.group(1)) if m else 0.0

    def load_archive(self, region: str) -> dict[str, Any]:
        """Load static intelligence archive for a region, keyed by project_id."""
        archive_path = RESEARCH_DIR / "projects" / f"{region}_archive.json"
        if not archive_path.exists():
            self.log(f"No archive found for region: {region}")
            return {}
        try:
            data = json.loads(archive_path.read_text(encoding="utf-8"))
            projects = {p["id"]: p for p in data.get("projects", [])}
            self.log(f"Loaded archive: {region} ({len(projects)} projects)")
            return projects
        except Exception as exc:
            self.log(f"load_archive error ({region}): {exc}")
            return {}

    # ── Core methods ───────────────────────────────────────────────────────

    def fetch_project_news(self, project: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch all SEARCH_SOURCES and return items matching project keywords."""
        all_keywords = project["keywords_tr"] + project["keywords_en"]
        district_keywords = [d.lower() for d in project["districts"]]
        matches: list[dict[str, Any]] = []

        for source in self.SEARCH_SOURCES:
            url = source["url"]
            self.log(f"[{project['id']}] Fetching {source['name']} ({url})")
            items = self._fetch_rss(url)
            self.log(f"[{project['id']}] {source['name']}: {len(items)} items fetched")
            for item in items:
                combined = (item.get("title", "") + " " + item.get("summary", "")).lower()
                if self._keyword_match(combined, all_keywords) or \
                   self._keyword_match(combined, district_keywords):
                    item["project_id"]   = project["id"]
                    item["source_name"]  = source["name"]
                    item["source_url"]   = url
                    item["fetched_at"]   = datetime.now(timezone.utc).isoformat()
                    matches.append(item)
            time.sleep(0.3)

        self.log(f"[{project['id']}] {len(matches)} matching items found")
        return matches

    def score_news_relevance(self, item: dict[str, Any], project: dict[str, Any]) -> int:
        """Keyword-based relevance score 0-100."""
        score = 0
        all_keywords = project["keywords_tr"] + project["keywords_en"]
        title   = item.get("title", "").lower()
        summary = item.get("summary", "").lower()

        if self._keyword_match(title, all_keywords):
            score += 40
        if self._keyword_match(summary, all_keywords):
            score += 30

        # Published within last 30 days
        pub = item.get("published", "")
        if pub:
            try:
                import email.utils
                pub_dt = datetime(*email.utils.parsedate(pub)[:6], tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - pub_dt).days
                if age_days <= 30:
                    score += 20
            except Exception:
                pass

        district_kw = [d.lower() for d in project["districts"]]
        if self._keyword_match(title + " " + summary, district_kw):
            score += 10

        return min(score, 100)

    def classify_news_impact(self, item: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
        """Call Claude to classify impact, urgency, affected zones and price signal."""
        prompt = (
            f"News title: {item.get('title', '')}\n"
            f"News summary: {item.get('summary', '')}\n"
            f"Published: {item.get('published', 'unknown')}\n\n"
            "Return ONLY valid JSON with these exact keys:\n"
            '{"impact": "positive|negative|neutral", '
            '"urgency": "immediate|medium|long-term", '
            '"affected_zones": ["zone1", "zone2"], '
            '"price_signal": "+X% or -X%", '
            '"summary": "one sentence in English"}'
        )
        system = (
            f"You are a real estate intelligence analyst. "
            f"Given a news item about the project '{project['name']}' in Turkey, classify:\n"
            "1. IMPACT: positive / negative / neutral for property prices\n"
            "2. URGENCY: immediate (0-3 months) / medium (3-12 months) / long-term (1+ years)\n"
            "3. AFFECTED_ZONES: list of specific neighborhoods or districts affected\n"
            "4. PRICE_SIGNAL: estimated % price impact (+X% or -X%)\n"
            "5. SUMMARY: one sentence in English\n"
            "Return as JSON only."
        )
        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception as exc:
            self.log(f"classify_news_impact error: {exc}")
            return {
                "impact":         "neutral",
                "urgency":        "medium",
                "affected_zones": project["districts"][:2],
                "price_signal":   "+0%",
                "summary":        item.get("title", "")[:120],
            }

    def research_project(self, project_id: str) -> dict[str, Any]:
        """Full research pipeline for one mega-project."""
        project = next((p for p in self.MEGA_PROJECTS if p["id"] == project_id), None)
        if not project:
            self.log(f"Project not found: {project_id}")
            return {"error": f"unknown project: {project_id}"}

        self.log(f"Researching project: {project['name']}")
        raw_items = self.fetch_project_news(project)

        enriched: list[dict[str, Any]] = []
        for item in raw_items:
            relevance = self.score_news_relevance(item, project)
            self.log(f"  Classifying: {item.get('title', '')[:60]!r} (relevance={relevance})")
            classification = self.classify_news_impact(item, project)
            enriched.append({
                **item,
                "relevance_score": relevance,
                "classification":  classification,
            })

        enriched.sort(key=lambda x: x["relevance_score"], reverse=True)
        top_signal = enriched[0] if enriched else None

        # Overall sentiment — majority vote
        sentiments = [e["classification"].get("impact", "neutral") for e in enriched]
        sentiment_counts = {s: sentiments.count(s) for s in set(sentiments)} if sentiments else {}
        overall_sentiment = max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else "neutral"

        # Average price signal
        price_signals = [self._parse_price_signal(e["classification"].get("price_signal", "0%"))
                         for e in enriched]
        price_signal_avg = round(sum(price_signals) / len(price_signals), 1) if price_signals else 0.0

        # Archive fallback — load static intelligence when no live RSS matches
        archive_data: dict[str, Any] | None = None
        if not enriched:
            region = project.get("region", "marmara").lower()
            archive = self.load_archive(region)
            if project["id"] in archive:
                archive_data = archive[project["id"]]
                self.log(f"No live matches — serving archive intelligence for {project['id']}")
            else:
                self.log(f"No live matches and no archive entry for {project['id']}")

        report: dict[str, Any] = {
            "project_id":        project["id"],
            "project_name":      project["name"],
            "status":            project["status"],
            "tradia_score":      project["tradia_score"],
            "districts":         project["districts"],
            "news_items":        enriched,
            "top_signal":        top_signal,
            "overall_sentiment": overall_sentiment,
            "price_signal_avg":  price_signal_avg,
            "archive_data":      archive_data,
            "data_source":       "live_rss" if enriched else ("archive" if archive_data else "none"),
            "research_date":     datetime.now(timezone.utc).isoformat(),
        }

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = RESEARCH_DIR / f"{project_id}_{date_str}.json"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log(f"Saved research → {out_path.name}")
        return report

    def research_all_marmara(self) -> dict[str, Any]:
        """Research all Marmara mega-projects and produce combined report."""
        marmara = [p for p in self.MEGA_PROJECTS if p["region"] == "Marmara"]
        self.log(f"Researching {len(marmara)} Marmara projects")

        results: list[dict[str, Any]] = []
        for project in marmara:
            result = self.research_project(project["id"])
            results.append(result)

        # Top opportunity = highest tradia_score with positive sentiment
        positive = [r for r in results if r.get("overall_sentiment") == "positive"]
        ranked   = sorted(
            positive or results,
            key=lambda r: r.get("tradia_score", 0),
            reverse=True,
        )
        top_opportunity = ranked[0] if ranked else None

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        combined: dict[str, Any] = {
            "date":               date_str,
            "region":             "Marmara",
            "projects_analyzed":  len(results),
            "top_opportunity":    {
                "project_id":   top_opportunity["project_id"],
                "project_name": top_opportunity["project_name"],
                "tradia_score": top_opportunity["tradia_score"],
                "sentiment":    top_opportunity["overall_sentiment"],
                "price_signal": top_opportunity["price_signal_avg"],
            } if top_opportunity else None,
            "projects": results,
        }

        out_path = RESEARCH_DIR / f"marmara_report_{date_str}.json"
        out_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log(f"Marmara combined report saved → {out_path.name}")

        self.report_to_ceo({
            "action":            "marmara_research_complete",
            "projects_analyzed": len(results),
            "top_opportunity":   combined["top_opportunity"],
            "priority":          "high",
        })
        return combined

    def generate_property_targets(self, project_id: str) -> list[dict[str, Any]]:
        """Generate 3 target property profiles for the given project via Claude."""
        project = next((p for p in self.MEGA_PROJECTS if p["id"] == project_id), None)
        if not project:
            self.log(f"Project not found: {project_id}")
            return []

        # Load latest research for this project if available
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        research_path = RESEARCH_DIR / f"{project_id}_{date_str}.json"
        impact_context = ""
        if research_path.exists():
            try:
                research = json.loads(research_path.read_text(encoding="utf-8"))
                top = research.get("top_signal") or {}
                clf = top.get("classification", {})
                impact_context = (
                    f"Latest signal: {clf.get('summary', 'N/A')}\n"
                    f"Price signal: {clf.get('price_signal', 'N/A')}\n"
                    f"Urgency: {clf.get('urgency', 'N/A')}\n"
                    f"Overall sentiment: {research.get('overall_sentiment', 'neutral')}\n"
                )
            except Exception:
                pass

        prompt = (
            f"Mega-project: {project['name']}\n"
            f"Status: {project['status']}\n"
            f"Districts: {', '.join(project['districts'])}\n"
            f"Impact radius: {project['impact_radius_km']} km\n"
            f"Tradia score: {project['tradia_score']}/100\n"
            f"{impact_context}\n"
            "Based on this mega-project and its impact analysis, describe exactly 3 ideal "
            "property types to target in this zone for foreign investors.\n"
            "Return a JSON array of exactly 3 objects, each with these keys:\n"
            '{"type": str, "district": str, "size_range_m2": str, '
            '"price_range_usd": str, "investment_horizon": str, '
            '"expected_return_pct": str, "key_risk": str}'
        )

        try:
            resp = self._llm.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            targets = json.loads(raw.strip())
        except Exception as exc:
            self.log(f"generate_property_targets error: {exc}")
            targets = []

        out_path = RESEARCH_DIR / f"{project_id}_targets_{date_str}.json"
        out_path.write_text(json.dumps(targets, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log(f"Property targets saved → {out_path.name}")
        return targets

    # ── Orchestration ──────────────────────────────────────────────────────

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "marmara")

        if action == "status_report":
            return {"status": "READY", "priority": "normal", "projects": len(self.MEGA_PROJECTS)}

        if action == "marmara":
            report = self.research_all_marmara()
            return {
                "status":            "OK",
                "projects_analyzed": report["projects_analyzed"],
                "top_opportunity":   report.get("top_opportunity"),
            }

        if action.startswith("project:"):
            pid    = action.split(":", 1)[1]
            result = self.research_project(pid)
            targets = self.generate_property_targets(pid)
            return {
                "status":            "OK",
                "project_id":        pid,
                "news_items":        len(result.get("news_items", [])),
                "overall_sentiment": result.get("overall_sentiment"),
                "price_signal_avg":  result.get("price_signal_avg"),
                "targets_generated": len(targets),
            }

        if action.startswith("targets:"):
            pid     = action.split(":", 1)[1]
            targets = self.generate_property_targets(pid)
            return {"status": "OK", "project_id": pid, "targets": targets}

        if action == "full":
            marmara_report = self.research_all_marmara()
            top3 = sorted(
                marmara_report.get("projects", []),
                key=lambda r: r.get("tradia_score", 0),
                reverse=True,
            )[:3]
            all_targets: dict[str, list] = {}
            for proj in top3:
                pid = proj["project_id"]
                all_targets[pid] = self.generate_property_targets(pid)
            return {
                "status":            "OK",
                "projects_analyzed": marmara_report["projects_analyzed"],
                "top_opportunity":   marmara_report.get("top_opportunity"),
                "targets_generated": {k: len(v) for k, v in all_targets.items()},
            }

        return {"status": "UNKNOWN_ACTION", "action": action}
