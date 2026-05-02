from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, ".")
from dotenv import load_dotenv

load_dotenv()

from core.config import Config
from core.logger import configure_root

# ── Config ─────────────────────────────────────────────────────────────────────

SITE_REPO_PATH = Path(os.getenv("SITE_REPO_PATH", "../LandGold"))
SITE_INDEX     = SITE_REPO_PATH / "docs" / "index.html"
SITE_MAIN_URL  = "https://e-misara.github.io/landgold-intelligence/"

_COLOR_TYPE = {
    "critical":    "#E24B4A",
    "opportunity": "#1D9E75",
    "threat":      "#BA7517",
    "neutral":     "#888780",
}
_COLOR_GRADE = {"A": "#1D9E75", "B": "#378ADD", "C": "#BA7517", "D": "#E24B4A"}
_COLOR_REC   = {"BUY": "#1D9E75", "WATCH": "#BA7517", "PASS": "#888780"}


# ── 1. Data loading ────────────────────────────────────────────────────────────

def _latest_report(pattern: str) -> dict | None:
    files = sorted(Config.REPORTS_DIR.glob(pattern), reverse=True)
    if not files:
        print(f"  ⚠ No file found for pattern: {pattern}")
        return None
    import json
    try:
        with files[0].open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  ⚠ Could not load {files[0].name}: {exc}")
        return None


def load_data() -> tuple[dict | None, dict | None, list[Path]]:
    news_report     = _latest_report("news_report_*.json")
    property_report = _latest_report("property_report_*.json")

    feat_dir   = Config.DATA_PATH / "dev" / "features"
    feat_files = sorted(feat_dir.glob("feat_*.html")) if feat_dir.exists() else []

    return news_report, property_report, feat_files


# ── 2. Build news HTML block ──────────────────────────────────────────────────

def _json_attr(data: dict) -> str:
    """JSON-encode dict safe for embedding in a single-quoted HTML attribute."""
    return json.dumps(data, ensure_ascii=False).replace("'", "&#39;")


def build_news_html(news_report: dict) -> tuple[str, int]:
    _NEWS_COLORS = {
        "opportunity": "#2ECC8A",
        "threat":      "#E8504A",
        "critical":    "#FF6B35",
        "neutral":     "#4B5563",
    }
    top_items = (news_report.get("top_items") or [])[:5]
    if not top_items:
        return "", 0

    items_html = ""
    for item in top_items:
        itype    = (item.get("type") or "neutral").lower()
        color    = _NEWS_COLORS.get(itype, _NEWS_COLORS["neutral"])
        score    = item.get("score", 0)
        title    = _esc(item.get("title") or "")
        type_lbl = itype.upper()

        summary_en = _esc(item.get("summary_en") or "")
        impact_en  = _esc(item.get("impact_en")  or "")

        data_en = _json_attr({"summary": item.get("summary_en", ""), "impact": item.get("impact_en", "")})
        data_ru = _json_attr({"summary": item.get("summary_ru", ""), "impact": item.get("impact_ru", "")})
        data_ar = _json_attr({"summary": item.get("summary_ar", ""), "impact": item.get("impact_ar", "")})
        data_tr = _json_attr({"summary": item.get("summary_tr", ""), "impact": item.get("impact_tr", "")})

        items_html += (
            f'<div class="lg-card lg-news-card"'
            f' data-en=\'{data_en}\''
            f' data-ru=\'{data_ru}\''
            f' data-ar=\'{data_ar}\''
            f' data-tr=\'{data_tr}\''
            f' style="background:#0D1525;border-left:3px solid {color};'
            f'padding:1.2rem 1.4rem;margin-bottom:1px;font-family:DM Sans,sans-serif">\n'
            f'  <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.6rem">\n'
            f'    <div style="width:6px;height:6px;border-radius:50%;background:{color};flex-shrink:0"></div>\n'
            f'    <span style="font-size:.6rem;letter-spacing:.18em;text-transform:uppercase;'
            f'color:{color}">{type_lbl}</span>\n'
            f'    <span style="margin-left:auto;font-size:.65rem;color:#C9973A">{score}/100</span>\n'
            f'  </div>\n'
            f'  <div class="lg-news-title" style="font-size:.9rem;font-weight:500;'
            f'color:#F2EFE8;margin-bottom:.5rem;line-height:1.4">{title}</div>\n'
            f'  <div class="lg-news-summary" style="font-size:.72rem;color:#8A8F9E;'
            f'line-height:1.7;margin-bottom:.5rem">{summary_en}</div>\n'
            f'  <div class="lg-news-impact" style="font-size:.68rem;color:#9A7A3A;'
            f'line-height:1.6;font-style:italic;padding-left:.8rem;'
            f'border-left:2px solid rgba(201,151,58,0.3)">{impact_en}</div>\n'
            f'</div>\n'
        )

    html = (
        '<section id="lg-news-feed" style="padding:.9rem;max-width:100%;margin:0;background:transparent">\n'
        + items_html.strip() + "\n</section>"
    )
    return html, len(top_items)


