"""
Tradia Ihale Parser
-------------------
~/Desktop/tradia/tradia_tic/data/raw_rg/ altindaki 41 PDF'i tarar,
"ARTIRMA, EKSILTME VE IHALE ILANLARI" bolumunden ihaleleri ayiklar,
her ihaleyi yapilandirilmis bir kayit olarak data/parsed/ihaleler.jsonl'e yazar.

Kural-bazli, AI yok. pypdf kullanir.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT.parent / "tradia_tic" / "data" / "raw_rg"
OUT_FILE = ROOT / "data" / "parsed" / "ihaleler.jsonl"
SUMMARY_FILE = ROOT / "data" / "parsed" / "_ozet.json"

# ----- yardimcilar -----------------------------------------------------------

def norm(s: str) -> str:
    """Turkce karakterleri ascii'ye dusur, upper'a cevir, fazlaliklari sil."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("İ", "I").replace("ı", "i")
    return re.sub(r"\s+", " ", s.upper()).strip()

# ----- bolum sinir tespiti ---------------------------------------------------

IHALE_BAS_PATTERNS = [
    re.compile(r"ARTIRMA[,\s]+EKSILTME\s+VE\s+IHALE\s+ILANLARI"),
    re.compile(r"IHALE\s+ILANLARI"),
]
CESITLI_PATTERN = re.compile(r"CESITLI\s+ILANLAR")
SON_PATTERN = re.compile(r"ICINDEKILER")

def ihale_sayfa_araligi(pdf: pypdf.PdfReader) -> tuple[int, int] | None:
    """PDF icinde ihale bolumunun (bas, son) sayfa indekslerini dondurur (exclusive son)."""
    bas = None
    son = None
    page_norms: list[str] = []
    try:
        toplam_sayfa = len(pdf.pages)
    except Exception:
        return None
    for i in range(toplam_sayfa):
        try:
            p = pdf.pages[i]
            t = p.extract_text() or ""
        except Exception:
            t = ""
            p = None
        n = norm(t[:600])
        page_norms.append(n)
        if bas is None and any(pat.search(n) for pat in IHALE_BAS_PATTERNS):
            bas = i
            continue
        if bas is not None and son is None and CESITLI_PATTERN.search(n):
            son = i
            break
        if bas is not None and son is None and SON_PATTERN.search(n):
            son = i
            break
    if bas is None:
        return None
    if son is None:
        son = toplam_sayfa
    return (bas, son)


# ----- ihale birim ayirma ----------------------------------------------------

# Bir ihalenin sonunu belirten action verb'ler. PDF'lerde satir bolunmesi
# yuzunden basliklar 3-5 satira yayilabilir, bu yuzden tum bolgeyi tarayip
# action verb'lerin pozisyonundan ihale baslangicini geri buluyoruz.
ACTION_VERB_REGEX = re.compile(
    r"\b(?:SATILACAKTIR|ALINACAKTIR|KIRALANACAKTIR|YAPTIRILACAKTIR|YAPILACAKTIR|"
    r"VERILECEKTIR|EDILECEKTIR|TAMAMLANACAKTIR|ONARILACAKTIR|GENISLETILECEKTIR|"
    r"DUZENLENECEKTIR)\b",
    re.UNICODE,
)

KURUM_REGEX = re.compile(
    r"([A-ZÇĞİÖŞÜa-zçğıöşü0-9 \./\-]+?(?:BASKANLIGINDAN|MUDURLUGUNDEN|"
    r"GENEL\s+MUDURLUGUNDEN|KOMUTANLIGINDAN|REKTORLUGUNDEN|MUSTESARLIGINDAN|"
    r"BELEDIYESINDEN|BAKANLIGI|ODALARI[NM]DAN|VAKFI[NM]DAN|MUDURLUGUNCE))\s*:",
    re.UNICODE,
)

