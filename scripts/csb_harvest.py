#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CC-Ihale — Milli Emlak / CSB Hazine Tasinmaz Satis (e-Devlet) TAM HARVEST
-------------------------------------------------------------------------
Kaynak: turkiye.gov.tr/csb-tasinmaz-satis-ilanlari-ihaleye-cikanlar (public, login YOK)
540 hazine tasinmaz -> il/ilce/MAHALLE + yuzolcumu + bedel (liste) + detay:
  ihale_tarihi + ada/parsel + tahmini bedel + gecici teminat + IMAR OZELLIK ADI (kullanim).

Sayfalama: ?sf=<satir_offset>  (sf=0,20,...,520 ; 20 satir/sayfa, 27 sayfa)
Detay    : ?detay=bilgisi&sf=<MUTLAKA_DOLU_offset>&index=<sayfa_ici_0-19>
           (KRITIK: sf BOS olursa server HEP page-0 detayini doner -> tum kayitlar duplike olur.
            Bu bug I2'de yakalandi/I3'te duzeltildi: sf=offset DOLU sart.)

DISIPLIN: $0 · bypass YOK (public) · KVKK kamu mulk/tuzel · Lane: mahalle HAM (harita Analiz'e).
Saf Python urllib (HTTP/1.1) — curl HTTP/2 reset sorununu by-pass eder; ek bagimlilik yok.
"""
from __future__ import annotations
import urllib.request, http.cookiejar, re, json, time, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "csb_540_harvest.json"
BASE = "https://www.turkiye.gov.tr/csb-tasinmaz-satis-ilanlari-ihaleye-cikanlar"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAGE = 20
PAUSE = 1.0          # nazik bekleme (throttle azalt)
RETRY = 4

def opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "tr-TR,tr;q=0.9"),
                     ("Accept", "text/html"), ("Referer", BASE)]
    return op

def get(op, url):
    last = None
    for _ in range(RETRY):
        try:
            return op.open(url, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            last = e; time.sleep(2)
    raise last

def total_count(h):
    m = re.search(r"([0-9]+)\s*kay[ıi]ttan", h)
    return int(m.group(1)) if m else None

def parse_list_rows(h):
    """Satir: [cins, img, imar_durumu, il, ilce, mahalle, yuzolcumu, fiyat, islem]"""
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) >= 8 and cells[2] in ("Hayır", "Evet"):
            rows.append({
                "tasinmaz_cinsi": cells[0],
                "imar_var_mi": cells[2],
                "il": cells[3], "ilce": cells[4], "mahalle_koy": cells[5],
                "yuzolcumu_m2": cells[6], "fiyat_ham": cells[7],
            })
    return rows

def dd(label, h):
    m = re.search(r"<dt>\s*" + re.escape(label) + r"\s*</dt>\s*<dd>\s*(.*?)\s*</dd>", h, re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None

def parse_detail(h):
    ihale = dd("İhale Tarihi ve Saati", h)
    tarih = None
    if ihale:
        m = re.search(r"([0-3]\d/[01]\d/20\d\d)", ihale)
        if m:
            g, a, yil = m.group(1).split("/")
            tarih = f"{yil}-{a}-{g}"
    return {
        "ihale_tarihi": tarih, "ihale_tarihi_saati_ham": ihale,
        "ada_parsel": dd("Pafta / Ada / Parsel", h),
        "imar_ozellik": dd("İmar Özellik Adı", h),
        "satilacak_yuzolcum": dd("Satılacak Yüz Ölçümü", h),
        "tahmini_bedel": dd("Toplam Tahmini Bedel", h),
        "gecici_teminat": dd("Geçici Teminat Bedeli", h),
        "tasinmaz_no": dd("Taşınmaz Numarası", h),
    }

def main():
    op = opener()
    first = get(op, BASE + "?sf=0")
    total = total_count(first) or 540
    print(f"[csb] toplam kayit: {total}", flush=True)
    records, offset, bos_atlanan = [], 0, []
    while offset < total:
        # liste sayfasi: bos donerse (throttle) birkac kez bekle+yeniden dene
        rows = []
        for deneme in range(5):
            h = first if (offset == 0 and deneme == 0) else get(op, BASE + f"?sf={offset}")
            rows = parse_list_rows(h)
            if rows:
                break
            time.sleep(4 + deneme * 3)   # throttle cooldown (backoff)
        if not rows:
            # kalici bos: bu sayfayi atla, dur DEGIL (V16: eksik dokumante)
            print(f"[csb] sf={offset} bos (5 deneme) -> ATLA", flush=True)
            bos_atlanan.append(offset)
            offset += PAGE
            continue
        for i, row in enumerate(rows):
            time.sleep(PAUSE)
            # KRITIK: detay URL'sinde sf=<offset> DOLU olmali (bos sf hep page-0 doner).
            try:
                d = parse_detail(get(op, BASE + f"?detay=bilgisi&sf={offset}&index={i}"))
                if not d.get("ihale_tarihi") and not d.get("tasinmaz_no"):
                    # bos donduyse: liste sayfasini yeniden yukle + tek retry
                    time.sleep(PAUSE)
                    get(op, BASE + f"?sf={offset}")
                    time.sleep(PAUSE)
                    d = parse_detail(get(op, BASE + f"?detay=bilgisi&sf={offset}&index={i}"))
            except Exception as e:
                d = {"ihale_tarihi": None, "detay_hata": str(e)[:80]}
            row.update(d)
            row["kaynak"] = "milli_emlak_csb"
            row["global_index"] = offset + i
            records.append(row)
        print(f"[csb] sf={offset} -> {len(rows)} satir | toplam {len(records)}", flush=True)
        # ara kayit (resume/guvenlik)
        OUT.write_text(json.dumps({"meta": {"toplam": total, "harvest_kismi": True,
                       "kaynak": BASE, "kayit": len(records)}, "kayitlar": records},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        offset += PAGE
        time.sleep(PAUSE)
    tarihli = sum(1 for r in records if r.get("ihale_tarihi"))
    OUT.write_text(json.dumps({"meta": {
        "kaynak": BASE, "harvest_tarihi": time.strftime("%Y-%m-%d"),
        "toplam_kayit": len(records), "ihale_tarihli_kayit": tarihli,
        "kvkk": "Kamu hazine tasinmazi; kisi verisi yok.",
        "lane": "il/ilce/mahalle HAM; harita Analiz'e devir.",
        "distinct_tasinmaz_no": len(set(r.get("tasinmaz_no") for r in records if r.get("tasinmaz_no"))),
        "atlanan_sayfa_offset": bos_atlanan,
        "harvest_kismi": False}, "kayitlar": records},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[csb] BITTI: {len(records)} kayit ({tarihli} tarihli) -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