# ── 3. Build property HTML block ──────────────────────────────────────────────

def build_property_html(property_report: dict) -> tuple[str, int]:
    _GRADE_STYLES = {
        "A": ("#0D2B1F", "#2ECC8A", "rgba(46,204,138,0.3)"),
        "B": ("#1A1608", "#C9973A", "rgba(201,151,58,0.3)"),
        "C": ("#1A1200", "#BA7517", "rgba(186,117,23,0.3)"),
    }
    _REC_COLORS = {"BUY": "#2ECC8A", "WATCH": "#C9973A", "PASS": "#6B7280"}

    opps = (property_report.get("top_opportunities") or [])[:3]
    if not opps:
        return "", 0

    items_html = ""
    for opp in opps:
        grade     = opp.get("grade", "C")
        score     = opp.get("score", 0) or 0
        score_pct = int(score)
        rec       = (opp.get("recommendation") or "WATCH").upper()
        title     = _esc(opp.get("title") or "Unnamed Property")
        photo_url = _esc(opp.get("photo_url") or "")
        price_usd = opp.get("price_usd") or 0
        area_m2   = opp.get("area_m2") or 0
        loc       = opp.get("location") or {}
        city      = _esc(loc.get("city") or "—")
        district  = _esc(loc.get("district") or "—")

        grade_bg, grade_color, grade_border = _GRADE_STYLES.get(grade, _GRADE_STYLES["C"])
        rec_color = _REC_COLORS.get(rec, _REC_COLORS["WATCH"])
        price_fmt = f"${price_usd:,}" if price_usd else "—"
        brief_en  = _esc(opp.get("brief_en") or opp.get("brief") or "")

        data_en = _json_attr({"brief": opp.get("brief_en") or opp.get("brief", "")})
        data_ru = _json_attr({"brief": opp.get("brief_ru", "")})
        data_ar = _json_attr({"brief": opp.get("brief_ar", "")})
        data_tr = _json_attr({"brief": opp.get("brief_tr", "")})

        items_html += (
            f'<div class="lg-card lg-prop-card"'
            f' data-en=\'{data_en}\''
            f' data-ru=\'{data_ru}\''
            f' data-ar=\'{data_ar}\''
            f' data-tr=\'{data_tr}\''
            f' style="background:#0D1525;border:1px solid rgba(201,151,58,0.15);'
            f'margin-bottom:1px;overflow:hidden">\n'
            f'  <div style="position:relative;height:200px;overflow:hidden">\n'
            f'    <img src="{photo_url}" alt="{title}"'
            f' style="width:100%;height:100%;object-fit:cover;opacity:0.65"'
            f' onerror="this.parentElement.style.background=\'#111827\'">\n'
            f'    <div style="position:absolute;inset:0;'
            f'background:linear-gradient(to bottom,transparent 30%,#0D1525 100%)"></div>\n'
            f'    <div style="position:absolute;top:1rem;right:1rem;'
            f'padding:.3rem .8rem;border:1px solid {grade_border};'
            f'color:{grade_color};font-size:.75rem;font-weight:700;'
            f'background:rgba(13,21,37,0.8)">{grade}</div>\n'
            f'    <div style="position:absolute;bottom:1rem;left:1.2rem;right:4rem">\n'
            f'      <div style="font-size:1rem;font-weight:500;color:#F2EFE8;'
            f'line-height:1.3">{title}</div>\n'
            f'    </div>\n'
            f'  </div>\n'
            f'  <div style="padding:1.2rem">\n'
            f'    <div style="font-size:.62rem;color:#6B7280;letter-spacing:.06em;'
            f'margin-bottom:.8rem">&#128205; {city} · {district} · {area_m2}m²</div>\n'
            f'    <div style="height:2px;background:#1F2937;margin-bottom:.3rem">\n'
            f'      <div style="height:100%;width:{score_pct}%;'
            f'background:linear-gradient(90deg,rgba(201,151,58,0.4),#C9973A)"></div>\n'
            f'    </div>\n'
            f'    <div style="display:flex;justify-content:space-between;'
            f'font-size:.58rem;color:#6B7280;margin-bottom:1rem">'
            f'<span>Intelligence Score</span><span>{score}/100</span></div>\n'
            f'    <div style="display:grid;grid-template-columns:1fr 1fr;'
            f'gap:.5rem;margin-bottom:1rem">\n'
            f'      <div style="background:#080D1A;padding:.6rem .8rem">\n'
            f'        <div style="font-size:.55rem;color:#6B7280;margin-bottom:.2rem">PRICE</div>\n'
            f'        <div style="font-size:.95rem;color:#F2EFE8">{price_fmt}</div>\n'
            f'      </div>\n'
            f'      <div style="background:#080D1A;padding:.6rem .8rem">\n'
            f'        <div style="font-size:.55rem;color:#6B7280;margin-bottom:.2rem">VERDICT</div>\n'
            f'        <div style="font-size:.7rem;font-weight:600;color:{rec_color}">{rec}</div>\n'
            f'      </div>\n'
            f'    </div>\n'
            f'    <div class="lg-prop-brief" style="font-size:.7rem;color:#8A8F9E;'
            f'line-height:1.7">{brief_en}</div>\n'
            f'  </div>\n'
            f'</div>\n'
        )

    html = (
        '<section id="lg-property-feed" style="padding:.9rem;max-width:100%;margin:0;background:transparent">\n'
        + items_html.strip() + "\n</section>"
    )
    return html, len(opps)