IL_LISTESI = [
    "ADANA","ADIYAMAN","AFYONKARAHISAR","AGRI","AMASYA","ANKARA","ANTALYA","ARTVIN",
    "AYDIN","BALIKESIR","BILECIK","BINGOL","BITLIS","BOLU","BURDUR","BURSA",
    "CANAKKALE","CANKIRI","CORUM","DENIZLI","DIYARBAKIR","EDIRNE","ELAZIG","ERZINCAN",
    "ERZURUM","ESKISEHIR","GAZIANTEP","GIRESUN","GUMUSHANE","HAKKARI","HATAY","ISPARTA",
    "MERSIN","ISTANBUL","IZMIR","KARS","KASTAMONU","KAYSERI","KIRKLARELI","KIRSEHIR",
    "KOCAELI","KONYA","KUTAHYA","MALATYA","MANISA","KAHRAMANMARAS","MARDIN","MUGLA",
    "MUS","NEVSEHIR","NIGDE","ORDU","RIZE","SAKARYA","SAMSUN","SIIRT","SINOP","SIVAS",
    "TEKIRDAG","TOKAT","TRABZON","TUNCELI","SANLIURFA","USAK","VAN","YOZGAT","ZONGULDAK",
    "AKSARAY","BAYBURT","KARAMAN","KIRIKKALE","BATMAN","SIRNAK","BARTIN","ARDAHAN",
    "IGDIR","YALOVA","KARABUK","KILIS","OSMANIYE","DUZCE",
]
IL_DISPLAY = {
    "ISTANBUL": "İstanbul","IZMIR": "İzmir","CANAKKALE":"Çanakkale","CORUM":"Çorum",
    "MUGLA":"Muğla","USAK":"Uşak","SANLIURFA":"Şanlıurfa","KAHRAMANMARAS":"Kahramanmaraş",
    "DIYARBAKIR":"Diyarbakır","KIRSEHIR":"Kırşehir","KOCAELI":"Kocaeli","BALIKESIR":"Balıkesir",
    "KIRKLARELI":"Kırklareli","SIVAS":"Sivas","KUTAHYA":"Kütahya","NIGDE":"Niğde",
    "AGRI":"Ağrı","BITLIS":"Bitlis","ESKISEHIR":"Eskişehir","TEKIRDAG":"Tekirdağ",
    "MUS":"Muş","HATAY":"Hatay","CANKIRI":"Çankırı","GUMUSHANE":"Gümüşhane",
    "IGDIR":"Iğdır","KARABUK":"Karabük","SIRNAK":"Şırnak","SIIRT":"Siirt",
    "AYDIN":"Aydın","TUNCELI":"Tunceli","ELAZIG":"Elazığ","ERZINCAN":"Erzincan",
    "DUZCE":"Düzce","BARTIN":"Bartın","AFYONKARAHISAR":"Afyonkarahisar","BILECIK":"Bilecik",
    "BINGOL":"Bingöl","BURDUR":"Burdur","GIRESUN":"Giresun","KASTAMONU":"Kastamonu",
    "KAYSERI":"Kayseri","KIRIKKALE":"Kırıkkale","MALATYA":"Malatya","MANISA":"Manisa",
    "MARDIN":"Mardin","NEVSEHIR":"Nevşehir","ORDU":"Ordu","SAKARYA":"Sakarya",
    "SAMSUN":"Samsun","TRABZON":"Trabzon","VAN":"Van","YOZGAT":"Yozgat",
    "AKSARAY":"Aksaray","BAYBURT":"Bayburt","KARAMAN":"Karaman","BATMAN":"Batman",
    "OSMANIYE":"Osmaniye","YALOVA":"Yalova","ARDAHAN":"Ardahan","KILIS":"Kilis",
    "ANKARA":"Ankara","ANTALYA":"Antalya","KONYA":"Konya","ADANA":"Adana",
    "BOLU":"Bolu","BURSA":"Bursa","DENIZLI":"Denizli","EDIRNE":"Edirne",
    "ERZURUM":"Erzurum","GAZIANTEP":"Gaziantep","HAKKARI":"Hakkari","ISPARTA":"Isparta",
    "KARS":"Kars","MERSIN":"Mersin","RIZE":"Rize","SINOP":"Sinop","TOKAT":"Tokat",
    "ZONGULDAK":"Zonguldak","ADIYAMAN":"Adıyaman","AMASYA":"Amasya","ARTVIN":"Artvin",
}

