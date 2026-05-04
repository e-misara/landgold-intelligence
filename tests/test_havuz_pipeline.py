"""
Tradia Havuz Pipeline — 5 integration test.
Mock data kullanır, API çağrısı YOK.

Çalıştırma:
    python -m pytest tests/test_havuz_pipeline.py -v
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from zoneinfo import ZoneInfo

TR = ZoneInfo("Europe/Istanbul")


def test_1_pipeline_with_mock_news(tmp_path, monkeypatch):
    """Test 1: Mock haberlerle pipeline dry-run modunda uçtan uca"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "vezir").mkdir()  # append_signal için

    mock_news = [
        {
            "baslik": "Lapseki imar değişikliği onaylandı",
            "kaynak": "Belediye",
            "tarih": "2026-05-03",
            "metin": "Lapseki Cumhuriyet Mahallesi emsal artışı...",
        }
    ]

    from scripts.daily_havuz_pipeline import run_daily_pipeline

    with patch("agents.news_agent.NewsAgent.__init__", return_value=None), \
         patch("agents.news_agent.NewsAgent.fetch_today", return_value=mock_news):
        sonuc = run_daily_pipeline(dry_run=True)

    assert sonuc["stages"]["fetch"]["status"] == "ok"
    assert sonuc["stages"]["fetch"]["count"] == 1
    # dry_run=True → classify aşaması atlanır (haber var ama dry_run)
    assert "heat" in sonuc["stages"]
    assert "summary" in sonuc["stages"]


def test_2_havuz_summary_format(tmp_path, monkeypatch):
    """Test 2: havuz_summary.json doğru formatta yazılıyor mu"""
    monkeypatch.chdir(tmp_path)
    havuz_dir = tmp_path / "data" / "havuz"
    havuz_dir.mkdir(parents=True)

    fake_isi = {
        "Esenyurt": {"isi": 287, "sicaklik": 4.2, "seviye": "patlamis"},
        "Lapseki": {"isi": 12, "sicaklik": 3.8, "seviye": "cok-sicak"},
        "Bingöl": {"isi": 0.5, "sicaklik": 0.3, "seviye": "donmus"},
    }
    (havuz_dir / "ilce_isi_son_6_ay.json").write_text(
        json.dumps(fake_isi), encoding="utf-8"
    )
    # Boş havuz dosyası oluştur (count_total_news için)
    (havuz_dir / "ilce_haber_havuzu.jsonl").write_text("", encoding="utf-8")

    from scripts.daily_havuz_pipeline import write_havuz_summary
    write_havuz_summary()

    summary_path = havuz_dir / "havuz_summary.json"
    assert summary_path.exists(), "havuz_summary.json oluşturulmadı"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    # Zorunlu alanlar
    assert "en_sicak_5_ilce" in summary
    assert "toplam_haber" in summary
    assert "son_24h_haber" in summary
    assert "guncellenme" in summary

    # Sıralama: Esenyurt (4.2) birinci olmalı
    assert len(summary["en_sicak_5_ilce"]) <= 5
    assert summary["en_sicak_5_ilce"][0]["ilce"] == "Esenyurt"
    assert summary["en_sicak_5_ilce"][0]["sicaklik"] == pytest.approx(4.2)

    # Bingöl sona yakın (en düşük sıcaklık)
    ilceler = [x["ilce"] for x in summary["en_sicak_5_ilce"]]
    assert ilceler.index("Esenyurt") < ilceler.index("Lapseki")
    assert ilceler.index("Lapseki") < ilceler.index("Bingöl")


def test_3_sali_kontrolu():
    """Test 3: Cron UTC → TR dönüşümü ve gün kontrolü"""
    # Salı = weekday 1
    sali = datetime(2026, 5, 5, 2, 0, tzinfo=TR)
    assert sali.weekday() == 1

    # Cuma = weekday 4
    cuma = datetime(2026, 5, 8, 2, 0, tzinfo=TR)
    assert cuma.weekday() == 4

    # Cron: 0 23 * * 1 (Pazartesi 23:00 UTC) = Salı 02:00 TR (+3)
    pazartesi_utc = datetime(2026, 5, 4, 23, 0, tzinfo=timezone.utc)
    pazartesi_tr = pazartesi_utc.astimezone(TR)
    assert pazartesi_tr.weekday() == 1, "Pazartesi 23:00 UTC Salı olmalı"
    assert pazartesi_tr.hour == 2, "02:00 TR olmalı"

    # Cron: 0 2 * * * (Her gün 02:00 UTC) = 05:00 TR
    saat_2_utc = datetime(2026, 5, 3, 2, 0, tzinfo=timezone.utc)
    saat_5_tr = saat_2_utc.astimezone(TR)
    assert saat_5_tr.hour == 5, "02:00 UTC → 05:00 TR olmalı"


def test_4_bootstrap_assessment(tmp_path, monkeypatch):
    """Test 4: Eski haber değerlendirme — tam metin/başlık ayrımı"""
    monkeypatch.chdir(tmp_path)
    news_dir = tmp_path / "data" / "news"
    news_dir.mkdir(parents=True)

    fake_news = [
        {
            "baslik": "Tam metinli haber",
            "metin": "Çok uzun metin içeriği bu haber için. " * 10,  # >100 karakter
        },
        {
            "baslik": "Başlık-only haber 1",
            "metin": "",
        },
        {
            "baslik": "Başlık-only haber 2",
            "metin": "kısa",  # <100 karakter
        },
    ]
    (news_dir / "news_archive.json").write_text(
        json.dumps(fake_news), encoding="utf-8"
    )

    from scripts.bootstrap_havuz import assess_old_news
    result = assess_old_news()

    assert result.get("error") is None, f"Beklenmeyen hata: {result.get('error')}"
    assert result["toplam"] == 3
    assert result["tam_metin"] == 1
    assert result["sadece_baslik"] == 2
    assert len(result["ornekler"]) <= 3


def test_5_pipeline_error_tolerance(tmp_path, monkeypatch):
    """Test 5: Fetch aşaması fail olunca sonraki aşamalar devam ediyor mu"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "vezir").mkdir()

    from scripts.daily_havuz_pipeline import run_daily_pipeline

    with patch("agents.news_agent.NewsAgent.__init__", return_value=None), \
         patch("agents.news_agent.NewsAgent.fetch_today", side_effect=Exception("API down")):
        sonuc = run_daily_pipeline(dry_run=True)

    # Fetch aşaması hatalı
    assert sonuc["stages"]["fetch"]["status"] == "error"
    assert "API down" in sonuc["stages"]["fetch"]["message"]

    # Isı ve özet aşamaları yine de çalıştı (dry_run sayesinde ok dönmeli)
    assert "heat" in sonuc["stages"]
    assert "summary" in sonuc["stages"]

    # Pipeline başarısız ve hata listesi dolu
    assert sonuc["success"] is False
    assert len(sonuc["errors"]) >= 1
    assert sonuc["errors"][0]["stage"] == "fetch"


# ── Standalone runner ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v"],
        cwd=str(Path(__file__).parent.parent),
    )
    sys.exit(result.returncode)
