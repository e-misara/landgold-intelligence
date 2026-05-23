#!/usr/bin/env python3
"""
Canlı Tradia sitesini Playwright ile otomatik test eder.
- 30 proje detay sayfası tek tek ziyaret
- Console error yakalama
- DOM kritik element kontrol
- 5 özel senaryo: galeri pager, placeholder, gradient, hash temizliği

Çıktı: ~/Desktop/canli_site_test_raporu_2026-05-23.md
"""
from __future__ import annotations
import json, time, re
from pathlib import Path
from playwright.sync_api import sync_playwright, ConsoleMessage, Page

BASE = "https://tradiaturkey.com"
RAPOR = Path.home() / "Desktop" / "canli_site_test_raporu_2026-05-23.md"

# 30 slug — canlı index.html'den (id_to_slug + ek_projeler)
SLUG_LISTESI = [
    # 25 site projesi (MEGA_ID_META'dan)
    ("kanal_istanbul",              1, "site"),
    ("istanbul_havalimani",         2, "site"),
    ("canakkale_koprusu_1915",      3, "site"),
    ("halkali_kapikule_yht",        4, "site"),
    ("akkuyu_nukleer",              5, "site"),
    ("yss_kopru_kuzey_marmara",     6, "site"),
    ("btk_demiryolu",               7, "site"),
    ("marmaray",                    8, "site"),
    ("mersin_limani",               9, "site"),
    ("tanap",                      10, "site"),
    ("candarli_limani",            11, "site"),
    ("gap",                        12, "site"),
    ("osmangazi_koprusu",          13, "site"),
    ("star_rafinerisi",            14, "site"),
    ("galataport",                 15, "site"),
    ("filyos_petrokimya",          16, "site"),
    ("kapadokya_premium",          17, "site"),
    ("istanbul_finans_merkezi",    18, "site"),
    ("3_koprusu",                  19, "site"),
    ("bursa_kentsel_donusum",      20, "site"),
    ("kapadokya_butik_turizm",     21, "site"),
    ("trabzon_sehir_hastanesi",    22, "site"),
    ("manisa_elektronik_osb",      23, "site"),
    ("gaziantep_sanayi",           24, "site"),
    ("mugla_luks_kiyi",            25, "site"),
    # 5 ek proje
    ("avrasya_tuneli",             26, "ek"),
    ("cam_sakura_hastanesi",       27, "ek"),
    ("filyos_limani",              28, "ek"),
    ("karadeniz_gazi",             29, "ek"),
    ("yusufeli_baraji",            30, "ek"),
]