# ── 3b. Build research HTML block ────────────────────────────────────────────

def build_research_html() -> tuple[str, int]:
    import glob as _glob

    archive_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data/research/projects",
    )

    all_projects: list[dict] = []
    region_order = ["Marmara", "Ege", "Karadeniz", "İç Anadolu", "Güneydoğu", "Doğu Anadolu"]

    for region in region_order:
        for f in _glob.glob(os.path.join(archive_dir, "*.json")):
            try:
                with open(f, encoding="utf-8") as fp:
                    data = json.load(fp)
                if data.get("region") == region:
                    for p in data.get("projects", []):
                        p["_region"] = region
                    all_projects.extend(data.get("projects", []))
                    break
            except Exception:
                continue

    all_projects.sort(key=lambda x: x.get("tradia_score", 0), reverse=True)
    top_projects = all_projects[:8]

    if not top_projects:
        print("  ⚠ No research archive projects found")
        return "", 0

    verdict_colors = {"BUY": "#2ECC8A", "WATCH": "#C9973A", "PASS": "#6B7280"}
    category_colors = {
        "tourism":               "#3B82F6",
        "luxury_tourism":        "#8B5CF6",
        "industrial":            "#F97316",
        "logistics":             "#F59E0B",
        "technology":            "#EAB308",
        "urban_renewal":         "#EC4899",
        "infrastructure":        "#14B8A6",
        "residential":           "#2ECC8A",
        "waterway":              "#06B6D4",
        "bridge":                "#6366F1",
        "airport":               "#F97316",
        "agricultural_industrial": "#84CC16",
        "luxury_coastal":        "#8B5CF6",
    }

    cards = []
    for p in top_projects:
        verdict_text = p.get("tradia_verdict", "WATCH")
        verdict_word = "WATCH"
        if verdict_text.startswith("BUY"):
            verdict_word = "BUY"
        elif verdict_text.startswith("PASS"):
            verdict_word = "PASS"

        verdict_color = verdict_colors.get(verdict_word, "#C9973A")
        score    = p.get("tradia_score", 75)
        region   = p.get("_region", "")
        category = p.get("category", "")
        cat_color = category_colors.get(category, "#C9973A")

        price_data  = p.get("price_data", {}).get("data", [])
        latest      = price_data[-1] if price_data else {}
        price_range = f"${latest.get('min',0):,}–${latest.get('max',0):,}/m²" if latest else "—"

        zones = p.get("hot_zones", [])[:3]
        zones_html = "".join([
            f'<div style="display:flex;align-items:center;gap:.5rem;'
            f'padding:.35rem 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:.62rem">'
            f'<span style="color:#C9973A;flex-shrink:0">›</span>'
            f'<span style="color:#F0EDE8">{_esc(z["name"])}</span>'
            f'<span style="color:#2ECC8A;margin-left:auto;font-size:.6rem">{_esc(z.get("upside",""))}</span>'
            f'</div>'
            for z in zones
        ])

        zones_fallback = '<div style="font-size:.62rem;color:#3A404F">Data being compiled</div>'
        zones_block = zones_html or zones_fallback

        cards.append(
            f'<div style="background:#0D1525;border:1px solid rgba(255,255,255,0.06);'
            f'padding:1.5rem;font-family:sans-serif;transition:border-color .2s">'
            f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.8rem">'
            f'<span style="font-size:.55rem;letter-spacing:.15em;text-transform:uppercase;'
            f'color:{cat_color};background:{cat_color}18;'
            f'border:1px solid {cat_color}33;padding:.2rem .6rem">'
            f'{_esc(category.replace("_"," ").upper())}</span>'
            f'<span style="font-size:.55rem;color:#3A404F;margin-left:auto">{_esc(region)}</span>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:flex-start;margin-bottom:.8rem">'
            f'<div style="font-family:Georgia,serif;font-size:.95rem;'
            f'font-weight:400;color:#F0EDE8;line-height:1.3;max-width:75%">'
            f'{_esc(p.get("name",""))}</div>'
            f'<div style="text-align:right;flex-shrink:0">'
            f'<div style="font-family:Georgia,serif;font-size:1.5rem;'
            f'color:#C9973A;line-height:1">{score}</div>'
            f'<div style="font-size:.5rem;color:#6B7280">/100</div>'
            f'</div></div>'
            f'<div style="font-size:.68rem;color:#8A8F9E;line-height:1.7;'
            f'margin-bottom:1rem;display:-webkit-box;'
            f'-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden">'
            f'{_esc(p.get("summary_en",""))}</div>'
            f'<div style="margin-bottom:1rem">'
            f'<div style="font-size:.55rem;letter-spacing:.12em;text-transform:uppercase;'
            f'color:#6B7280;margin-bottom:.4rem">HOT ZONES</div>'
            f'{zones_block}'
            f'</div>'
            f'<div style="display:flex;align-items:center;'
            f'justify-content:space-between;'
            f'padding-top:.8rem;border-top:1px solid rgba(255,255,255,0.04)">'
            f'<div style="font-size:.6rem;color:#6B7280">{_esc(price_range)} USD</div>'
            f'<div style="font-size:.62rem;font-weight:600;letter-spacing:.1em;'
            f'color:{verdict_color};border:1px solid {verdict_color}44;'
            f'padding:.2rem .7rem">{verdict_word}</div>'
            f'</div></div>'
        )

    # Region summary bar
    region_counts: dict[str, int] = {}
    for p in all_projects:
        r = p.get("_region", "")
        region_counts[r] = region_counts.get(r, 0) + 1

    region_bar = " · ".join([
        f'<span style="color:#C9973A">{_esc(r)}</span>'
        f' <span style="color:#6B7280">{c}</span>'
        for r, c in region_counts.items()
    ])

    grid = (
        '<section id="lg-research-feed" style="padding:4rem 2.5rem;'
        'background:#080D1A;border-top:1px solid rgba(255,255,255,0.05)">'
        '<div style="display:flex;align-items:flex-end;'
        'justify-content:space-between;margin-bottom:2rem;'
        'flex-wrap:wrap;gap:1rem">'
        '<div>'
        '<div style="font-size:.58rem;letter-spacing:.25em;text-transform:uppercase;'
        'color:#C9973A;margin-bottom:.5rem;display:flex;align-items:center;gap:.6rem">'
        '<span style="width:18px;height:1px;background:#C9973A;display:inline-block"></span>'
        'Regional Intelligence</div>'
        '<h2 style="font-family:Georgia,serif;font-size:2rem;'
        'font-weight:400;color:#F0EDE8;margin-bottom:.4rem">'
        'Turkey Mega Project <em style="font-style:italic;color:#E8C97A">Intelligence</em></h2>'
        f'<div style="font-size:.65rem;color:#6B7280">{region_bar}</div>'
        '</div>'
        f'<div style="font-size:.62rem;color:#3A404F;text-align:right">'
        f'Scored by Tradia Research Agent<br>'
        f'{len(all_projects)} projects · {len(region_counts)} regions</div>'
        '</div>'
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
        'gap:1px;background:rgba(255,255,255,0.04);'
        'border:1px solid rgba(255,255,255,0.04)">'
        + "".join(cards)
        + '</div>'
        '<div style="margin-top:1rem;text-align:center">'
        '<button onclick="document.getElementById(\'survey\').scrollIntoView({behavior:\'smooth\'})"'
        ' style="background:none;color:#C9973A;border:1px solid rgba(201,151,58,0.3);'
        'padding:.6rem 2rem;font-size:.65rem;letter-spacing:.15em;'
        'text-transform:uppercase;cursor:pointer;font-family:inherit">'
        'Request Full Regional Analysis →</button>'
        '</div>'
        '</section>'
    )
    return grid, len(top_projects)