# kategori anahtar kelime kumeleri (Turkce normalize edilmis)
KATEGORI_KEYWORDS = {
    "osb": ["ORGANIZE SANAYI","OSB","SANAYI PARSEL"],
    "belediye_gayrimenkul": [
        "TASINMAZ SATIL","TASINMAZLAR SATIL","ARSA SATIL","GAYRIMENKUL SATIL",
        "ARSA KIRAYA","TASINMAZ KIRAYA","TASINMAZLARIN SATIS",
    ],
    "toki": ["TOKI","SOSYAL KONUT","YENIDEN INSA","TOPLU KONUT","KONUT YAPIM"],
    "karayollari": [
        "KARAYOLLARI","YOL YAPIM","YOL GENISLET","YOL ONARIM","YOL BAKIM",
        "VIYADUK","TUNEL","OTOYOL","KOPRU YAPIM","ASFALT",
    ],
    "dsi": ["DSI","BARAJ","SULAMA","ICME SUYU","KANAL YAPIM","ATIKSU"],
    "saglik": ["SEHIR HASTANESI","HASTANE YAPIM","SAGLIK KOMPLEKS","SAGLIK TESIS"],
    "egitim": ["UNIVERSITE","KAMPUS","EGITIM KOMPLEKS","OKUL YAPIM","FAKULTE","YURT YAPIM"],
    "enerji": ["RUZGAR ENERJI","GUNES ENERJI","TRAFO","ENERJI NAKIL","RUZGAR SANTRAL","GUNES SANTRAL"," GES "," RES "],
    "afet_yeniden_insa": ["DEPREM","AFET","YENIDEN INSA","HASARSIZ","ENKAZ KALDIRMA"],
    "kira_kiralama": ["KIRAYA VERILECEK","KIRALANACAKTIR","KIRAYA VERILMESI"],
    "mal_alimi": ["MAL ALINACAKTIR","MAL ALIMI"],
    "hizmet_alimi": ["HIZMET ALINACAKTIR","HIZMET ALIMI"],
    "yapim_isi": ["YAPIM ISI","YAPTIRILACAKTIR","INSAATI YAPTIRIL"],
}

ACTION_VERB_TO_TIP = {
    "SATILACAKTIR": "satis",
    "KIRAYA": "kiralama",
    "KIRALANACAKTIR": "kiralama",
    "ALINACAKTIR": "alim",
    "YAPTIRILACAKTIR": "yapim",
    "YAPILACAKTIR": "yapim",
    "VERILECEKTIR": "kiralama_veya_hizmet",
    "EDILECEKTIR": "ihale_genel",
    "TAMAMLANACAKTIR": "yapim",
    "ONARILACAKTIR": "yapim",
    "GENISLETILECEKTIR": "yapim",
    "DUZENLENECEKTIR": "ihale_genel",
}

# baslik icindeki ekstra ipuclari
ISLEM_ALT_TIP = [
    ("mal_alim", re.compile(r"MAL\s+ALIN|MAL\s+ALIMI")),
    ("hizmet_alim", re.compile(r"HIZMET\s+ALIN|HIZMET\s+ALIMI")),
    ("yapim_isi", re.compile(r"YAPIM\s+ISI|INSAATI\s+YAP")),
    ("kira", re.compile(r"KIRAYA\s+VERILECEK|KIRALAMA")),
    ("satis", re.compile(r"SATIS|SATILACAK")),
]


def il_bul(metin_norm: str) -> str | None:
    """Kurum ifadesi icinde gecen il adini ariyor."""
    for il in IL_LISTESI:
        if re.search(rf"\b{il}\b", metin_norm):
            return IL_DISPLAY.get(il, il.title())
    return None


