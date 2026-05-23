#!/usr/bin/env python3
"""
MEGA_PROJELER (site içi, zengin metin) + mega_projects_map.json (slug, kategori)
verilerini birleştirip site için JS const üretir.

Çıktı: /tmp/mega_inject.js
  - MEGA_GORSEL_HARITASI: { slug: { thumb, full, count } }
  - MEGA_KATEGORI_GRUP   : { detayli_kat: ana_grup }
  - MEGA_SLUG_TO_ID      : { slug: site_id }  (eşleşen 7 proje için)
  - YENI_MEGA_PROJELER   : 5 yeni proje (id 26-30, placeholder metin)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GORSEL_RAPOR = ROOT / "data/site/gorsel_optimize_rapor.json"
MAP_JSON = Path.home() / "Desktop/tradia_gorsel_arsiv/mega_projects_map.json"

# Slug → mevcut site MEGA_PROJELER id eşleşmesi (manuel mapping)
SLUG_TO_ID = {
    "kanal_istanbul":         1,
    "istanbul_havalimani":    2,
    "canakkale_koprusu_1915": 3,
    # Halkalı-Kapıkule YHT (site id:4) → slug map'te yok
    "akkuyu_nukleer":         5,
    "yss_kopru_kuzey_marmara": 6,   # Kuzey Marmara Otoyolu
    # BTK (site id:7) → map'te yok
    "marmaray":               8,
    # Mersin Liman (id:9) → map'te yok ama site verisinde var
    "tanap":                  10,
    # Çandarlı (id:11) → map'te yok
    "gap":                    12,
    "osmangazi_koprusu":      13,
    # STAR (id:14) → map'te yok
    "galataport":             15,
    # id:16-25 — map'teki diğer projeler kontrol edilecek
}

# Detaylı kategori → 6 ana grup mapping
KAT_GRUP = {
    "kopru":              "Ulaşım",
    "kopru_otoyol":       "Ulaşım",
    "otoyol":             "Ulaşım",
    "tunel":              "Ulaşım",
    "demir_yolu":         "Ulaşım",
    "demir_yolu_yht":     "Ulaşım",
    "metro":              "Ulaşım",
    "havalimani":         "Ulaşım",
    "su_yolu":            "Su",
    "enerji_baraj":       "Su",
    "enerji_nukleer":     "Enerji",
    "enerji_dogalgaz":    "Enerji",
    "enerji_boru_hatti":  "Enerji",
    "saglik_sehir_hastanesi": "Sağlık",
    "kultur_yapi":        "Kentsel",
    "din_yapi":           "Kentsel",
    "haberlesme_yapi":    "Kentsel",
    "liman":              "Lojistik",
    "liman_kentsel_donusum": "Lojistik",
    "kalkinma_bolgesel":  "Lojistik",
}

YENI_PROJE_TEMPLATE = {
    "ad":        "",
    "slug":      "",
    "kategori":  "",
    "ana_grup":  "",
    "il":        "",
    "lon":       0,
    "lat":       0,
    "durum":     "",
    "yatirim":   "Detay yakında",
    "isi":       7.5,
    "ilceler":   [],
    "aciklama":  "Tradia tarafından zenginleştiriliyor. Detay metni yakında.",
    "etki":      "Detay analiz hazırlanıyor",
    "fiyat":     [],
    "verdict":   "Yakında — Tradia veriyi tamamlıyor",
    "renk":      "#6B7280",
    "placeholder": True,
}


def main():
    gorsel_rap = json.loads(GORSEL_RAPOR.read_text(encoding="utf-8"))
    mega_map = json.loads(MAP_JSON.read_text(encoding="utf-8"))

    # 1) MEGA_GORSEL_HARITASI
    gorsel_haritasi = {}
    for slug, kayitlar in gorsel_rap["projeler"].items():
        gorsel_haritasi[slug] = {
            "count": len(kayitlar),
            "thumb": kayitlar[0]["thumb"],
            "full":  kayitlar[0]["full"],
            "tum_gorseller": [{"thumb": k["thumb"], "full": k["full"]} for k in kayitlar],
        }
    # Genel kolaj + sağlık
    gorsel_haritasi["_kolaj"] = {"thumb": "images/mega/_genel/kolaj-thumb.webp", "full": "images/mega/_genel/kolaj-full.webp"}
    gorsel_haritasi["_saglik_kapak"] = {"thumb": "images/mega/_genel/saglik-thumb.webp", "full": "images/mega/_genel/saglik-full.webp"}

    # 2) Görsel yok ama mega_projects_map'te olan projeler için ana_grup tablosu
    ek_projeler = []
    next_id = 26
    eklenecek_slug = ["avrasya_tuneli", "cam_sakura_hastanesi", "filyos_limani", "karadeniz_gazi", "yusufeli_baraji"]
    site_ad_haritasi = {
        "avrasya_tuneli": {"ad": "Avrasya Tüneli", "il": "İstanbul", "lon": 29.02, "lat": 41.00, "renk": "#3B82F6"},
        "cam_sakura_hastanesi": {"ad": "Çam-Sakura Şehir Hastanesi", "il": "İstanbul", "lon": 29.11, "lat": 41.05, "renk": "#10B981"},
        "filyos_limani": {"ad": "Filyos Limanı", "il": "Zonguldak", "lon": 32.04, "lat": 41.57, "renk": "#06B6D4"},
        "karadeniz_gazi": {"ad": "Sakarya Karadeniz Doğal Gazı", "il": "Zonguldak", "lon": 32.10, "lat": 41.80, "renk": "#F59E0B"},
        "yusufeli_baraji": {"ad": "Yusufeli Barajı", "il": "Artvin", "lon": 41.62, "lat": 40.83, "renk": "#06B6D4"},
    }
    for slug in eklenecek_slug:
        m = mega_map.get(slug, {})
        meta = site_ad_haritasi.get(slug, {})
        kat = m.get("kategori", "")
        ek_projeler.append({
            "id": next_id,
            "ad": meta.get("ad", m.get("ad", slug)),
            "slug": slug,
            "kategori": "ulaşım" if KAT_GRUP.get(kat) == "Ulaşım" else "enerji" if "enerji" in kat or kat == "enerji_baraj" else "sanayi",
            "ana_grup": KAT_GRUP.get(kat, "Diğer"),
            "il": meta.get("il", ""),
            "lon": meta.get("lon", 0),
            "lat": meta.get("lat", 0),
            "durum": m.get("durum", "tamamlandı"),
            "yatirim": "Detay yakında",
            "isi": 7.5,
            "ilceler": [],
            "aciklama": "Tradia tarafından zenginleştiriliyor — projenin detaylı analizi yakında.",
            "etki": "Etki analizi hazırlanıyor",
            "fiyat": [],
            "verdict": "Yakında",
            "renk": meta.get("renk", "#6B7280"),
            "placeholder": True,
        })
        next_id += 1

    # 3) SLUG_TO_ID + ANA_GRUP_HARITASI: tüm slugların ana grubunu üret
    ana_grup_haritasi = {}
    for slug, m in mega_map.items():
        if slug == "_meta":
            continue
        kat = m.get("kategori", "")
        ana_grup_haritasi[slug] = KAT_GRUP.get(kat, "Diğer")

    # Mevcut site MEGA_PROJELER'in id:1-25'i için slug eşleşmesi yoksa
    # id → slug mapping de yapalım (manual): site id'ye slug ekle
    ID_TO_SLUG_AD_HARITASI = {
        # Slug, ana_grup
        1:  ("kanal_istanbul",         "Su"),
        2:  ("istanbul_havalimani",    "Ulaşım"),
        3:  ("canakkale_koprusu_1915", "Ulaşım"),
        4:  ("halkali_kapikule_yht",   "Ulaşım"),     # slug yok ama uydur
        5:  ("akkuyu_nukleer",         "Enerji"),
        6:  ("yss_kopru_kuzey_marmara", "Ulaşım"),
        7:  ("btk_demiryolu",          "Ulaşım"),
        8:  ("marmaray",               "Ulaşım"),
        9:  ("mersin_limani",          "Lojistik"),
        10: ("tanap",                  "Enerji"),
        11: ("candarli_limani",        "Lojistik"),
        12: ("gap",                    "Su"),
        13: ("osmangazi_koprusu",      "Ulaşım"),
        14: ("star_rafinerisi",        "Lojistik"),
        15: ("galataport",             "Kentsel"),
        16: ("filyos_petrokimya",      "Lojistik"),
        17: ("kapadokya_premium",      "Kentsel"),
        18: ("istanbul_finans_merkezi", "Kentsel"),
        19: ("3_koprusu",              "Ulaşım"),
        20: ("bursa_kentsel_donusum",  "Kentsel"),
        21: ("kapadokya_butik_turizm", "Kentsel"),
        22: ("trabzon_sehir_hastanesi", "Sağlık"),
        23: ("manisa_elektronik_osb",  "Lojistik"),
        24: ("gaziantep_sanayi",       "Lojistik"),
        25: ("mugla_luks_kiyi",        "Kentsel"),
    }

    # JS const üret
    out_lines = []
    out_lines.append("/* === Mega Proje Görsel + Eşleşme + Yeni 5 Proje === */")
    out_lines.append("")
    out_lines.append("const MEGA_GORSEL = " + json.dumps(gorsel_haritasi, ensure_ascii=False, separators=(',', ':')) + ";")
    out_lines.append("")
    out_lines.append("const MEGA_ID_META = " + json.dumps(
        {str(k): {"slug": v[0], "grup": v[1]} for k, v in ID_TO_SLUG_AD_HARITASI.items()},
        ensure_ascii=False, separators=(',', ':')
    ) + ";")
    out_lines.append("")
    out_lines.append("const MEGA_GRUP_RENK = {")
    out_lines.append('  "Ulaşım":  "#3B82F6",')
    out_lines.append('  "Enerji":  "#D97706",')
    out_lines.append('  "Su":      "#06B6D4",')
    out_lines.append('  "Sağlık":  "#2D7A3E",')
    out_lines.append('  "Kentsel": "#DC2626",')
    out_lines.append('  "Lojistik":"#8B5CF6",')
    out_lines.append('  "Diğer":   "#6B7280",')
    out_lines.append("};")
    out_lines.append("")
    out_lines.append("const MEGA_GRUP_IKON = {")
    out_lines.append('  "Ulaşım":  "🛣️",')
    out_lines.append('  "Enerji":  "⚡",')
    out_lines.append('  "Su":      "💧",')
    out_lines.append('  "Sağlık":  "🏥",')
    out_lines.append('  "Kentsel": "🏙️",')
    out_lines.append('  "Lojistik":"⚓",')
    out_lines.append('  "Diğer":   "◈",')
    out_lines.append("};")
    out_lines.append("")
    out_lines.append("/* 5 yeni proje (görsel-zengin, metin placeholder) */")
    out_lines.append("const MEGA_EK_PROJELER = [")
    for ek in ek_projeler:
        out_lines.append("  " + json.dumps(ek, ensure_ascii=False))
        if ek != ek_projeler[-1]:
            out_lines[-1] += ","
    out_lines.append("];")

    out_path = Path("/tmp/mega_inject.js")
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"→ {out_path}  ({out_path.stat().st_size} byte)")
    print(f"  Görsel proje: {len(gorsel_haritasi)} ({sum(1 for k in gorsel_haritasi if not k.startswith('_'))} mega + {sum(1 for k in gorsel_haritasi if k.startswith('_'))} genel)")
    print(f"  ID meta: {len(ID_TO_SLUG_AD_HARITASI)}")
    print(f"  Yeni proje: {len(ek_projeler)}")


if __name__ == "__main__":
    main()
