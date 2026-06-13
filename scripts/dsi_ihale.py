#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CC-Ihale — DSİ (Devlet Su İşleri) su-altyapı ihale per-site parser (İ9)
----------------------------------------------------------------------
Kaynak: dsi.gov.tr/ihale/ihaleListe (public, $0, server-render liste).
RG'nin sığ yakaladığı SU ALTYAPI yapım işlerini doldurur (içme suyu/isale/baraj/sulama/arıtma).
Liste başlıkta iş adı + il taşır; YAPIM filtrelenir (hizmet/eğitim/malzeme alımı HARİÇ).
ihale_tarihi/bedel detay sayfasında JS-render → null (dürüst), url verilir (Analiz/manuel).
DISIPLIN: $0 · public · Lane (il HAM, harita Analiz) · KVKK kamu (kişi yok).
"""
from __future__ import annotations
import sys, urllib.request, re, json, time, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import _rg_parser_lib as P  # IL_LISTESI, IL_DISPLAY, norm

OUT = ROOT / "data" / "dsi_ihale.json"
LIST_URL = "https://www.dsi.gov.tr/ihale/ihaleListe"
BASE = "https://www.dsi.gov.tr"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Su-altyapı YAPIM (öncü sinyal) — hizmet/eğitim/malzeme alımı HARİÇ
YAPIM_RE = re.compile(r"(İSALE|ICMESU|İÇME ?SU|SULAMA|BARAJ|GÖLET|GOLET|ARITMA|"
                      r"KANALIZASYON|POMPAJ|İNŞAAT|INSAAT|YAPTIRIL|REGÜLATÖR|"
                      r"DERİVASYON|TÜNEL|KUYU)", re.I)
HARIC_RE = re.compile(r"(EĞİTİM|HİZMETİ ALIN|HİZMET ALIM|DANIŞMANLIK|SATIN ALIN|"
                      r"ALIMI|SATILACAK|KİRALAMA|ARAÇ|AKÜMÜLATÖR|TREYLER|HALAT|"
                      r"YAZILIM|SİGORTA|TEMİZLİK|GÜVENLİK|PERSONEL)", re.I)

def get(url, tries=3):
    for _ in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30
            ).read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2)
    return ""

def il_bul_title(title: str):
    n = P.norm(title)
    for il in P.IL_LISTESI:
        if re.search(rf"\b{il}\b", n):
            return P.IL_DISPLAY.get(il, il.title())
    return None

def main():
    h = html.unescape(get(LIST_URL))
    items, seen = [], set()
    for m in re.finditer(r"/Ihale/Detay/(\d+)", h):
        iid = m.group(1)
        if iid in seen:
            continue
        seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h[max(0, m.start()-300):m.start()])).strip()
        cands = re.findall(r"[A-ZÇĞİÖŞÜ0-9][A-ZÇĞİÖŞÜa-zçğıöşü0-9 ,./\-()]{15,}", seg)
        title = (cands[-1].strip() if cands else seg[-70:])[:90]
        seen.add(iid)
        # yalniz su-altyapi YAPIM (hizmet/alim haric)
        if not YAPIM_RE.search(title) or HARIC_RE.search(title):
            continue
        items.append({
            "kaynak": "dsi",
            "ihale_id": iid,
            "is_adi": title,
            "il": il_bul_title(title),
            "tur": "su_altyapi",
            "oncu_guc": "yapim_oncu",
            "ihale_tarihi": None,        # detay JS-render -> null (dürüst)
            "bedel_ham": None,
            "url": f"{BASE}/Ihale/Detay/{iid}",
            "durum": "aktif_listede",
            "aday_not": "Su-altyapı yapım öncü sinyali; lead-time Analiz fiyat-çaprazında test edilir.",
        })
    out = {
        "meta": {
            "kaynak": LIST_URL, "harvest_tarihi": time.strftime("%Y-%m-%d"),
            "toplam_yapim_sinyal": len(items),
            "v16": "Liste başlıktan su-altyapı YAPIM filtrelendi (hizmet/eğitim/malzeme alımı HARİÇ). "
                   "ihale_tarihi/bedel detay sayfasında JS-render -> null; url ile Analiz/manuel.",
            "kvkk": "Kamu su-altyapı ihalesi; kişi yok.",
            "lane": "il HAM; harita Analiz'e.",
        },
        "kayitlar": items,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[dsi] {len(items)} su-altyapı yapım sinyali -> {OUT}")
    for r in items:
        print(f"  {r['il']} | {r['is_adi'][:60]}")

if __name__ == "__main__":
    main()