# ── 4 & 5. Inject / replace HTML in target file ───────────────────────────────

def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def inject_section(html_content: str, section_id: str, new_block: str) -> tuple[str, str]:
    """
    If <section id="section_id"...> exists, replace the entire element (to closing </section>).
    Otherwise insert new_block before </body>.
    Returns (updated_html, action_label).
    """
    open_pattern = re.compile(
        rf'<section\b[^>]*\bid=["\']' + re.escape(section_id) + r'["\'][^>]*>',
        re.IGNORECASE,
    )
    m = open_pattern.search(html_content)

    if m:
        # find the matching </section> by tracking nesting depth
        start = m.start()
        search_from = m.end()
        depth = 1
        pos = search_from
        while depth > 0 and pos < len(html_content):
            next_open  = html_content.find("<section", pos)
            next_close = html_content.lower().find("</section>", pos)
            if next_close == -1:
                break
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 1
            else:
                depth -= 1
                if depth == 0:
                    end = next_close + len("</section>")
                    html_content = html_content[:start] + new_block + html_content[end:]
                    return html_content, "updated"
                pos = next_close + 1
        # fallback: no proper close found — just replace open tag area
        html_content = html_content[:start] + new_block + html_content[m.end():]
        return html_content, "updated"
    else:
        html_content = html_content.replace("</body>", new_block + "\n</body>", 1)
        return html_content, "injected"


