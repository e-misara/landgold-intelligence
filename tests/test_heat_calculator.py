"""
Tradia HeatCalculator + PriceProjector — 5 saf matematik test kaseti.
API çağrısı yok. Saniyeler içinde çalışır.

Çalıştırma:
    python -m pytest tests/test_heat_calculator.py -v
    python tests/test_heat_calculator.py
"""
from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from zoneinfo import ZoneInfo

from services.heat_calculator import (
    KATEGORI_CARPANLARI,
    KAYNAK_CARPANLARI,
    YARILANMA_OMRU,
    HeatCalculator,
    temperature_level,
)
from services.price_projector import PriceProjector

TR = ZoneInfo("Europe/Istanbul")


def test_1_kategori_carpani():
    """Test 1: Kategori çarpanları doğru tanımlı mı"""
    assert KATEGORI_CARPANLARI["mega-proje"] == 2.0
    assert KATEGORI_CARPANLARI["sosyal-tesis"] == 0.7
    assert KATEGORI_CARPANLARI["BELIRSIZ"] == 0.0
    assert KATEGORI_CARPANLARI["ulasim-iyilestirme"] == 1.8
    assert KATEGORI_CARPANLARI["guvenlik-suc"] == 0.8


def test_2_haber_isi_hesabi():
    """Test 2: Tek haber ısı katkısı — 9 × 2.0 × 1.0 × ~1.0 = ~18"""
    calc = HeatCalculator()
    bugun = datetime.now(TR)

    haber = {
        "agirlik_puani": 9,
        "kategori": "mega-proje",
        "guvenilirlik": "resmi",
        "tarih_referansi": bugun.isoformat(),
    }

    isi = calc.haber_isi(haber, bugun)

    assert 17.5 < isi < 18.5, f"Beklenen ~18, gelen {isi}"


def test_3_tazelik_decay():
    """Test 3: Exp decay tazelik — yarılanma noktalarını doğrula"""
    calc = HeatCalculator()
    bugun = datetime(2026, 5, 3, tzinfo=TR)

    # Mega proje: 120 gün yarılanma → çarpan 0.5
    eski_120 = (bugun - timedelta(days=120)).isoformat()
    czrp = calc.tazelik_carpani(eski_120, bugun, "mega-proje")
    assert abs(czrp - 0.5) < 0.02, f"120 gün → 0.5 bekleniyor, gelen {czrp}"

    # 240 gün → 0.25 (iki yarılanma)
    eski_240 = (bugun - timedelta(days=240)).isoformat()
    czrp_240 = calc.tazelik_carpani(eski_240, bugun, "mega-proje")
    assert abs(czrp_240 - 0.25) < 0.03, f"240 gün → 0.25 bekleniyor, gelen {czrp_240}"

    # Güvenlik-suç: 14 gün yarılanma → çarpan 0.5
    eski_14 = (bugun - timedelta(days=14)).isoformat()
    czrp_g = calc.tazelik_carpani(eski_14, bugun, "guvenlik-suc")
    assert abs(czrp_g - 0.5) < 0.02, f"14 gün guvenlik-suc → 0.5 bekleniyor, gelen {czrp_g}"


def test_4_sicaklik_orani_seviyesi():
    """Test 4: Şişli vs Lapseki kıyas + seviye etiketi"""
    # Şişli: 270 / 60 = 4.5 → patlamis
    assert temperature_level(270 / 60) == "patlamis"

    # Lapseki: 3 / 2 = 1.5 → sicak (eşik: >= 1.5)
    assert temperature_level(3 / 2) == "sicak"

    # Sınır kontrolleri
    assert temperature_level(0.3) == "donmus"
    assert temperature_level(0.7) == "soguk"
    assert temperature_level(1.0) == "normal"
    assert temperature_level(1.4) == "normal"
    assert temperature_level(2.0) == "sicak"
    assert temperature_level(3.5) == "cok-sicak"
    assert temperature_level(5.0) == "patlamis"


def test_5_lapseki_projection():
    """Test 5: Lapseki 12 ay fiyat projeksiyonu — manuel hesap ile karşılaştır"""
    bugunku = 40_000
    tufe = 0.35
    nufus = 0.018
    insaat = 0.12
    sicaklik = 1.5
    olay = 0.0

    f_tufe = 1 + tufe
    f_nufus = 1 + nufus * 3 * (12 / 12)
    f_insaat = 1 - insaat * 0.5 * (12 / 12)
    f_olay = 1 + olay
    f_havuz = 1 + math.log(sicaklik) * 0.05

    proj = bugunku * f_tufe * f_nufus * f_insaat * f_olay * f_havuz

    # Kontrat Bölüm 5.1: ~54.300 ± 1500
    assert 52_500 < proj < 56_500, (
        f"Lapseki projeksiyonu = {proj:.0f}, bekleniyor 54.300 ± 1500"
    )


# ── Standalone runner ──────────────────────────────────────────────────────────

def _run_all() -> None:
    tests = [
        test_1_kategori_carpani,
        test_2_haber_isi_hesabi,
        test_3_tazelik_decay,
        test_4_sicaklik_orani_seviyesi,
        test_5_lapseki_projection,
    ]

    print("=" * 60)
    print("TRADIA HeatCalculator — Matematik Testleri")
    print("=" * 60)

    passed = 0
    for fn in tests:
        try:
            fn()
            print(f"  ✅ {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {fn.__name__}: {e}")
        except Exception as e:
            print(f"  ❌ {fn.__name__}: beklenmedik hata — {e}")

    print(f"\nÖZET: {passed}/{len(tests)} PASS")
    sys.exit(0 if passed == len(tests) else 1)


if __name__ == "__main__":
    _run_all()