# Tradia odak illeri ve ilceleri (norm edilmis ASCII upper).
# Generic regex'in yakalayamadigi durumlar icin fallback sozluk.
ODAK_IL_ILCELERI = {
    "BURSA": [
        "OSMANGAZI", "YILDIRIM", "NILUFER", "GEMLIK", "MUDANYA", "KARACABEY",
        "MUSTAFAKEMALPASA", "INEGOL", "YENISEHIR", "ORHANGAZI", "GURSU",
        "KESTEL", "BUYUKORHAN", "HARMANCIK", "KELES", "ORHANELI", "IZNIK",
    ],
    "ISTANBUL": [
        "KADIKOY", "BESIKTAS", "SISLI", "USKUDAR", "BAKIRKOY", "FATIH", "BEYOGLU",
        "PENDIK", "MALTEPE", "KARTAL", "ATASEHIR", "UMRANIYE", "TUZLA", "CEKMEKOY",
        "SANCAKTEPE", "BEYKOZ", "EYUP", "EYUPSULTAN", "ZEYTINBURNU", "BAYRAMPASA",
        "ESENLER", "GAZIOSMANPASA", "KAGITHANE", "SARIYER", "ATATURK", "BAGCILAR",
        "GUNGOREN", "BAHCELIEVLER", "AVCILAR", "KUCUKCEKMECE", "BUYUKCEKMECE",
        "BEYLIKDUZU", "ESENYURT", "ARNAVUTKOY", "BASAKSEHIR", "SILIVRI", "CATALCA",
        "SILE", "ADALAR",
    ],
    "ANKARA": [
        "CANKAYA", "KECIOREN", "YENIMAHALLE", "MAMAK", "ETIMESGUT", "SINCAN",
        "ALTINDAG", "POLATLI", "PURSAKLAR", "GOLBASI", "BEYPAZARI", "AKYURT",
        "CUBUK", "ELMADAG", "KAZAN", "KIZILCAHAMAM",
    ],
    "IZMIR": [
        "KONAK", "KARSIYAKA", "BORNOVA", "BUCA", "CIGLI", "GAZIEMIR", "BALCOVA",
        "NARLIDERE", "GUZELBAHCE", "URLA", "CESME", "FOCA", "MENDERES", "TORBALI",
        "BERGAMA", "ALIAGA", "MENEMEN", "TIRE", "ODEMIS", "BAYRAKLI", "KEMALPASA",
    ],
    "ANTALYA": ["MURATPASA", "KEPEZ", "KONYAALTI", "ALANYA", "MANAVGAT", "SERIK",
                "KEMER", "FINIKE", "DEMRE", "KAS", "KORKUTELI", "AKSEKI"],
    "KONYA": ["SELCUKLU", "MERAM", "KARATAY", "EREGLI", "AKSEHIR", "BEYSEHIR",
              "CIHANBEYLI", "EMIRGAZI", "KULU", "SARAYONU", "SEYDISEHIR"],
    "KAHRAMANMARAS": ["DULKADIROGLU", "ONIKISUBAT", "AFSIN", "ELBISTAN", "PAZARCIK",
                       "TURKOGLU", "GOKSUN", "ANDIRIN", "NURHAK", "EKINOZU", "CAGLAYANCERIT"],
    "TEKIRDAG": ["SULEYMANPASA", "CORLU", "CERKEZKOY", "KAPAKLI", "ERGENE", "MURATLI",
                  "MALKARA", "HAYRABOLU", "SARAY", "MARMARAEREGLI"],
}

# Generic: "X ILI <ILCE> BELEDIYE" pattern - tum 81 il icin calisir
ILCE_REGEX = re.compile(
    r"\bILI\s+([A-Z]+(?:\s+[A-Z]+)?)\s+(?:BELEDIYE|KAYMAKAM|ILCE)\b",
    re.UNICODE,
)


def ilce_bul(metin_norm: str, il: str | None) -> str | None:
    """Generic regex once, sonra odak il sozlugu fallback."""
    m = ILCE_REGEX.search(metin_norm)
    if m:
        cand = m.group(1).strip()
        if len(cand) >= 3 and cand not in ("BELEDIYE", "BUYUKSEHIR"):
            return cand.title()
    if il:
        il_norm_key = unicodedata.normalize("NFKD", il)
        il_norm_key = "".join(c for c in il_norm_key if not unicodedata.combining(c))
        il_norm_key = il_norm_key.replace("İ","I").replace("ı","i").upper()
        ilceler = ODAK_IL_ILCELERI.get(il_norm_key, [])
        for ilce in ilceler:
            if re.search(rf"\b{ilce}\b", metin_norm):
                return ilce.title()
    return None


def kategori_belirle(baslik_norm: str, kurum_norm: str, full_norm: str) -> list[str]:
    hits = []
    blob = " ".join([baslik_norm, kurum_norm, full_norm[:1500]])
    for kat, kws in KATEGORI_KEYWORDS.items():
        if any(kw in blob for kw in kws):
            hits.append(kat)
    return hits


def islem_tipi(action_verb: str, baslik_norm: str, kurum_norm: str) -> str:
    """Action verb birinci kaynak, kurum/baslik destek."""
    blob = " ".join([baslik_norm, kurum_norm])
    for tip, pat in ISLEM_ALT_TIP:
        if pat.search(blob):
            return tip
    return ACTION_VERB_TO_TIP.get(action_verb, "diger")


# ----- ana islem -------------------------------------------------------------

