"""
Tradia NewsClassifier — 5 entegrasyon test kaseti.
Her test Haiku 4.5'a gerçek API çağrısı yapar (~$0.01 toplam).

Çalıştırma:
    python tests/test_news_classifier.py
    python -m pytest tests/test_news_classifier.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.news_classifier import NewsClassifier

# Token sayacı (maliyet tahmini için)
_total_input_tokens = 0
_total_output_tokens = 0

# Haiku 4.5 fiyatlandırma (per 1M token)
HAIKU_INPUT_PRICE  = 0.80   # $0.80
HAIKU_OUTPUT_PRICE = 4.00   # $4.00


def _run_test(name: str, haber: dict, checks: list[tuple]) -> bool:
    """Tek test kaseti çalıştırır. Başarı/başarısızlık döner."""
    global _total_input_tokens, _total_output_tokens

    print(f"\n{'─'*60}")
    print(f"TEST: {name}")
    print(f"  Başlık: {haber['baslik'][:60]}")

    clf = NewsClassifier()
    try:
        result = clf.classify_news(haber)
    except Exception as exc:
        print(f"  ❌ API/parse hatası: {exc}")
        return False

    # Token sayacı güncelle
    _total_input_tokens  += result.get("_input_tokens", 0)
    _total_output_tokens += result.get("_output_tokens", 0)

    print(f"  Gerçek JSON çıktısı:")
    import json
    display = {k: v for k, v in result.items() if not k.startswith("_")}
    for k, v in display.items():
        print(f"    {k}: {v!r}")

    # Kontroller
    failures = []
    for check_desc, check_fn in checks:
        try:
            ok = check_fn(result)
        except Exception as e:
            ok = False
            check_desc = f"{check_desc} [hata: {e}]"
        status = "✅" if ok else "❌"
        print(f"  {status} {check_desc}")
        if not ok:
            failures.append(check_desc)

    if failures:
        print(f"  SONUÇ: FAIL ({len(failures)} kontrol başarısız)")
        return False
    print(f"  SONUÇ: PASS")
    return True


def test_1_imar_degisikligi() -> bool:
    haber = {
        "baslik": "Lapseki Cumhuriyet Mahallesi Emsal Değişikliği Onaylandı",
        "kaynak": "Çanakkale Belediye Meclis Kararları",
        "tarih":  "2026-05-03",
        "metin":  (
            "Çanakkale Belediye Meclisi 2026 Mayıs olağan toplantısında "
            "Lapseki Cumhuriyet Mahallesi 1842 ada 5 parselde emsal "
            "1.20'den 1.50'ye yükseltilmesini onayladı."
        ),
    }
    checks = [
        ("il == 'Çanakkale'",            lambda r: r.get("il") == "Çanakkale"),
        ("ilce == 'Lapseki'",            lambda r: r.get("ilce") == "Lapseki"),
        ("kategori == 'imar-degisikligi'", lambda r: r.get("kategori") == "imar-degisikligi"),
        ("alt_kategori == 'yogunluk-artisi'", lambda r: r.get("alt_kategori") == "yogunluk-artisi"),
        ("agirlik_puani >= 4",            lambda r: float(r.get("agirlik_puani", 0)) >= 4),
        ("agirlik_puani <= 7",            lambda r: float(r.get("agirlik_puani", 0)) <= 7),
        ("guvenilirlik == 'resmi'",       lambda r: r.get("guvenilirlik") == "resmi"),
    ]
    return _run_test("Test 1 — İmar Değişikliği", haber, checks)


def test_2_mega_proje() -> bool:
    haber = {
        "baslik": "M11 Gayrettepe-Havalimanı Metrosu Resmi Açılış",
        "kaynak": "Anadolu Ajansı",
        "tarih":  "2024-01-22",
        "metin":  (
            "İstanbul'un en büyük metro hattı M11 bugün resmi olarak "
            "açıldı. 37 km uzunluğunda Gayrettepe'den İstanbul Havalimanı'na "
            "uzanıyor. Beklenen günlük yolcu 250.000."
        ),
    }
    checks = [
        ("il == 'İstanbul'",                      lambda r: r.get("il") == "İstanbul"),
        ("kategori == 'ulasim-iyilestirme'",       lambda r: r.get("kategori") == "ulasim-iyilestirme"),
        ("alt_kategori == 'acilis'",               lambda r: r.get("alt_kategori") == "acilis"),
        ("etki_buyuklugu in [buyuk, cot-buyuk]",   lambda r: r.get("etki_buyuklugu") in ("buyuk", "cok-buyuk")),
        ("agirlik_puani >= 8",                     lambda r: float(r.get("agirlik_puani", 0)) >= 8),
        ("guvenilirlik in [resmi, yari-resmi]",    lambda r: r.get("guvenilirlik") in ("resmi", "yari-resmi")),
    ]
    return _run_test("Test 2 — Mega Proje / Ulaşım", haber, checks)


def test_3_yargi_karari() -> bool:
    haber = {
        "baslik": "Danıştay Maslak 1453 Projesinin İmar Planını İptal Etti",
        "kaynak": "Hürriyet",
        "tarih":  "2025-09-15",
        "metin":  (
            "Danıştay 6. Dairesi, İstanbul Sarıyer Maslak'taki 1453 "
            "konut projesinin imar planını iptal etti."
        ),
    }
    checks = [
        ("il == 'İstanbul'",             lambda r: r.get("il") == "İstanbul"),
        ("ilce == 'Sarıyer'",            lambda r: r.get("ilce") == "Sarıyer"),
        ("kategori == 'yargi-karari'",   lambda r: r.get("kategori") == "yargi-karari"),
        ("alt_kategori == 'imar-plan-iptali'", lambda r: r.get("alt_kategori") == "imar-plan-iptali"),
        ("etki_tipi negatif",            lambda r: r.get("etki_tipi") in ("negatif-talep", "negatif-arz-arttirici")),
        ("agirlik_puani >= 6",           lambda r: float(r.get("agirlik_puani", 0)) >= 6),
    ]
    return _run_test("Test 3 — Yargı Kararı (Negatif)", haber, checks)


def test_4_belirsiz() -> bool:
    haber = {
        "baslik": "Galatasaray Trabzonspor Maçı 2-1 Bitti",
        "kaynak": "NTV Spor",
        "tarih":  "2026-05-03",
        "metin":  (
            "Süper Lig'in 35. haftasında Galatasaray sahasında "
            "Trabzonspor'u 2-1 yendi."
        ),
    }
    checks = [
        ("kategori == 'BELIRSIZ'",  lambda r: r.get("kategori") == "BELIRSIZ"),
        ("il is null",              lambda r: r.get("il") is None),
        ("ilce is null",            lambda r: r.get("ilce") is None),
    ]
    return _run_test("Test 4 — BELİRSİZ (Spor Haberi)", haber, checks)


def test_5_sanayi_yatirim() -> bool:
    haber = {
        "baslik": "Ford Otosan Yeniköy Fabrikasına Yeni Hat",
        "kaynak": "KAP - Şirket Açıklaması",
        "tarih":  "2026-04-12",
        "metin":  (
            "Ford Otosan, Kocaeli Yeniköy fabrikasında elektrikli "
            "ticari araç üretimi için yeni hat kuracağını açıkladı. "
            "Yatırım 2 milyar Euro, 2.000 yeni istihdam."
        ),
    }
    checks = [
        ("il == 'Kocaeli'",                        lambda r: r.get("il") == "Kocaeli"),
        ("kategori == 'sanayi-yatirim'",           lambda r: r.get("kategori") == "sanayi-yatirim"),
        ("etki_buyuklugu in [buyuk, cot-buyuk]",   lambda r: r.get("etki_buyuklugu") in ("buyuk", "cok-buyuk")),
        ("agirlik_puani >= 7",                     lambda r: float(r.get("agirlik_puani", 0)) >= 7),
    ]
    return _run_test("Test 5 — Sanayi Yatırım", haber, checks)


# ── Runner ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("TRADIA NewsClassifier — Entegrasyon Testleri")
    print(f"Model: claude-haiku-4-5-20251001")
    print("=" * 60)

    tests = [
        test_1_imar_degisikligi,
        test_2_mega_proje,
        test_3_yargi_karari,
        test_4_belirsiz,
        test_5_sanayi_yatirim,
    ]

    results = []
    for fn in tests:
        try:
            passed = fn()
        except Exception as exc:
            print(f"  ❌ Test çalıştırma hatası: {exc}")
            passed = False
        results.append(passed)

    # Maliyet tahmini
    cost_input  = (_total_input_tokens  / 1_000_000) * 0.80
    cost_output = (_total_output_tokens / 1_000_000) * 4.00
    total_cost  = cost_input + cost_output

    passed_count = sum(results)
    total_count  = len(results)

    print(f"\n{'=' * 60}")
    print(f"ÖZET: {passed_count}/{total_count} PASS")
    print(f"Token kullanımı: {_total_input_tokens} input + {_total_output_tokens} output")
    print(f"Tahmini API maliyeti: ${total_cost:.4f}")
    print("=" * 60)

    sys.exit(0 if passed_count == total_count else 1)


# ── pytest uyumu ───────────────────────────────────────────────────────────

def test_imar_degisikligi():
    assert test_1_imar_degisikligi()

def test_mega_proje():
    assert test_2_mega_proje()

def test_yargi_karari():
    assert test_3_yargi_karari()

def test_belirsiz():
    assert test_4_belirsiz()

def test_sanayi_yatirim():
    assert test_5_sanayi_yatirim()


if __name__ == "__main__":
    main()
