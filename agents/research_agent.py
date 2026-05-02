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
        {
            "id":               "canakkale-koprusu",
            "name":             "Çanakkale 1915 Köprüsü Etki Bölgesi",
            "name_en":          "Canakkale 1915 Bridge Impact Zone",
            "region":           "Marmara",
            "category":         "bridge",
            "districts":        ["Çanakkale", "Lapseki", "Gelibolu", "Biga"],
            "status":           "active",
            "keywords_tr":      ["çanakkale köprüsü", "1915 köprüsü", "lapseki", "gelibolu"],
            "keywords_en":      ["canakkale bridge", "1915 bridge", "dardanelles"],
            "impact_radius_km": 25,
            "tradia_score":     81,
            "investment_horizon": "3-8 years",
        },
        {
            "id":               "gebze-kocaeli-oiz",
            "name":             "Gebze-Kocaeli Organize Sanayi Genişlemesi",
            "name_en":          "Gebze-Kocaeli Industrial Zone Expansion",
            "region":           "Marmara",
            "category":         "industrial",
            "districts":        ["Gebze", "Dilovası", "Darıca", "Çayırova"],
            "status":           "active",
            "keywords_tr":      ["gebze osb", "kocaeli sanayi", "dilovası", "gebze lojistik"],
            "keywords_en":      ["gebze industrial", "kocaeli OIZ", "marmara industrial"],
            "impact_radius_km": 8,
            "tradia_score":     83,
            "investment_horizon": "2-4 years",
        },
        # ── Karadeniz Region ───────────────────────────────────────────────
        {
            "id":               "trabzon-gulf-demand",
            "name":             "Trabzon Körfez Talebi",
            "region":           "Karadeniz",
            "category":         "residential",
            "districts":        ["Trabzon", "Akçaabat", "Of"],
            "status":           "active",
            "keywords_tr":      ["trabzon", "trabzon konut", "trabzon arsa", "karadeniz yatırım"],
            "keywords_en":      ["trabzon real estate", "trabzon property", "black sea investment"],
            "impact_radius_km": 30,
            "tradia_score":     86,
        },
        {
            "id":               "samsun-karadeniz-hub",
            "name":             "Samsun Lojistik Merkezi",
            "region":           "Karadeniz",
            "category":         "logistics",
            "districts":        ["Samsun", "Tekkeköy", "Atakum"],
            "status":           "active",
            "keywords_tr":      ["samsun liman", "samsun osb", "karadeniz lojistik"],
            "keywords_en":      ["samsun port", "black sea logistics", "samsun industrial"],
            "impact_radius_km": 20,
            "tradia_score":     78,
        },
        {
            "id":               "rize-artvin-hidroelektrik",
            "name":             "Rize-Artvin Havalimanı Bölgesi",
            "region":           "Karadeniz",
            "category":         "infrastructure",
            "districts":        ["Rize", "Artvin", "Hopa"],
            "status":           "active",
            "keywords_tr":      ["rize artvin havalimanı", "rize serbest bölge", "hopa liman"],
            "keywords_en":      ["rize artvin airport", "rize free trade zone"],
            "impact_radius_km": 25,
            "tradia_score":     74,
        },
        # ── İç Anadolu Region ──────────────────────────────────────────────
        {
            "id":               "ankara-teknoloji-usu",
            "name":             "Ankara Teknoloji Üssü",
            "region":           "İç Anadolu",
            "category":         "technology",
            "districts":        ["Çankaya", "Bilkent", "İncek", "Sincan"],
            "status":           "active",
            "keywords_tr":      ["ankara teknoloji", "odtü teknokent", "savunma sanayi ankara", "aselsan"],
            "keywords_en":      ["ankara technology", "ODTU technopark", "defense industry ankara"],
            "impact_radius_km": 20,
            "tradia_score":     85,
        },
        {
            "id":               "konya-tarim-lojistik",
            "name":             "Konya Tarım ve Lojistik",
            "region":           "İç Anadolu",
            "category":         "agricultural_industrial",
            "districts":        ["Konya", "Karatay", "Selçuklu", "Karaman"],
            "status":           "active",
            "keywords_tr":      ["konya osb", "konya lojistik", "konya tarım teknoloji"],
            "keywords_en":      ["konya industrial", "konya logistics", "central anatolia hub"],
            "impact_radius_km": 30,
            "tradia_score":     76,
        },
        {
            "id":               "kayseri-organize-sanayi",
            "name":             "Kayseri OSB Mobilya Merkezi",
            "region":           "İç Anadolu",
            "category":         "industrial",
            "districts":        ["Kayseri", "Melikgazi", "Kocasinan"],
            "status":           "active",
            "keywords_tr":      ["kayseri mobilya", "kayseri osb", "kayseri tekstil"],
            "keywords_en":      ["kayseri furniture", "kayseri industrial", "kayseri OIZ"],
            "impact_radius_km": 15,
            "tradia_score":     77,
        },
        # ── Güneydoğu Region ──────────────────────────────────────────────
        {
            "id":               "gaziantep-osb-ihracat",
            "name":             "Gaziantep OSB İhracat Merkezi",
            "region":           "Güneydoğu",
            "category":         "industrial",
            "districts":        ["Gaziantep", "Nizip", "İslahiye"],
            "status":           "active",
            "keywords_tr":      ["gaziantep osb", "gaziantep tekstil", "gaziantep ihracat", "nizip sanayi"],
            "keywords_en":      ["gaziantep industrial", "gaziantep export", "gaziantep OIZ"],
            "impact_radius_km": 25,
            "tradia_score":     83,
        },
        {
            "id":               "mersin-serbest-ticaret",
            "name":             "Mersin Serbest Ticaret Bölgesi",
            "region":           "Güneydoğu",
            "category":         "logistics",
            "districts":        ["Mersin", "Tarsus", "Silifke"],
            "status":           "active",
            "keywords_tr":      ["mersin liman", "mersin serbest bölge", "tarsus osb", "mersin konteyner"],
            "keywords_en":      ["mersin port", "mersin free trade zone", "mediterranean logistics turkey"],
            "impact_radius_km": 20,
            "tradia_score":     86,
        },
        {
            "id":               "gap-sanliurfa-tarim",
            "name":             "GAP Şanlıurfa Tarım Dönüşümü",
            "region":           "Güneydoğu",
            "category":         "agricultural_industrial",
            "districts":        ["Şanlıurfa", "Harran", "Birecik"],
            "status":           "active",
            "keywords_tr":      ["gap projesi", "şanlıurfa sulama", "harran ovası", "güneydoğu tarım"],
            "keywords_en":      ["GAP project", "sanliurfa irrigation", "southeast anatolia agricultural"],
            "impact_radius_km": 40,
            "tradia_score":     74,
        },
        {
            "id":               "adana-ceyhan-enerji",
            "name":             "Adana-Ceyhan Enerji Koridoru",
            "region":           "Güneydoğu",
            "category":         "industrial",
            "districts":        ["Adana", "Ceyhan", "Seyhan", "Yüreğir"],
            "status":           "active",
            "keywords_tr":      ["ceyhan boru hattı", "adana petrokimya", "btc terminali", "ceyhan lng"],
            "keywords_en":      ["ceyhan pipeline", "adana energy", "BTC terminal turkey", "ceyhan LNG"],
            "impact_radius_km": 30,
            "tradia_score":     80,
        },
        # ── Ege Region ─────────────────────────────────────────────────────
        {
            "id":               "antalya-turizm-kusagi",
            "name":             "Antalya Turizm Kuşağı Gelişim Aksı",
            "name_en":          "Antalya Tourism Belt Development Corridor",
            "region":           "Ege",
            "category":         "tourism",
            "districts":        ["Antalya", "Alanya", "Serik", "Kaş"],
            "status":           "active",
            "keywords_tr":      ["antalya turizm", "antalya otel yatırım", "alanya konut", "kaş villa"],
            "keywords_en":      ["antalya tourism", "antalya investment", "alanya property", "kas villa"],
            "impact_radius_km": 30,
            "tradia_score":     88,
            "investment_horizon": "2-5 years",
        },
        {
            "id":               "mugla-bodrum-marmaris",
            "name":             "Muğla Lüks Kıyı Kuşağı",
            "name_en":          "Mugla Luxury Coast Belt",
            "region":           "Ege",
            "category":         "luxury_coastal",
            "districts":        ["Bodrum", "Marmaris", "Fethiye", "Göcek"],
            "status":           "active",
            "keywords_tr":      ["bodrum villa", "marmaris yat limanı", "fethiye yazlık", "göcek marina"],
            "keywords_en":      ["bodrum villa", "marmaris marina", "fethiye property", "gocek luxury"],
            "impact_radius_km": 20,
            "tradia_score":     91,
            "investment_horizon": "2-4 years",
        },
        {
            "id":               "izmir-lojistik-aksi",
            "name":             "İzmir Lojistik ve Sanayi Aksı",
            "name_en":          "Izmir Logistics and Industrial Corridor",
            "region":           "Ege",
            "category":         "industrial",
            "districts":        ["Torbalı", "Kemalpaşa", "Aliağa", "Gaziemir"],
            "status":           "active",
            "keywords_tr":      ["izmir osb", "torbalı sanayi", "aliağa liman", "kemalpaşa lojistik"],
            "keywords_en":      ["izmir industrial", "torbali OIZ", "aliaga port", "izmir logistics"],
            "impact_radius_km": 15,
            "tradia_score":     82,
            "investment_horizon": "3-5 years",
        },
        {
            "id":               "izmir-alsancak-gelisim",
            "name":             "İzmir Alsancak-Bayraklı Kentsel Dönüşüm Aksı",
            "name_en":          "Izmir Alsancak-Bayrakli Urban Renewal Corridor",
            "region":           "Ege",
            "category":         "urban_renewal",
            "districts":        ["Alsancak", "Bayraklı", "Karşıyaka", "Bornova"],
            "status":           "active",
            "keywords_tr":      ["alsancak dönüşüm", "bayraklı ofis", "karşıyaka metro", "bornova konut"],
            "keywords_en":      ["alsancak renewal", "bayrakli office", "karsiyaka metro", "bornova residential"],
            "impact_radius_km": 10,
            "tradia_score":     79,
            "investment_horizon": "2-4 years",
        },
        {
            "id":               "nevsehir-kappadokya",
            "name":             "Nevşehir Kapadokya Turizm Yatırım Bölgesi",
            "name_en":          "Nevsehir Cappadocia Tourism Investment Zone",
            "region":           "Ege",
            "category":         "tourism",
            "districts":        ["Göreme", "Ürgüp", "Uçhisar", "Avanos"],
            "status":           "active",
            "keywords_tr":      ["kapadokya otel", "göreme yatırım", "ürgüp villa", "nevşehir turizm"],
            "keywords_en":      ["cappadocia hotel", "goreme investment", "urgup villa", "nevsehir tourism"],
            "impact_radius_km": 25,
            "tradia_score":     84,
            "investment_horizon": "3-6 years",
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

    ARCHIVE_FILES: dict[str, str] = {
        "marmara":       "marmara_archive.json",
        "ege":           "ege_archive.json",
        "karadeniz":     "karadeniz_archive.json",
        "iç anadolu":    "ic_anadolu_archive.json",
        "güneydoğu":     "guneydogu_archive.json",
        "doğu anadolu":  "dogu_anadolu_archive.json",
    }

    def load_archive(self, region: str | None = None) -> dict[str, Any]:
        """Load static intelligence archive keyed by project_id.

        If region is None, all known archives are merged and returned.
        """
        if region is None:
            merged: dict[str, Any] = {}
            for r in self.ARCHIVE_FILES:
                merged.update(self.load_archive(r))
            return merged

        # Normalize Turkish İ (U+0130) → i before lowercasing to avoid
        # the two-char "i̇" produced by str.lower() on that codepoint.
        region_key = region.replace("İ", "i").replace("I", "ı").lower()
        filename = self.ARCHIVE_FILES.get(region_key, f"{region_key}_archive.json")
        archive_path = RESEARCH_DIR / "projects" / filename
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
        return self._research_all_region("Marmara")

    def _research_all_region(self, region: str) -> dict[str, Any]:
        """Generic: research all mega-projects for a given region label."""
        projects = [p for p in self.MEGA_PROJECTS if p["region"] == region]
        self.log(f"Researching {len(projects)} {region} projects")

        results: list[dict[str, Any]] = []
        for project in projects:
            results.append(self.research_project(project["id"]))

        positive = [r for r in results if r.get("overall_sentiment") == "positive"]
        ranked   = sorted(
            positive or results,
            key=lambda r: r.get("tradia_score", 0),
            reverse=True,
        )
        top_opportunity = ranked[0] if ranked else None

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = region.lower().replace(" ", "_").replace("ç", "c").replace("ı", "i")
        combined: dict[str, Any] = {
            "date":               date_str,
            "region":             region,
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

        out_path = RESEARCH_DIR / f"{slug}_report_{date_str}.json"
        out_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log(f"{region} combined report saved → {out_path.name}")

        self.report_to_ceo({
            "action":            f"{slug}_research_complete",
            "projects_analyzed": len(results),
            "top_opportunity":   combined["top_opportunity"],
            "priority":          "high",
        })
        return combined

    def research_all_ege(self) -> dict[str, Any]:
        return self._research_all_region("Ege")

    def research_all_karadeniz(self) -> dict[str, Any]:
        return self._research_all_region("Karadeniz")

    def research_all_ic_anadolu(self) -> dict[str, Any]:
        return self._research_all_region("İç Anadolu")

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

    # ── OSB Database Methods ────────────────────────────────────────────────────

    def get_osb_by_il(self, il_adi: str) -> dict[str, Any]:
        """Return all OSBs and incentive region for a given province."""
        osb_db_path = RESEARCH_DIR / "osb_database.json"
        try:
            db = json.loads(osb_db_path.read_text(encoding="utf-8"))
            results = []
            for region, data in db.get("regions", {}).items():
                for osb in data.get("osb_list", []):
                    if osb.get("il", "").lower() == il_adi.lower():
                        osb["region"] = region
                        results.append(osb)
            results = sorted(results, key=lambda x: x.get("tradia_score", 0), reverse=True)
        except Exception as exc:
            self.log(f"OSB DB error: {exc}")
            results = []
        tesvik = self.get_tesvik_bolge(il_adi)
        return {"osbs": results, "tesvik": tesvik}

    def get_tesvik_bolge(self, il_adi: str) -> dict[str, Any]:
        """Return investment incentive region for a province."""
        tesvik_path = RESEARCH_DIR / "tesvikler" / "tesvik_bolgeleri.json"
        try:
            data = json.loads(tesvik_path.read_text(encoding="utf-8"))
            for bolge_no, bolge in data["incentives_by_region"].items():
                if il_adi in bolge["iller"]:
                    return {
                        "bolge":           bolge_no,
                        "label":           bolge["label"],
                        "description":     bolge["description"],
                        "kdv_istisna":     bolge.get("kdv_istisna"),
                        "faiz_destegi":    bolge.get("faiz_destegi"),
                        "sigorta_destegi": bolge.get("sigorta_destegi"),
                        "yatirim_yeri":    bolge.get("yatirim_yeri"),
                        "vergi_indirimi":  bolge.get("vergi_indirimi_orani"),
                        "tradia_note":     f"Bölge {bolge_no} teşvikleri geçerli",
                    }
            return {"bolge": "?", "label": "Belirtilmemiş", "tradia_note": "Teşvik bölgesi verisi güncelleniyor"}
        except Exception as exc:
            self.log(f"Teşvik error: {exc}")
            return {}

    def get_imar_firsatlari(self, il: str | None = None, min_score: int = 70) -> list[dict]:
        """Return zoning opportunity areas, optionally filtered by province."""
        imar_path = RESEARCH_DIR / "tesvikler" / "imara_acilacak_alanlar.json"
        try:
            data  = json.loads(imar_path.read_text(encoding="utf-8"))
            areas = data.get("areas", [])
            if il:
                areas = [a for a in areas if a.get("il") == il]
            areas = [a for a in areas if a.get("tradia_score", 0) >= min_score]
            return sorted(areas, key=lambda x: x.get("tradia_score", 0), reverse=True)
        except Exception as exc:
            self.log(f"İmar error: {exc}")
            return []

    def get_osb_summary_by_region(self, region: str | None = None) -> dict[str, Any]:
        """Return OSB summary stats per region or all regions."""
        osb_db_path = RESEARCH_DIR / "osb_database.json"
        try:
            db = json.loads(osb_db_path.read_text(encoding="utf-8"))
            summary: dict[str, Any] = {}
            for reg, data in db.get("regions", {}).items():
                if region and reg != region:
                    continue
                osbs = data.get("osb_list", [])
                if not osbs:
                    continue
                total_ihracat = sum(o.get("ihracat_milyon_usd", 0) for o in osbs)
                avg_score     = sum(o.get("tradia_score", 0) for o in osbs) / len(osbs)
                top_osbs      = sorted(osbs, key=lambda x: x.get("tradia_score", 0), reverse=True)[:3]
                summary[reg] = {
                    "total_osb":                 len(osbs),
                    "total_ihracat_milyon_usd":  total_ihracat,
                    "avg_tradia_score":           round(avg_score, 1),
                    "grade_a":                   len([o for o in osbs if o.get("yatirim_notu") == "A"]),
                    "grade_b":                   len([o for o in osbs if o.get("yatirim_notu") == "B"]),
                    "grade_c":                   len([o for o in osbs if o.get("yatirim_notu") == "C"]),
                    "top_osbs": [
                        {
                            "ad":         o["osb_adi"],
                            "il":         o["il"],
                            "score":      o["tradia_score"],
                            "arsa_usd_m2": o["arsa_usd_m2"],
                            "trend":      o["arsa_trend"],
                            "sektor":     o["sektor"],
                        }
                        for o in top_osbs
                    ],
                }
            return summary
        except Exception as exc:
            self.log(f"OSB summary error: {exc}")
            return {}

    def generate_osb_report(self) -> dict[str, Any]:
        """Generate full OSB intelligence report for CEO."""
        import datetime as _dt
        summary      = self.get_osb_summary_by_region()
        osb_db_path  = RESEARCH_DIR / "osb_database.json"
        db           = json.loads(osb_db_path.read_text(encoding="utf-8"))

        all_osbs: list[dict] = []
        for reg, data in db.get("regions", {}).items():
            for osb in data.get("osb_list", []):
                osb["region"] = reg
                all_osbs.append(osb)

        top10 = sorted(all_osbs, key=lambda x: x.get("tradia_score", 0), reverse=True)[:10]
        best_value = sorted(
            [o for o in all_osbs if o.get("tradia_score", 0) >= 75],
            key=lambda x: x.get("arsa_usd_m2", 9999),
        )[:5]

        report: dict[str, Any] = {
            "date":                    str(_dt.date.today()),
            "agent":                   "ResearchAgent",
            "type":                    "osb_intelligence",
            "total_osb_tracked":       len(all_osbs),
            "region_summary":          summary,
            "top10_by_score": [
                {
                    "rank":          i + 1,
                    "osb":           o["osb_adi"],
                    "il":            o["il"],
                    "region":        o["region"],
                    "score":         o["tradia_score"],
                    "grade":         o["yatirim_notu"],
                    "arsa_usd_m2":   o["arsa_usd_m2"],
                    "trend":         o["arsa_trend"],
                    "ihracat_musd":  o["ihracat_milyon_usd"],
                    "sektor":        o["sektor"],
                }
                for i, o in enumerate(top10)
            ],
            "best_value_opportunities": [
                {
                    "osb":          o["osb_adi"],
                    "il":           o["il"],
                    "region":       o["region"],
                    "score":        o["tradia_score"],
                    "arsa_usd_m2":  o["arsa_usd_m2"],
                    "trend":        o["arsa_trend"],
                    "note":         "High score, affordable entry",
                }
                for o in best_value
            ],
        }

        report_path = Config.REPORTS_DIR / f"osb_report_{report['date']}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log(f"OSB report saved → osb_report_{report['date']}.json")
        self.report_to_ceo(report)
        return report

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

        if action == "ege":
            report = self.research_all_ege()
            return {
                "status":            "OK",
                "projects_analyzed": report["projects_analyzed"],
                "top_opportunity":   report.get("top_opportunity"),
            }

        if action == "karadeniz":
            report = self.research_all_karadeniz()
            return {
                "status":            "OK",
                "projects_analyzed": report["projects_analyzed"],
                "top_opportunity":   report.get("top_opportunity"),
            }

        if action == "ic_anadolu":
            report = self.research_all_ic_anadolu()
            return {
                "status":            "OK",
                "projects_analyzed": report["projects_analyzed"],
                "top_opportunity":   report.get("top_opportunity"),
            }

        if action == "guneydogu":
            report = self._research_all_region("Güneydoğu")
            return {
                "status":            "OK",
                "projects_analyzed": report["projects_analyzed"],
                "top_opportunity":   report.get("top_opportunity"),
            }

        if action == "dogu_anadolu":
            return self._research_all_region("Doğu Anadolu")

        if action == "all_regions":
            totals: dict[str, Any] = {}
            for region_action in ("marmara", "ege", "karadeniz", "ic_anadolu", "guneydogu", "dogu_anadolu"):
                result = self.run_task({"action": region_action})
                totals[region_action] = result.get("projects_analyzed", 0)
            return {"status": "OK", "regions": totals, "total": sum(totals.values())}

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

        if action.startswith("tesvik:"):
            il = action.split(":", 1)[1]
            result = self.get_tesvik_bolge(il)
            return {"status": "OK", "il": il, **result}

        if action == "imar":
            areas = self.get_imar_firsatlari()
            return {"status": "OK", "count": len(areas), "areas": areas}

        if action.startswith("imar:"):
            il = action.split(":", 1)[1]
            areas = self.get_imar_firsatlari(il=il)
            return {"status": "OK", "il": il, "count": len(areas), "areas": areas}

        if action == "osb_report":
            report = self.generate_osb_report()
            return {
                "status":            "OK",
                "total_osb_tracked": report["total_osb_tracked"],
                "top1_osb":          report["top10_by_score"][0]["osb"] if report["top10_by_score"] else None,
                "best_value_count":  len(report["best_value_opportunities"]),
            }

        if action.startswith("osb_il:"):
            il_adi = action.split(":", 1)[1]
            results = self.get_osb_by_il(il_adi)
            return {
                "status":  "OK",
                "il":      il_adi,
                "count":   len(results),
                "osbs":    results,
            }

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