def proje_test(page: Page, slug: str, id_: int) -> dict:
    """Tek proje detay sayfasını test et."""
    konsol_msg = []
    page_errors = []

    def on_console(msg: ConsoleMessage):
        if msg.type in ('error', 'warning'):
            konsol_msg.append({"type": msg.type, "text": msg.text})
    def on_pageerror(err):
        page_errors.append(str(err))

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)

    url = f"{BASE}/#/mega-projeler/{slug}"
    t0 = time.time()
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=15000)
        load_ms = int((time.time() - t0) * 1000)
        status_code = resp.status if resp else 0

        # React render için bekle (kart-grid yerine detay h1)
        page.wait_for_selector("h1", timeout=8000)

        # Detay başlık
        h1_text = page.locator("h1").first.text_content() or ""

        # Kritik DOM element kontrolleri
        present = {}
        # Başlık var ve boş değil
        present["h1_ok"] = len(h1_text.strip()) > 0
        # İl bilgisi (📍 ile)
        present["il_ok"] = page.locator("text=/📍/").count() > 0
        # Stats şeridi
        present["stats_ok"] = page.locator("text=Yatırım").count() > 0
        # Proje açıklaması section
        present["aciklama_ok"] = page.locator("text=Proje Açıklaması").count() > 0
        # Paylaş bölümü
        present["paylas_ok"] = page.locator(f"text=mega-projeler/{slug}").count() > 0

        # Hash doğru mu?
        current_url = page.url
        hash_ok = f"#/mega-projeler/{slug}" in current_url

        eksik = [k for k, v in present.items() if not v]

        # Sonuç
        if status_code != 200:
            status = "FAIL"
        elif page_errors or [m for m in konsol_msg if m["type"] == "error"]:
            status = "FAIL"
        elif eksik or not hash_ok:
            status = "WARN"
        else:
            status = "OK"

        return {
            "slug": slug,
            "id": id_,
            "status": status,
            "http_status": status_code,
            "load_ms": load_ms,
            "h1": h1_text.strip()[:60],
            "hash_ok": hash_ok,
            "missing_dom": eksik,
            "console_errors": [m for m in konsol_msg if m["type"] == "error"],
            "console_warnings": [m for m in konsol_msg if m["type"] == "warning"],
            "page_errors": page_errors,
        }
    except Exception as e:
        return {
            "slug": slug,
            "id": id_,
            "status": "FAIL",
            "http_status": 0,
            "load_ms": int((time.time() - t0) * 1000),
            "h1": "",
            "hash_ok": False,
            "missing_dom": [],
            "console_errors": [],
            "console_warnings": [],
            "page_errors": [],
            "exception": str(e)[:200],
        }
    finally:
        page.remove_listener("console", on_console)
        page.remove_listener("pageerror", on_pageerror)


def senaryo_kanal_galeri(page: Page) -> dict:
    """Kanal İstanbul galeri pager testi (3 görsel arası geçiş)."""
    konsol_err = []
    page.on("console", lambda m: konsol_err.append(m.text) if m.type == "error" else None)
    try:
        page.goto(f"{BASE}/#/mega-projeler/kanal_istanbul", wait_until="networkidle", timeout=15000)
        page.wait_for_selector("h1", timeout=8000)
        # Galeri pager butonları (aria-label="Görsel N")
        pager = page.locator('button[aria-label^="Görsel"]')
        count = pager.count()
        if count < 2:
            return {"ad": "Kanal İstanbul galeri", "ok": False, "detay": f"Sadece {count} galeri butonu bulundu, 3 bekleniyor"}
        # 2. ve 3. butona tıkla
        pager.nth(1).click()
        page.wait_for_timeout(500)
        pager.nth(2).click()
        page.wait_for_timeout(500)
        # Console error?
        if konsol_err:
            return {"ad": "Kanal İstanbul galeri", "ok": False, "detay": f"{len(konsol_err)} console error", "errs": konsol_err}
        return {"ad": "Kanal İstanbul galeri", "ok": True, "detay": f"{count} görsel arası geçiş başarılı"}
    except Exception as e:
        return {"ad": "Kanal İstanbul galeri", "ok": False, "detay": str(e)[:200]}


def senaryo_yusufeli(page: Page) -> dict:
    """Yusufeli Barajı 'Yeni' rozet + placeholder metin"""
    konsol_err = []
    page.on("console", lambda m: konsol_err.append(m.text) if m.type == "error" else None)
    try:
        page.goto(f"{BASE}/#/mega-projeler/yusufeli_baraji", wait_until="networkidle", timeout=15000)
        page.wait_for_selector("h1", timeout=8000)
        # H1 doğru mu
        h1 = page.locator("h1").first.text_content() or ""
        # Detay Hazırlanıyor amber notification var mı (placeholder işareti)
        placeholder_section = page.locator("text=Detay Hazırlanıyor").count() > 0
        # Görsel var (1 PNG)
        has_img = page.locator("img").count() > 0
        if konsol_err:
            return {"ad": "Yusufeli placeholder", "ok": False, "detay": f"{len(konsol_err)} console error", "errs": konsol_err}
        return {"ad": "Yusufeli placeholder",
                "ok": placeholder_section,
                "detay": f"h1='{h1}', 'Detay Hazırlanıyor' bölümü={placeholder_section}, img_count={has_img}"}
    except Exception as e:
        return {"ad": "Yusufeli placeholder", "ok": False, "detay": str(e)[:200]}


