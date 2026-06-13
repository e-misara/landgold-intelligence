#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CC-Ihale — RESMI GAZETE Gunluk Ihale Parser  (Artirma, Eksiltme ve Ihale Ilanlari)
----------------------------------------------------------------------------------
Kaynak: resmigazete.gov.tr/ilanlar/eskiilanlar/YYYY/MM/YYYYMMDD-3.htm  (public, $0)
  -3.htm = indeks (cp1254) -> her ilan ayri PDF (YYYYMMDD-3-N.pdf).
  RG agregatordur: belediye + Milli Emlak + Ozellestirme + TIGEM + TMSF + bakanlik.

Akis: indeks fetch (cp1254) -> N pdf linki -> her pdf pypdf text -> 1 ilan = 1 kayit
      -> kurum / il / ilce / islem_tipi / kategori / IHALE TARIHI / bedel.

Mevcut tradia_ihale/parser.py yardimcilari (IL_LISTESI, KATEGORI, il_bul, ...) re-use edilir.
DISIPLIN: $0 · public · KVKK kamu/tuzel · Lane: il/ilce HAM (mahalle/harita Analiz'e).
launchd gunluk job icin uygundur (bkz. com.tradia.ccihale.rg.plist).
"""
from __future__ import annotations
import sys, re, json, io, time, datetime
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSONL = ROOT / "data" / "rg_ihale_gunluk.jsonl"
OUT_GUN = ROOT / "data" / "rg_gun_ozet.json"

# --- mevcut modulun proven yardimcilarini re-use et ---
sys.path.insert(0, str(ROOT / "scripts"))  # I6: vendored, Desktop/TCC bagimliligi yok
import _rg_parser_lib as P  # noqa: E402  (norm, il_bul, ilce_bul, kategori_belirle, islem_tipi, ACTION_VERB_REGEX)

import pypdf  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
AYLAR = {"OCAK":1,"SUBAT":2,"MART":3,"NISAN":4,"MAYIS":5,"HAZIRAN":6,"TEMMUZ":7,
         "AGUSTOS":8,"EYLUL":9,"EKIM":10,"KASIM":11,"ARALIK":12}

def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    data = urllib.request.urlopen(req, timeout=40).read()
    return data if binary else data

def index_url(d: datetime.date) -> str:
    return (f"https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/"
            f"{d.year}/{d.month:02d}/{d.strftime('%Y%m%d')}-3.htm")

def pdf_links(index_html: bytes, d: datetime.date) -> list[str]:
    html = index_html.decode("cp1254", "replace")
    base = index_url(d).rsplit("/", 1)[0] + "/"
    out = []
    for href in re.findall(r'href="([^"]+\.pdf)"', html, re.I):
        out.append(href if href.startswith("http") else base + href)
    # dogal sira: -3-1, -3-2 ...
    def k(u):
        m = re.search(r"-3-(\d+)\.pdf", u)
        return int(m.group(1)) if m else 999
    return sorted(set(out), key=k)

def pdf_text(b: bytes) -> str:
    try:
        r = pypdf.PdfReader(io.BytesIO(b))
        return "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception:
        return ""

# --- tarih & bedel cikarimi ---
TARIH_DMY = re.compile(r"\b([0-3]?\d)[./]([01]?\d)[./](20\d\d)\b")
TARIH_METIN = re.compile(r"\b([0-3]?\d)\s+([A-ZÇĞİÖŞÜ]+)\s+(20\d\d)\b")
SAAT = re.compile(r"\bsaat\b", re.I)
# Bedel: "Muhammen/Tahmini/Keşif Bedeli (TL) : 1.234.567,00" + esnek varyantlar
PARA = r"([0-9]{1,3}(?:[.\s][0-9]{3})+(?:,[0-9]{2})?)"
BEDEL = re.compile(
    r"(?:muhammen|tahmini|mufredat|ke[sş]if)\s+bedel[a-zçğıöşü ]*?(?:\(?\s*TL\s*\)?)?\s*[:.]?\s*" + PARA,
    re.I)
BEDEL2 = re.compile(r"bedeli\s*\(\s*TL\s*\)\s*[:.]?\s*" + PARA, re.I)

# Merkezi / cok-ilceli kurumlar: il kurum adindan gelmeli; govde-tarama YANLIS-POZ uretir
# (orn. Ozellestirme ilani govdesinde gecen "AGRI" il SANILMAMALI). Bunlarda govde-il tarama KAPALI.
MERKEZI_KURUM = re.compile(
    r"(OZELLESTIRME|TASARRUF MEVDUATI|TARIM ISLETMELERI|TIGEM|TPAO|TCDD|"
    r"DEVLET DEMIRYOLLARI|ETI MADEN|MAKINA VE KIMYA|TMSF|DSI GENEL|"
    r"VAKIFLAR GENEL|HAZINE VE MALIYE)", re.UNICODE)

def ihale_tarihi(text: str, yayin: datetime.date) -> str | None:
    """Ilan govdesinden ihale tarihi; yayindan ONCE olanlari eler (kabul/ilan tarihi olabilir)."""
    adaylar = []
    for g, a, y in TARIH_DMY.findall(text):
        try: adaylar.append(datetime.date(int(y), int(a), int(g)))
        except ValueError: pass
    nrm = P.norm(text)
    for g, ay, y in TARIH_METIN.findall(text):
        ayn = P.norm(ay)
        if ayn in AYLAR:
            try: adaylar.append(datetime.date(int(y), AYLAR[ayn], int(g)))
            except ValueError: pass
    gelecek = sorted([d for d in adaylar if d >= yayin])
    return gelecek[0].isoformat() if gelecek else None

def bedel_bul(text: str) -> str | None:
    m = BEDEL.search(text) or BEDEL2.search(text)
    return re.sub(r"\s", "", m.group(1)).strip() if m else None

# --- İ8 ALTYAPI ÖNCÜ SİNYAL sınıflandırıcı (normalize ASCII upper, full text) ---
# NOT: Sadece altyapı-NESNESİ anahtarlari (kurum-adı tek-başına TETİKLEMEZ — TCDD balast/
# kereste alımı gibi operasyonel tedarik gürültüsünü önler; gerçek yol/su/enerji İŞİ ister).
ALTYAPI_KEYWORDS = {
    "enerji": ["ENERJI NAKIL", "NAKIL HATTI", "TRAFO MERKEZI", "TRAFO BINASI",
               "ELEKTRIK DAGITIM", "ELEKTRIK SEBEKE", "SEBEKE YENILEME", "AYDINLATMA",
               "SALT MERKEZI", "ENERJI ISI", "RUZGAR SANTRAL", "GUNES SANTRAL", "YG-AG", "YG AG"],
    "dogalgaz": ["DOGALGAZ", "DOGAL GAZ", "BORU HATTI", "GAZ DAGITIM", "DAGITIM SEBEKE"],
    "ulasim": ["KARAYOLU", "KARAYOLLARI", "KOPRU YAPIM", "KOPRU INSAAT", "METRO INSAAT",
               "METRO YAPIM", "RAYLI SISTEM", "VIYADUK", "OTOYOL", "BOLUNMUS YOL",
               "YOL YAPIM", "YOL INSAAT", "ALT GECIT", "UST GECIT", "TUNEL INSAAT",
               "ASFALT", "SICAK KARISIM", "BORDUR", "PARKE DOSEME"],
    "su_altyapi": ["ICME SUYU", "KANALIZASYON", "ARITMA TESIS", "ATIKSU", "ISALE HATTI",
                   "SU DEPOSU", "BARAJ", "GOLET", "SULAMA", "ICMESUYU", "YAGMURSUYU"],
    "yesil_rekreasyon": ["MILLET BAHCESI", "MESIRE", "REKREASYON", "YESIL ALAN",
                          "KENT PARKI", "PARK YAPIM", "PEYZAJ", "MILLI PARK",
                          "BOTANIK", "SAHIL DUZENLEME", "KIYI DUZENLEME"],
    "osb_kentsel_altyapi": ["ALTYAPI YAPIM", "ALTYAPI INSAAT", "USTYAPI VE ALTYAPI",
                            "OSB ALTYAPI", "KENTSEL ALTYAPI"],
}

# Insaat/yapim baglami: ÖNCÜ SİNYAL ancak YAPIM/İNŞAAT ihalesi ise (mal/hizmet alimi DEGIL).
# "Balast/kereste alimi" gibi malzeme alimlari altyapi-kurumdan olsa bile ÖNCÜ SİNYAL DEGIL.
INSAAT_BAGLAM = re.compile(
    r"(YAPILACAKTIR|YAPTIRILACAKTIR|INSAAT|YAPIM ISI|ONARIM KARSILIGI|"
    r"YAPIM VEYA ONARIM|TADILAT|GENISLETILECEKTIR|ALTYAPI)", re.UNICODE)

def altyapi_kategori(subject_nrm: str) -> list:
    """Yalniz SUBJECT/baslik bolgesinden (govde boilerplate'i degil)."""
    hits = []
    for kat, kws in ALTYAPI_KEYWORDS.items():
        if any(kw in subject_nrm for kw in kws):
            hits.append(kat)
    return hits

def kurum_bul(text: str) -> str | None:
    nrm = P.norm(text)
    m = P.KURUM_REGEX.search(nrm)
    if not m:
        return None
    # orijinal metinden ayni araligi (yaklasik) cek - basit: norm kurumu title'la
    return re.sub(r"\s+", " ", m.group(1).strip()).title()

def parse_ilan(text: str, yayin: datetime.date, idx: int) -> dict:
    nrm = P.norm(text)
    verbs = P.ACTION_VERB_REGEX.findall(nrm)
    av = verbs[0] if verbs else ""
    kurum = kurum_bul(text)
    kurum_norm = P.norm(kurum or "")
    baslik_norm = nrm[:300]
    # il: ÖNCE kurum adindan (≥2 kaynak: kurum birincil). Merkezi/cok-ilceli kurumda
    # govde-tarama KAPALI (yanlis-poz onler). Aksi halde govdeden fallback + il_kaynak isaretle.
    merkezi = bool(MERKEZI_KURUM.search(kurum_norm))
    il = P.il_bul(kurum_norm)
    il_kaynak = "kurum" if il else None
    if not il and not merkezi:
        il = P.il_bul(nrm[:1200]); il_kaynak = "govde" if il else None
    # image-PDF tespiti: cikarilan metin cok kisa -> bedel/detay goruntude (OCR gerek)
    image_pdf = len(text.strip()) < 200
    bedel = bedel_bul(text)
    kats = P.kategori_belirle(baslik_norm, kurum_norm, nrm)
    # SUBJECT bolgesi = baslik + kurum (govde boilerplate HARIC -> yanlis-poz onler)
    subject = (nrm[:400] + " " + kurum_norm)
    altyapi_kats = altyapi_kategori(subject)
    insaat = bool(INSAAT_BAGLAM.search(subject))
    # katman: gayrimenkul (satış/kira/arsa) | altyapi (öncü=infra+inşaat) | diger
    gm = bool(set(kats) & {"belediye_gayrimenkul", "toki", "osb", "kira_kiralama"}) or \
        (av in ("SATILACAKTIR",) and "TASINMAZ" in nrm[:400])
    # ÖNCELİK: altyapı+inşaat ÖNCÜ SİNYAL'dir (OSB altyapı/atıksu arıtma gibi dual kayıtlar
    # gm gate'ine kapılmasın). Sonra gayrimenkul, sonra zayıf altyapı, sonra diğer.
    if altyapi_kats and insaat:
        katman = "altyapi"
    elif gm:
        katman = "gayrimenkul"
    elif altyapi_kats:
        katman = "altyapi"
    else:
        katman = "diger"
    # ÖNCÜ SİNYAL gücü: insaat_baglam=True => yapım/inşaat (güçlü lead-time adayı);
    # False => malzeme/hizmet alımı (zayıf). Analiz bu flag'le süzer.
    oncu_guc = "yapim_oncu" if (katman == "altyapi" and insaat) else \
               ("malzeme_hizmet" if katman == "altyapi" else None)
    return {
        "id": f"{yayin.strftime('%Y%m%d')}_rg_{idx:02d}",
        "kaynak": "resmi_gazete",
        "yayin_tarihi": yayin.isoformat(),
        "ihale_tarihi": ihale_tarihi(text, yayin),
        "kurum": kurum,
        "il": il,
        "il_kaynak": il_kaynak,
        "merkezi_kurum": merkezi,
        "ilce": P.ilce_bul(nrm, il),
        "islem_tipi": P.islem_tipi(av, baslik_norm, kurum_norm) if av else None,
        "kategoriler": kats,
        "katman": katman,
        "altyapi_kategoriler": altyapi_kats,
        "insaat_baglam": insaat if katman == "altyapi" else None,
        "oncu_guc": oncu_guc,
        "bedel_ham": bedel,
        "bedel_kaynak": ("metin" if bedel else ("image_pdf_OCR_gerek" if image_pdf else "yok")),
        "action_verb": av or None,
    }

def tradia_relevant(rec: dict) -> bool:
    kats = set(rec.get("kategoriler") or [])
    if kats & {"belediye_gayrimenkul", "toki", "osb", "kira_kiralama"}:
        return True
    return rec.get("islem_tipi") in ("satis", "kiralama")

def run(d: datetime.date) -> dict:
    try:
        idx = fetch(index_url(d))
    except Exception as e:
        return {"tarih": d.isoformat(), "durum": "indeks_yok", "hata": str(e)[:80], "kayit": 0}
    links = pdf_links(idx, d)
    kayitlar = []
    for i, url in enumerate(links, 1):
        try:
            txt = pdf_text(fetch(url, binary=True))
        except Exception:
            txt = ""
        if not txt.strip():
            continue
        rec = parse_ilan(txt, d, i)
        rec["tradia_relevant"] = tradia_relevant(rec)
        rec["pdf"] = url.rsplit("/", 1)[-1]
        kayitlar.append(rec)
        time.sleep(0.3)
    # jsonl append (id-dedup)
    var = set()
    if OUT_JSONL.exists():
        for ln in OUT_JSONL.read_text(encoding="utf-8").splitlines():
            try: var.add(json.loads(ln)["id"])
            except Exception: pass
    with OUT_JSONL.open("a", encoding="utf-8") as f:
        for r in kayitlar:
            if r["id"] not in var:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ozet = {"tarih": d.isoformat(), "durum": "ok", "ilan_pdf": len(links),
            "kayit": len(kayitlar), "tasinmaz_relevant": sum(1 for r in kayitlar if r["tradia_relevant"]),
            "tarihli": sum(1 for r in kayitlar if r["ihale_tarihi"])}
    OUT_GUN.write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    return ozet

def main():
    if len(sys.argv) > 1:
        d = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        d = datetime.date.today()
    print(json.dumps(run(d), ensure_ascii=False))

if __name__ == "__main__":
    main()