def inject_into_site(
    news_html:      str,
    property_html:  str,
    feat_files:     list[Path],
    research_html:  str = "",
) -> tuple[str, str, int, str]:
    """Returns (news_action, property_action, features_processed, research_action)."""
    if not SITE_INDEX.exists():
        raise FileNotFoundError(f"Site index not found: {SITE_INDEX}")

    content = SITE_INDEX.read_text(encoding="utf-8")

    news_action = prop_action = research_action = "skipped"
    if news_html:
        content, news_action = inject_section(content, "lg-news-feed", news_html)
    if property_html:
        content, prop_action = inject_section(content, "lg-property-feed", property_html)
    if research_html:
        content, research_action = inject_section(content, "lg-research-feed", research_html)

    feats_done = 0
    for feat_path in feat_files:
        feat_content = feat_path.read_text(encoding="utf-8")
        id_match = re.search(r'\bid=["\']([^"\']+)["\']', feat_content)
        if not id_match:
            print(f"  ⚠ No section id found in {feat_path.name}, skipping")
            continue
        section_id = id_match.group(1)
        if not section_id.startswith("lg-"):
            print(f"  ⚠ id={section_id!r} lacks 'lg-' prefix in {feat_path.name}, skipping")
            continue
        content, action = inject_section(content, section_id, feat_content)
        print(f"  ✓ Feature {feat_path.name} ({section_id}) {action}")
        feats_done += 1

    SITE_INDEX.write_text(content, encoding="utf-8")
    return news_action, prop_action, feats_done, research_action


# ── 6. Git commit and push ─────────────────────────────────────────────────────