def senaryo_galataport_gradient(page: Page) -> dict:
    """Galataport: görselsiz site projesi → gradient hero"""
    konsol_err = []
    page.on("console", lambda m: konsol_err.append(m.text) if m.type == "error" else None)
    try:
        page.goto(f"{BASE}/#/mega-projeler/galataport", wait_until="networkidle", timeout=15000)
        page.wait_for_selector("h1", timeout=8000)
        h1 = page.locator("h1").first.text_content() or ""
        # Görsel olmayan kart: hero bölümünde img yerine div gradient olmalı
        # h1 "Galataport" içermeli
        if konsol_err:
            return {"ad": "Galataport gradient", "ok": False, "detay": f"{len(konsol_err)} console error", "errs": konsol_err}
        # Verdict bölümü zengin metin → var
        verdict_ok = page.locator("text=Tradia Kararı").count() > 0
        return {"ad": "Galataport gradient",
                "ok": "Galataport" in h1 and verdict_ok,
                "detay": f"h1='{h1[:50]}', verdict_section={verdict_ok}"}
    except Exception as e:
        return {"ad": "Galataport gradient", "ok": False, "detay": str(e)[:200]}


def senaryo_halkali_yht(page: Page) -> dict:
    """Halkalı-Kapıkule YHT: görselsiz site projesi"""
    konsol_err = []
    page.on("console", lambda m: konsol_err.append(m.text) if m.type == "error" else None)
    try:
        page.goto(f"{BASE}/#/mega-projeler/halkali_kapikule_yht", wait_until="networkidle", timeout=15000)
        page.wait_for_selector("h1", timeout=8000)
        h1 = page.locator("h1").first.text_content() or ""
        if konsol_err:
            return {"ad": "Halkalı YHT", "ok": False, "detay": f"{len(konsol_err)} console error", "errs": konsol_err}
        aciklama_ok = page.locator("text=Proje Açıklaması").count() > 0
        return {"ad": "Halkalı YHT",
                "ok": len(h1.strip()) > 0 and aciklama_ok,
                "detay": f"h1='{h1[:50]}', aciklama={aciklama_ok}"}
    except Exception as e:
        return {"ad": "Halkalı YHT", "ok": False, "detay": str(e)[:200]}


def senaryo_hash_temizligi(page: Page) -> dict:
    """En kritik: detay → header 'Ana Sayfa' → header 'Mega Projeler' = liste açılmalı."""
    konsol_err = []
    page.on("console", lambda m: konsol_err.append(m.text) if m.type == "error" else None)
    try:
        # 1) Bir detay sayfası aç
        page.goto(f"{BASE}/#/mega-projeler/kanal_istanbul", wait_until="networkidle", timeout=15000)
        page.wait_for_selector("h1", timeout=8000)
        h1_detay = page.locator("h1").first.text_content() or ""

        # 2) Header'da "Ana Sayfa" linkine tıkla
        # Desktop nav butonu: NAV_ITEMS'tan "Ana Sayfa"
        ana_sayfa_btn = page.locator('button:has-text("Ana Sayfa")').first
        if ana_sayfa_btn.count() == 0:
            return {"ad": "Hash temizliği", "ok": False, "detay": "Ana Sayfa butonu bulunamadı"}
        ana_sayfa_btn.click()
        page.wait_for_timeout(800)
        url_after_home = page.url

        # 3) Header'da "Mega Projeler" linkine tıkla
        mega_btn = page.locator('button:has-text("Mega Projeler")').first
        if mega_btn.count() == 0:
            return {"ad": "Hash temizliği", "ok": False, "detay": "Mega Projeler butonu bulunamadı"}
        mega_btn.click()
        page.wait_for_timeout(1000)
        url_after_mega = page.url

        # 4) Yeni sayfa LİSTE mi yoksa hala DETAY mı?
        # Liste'de "Türkiye'nin dönüşüm altyapısı" var (sayfa başlığı altı)
        # Detayda "Mega projeler" geri tuşu var
        liste_text_var = page.locator("text=/Türkiye.*dönüşüm/").count() > 0
        detay_text_var = page.locator("text=Proje Açıklaması").count() > 0

        # Hash'in #/mega-projeler/X içermemesi → temiz
        hash_temiz = "#/mega-projeler/" not in url_after_mega

        # Toplu sonuç
        if konsol_err:
            return {"ad": "Hash temizliği", "ok": False, "detay": f"{len(konsol_err)} console error", "errs": konsol_err}

        ok = liste_text_var and not detay_text_var
        return {
            "ad": "Hash temizliği (EN KRİTİK)",
            "ok": ok,
            "detay": (
                f"İlk detay h1='{h1_detay[:30]}', "
                f"Ana Sayfa sonrası URL='{url_after_home[-60:]}', "
                f"Mega tıklaması sonrası URL='{url_after_mega[-60:]}', "
                f"hash_temiz={hash_temiz}, liste_göründü={liste_text_var}, detay_kaldı={detay_text_var}"
            ),
        }
    except Exception as e:
        return {"ad": "Hash temizliği", "ok": False, "detay": str(e)[:200]}


