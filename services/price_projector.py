"""
Tradia Fiyat Projektörü
Kontrat: docs/havuz/ADIM-2-ISI-PROJEKSIYON-V1.md Bölüm 3
"""
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import yaml

from services.heat_calculator import HeatCalculator

TR = ZoneInfo("Europe/Istanbul")


def load_macro_config() -> dict:
    """config/macro_assumptions.yaml yükle"""
    config_path = Path("config/macro_assumptions.yaml")
    if not config_path.exists():
        return {
            "inflation": {"tufe_12_ay_beklenti": 35.0},
            "multipliers": {
                "nufus_carpani": 3.0,
                "arz_carpani": 0.5,
                "havuz_carpani": 0.05,
            },
            "event_impacts": {
                "cok-buyuk": 0.15,
                "buyuk": 0.08,
                "orta": 0.04,
                "kucuk": 0.02,
            },
        }

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class PriceProjector:
    """N ay sonraki m² tahmini"""

    def __init__(self):
        self.config = load_macro_config()
        self.heat = HeatCalculator()

    def get_current_m2(
        self, ilce_kodu: str, baseline_db: Optional[dict] = None
    ) -> float:
        """Bugünkü m² (manuel baseline veya fallback)"""
        if baseline_db and ilce_kodu in baseline_db:
            return float(baseline_db[ilce_kodu]["m2_ortalama"])

        # Fallback: 30K (Türkiye ortalama tahmini)
        # Üretimde her ilçe için baseline doldurulmalı
        return 30000.0

    def calculate_event_impact(self, ilce_kodu: str, n_ay: int) -> float:
        """Aktif büyük olayların toplam etki yüzdesi"""
        bugun = datetime.now(TR)
        active = self.heat.get_active_events(ilce_kodu, min_agirlik=8)

        toplam_etki = 0.0
        impacts = self.config["event_impacts"]

        for olay in active:
            try:
                ht = datetime.fromisoformat(olay["tarih"].replace("Z", "+00:00"))
                if ht.tzinfo is None:
                    ht = ht.replace(tzinfo=TR)
            except (ValueError, KeyError):
                continue

            gun_olaydan = (bugun - ht).days

            # Etki gecikmesi kontrolü — havuzdan ilgili haberi bul
            haber = next(
                (
                    h
                    for h in self.heat._load_haberler()
                    if h.get("tarih_referansi") == olay["tarih"]
                ),
                None,
            )
            if haber:
                gec_min = haber.get("etki_gecikmesi_ay_min", 0) or 0
                gec_max = haber.get("etki_gecikmesi_ay_max", 24) or 24

                if gun_olaydan < gec_min * 30:
                    continue  # Etki henüz başlamadı
                if gun_olaydan > gec_max * 30 + 365:
                    continue  # Etki sönümlendi

            buyukluk = haber.get("etki_buyuklugu", "kucuk") if haber else "kucuk"
            etki = impacts.get(buyukluk, 0.02)

            etki_tipi = olay.get("etki_tipi", "")
            if "negatif" in etki_tipi:
                etki = -etki

            toplam_etki += etki

        # Tek ilçeye ±%30'dan fazla etki verme
        return max(-0.30, min(0.30, toplam_etki))

    def project(
        self,
        ilce_kodu: str,
        n_ay: int = 12,
        ilce_db: Optional[dict] = None,
        baseline_db: Optional[dict] = None,
    ) -> dict:
        """Ana projeksiyon metodu"""
        bugunku = self.get_current_m2(ilce_kodu, baseline_db)

        tufe_yillik = self.config["inflation"]["tufe_12_ay_beklenti"] / 100
        tufe_n = (1 + tufe_yillik) ** (n_ay / 12) - 1

        nufus_artisi = 0.01  # Default %1
        if ilce_db and ilce_kodu in ilce_db:
            nufus_artisi = ilce_db[ilce_kodu].get("nufus_artisi_yillik", 0.01)

        insaat_artisi = 0.0  # TODO: TÜİK ruhsat verisi entegrasyonu

        olay_etkisi = self.calculate_event_impact(ilce_kodu, n_ay)

        temp = self.heat.get_temperature(ilce_kodu, ilce_db=ilce_db)
        sicaklik_orani = max(temp["sicaklik_orani"], 1.0)

        m = self.config["multipliers"]
        f_tufe = 1 + tufe_n
        f_nufus = 1 + nufus_artisi * m["nufus_carpani"] * (n_ay / 12)
        f_insaat = 1 - insaat_artisi * m["arz_carpani"] * (n_ay / 12)
        f_olay = 1 + olay_etkisi
        f_havuz = 1 + math.log(sicaklik_orani) * m["havuz_carpani"]

        projeksiyon = bugunku * f_tufe * f_nufus * f_insaat * f_olay * f_havuz

        nominal = (projeksiyon / bugunku - 1) * 100
        reel = nominal - tufe_n * 100

        return {
            "ilce": ilce_kodu,
            "n_ay": n_ay,
            "bugunku_m2": int(bugunku),
            "projeksiyon_m2": int(projeksiyon),
            "nominal_artis_yuzde": round(nominal, 1),
            "reel_artis_yuzde": round(reel, 1),
            "guven_araligi": (int(projeksiyon * 0.80), int(projeksiyon * 1.20)),
            "kaynak": "tahmin-v1",
            "uyari": (
                "Bu projeksiyon AI modeli tahminidir. "
                "Endeksa entegrasyonu sonrası v2'ye yükseltilecektir."
            ),
            "bilesenler": {
                "tufe_yuzde": round(tufe_n * 100, 1),
                "nufus_etkisi_yuzde": round((f_nufus - 1) * 100, 1),
                "arz_etkisi_yuzde": round((f_insaat - 1) * 100, 1),
                "olay_etkisi_yuzde": round(olay_etkisi * 100, 1),
                "havuz_etkisi_yuzde": round((f_havuz - 1) * 100, 1),
            },
            "sicaklik_seviyesi": temp["seviye"],
        }
