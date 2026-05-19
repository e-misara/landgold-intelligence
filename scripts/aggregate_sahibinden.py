#!/usr/bin/env python3
"""
Sahibinden 97K ham veriden Tradia için ilçe-seviye aggregate JSON üretir.

Girdi : ~/Desktop/Sahibinden_Proje/turkiye_tum_veriler.csv
Çıktı : ~/landgold-agents/data/site/ilce_aggregate.json
         + ~/landgold-agents/docs/data/ilce_aggregate.json (Tradia sitesi için)

ÖNEMLİ: Aggregate only — hiçbir ilan başlığı veya kimliği gösterilmez.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# ── Yapılandırma ───────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
CSV_PATH  = Path.home() / "Desktop" / "Sahibinden_Proje" / "turkiye_tum_veriler.csv"
OUT_DATA  = ROOT / "data" / "site" / "ilce_aggregate.json"
OUT_DOCS  = ROOT / "docs" / "data" / "ilce_aggregate.json"

# Aykırı değer eşikleri
M2_MIN, M2_MAX = 20, 1000
PRICE_PCT = (1, 99)  # p1-p99 dışı filtrele

# Türkçe ay → ay numarası
TR_AYLAR = {
    "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6,
    "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12,
}
DATE_RX = re.compile(r"^(\d{1,2})\s+([A-Za-zÇĞİıÖŞÜçğıöşü]+)\s+(\d{4})$")


def parse_tr_date(s):
    if not isinstance(s, str):
        return pd.NaT
    m = DATE_RX.match(s.strip())
    if not m:
        return pd.NaT
    day, ay_str, year = m.groups()
    ay = TR_AYLAR.get(ay_str)
    if not ay:
        return pd.NaT
    try:
        return datetime(int(year), ay, int(day))
    except ValueError:
        return pd.NaT


def split_il_ilce(il_field):
    """'Istanbul-Tuzla' → ('Istanbul', 'Tuzla')"""
    if not isinstance(il_field, str) or "-" not in il_field:
        return (il_field, None)
    parts = il_field.split("-", 1)
    return (parts[0].strip(), parts[1].strip())


def safe_mean(s):
    s = s.dropna()
    return round(float(s.mean()), 1) if len(s) else None


def safe_median(s):
    s = s.dropna()
    return round(float(s.median()), 0) if len(s) else None


def percentile(s, q):
    s = s.dropna()
    if not len(s):
        return None
    return round(float(s.quantile(q / 100.0)), 0)


# ── Ana akış ───────────────────────────────────────────────────────────────────
def main():
    print(f"📖 CSV yükleniyor: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"   {len(df):,} satır, {df['il'].nunique()} unik il-ilçe")

    # İl/ilçe ayrıştır
    df[["il_clean", "ilce"]] = df["il"].apply(lambda x: pd.Series(split_il_ilce(x)))

    # Tarih
    df["tarih_dt"] = df["tarih"].apply(parse_tr_date)
    son_tarih = df["tarih_dt"].max()
    print(f"   En taze ilan: {son_tarih.date()}")
    cutoff_30 = son_tarih - timedelta(days=30)
    cutoff_60 = son_tarih - timedelta(days=60)

    # Aykırı değer temizleme
    before = len(df)
    df = df[df["m2"].isna() | ((df["m2"] >= M2_MIN) & (df["m2"] <= M2_MAX))]
    # Fiyat outlier — kategori bazında p1-p99
    keep_mask = pd.Series(False, index=df.index)
    for cat in df["kategori"].unique():
        sub = df[df["kategori"] == cat]["fiyat"].dropna()
        if not len(sub):
            continue
        lo, hi = sub.quantile(PRICE_PCT[0] / 100), sub.quantile(PRICE_PCT[1] / 100)
        cat_mask = (df["kategori"] == cat) & df["fiyat"].between(lo, hi)
        keep_mask |= cat_mask
    df = df[keep_mask | df["fiyat"].isna()]
    print(f"   Aykırı temizlik: {before:,} → {len(df):,} satır")

    # m² fiyatı türetilmiş kolon
    df["m2_fiyat"] = df["fiyat"] / df["m2"]
    df.loc[df["m2"].isna() | df["fiyat"].isna(), "m2_fiyat"] = pd.NA

    # ── İlçe bazında aggregate ────────────────────────────────────────────────
    sonuc = []
    katlar = ["daire satılık", "residans satılık", "villa satılık",
              "ticari satılık", "işyeri kiralık", "konut kiralık"]

    for (il, ilce), g in df.groupby(["il_clean", "ilce"]):
        if ilce is None:
            continue

        # Mülk tipi dağılımı
        kat_say = g["kategori"].value_counts().to_dict()
        total = int(g.shape[0])
        mulk_dag = []
        for k in katlar:
            n = int(kat_say.get(k, 0))
            mulk_dag.append({"tip": k, "sayi": n, "yuzde": round(n / total * 100, 1)})

        daire = g[g["kategori"] == "daire satılık"]
        ticari = g[g["kategori"] == "ticari satılık"]
        isyeri = g[g["kategori"] == "işyeri kiralık"]

        # Son 30/60 gün
        last_30 = int((g["tarih_dt"] >= cutoff_30).sum())
        prev_30 = int(((g["tarih_dt"] >= cutoff_60) & (g["tarih_dt"] < cutoff_30)).sum())
        if prev_30 > 0:
            degisim = round((last_30 - prev_30) / prev_30 * 100, 1)
        else:
            degisim = None

        # Son 30 gün haftalık dağılım (4 nokta sparkline için)
        hafta_dagilim = []
        for w in range(4, 0, -1):
            w_start = son_tarih - timedelta(days=w * 7)
            w_end = son_tarih - timedelta(days=(w - 1) * 7)
            n = int(((g["tarih_dt"] >= w_start) & (g["tarih_dt"] < w_end)).sum())
            hafta_dagilim.append(n)

        # Oda tipi (sadece daire satılık)
        oda_counts = Counter(daire["oda"].dropna())
        en_yogun_oda = oda_counts.most_common(1)[0][0] if oda_counts else None
        oda_dagilim = [{"oda": o, "sayi": int(n)}
                       for o, n in oda_counts.most_common(6)]

        kayit = {
            "il": il,
            "ilce": ilce,
            "toplam_ilan": total,
            "mulk_tipi_dagilim": mulk_dag,
            "ortalama_m2_fiyat_daire_satilik": safe_mean(daire["m2_fiyat"]),
            "medyan_fiyat_daire_satilik": safe_median(daire["fiyat"]),
            "ortalama_m2_buyukluk_daire": safe_mean(daire["m2"]),
            "ortalama_m2_fiyat_ticari_satilik": safe_mean(ticari["m2_fiyat"]),
            "ortalama_kira_isyeri": safe_mean(isyeri["m2_fiyat"]),
            "fiyat_araligi_daire": {
                "min":  percentile(daire["fiyat"], 1),
                "p25":  percentile(daire["fiyat"], 25),
                "p50":  percentile(daire["fiyat"], 50),
                "p75":  percentile(daire["fiyat"], 75),
                "max":  percentile(daire["fiyat"], 99),
            },
            "son_30_gun_ilan_sayisi": last_30,
            "son_30_gun_yuzde_degisim": degisim,
            "haftalik_trend_4hafta": hafta_dagilim,
            "en_yogun_oda_tipi": en_yogun_oda,
            "oda_dagilim_top6": oda_dagilim,
        }
        sonuc.append(kayit)

    # Meta + sırala
    sonuc.sort(key=lambda r: (r["il"], -r["toplam_ilan"]))
    meta = {
        "kaynak": "sahibinden.com (web scraping, aggregate only)",
        "son_guncelleme": datetime.now().strftime("%Y-%m-%d"),
        "kapsanan_ilce_sayisi": len(sonuc),
        "toplam_ilan": int(len(df)),
        "veri_dilimi": {
            "en_eski_ilan": str(df["tarih_dt"].min().date()) if df["tarih_dt"].notna().any() else None,
            "en_taze_ilan": str(son_tarih.date()),
        },
        "metodoloji": (
            "İlçe bazında özet metrikler. m² < 20 veya m² > 1000 filtrelendi. "
            "Kategori bazında p1-p99 aykırı temizliği uygulandı. Hiçbir ilan "
            "başlığı/kimliği saklanmaz, sadece toplulaştırılmış istatistikler."
        ),
    }

    payload = {"meta": meta, "ilceler": sonuc}

    # Yaz
    OUT_DATA.parent.mkdir(parents=True, exist_ok=True)
    OUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    OUT_DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_DOCS.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")  # minified
    print(f"\n✓ Yazıldı:")
    print(f"  {OUT_DATA}  ({OUT_DATA.stat().st_size:,} byte)")
    print(f"  {OUT_DOCS}  ({OUT_DOCS.stat().st_size:,} byte, minified)")
    print(f"\n📊 Özet:")
    print(f"  İlçe sayısı : {len(sonuc)}")
    print(f"  Toplam ilan : {len(df):,}")
    iller = Counter(r["il"] for r in sonuc)
    for il, n in iller.most_common():
        print(f"  {il:20s}  {n} ilçe")


if __name__ == "__main__":
    main()