def git_commit_push(news_count: int, prop_count: int) -> bool:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    msg   = f"auto: agent update {today} — news:{news_count} items, properties:{prop_count} opportunities"

    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            cwd=str(SITE_REPO_PATH),
            capture_output=True,
            text=True,
        )

    _run(["git", "stash"])
    pull = _run(["git", "pull", "--rebase", "origin", "main"])
    _run(["git", "stash", "pop"])
    if pull.returncode != 0:
        print(f"  ⚠ git pull --rebase failed: {pull.stderr.strip()}")
        return False

    _run(["git", "add", "docs/index.html"])
    commit = _run(["git", "commit", "-m", msg])
    if commit.returncode != 0:
        if "nothing to commit" in commit.stdout + commit.stderr:
            print("  ℹ Nothing new to commit")
            return True
        print(f"  ⚠ git commit failed: {commit.stderr.strip()}")
        return False

    push = _run(["git", "push"])
    if push.returncode != 0:
        print(f"  ⚠ git push failed: {push.stderr.strip()}")
        return False

    print("  ✓ Pushed to GitHub Pages")
    return True


# ── 7. Verify ─────────────────────────────────────────────────────────────────

def verify_site() -> dict:
    print("  Waiting 10s for GitHub Pages to propagate…")
    time.sleep(10)
    from agents.dev_agent import DevAgent
    agent  = DevAgent()
    result = agent.check_url({
        "name":             "LandGold Main",
        "url":              SITE_MAIN_URL,
        "expected_status":  200,
        "expected_content": "TRADIA",
        "critical":         True,
    })
    health = result.get("health", "unknown")
    rt     = result.get("response_time_ms", "—")
    if health == "ok":
        print(f"  ✓ Site live — {rt}ms")
    else:
        print(f"  ⚠ Site check: {health}  ({rt}ms)")
    return result


# ── 8. Summary ────────────────────────────────────────────────────────────────

def print_summary(news_n: int, prop_n: int, feat_n: int, research_n: int, git_ok: bool, health: str) -> None:
    w = 36
    print("\n" + "=" * w)
    print("LANDGOLD DEPLOY COMPLETE")
    print("=" * w)
    print(f"News items injected:    {news_n}")
    print(f"Properties injected:    {prop_n}")
    print(f"Research projects:      {research_n}")
    print(f"Features processed:     {feat_n}")
    print(f"Git commit:             {'success' if git_ok else 'failed'}")
    print(f"Site health:            {health}")
    print("=" * w)


# ── Main ───────────────────────────────────────────────────────────────────────

def deploy() -> int:
    configure_root()
    Config.ensure_dirs()

    print("\n=== LANDGOLD DEPLOY STARTING ===\n")
    print(f"Site repo:  {SITE_REPO_PATH.resolve()}")
    print(f"Index:      {SITE_INDEX}\n")

    if not SITE_INDEX.exists():
        print(f"✗ index.html not found at {SITE_INDEX}")
        print("  Set SITE_REPO_PATH in .env to the correct path.")
        return 1

    # 1. Load data
    print("[1/7] Loading agent report data…")
    news_report, property_report, feat_files = load_data()

    # 2. Build HTML blocks
    print("[2/7] Building news HTML block…")
    news_html, news_count = ("", 0) if not news_report else build_news_html(news_report)
    if not news_html:
        print("  ⚠ No news items — skipping news section")

    print("[3/7] Building property HTML block…")
    prop_html, prop_count = ("", 0) if not property_report else build_property_html(property_report)
    if not prop_html:
        print("  ⚠ No property opportunities — skipping property section")

    print("[3b/7] Building research HTML block…")
    research_html, research_count = build_research_html()
    if research_html:
        print(f"  ✓ Research archive: {research_count} projects")
    else:
        print("  ⚠ No research data — skipping research section")

    # 4+5. Inject into site
    print("[4/7] Injecting sections into site index…")
    try:
        news_action, prop_action, feat_count, research_action = inject_into_site(
            news_html, prop_html, feat_files, research_html
        )
        if news_html:
            print(f"  ✓ News section {news_action}")
        if prop_html:
            print(f"  ✓ Property section {prop_action}")
        if research_html:
            print(f"  ✓ Research section {research_action}")
    except Exception as exc:
        print(f"  ✗ Inject failed: {exc}")
        return 1

    # 6. Git commit + push
    print("[5/7] Committing and pushing to GitHub Pages…")
    git_ok = git_commit_push(news_count, prop_count)

    # 7. Verify
    print("[6/7] Verifying deployment…")
    health_result = verify_site()
    health = health_result.get("health", "unknown")

    # 8. Summary
    print_summary(news_count, prop_count, feat_count, research_count, git_ok, health)
    return 0 if git_ok else 1


if __name__ == "__main__":
    sys.exit(deploy())