def pdf_isle(pdf_path: Path) -> list[dict]:
    try:
        pdf = pypdf.PdfReader(open(pdf_path, "rb"))
    except Exception as e:
        print(f"  Hata: {pdf_path.name} - {e}")
        return []

    try:
        aralik = ihale_sayfa_araligi(pdf)
    except Exception as e:
        print(f"  PDF okuma hatasi: {pdf_path.name} - {e}")
        return []
    if aralik is None:
        return []
    bas, son = aralik

    sayfa_metinleri: list[str] = []
    for i in range(bas, son):
        try:
            t = pdf.pages[i].extract_text() or ""
        except Exception:
            t = ""
        sayfa_metinleri.append(t)
    full_text = "\n".join(sayfa_metinleri)

    # Tarih bilgisini dosya adindan al
    tarih_str = pdf_path.stem.split("-")[0]  # 20260520 veya 20260520-1
    if len(tarih_str) == 8:
        yayin_tarihi = f"{tarih_str[:4]}-{tarih_str[4:6]}-{tarih_str[6:]}"
    else:
        yayin_tarihi = None

    full_norm = norm(full_text)

    # Action verb pozisyonlari - olasi ihale baslik sonlari
    verb_matches = list(ACTION_VERB_REGEX.finditer(full_norm))
    if not verb_matches:
        return []

    # Gercek ihale baslangici filtresi:
    # action verb'ten SONRAKI 250 karakterde mutlaka bir KURUM ifadesi
    # ("...NDAN:" gibi) olmali. Yoksa bu govde icinde gecen bir kelimedir.

    kayitlar: list[dict] = []
    used_positions: list[int] = []
    for vm in verb_matches:
        verb_end = vm.end()
        sonraki = full_norm[verb_end: verb_end + 350]
        kurum_m = KURUM_REGEX.search(sonraki)
        if not kurum_m:
            continue  # govde icinde gecen action verb, atla

        # Onceki gercek ihale baslangicindan en az 200 karakter ileride miyiz?
        if used_positions and verb_end - used_positions[-1] < 200:
            continue

        # Baslik: action verb'ten geriye dogru, onceki kurum ifadesinin
        # SONUNDAN veya onceki action verb sonundan veya cok geriye gitmemek
        # icin max 500 karaktere kadar.
        bas_pos = max(0, verb_end - 500)
        if used_positions:
            bas_pos = max(bas_pos, used_positions[-1])
        # Onceki kurum sonundan basla
        onceki_kurum = list(KURUM_REGEX.finditer(full_norm[bas_pos: verb_end]))
        if onceki_kurum:
            bas_pos = bas_pos + onceki_kurum[-1].end()
        baslik = re.sub(r"\s+", " ", full_norm[bas_pos: verb_end]).strip()
        if len(baslik) > 250:
            baslik = baslik[-250:]

        kurum = re.sub(r"\s+", " ", kurum_m.group(1)).strip()
        # Detay blok: verb_end'ten +1500 karakter (kategori + il aramasi icin)
        detay_blok = full_norm[max(0, verb_end - 100): verb_end + 1200]

        il = il_bul(kurum) or il_bul(detay_blok)
        ilce = ilce_bul(kurum, il) or ilce_bul(detay_blok, il)
        kategoriler = kategori_belirle(baslik, kurum, detay_blok)
        tip = islem_tipi(vm.group(0), baslik, kurum)

        kayitlar.append({
            "id": f"{pdf_path.stem}_{len(kayitlar):03d}",
            "kaynak_pdf": pdf_path.name,
            "yayin_tarihi": yayin_tarihi,
            "baslik": baslik,
            "kurum": kurum,
            "il": il,
            "ilce": ilce,
            "islem_tipi": tip,
            "kategoriler": kategoriler,
            "action_verb": vm.group(0),
        })
        used_positions.append(verb_end)
    return kayitlar


def main():
    pdf_files = sorted(RAW_DIR.glob("*.pdf"))
    print(f"{len(pdf_files)} PDF taranacak. RAW_DIR={RAW_DIR}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    toplam = 0
    pdf_bazli_sayilar: dict[str, int] = {}
    with OUT_FILE.open("w", encoding="utf-8") as out:
        for pdf_path in pdf_files:
            kayitlar = pdf_isle(pdf_path)
            for k in kayitlar:
                out.write(json.dumps(k, ensure_ascii=False) + "\n")
            n = len(kayitlar)
            toplam += n
            pdf_bazli_sayilar[pdf_path.name] = n
            print(f"  {pdf_path.name:25s} ihale={n}")

    # ozet
    ozet = {
        "veri_penceresi": "son 30 gun (2026-04-21..2026-05-20)",
        "toplam_pdf": len(pdf_files),
        "toplam_ihale": toplam,
        "pdf_bazli_ihale_sayilari": pdf_bazli_sayilar,
    }
    SUMMARY_FILE.write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nToplam ihale kaydi: {toplam}")
    print(f"Yazildi: {OUT_FILE}")
    print(f"Ozet: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
