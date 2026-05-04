from __future__ import annotations

import json
import re
import string
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import warnings

import anthropic
import feedparser
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from core.config import Config
from .base_agent import BaseAgent

_HEADERS = {
    "User-Agent":      ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
    "Accept":          "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Cache-Control":   "no-cache",
}

_PUNCT      = re.compile(rf"[{re.escape(string.punctuation)}]")
_TYPE_SCORE = {"critical": 90, "opportunity": 70, "threat": 60, "neutral": 20}


class NewsAgent(BaseAgent):
    """Fetches, deduplicates and persists land/zoning/gov news from TR sources."""

    KEYWORDS: dict[str, list[str]] = {
        "critical": [
            "yabanci tapu", "tapu yasak", "mulk edinim", "dovizle satis",
            "imar iptali", "kamulastirma", "3194", "yonetmelik degisikligi",
            "foreign ownership", "title deed ban", "property law change",
        ],
        "opportunity": [
            "imar degisikligi", "yapilasmaya acildi", "lojistik merkez",
            "havalimanı", "otoyol", "serbest bolge", "tesvik", "kdv muafiyet",
            "zoning change", "investment zone", "infrastructure project",
        ],
        "threat": [
            "kdv artis", "vergi artis", "kisitlama", "moratoriyum",
            "tapu serhi", "ipotek artis", "inflation", "restriction", "freeze",
        ],
        "neutral": [],
    }

    SOURCES: list[dict[str, str]] = [
        {
            "name":     "Sabah Ekonomi",
            "url":      "https://www.sabah.com.tr/rss/ekonomi.xml",
            "type":     "rss",
            "language": "tr",
        },
        {
            "name":     "Dünya Gazetesi",
            "url":      "https://www.dunya.com/rss",
            "type":     "rss",
            "language": "tr",
        },
        {
            "name":     "World Property Journal",
            "url":      "https://www.worldpropertyjournal.com/real-estate-news-rss-feed.php",
            "type":     "rss",
            "language": "en",
        },
        {
            "name":     "Daily Sabah Turkiye",
            "url":      "https://www.dailysabah.com/feeds/turkiye",
            "type":     "rss",
            "language": "en",
        },
        {
            "name":     "Daily Sabah Finance",
            "url":      "https://www.dailysabah.com/feeds/finance",
            "type":     "rss",
            "language": "en",
        },
        {
            "name":     "Milliyet Ekonomi",
            "url":      "https://www.milliyet.com.tr/rss/rssNew/ekonomiRss.xml",
            "type":     "rss",
            "language": "tr",
        },
        {
            "name":     "Hurriyet Ekonomi",
            "url":      "https://www.hurriyet.com.tr/rss/ekonomi",
            "type":     "rss",
            "language": "tr",
        },
        {
            "name":     "Resmi Gazete",
            "url":      "https://www.resmigazete.gov.tr/rss",
            "type":     "rss",
            "language": "tr",
        },
    ]

    _SUMMARIZE_SYSTEM = (
        "You are a real estate intelligence analyst for Tradia Turkey, "
        "an AI-powered Turkish property advisory platform serving "
        "international investors from Dubai, Russia, and Europe.\n\n"
        "Analyze the following Turkish or English news item and respond "
        "in ENGLISH ONLY — never use Turkish, Arabic, or Russian in your response.\n\n"
        "Format your response exactly like this:\n"
        "SUMMARY: [2 sentences explaining what happened, in clear English]\n"
        "IMPACT: [1 sentence on how this specifically affects foreign property "
        "investors in Turkey — be concrete, mention property types or regions "
        "if relevant]\n\n"
        "Be factual, specific, and professional. Never translate the title — "
        "summarize the content instead."
    )

    def __init__(self, ceo_callback=None) -> None:
        super().__init__(name="news", role="Market Intelligence", ceo_callback=ceo_callback)
        self._session  = requests.Session()
        self._session.headers.update(_HEADERS)
        self._last_fetch_count = 0
        self._llm = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    # ── Public interface (run_task) ────────────────────────────────────────

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "fetch")

        if action == "status_report":
            return {
                "status":           "READY",
                "priority":         "normal",
                "headlines_cached": self._last_fetch_count,
            }

        if action == "fetch":
            items = self.fetch_all_sources()
            items = self.deduplicate(items)
            path  = self._save(items)
            self._last_fetch_count = len(items)
            self.log(f"Fetched {len(items)} unique items → {path.name}")
            self.report_to_ceo({
                "action":   "fetch_complete",
                "count":    len(items),
                "file":     str(path),
                "priority": "normal",
            })
            return {"status": "OK", "count": len(items), "file": str(path)}

        if action == "analyze":
            raw, raw_path = self._load_latest_raw()
            if not raw:
                self.log("No raw file found — run 'fetch' first")
                return {"status": "NO_DATA", "action": action}

            scored    = self.score_all(raw)
            top20     = self.prioritize(scored)
            out_path  = self._save_analyzed(top20)

            # Summarise classification distribution for CEO report
            dist: dict[str, int] = {"critical": 0, "opportunity": 0, "threat": 0, "neutral": 0}
            for item in top20:
                dist[item["classification"]["type"]] += 1

            priority_signal = "high" if dist["critical"] > 0 else "normal"
            self.log(
                f"Analyzed {len(raw)} items → top {len(top20)} saved | "
                f"critical={dist['critical']} opp={dist['opportunity']} "
                f"threat={dist['threat']} neutral={dist['neutral']}"
            )
            self.report_to_ceo({
                "action":       "analyze_complete",
                "input_count":  len(raw),
                "top_count":    len(top20),
                "distribution": dist,
                "file":         str(out_path),
                "priority":     priority_signal,
            })
            return {
                "status":       "OK",
                "input_count":  len(raw),
                "top_count":    len(top20),
                "distribution": dist,
                "file":         str(out_path),
            }

        if action == "digest":
            return self.generate_ceo_report()

        if action == "full":
            items = self.fetch_all_sources()
            items = self.deduplicate(items)
            self._save(items)
            self._last_fetch_count = len(items)
            items = self.score_all(items)
            items = self.prioritize(items)
            return self.generate_ceo_report(top_items=items)

        return {"status": "UNKNOWN_ACTION", "action": action}

    # ── Anthropic helpers ─────────────────────────────────────────────────

    def _chat(
        self,
        system: str,
        user: str,
        *,
        cache_system: bool = False,
    ) -> str:
        """Single-turn call to claude-sonnet-4-6. Caches system prompt when requested."""
        system_block: dict = {"type": "text", "text": system}
        if cache_system:
            system_block["cache_control"] = {"type": "ephemeral"}

        resp = self._llm.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=[system_block],
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip()

    def summarize_item(self, item: dict[str, Any]) -> dict[str, str]:
        title = item.get("title", "")
        text  = (item.get("summary") or item.get("text") or "")[:500]

        _LANGS = {
            "en": "English",
            "ru": "Russian",
            "ar": "Arabic",
            "tr": "Turkish",
        }

        results: dict[str, str] = {}
        for lang_code, lang_name in _LANGS.items():
            prompt = (
                f"You are a real estate intelligence analyst for Tradia Turkey.\n\n"
                f"Analyze this news item and respond ONLY in {lang_name}.\n"
                f"Never mix languages. Respond entirely in {lang_name}.\n\n"
                f"News title: {title}\n"
                f"News content: {text}\n\n"
                f"Respond in this exact format:\n"
                f"SUMMARY: [2 sentences about what happened]\n"
                f"IMPACT: [1 sentence on how this affects foreign property investors in Turkey]"
            )
            try:
                resp = self._llm.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = resp.content[0].text.strip().replace("**", "").replace("__", "")
                summary = ""
                impact  = ""
                for line in raw.split("\n"):
                    if line.startswith("SUMMARY:"):
                        summary = line.replace("SUMMARY:", "", 1).strip()
                    elif line.startswith("IMPACT:"):
                        impact = line.replace("IMPACT:", "", 1).strip()
                results[f"summary_{lang_code}"] = summary
                results[f"impact_{lang_code}"]  = impact
            except Exception as exc:
                self.log(f"summarize_item({lang_code}) error: {exc}")
                results[f"summary_{lang_code}"] = f"[{lang_name} summary unavailable]"
                results[f"impact_{lang_code}"]  = ""

        self.log(f"Summarized (4 langs): {title[:60]!r}")
        return results

    def translate_item(self, item: dict[str, Any], lang: str) -> str:
        supported = {"Russian", "Arabic"}
        if lang not in supported:
            raise ValueError(f"lang must be one of {supported}")
        system = (
            f"Translate the following real estate news summary to {lang}. "
            "Keep it professional and concise."
        )
        text       = item.get("summary_en", item.get("summary", item.get("title", "")))
        translated = self._chat(system, text, cache_system=True)
        result     = translated.replace("**", "").replace("__", "").strip()
        self.log(f"Translated to {lang}: {text[:40]!r}…")
        return result

    # ── Digest + CEO report ────────────────────────────────────────────────

    def build_digest(
        self,
        top_items: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if top_items is None:
            raw, _ = self._load_latest_raw()
            if not raw:
                return []
            top_items = self.prioritize(self.score_all(raw))

        _EMPTY_AI: dict[str, str] = {
            "summary_en": "", "impact_en": "",
            "summary_ru": "", "impact_ru": "",
            "summary_ar": "", "impact_ar": "",
            "summary_tr": "", "impact_tr": "",
        }

        digest: list[dict[str, Any]] = []
        for item in top_items[:10]:
            clf = item.get("classification", {})
            try:
                ai = self.summarize_item(item)
            except Exception as exc:
                self.log(f"LLM error for {item.get('title','?')[:50]!r}: {exc}")
                ai = dict(_EMPTY_AI)

            digest.append({
                "title":  item.get("title", ""),
                "link":   item.get("link", ""),
                "source": item.get("source", ""),
                "type":   clf.get("type", "neutral"),
                "score":  clf.get("score", 20),
                **ai,
            })
        return digest

    def generate_ceo_report(
        self,
        top_items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        digest = self.build_digest(top_items)

        dist: dict[str, int] = {"critical": 0, "opportunity": 0, "threat": 0, "neutral": 0}
        for entry in digest:
            dist[entry["type"]] = dist.get(entry["type"], 0) + 1

        # Derive a one-sentence CEO recommendation from distribution
        if dist["critical"] > 0:
            recommendation = (
                f"Immediate review required: {dist['critical']} critical regulatory item(s) "
                "detected that may affect foreign ownership or zoning rights."
            )
        elif dist["opportunity"] > 0:
            recommendation = (
                f"{dist['opportunity']} investment opportunity signal(s) identified — "
                "recommend briefing acquisition team within 24 hours."
            )
        elif dist["threat"] > 0:
            recommendation = (
                f"{dist['threat']} market threat(s) detected — monitor and advise clients "
                "to hold pending further analysis."
            )
        else:
            recommendation = "No material signals today — routine monitoring sufficient."

        date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report = {
            "date":               date,
            "agent":              "NewsAgent",
            "critical_count":     dist["critical"],
            "opportunity_count":  dist["opportunity"],
            "threat_count":       dist["threat"],
            "neutral_count":      dist["neutral"],
            "top_items":          digest,
            "recommendation":     recommendation,
        }

        # Persist
        Config.ensure_dirs()
        out_path = Config.REPORTS_DIR / f"news_report_{date}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        self.log(f"CEO report saved → {out_path.name}")

        self.report_to_ceo({
            **{k: v for k, v in report.items() if k != "top_items"},
            "file":     str(out_path),
            "priority": "high" if dist["critical"] > 0 else "normal",
        })
        return {"status": "OK", **report}

    # ── RSS ────────────────────────────────────────────────────────────────

    def fetch_rss(self, url: str) -> list[dict[str, str]]:
        try:
            resp = self._session.get(url, timeout=20, headers=_HEADERS)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            self.log(f"RSS error {url}: {exc}")
            return []

        items: list[dict[str, str]] = []
        for entry in feed.entries:
            items.append({
                "title":     entry.get("title", "").strip(),
                "link":      entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary":   BeautifulSoup(
                    entry.get("summary", ""), "html.parser"
                ).get_text(" ", strip=True)[:400],
            })
        return items

    # ── HTML ───────────────────────────────────────────────────────────────

    def fetch_html(self, url: str, selector: str = "article") -> list[dict[str, str]]:
        try:
            resp = self._session.get(url, timeout=20, headers=_HEADERS)
            resp.raise_for_status()
        except Exception as exc:
            self.log(f"HTML error {url}: {exc}")
            return []

        soup  = BeautifulSoup(resp.content, "html.parser")
        nodes = soup.select(selector) or soup.find_all(["h2", "h3"])

        items: list[dict[str, str]] = []
        for node in nodes[:30]:
            anchor = node.find("a") or node
            title  = anchor.get_text(" ", strip=True)
            href   = anchor.get("href", "")
            if href and not href.startswith("http"):
                from urllib.parse import urljoin
                href = urljoin(url, href)
            if not title:
                continue
            items.append({
                "title": title,
                "link":  href,
                "text":  node.get_text(" ", strip=True)[:400],
            })
        return items

    # ── Aggregation ────────────────────────────────────────────────────────

    def fetch_all_sources(self) -> list[dict[str, Any]]:
        combined: list[dict[str, Any]] = []
        for source in self.SOURCES:
            self.log(f"Fetching [{source['type'].upper()}] {source['name']}")
            if source["type"] == "rss":
                raw = self.fetch_rss(source["url"])
            else:
                raw = self.fetch_html(source["url"])

            for item in raw:
                item["source"]   = source["name"]
                item["language"] = source["language"]
                item["fetched_at"] = datetime.now(timezone.utc).isoformat()
            combined.extend(raw)
            time.sleep(0.3)     # polite crawl delay

        self.log(f"Raw total: {len(combined)} items from {len(self.SOURCES)} sources")
        return combined

    def fetch_today(self) -> list[dict[str, Any]]:
        """Bugünün haberlerini çek (fetch_all_sources wrapper)."""
        return self.fetch_all_sources()

    # ── Deduplication ──────────────────────────────────────────────────────

    def deduplicate(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen:   set[str]           = set()
        unique: list[dict[str, Any]] = []
        for item in items:
            key = _PUNCT.sub("", item.get("title", "").lower()).split()
            key = " ".join(key)
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        removed = len(items) - len(unique)
        if removed:
            self.log(f"Deduplicated: removed {removed} duplicate(s)")
        return unique

    # ── Persistence ────────────────────────────────────────────────────────

    def _save(self, items: list[dict[str, Any]]) -> Path:
        Config.ensure_dirs()
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = Config.NEWS_DIR / f"raw_{date}.json"
        # Merge with existing file if it exists (idempotent daily runs)
        existing: list[dict] = []
        if path.exists():
            with path.open(encoding="utf-8") as f:
                existing = json.load(f)
        merged = self.deduplicate(existing + items)
        with path.open("w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        return path

    # ── Classification ────────────────────────────────────────────────────

    def classify_item(self, item: dict[str, Any]) -> dict[str, Any]:
        text = (
            item.get("title", "") + " " +
            item.get("summary", item.get("text", ""))
        ).lower()
        # Normalise: remove punctuation for keyword matching
        text_plain = _PUNCT.sub(" ", text)

        best_type    = "neutral"
        best_score   = _TYPE_SCORE["neutral"]
        all_matched:  list[str] = []

        for ktype, keywords in self.KEYWORDS.items():
            matched = [kw for kw in keywords if kw in text_plain]
            if matched:
                all_matched.extend(matched)
                candidate_score = _TYPE_SCORE[ktype]
                if candidate_score > best_score:
                    best_score = candidate_score
                    best_type  = ktype

        return {
            "type":             best_type,
            "score":            best_score,
            "matched_keywords": list(dict.fromkeys(all_matched)),  # dedup, preserve order
        }

    def score_all(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for item in items:
            item["classification"] = self.classify_item(item)
        return items

    def prioritize(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def _key(item: dict) -> int:
            return item.get("classification", {}).get("score", _TYPE_SCORE["neutral"])
        return sorted(items, key=_key, reverse=True)[:20]

    # ── Analyzed persistence ───────────────────────────────────────────────

    def _load_latest_raw(self) -> tuple[list[dict[str, Any]], Path | None]:
        """Return (items, path) for the most recent raw_*.json, or ([], None)."""
        candidates = sorted(Config.NEWS_DIR.glob("raw_*.json"), reverse=True)
        if not candidates:
            return [], None
        path = candidates[0]
        with path.open(encoding="utf-8") as f:
            return json.load(f), path

    def _save_analyzed(self, items: list[dict[str, Any]]) -> Path:
        Config.ensure_dirs()
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = Config.NEWS_DIR / f"analyzed_{date}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return path

    # ── Legacy helpers kept for compatibility ──────────────────────────────

    def fetch_headlines(self, region: str, keywords: list[str]) -> list[dict]:
        items = self.fetch_all_sources()
        kw    = [k.lower() for k in keywords]
        return [
            i for i in items
            if any(k in i.get("title", "").lower() or k in i.get("summary", i.get("text", "")).lower()
                   for k in kw)
        ]

    def summarise(self, articles: list[dict]) -> str:
        return "\n".join(
            f"• [{a.get('source','')}] {a.get('title','')}" for a in articles[:10]
        )

    def score_relevance(self, article: dict, lead: dict) -> float:
        keywords = str(lead.get("keywords", "")).lower().split()
        text     = (article.get("title", "") + " " + article.get("summary", article.get("text", ""))).lower()
        if not keywords:
            return 0.0
        hits = sum(1 for kw in keywords if kw in text)
        return round(hits / len(keywords), 2)