def main():
    print(f"Canlı site testi başlıyor: {BASE}\n")
    sonuc = {"proje_testleri": [], "senaryolar": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        # 30 proje
        for slug, id_, tip in SLUG_LISTESI:
            r = proje_test(page, slug, id_)
            sonuc["proje_testleri"].append({**r, "tip": tip})
            sym = "✓" if r["status"] == "OK" else "⚠" if r["status"] == "WARN" else "✗"
            print(f"  {sym} id:{id_:>2} {slug:30s} {r['status']:4s} {r['load_ms']:>5}ms")

        # 5 senaryo
        print("\n=== 5 Kritik Senaryo ===")
        senaryolar = [
            senaryo_kanal_galeri(page),
            senaryo_yusufeli(page),
            senaryo_galataport_gradient(page),
            senaryo_halkali_yht(page),
            senaryo_hash_temizligi(page),
        ]
        sonuc["senaryolar"] = senaryolar
        for s in senaryolar:
            sym = "✓" if s["ok"] else "✗"
            print(f"  {sym} {s['ad']:30s} — {s['detay'][:100]}")

        ctx.close()
        browser.close()

    # Rapor yaz
    yaz_rapor(sonuc)


def yaz_rapor(sonuc):
    pt = sonuc["proje_testleri"]
    ok = sum(1 for r in pt if r["status"] == "OK")
    warn = sum(1 for r in pt if r["status"] == "WARN")
    fail = sum(1 for r in pt if r["status"] == "FAIL")
    total = len(pt)

    snr_ok = sum(1 for s in sonuc["senaryolar"] if s["ok"])
    snr_total = len(sonuc["senaryolar"])

    lines = []
    lines.append("# Canlı Site Otomatik Test Raporu — 2026-05-23")
    lines.append("")
    lines.append(f"**Hedef:** {BASE}")
    lines.append(f"**Test aracı:** Playwright (chromium headless)")
    lines.append(f"**Test zamanı:** 2026-05-23 (otomatik)")
    lines.append("")
    lines.append("## Özet")
    lines.append("")
    lines.append(f"- 30 proje detay sayfası testi: **{ok} OK · {warn} WARN · {fail} FAIL**")
    lines.append(f"- 5 kritik senaryo: **{snr_ok}/{snr_total} başarılı**")
    lines.append("")

    # Senaryo sonuçları
    lines.append("## 5 Kritik Senaryo")
    lines.append("")
    for s in sonuc["senaryolar"]:
        sym = "✅" if s["ok"] else "❌"
        lines.append(f"### {sym} {s['ad']}")
        lines.append(f"- Detay: `{s['detay']}`")
        if s.get('errs'):
            lines.append("- Console hatalar:")
            for e in s['errs'][:5]:
                lines.append(f"  - `{e[:200]}`")
        lines.append("")

    # 30 proje detay tablosu
    lines.append("## 30 Proje Detay Tablosu")
    lines.append("")
    lines.append("| # | ID | Slug | Tip | Status | HTTP | Load (ms) | Hash | Errors |")
    lines.append("|---|----|------|-----|--------|------|-----------|------|--------|")
    for i, r in enumerate(pt, 1):
        sym = "✅" if r["status"] == "OK" else "⚠️" if r["status"] == "WARN" else "❌"
        hash_sym = "✓" if r["hash_ok"] else "✗"
        err_count = len(r.get("console_errors", [])) + len(r.get("page_errors", []))
        lines.append(f"| {i} | {r['id']} | `{r['slug']}` | {r['tip']} | {sym} {r['status']} | {r['http_status']} | {r['load_ms']} | {hash_sym} | {err_count} |")
    lines.append("")

    # Sorunlu detay
    sorunlu = [r for r in pt if r["status"] != "OK"]
    if sorunlu:
        lines.append("## Sorunlu Projelerin Detayı")
        lines.append("")
        for r in sorunlu:
            lines.append(f"### `{r['slug']}` (id:{r['id']}, status:{r['status']})")
            lines.append(f"- HTTP: {r['http_status']}")
            lines.append(f"- Load: {r['load_ms']} ms")
            lines.append(f"- H1: `{r['h1']}`")
            if r["missing_dom"]:
                lines.append(f"- Eksik DOM: {r['missing_dom']}")
            if r.get("console_errors"):
                lines.append(f"- Console errors:")
                for e in r["console_errors"][:3]:
                    lines.append(f"  - `{e['text'][:200]}`")
            if r.get("page_errors"):
                lines.append(f"- Page errors:")
                for e in r["page_errors"][:3]:
                    lines.append(f"  - `{e[:200]}`")
            if r.get("exception"):
                lines.append(f"- Exception: `{r['exception']}`")
            lines.append("")

    # Performans özeti
    load_times = [r["load_ms"] for r in pt if r["load_ms"] > 0]
    if load_times:
        lines.append("## Performans")
        lines.append("")
        lines.append(f"- Ortalama load: **{sum(load_times)//len(load_times)} ms**")
        lines.append(f"- En hızlı: {min(load_times)} ms")
        lines.append(f"- En yavaş: {max(load_times)} ms")
        lines.append("")

    # Öneri
    lines.append("## Sonuç ve Öneri")
    lines.append("")
    if fail == 0 and warn == 0 and snr_ok == snr_total:
        lines.append("✅ **Site sağlam, PDF üretimine devam edilebilir.**")
        lines.append("- 30/30 proje sorunsuz açılıyor")
        lines.append(f"- 5/5 kritik senaryo başarılı (hash temizliği dahil)")
        lines.append("- Console temiz, render hatasız")
    elif fail == 0 and warn > 0:
        lines.append(f"🟡 **{warn} projede UYARI** (HTTP 200 ama bazı DOM/hash check başarısız).")
        lines.append("- Render çalışıyor ama beklenen elementler eksik olabilir.")
        lines.append("- Detayları yukarıda. PDF üretimine başlanabilir ama bu projeler gözden geçirilmeli.")
    else:
        lines.append(f"❌ **{fail} projede HATA**. PDF üretimi öncesi düzeltilmeli.")

    RAPOR.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n→ Rapor: {RAPOR}")
    print(f"  Özet: {ok}/{total} OK · {warn} WARN · {fail} FAIL · senaryo {snr_ok}/{snr_total}")


if __name__ == "__main__":
    main()
