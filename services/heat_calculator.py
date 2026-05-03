"""
Tradia Isı Hesaplayıcı Servisi
Kontrat: docs/havuz/ADIM-2-ISI-PROJEKSIYON-V1.md
"""
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

TR = ZoneInfo("Europe/Istanbul")

# Kategori çarpanları (kontrat Bölüm 2.1.2)
KATEGORI_CARPANLARI = {
    "mega-proje": 2.0,
    "ulasim-iyilestirme": 1.8,
    "saglik-tesisi": 1.6,
    "yargi-karari": 1.5,
    "sanayi-yatirim": 1.5,
    "imar-degisikligi": 1.3,
    "kamulastirma": 1.3,
    "donusum-ilani": 1.4,
    "egitim-tesisi": 1.2,
    "ekonomik-karar": 1.2,
    "yatirim-tesvik": 1.1,
    "ihale-ilani": 1.0,
    "yabanci-satis": 1.0,
    "vergi-harc-degisikligi": 1.0,
    "turizm-yatirim": 1.0,
    "dogal-afet": 1.5,
    "dogal-olay": 0.9,
    "sosyal-tesis": 0.7,
    "demografik-haber": 0.8,
    "guvenlik-suc": 0.8,
    "BELIRSIZ": 0.0,
}

# Kaynak çarpanları (Bölüm 2.1.3)
KAYNAK_CARPANLARI = {
    "resmi": 1.0,
    "yari-resmi": 0.85,
    "haber": 0.6,
    "soylenti": 0.3,
}

# Yarılanma ömrü gün cinsinden (Bölüm 2.1.4)
YARILANMA_OMRU = {
    "mega-proje": 120,
    "ulasim-iyilestirme": 90,
    "saglik-tesisi": 90,
    "egitim-tesisi": 90,
    "donusum-ilani": 75,
    "sanayi-yatirim": 60,
    "imar-degisikligi": 45,
    "yargi-karari": 60,
    "kamulastirma": 45,
    "ihale-ilani": 30,
    "ekonomik-karar": 30,
    "yatirim-tesvik": 60,
    "yabanci-satis": 45,
    "vergi-harc-degisikligi": 45,
    "turizm-yatirim": 60,
    "dogal-afet": 90,
    "dogal-olay": 45,
    "sosyal-tesis": 30,
    "demografik-haber": 30,
    "guvenlik-suc": 14,
}


def temperature_level(orani: float) -> str:
    if orani < 0.5:
        return "donmus"
    if orani < 0.8:
        return "soguk"
    if orani < 1.5:
        return "normal"
    if orani < 2.5:
        return "sicak"
    if orani < 4.0:
        return "cok-sicak"
    return "patlamis"


class HeatCalculator:
    """İlçe ısı puanı + sıcaklık oranı hesaplayıcı"""

    def __init__(self, havuz_path: str = "data/havuz/ilce_haber_havuzu.jsonl"):
        self.havuz_path = Path(havuz_path)
        self._haberler_cache = None
        self._cache_zamani = None

    def _load_haberler(self) -> list:
        """Havuzu lazy-load + 5dk cache"""
        if (
            self._haberler_cache is not None
            and self._cache_zamani is not None
            and (datetime.now(TR) - self._cache_zamani).seconds < 300
        ):
            return self._haberler_cache

        if not self.havuz_path.exists():
            return []

        haberler = []
        with self.havuz_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    h = json.loads(line)
                    if h.get("kategori") != "BELIRSIZ":
                        haberler.append(h)
                except json.JSONDecodeError:
                    continue

        self._haberler_cache = haberler
        self._cache_zamani = datetime.now(TR)
        return haberler

    def tazelik_carpani(
        self, haber_tarihi: str, bugun: datetime, kategori: str
    ) -> float:
        """Exp decay tazelik çarpanı"""
        try:
            ht = datetime.fromisoformat(haber_tarihi.replace("Z", "+00:00"))
            if ht.tzinfo is None:
                ht = ht.replace(tzinfo=TR)
        except (ValueError, AttributeError):
            return 0.5  # Bozuk tarih → orta değer

        gun_sayisi = (bugun - ht).days
        if gun_sayisi < 0:
            return 1.0  # Gelecek tarihi → tam ağırlık

        yarilanma = YARILANMA_OMRU.get(kategori, 60)
        return math.exp(-gun_sayisi * math.log(2) / yarilanma)

    def haber_isi(self, haber: dict, bugun: Optional[datetime] = None) -> float:
        """Tek haberin ısı katkısını hesapla"""
        if bugun is None:
            bugun = datetime.now(TR)

        agirlik = haber.get("agirlik_puani", 0)
        kategori = haber.get("kategori", "BELIRSIZ")
        kaynak = haber.get("guvenilirlik", "haber")
        tarih = haber.get("tarih_referansi") or haber.get("tarih")

        kategori_c = KATEGORI_CARPANLARI.get(kategori, 0.5)
        kaynak_c = KAYNAK_CARPANLARI.get(kaynak, 0.5)
        tazelik_c = self.tazelik_carpani(tarih, bugun, kategori) if tarih else 0.5

        return agirlik * kategori_c * kaynak_c * tazelik_c

    def calculate(self, ilce_kodu: str, gun_sayisi: int = 180) -> float:
        """Bir ilçenin son N gün toplam ısısı"""
        bugun = datetime.now(TR)
        cutoff = bugun - timedelta(days=gun_sayisi)

        haberler = self._load_haberler()
        toplam = 0.0

        for h in haberler:
            if h.get("ilce", "").lower() != ilce_kodu.lower():
                ek_ilceler = [i.lower() for i in h.get("etkilenen_ek_ilceler", [])]
                if ilce_kodu.lower() not in ek_ilceler:
                    continue

            tarih_str = h.get("tarih_referansi") or h.get("tarih")
            if not tarih_str:
                continue
            try:
                ht = datetime.fromisoformat(tarih_str.replace("Z", "+00:00"))
                if ht.tzinfo is None:
                    ht = ht.replace(tzinfo=TR)
                if ht < cutoff:
                    continue
            except ValueError:
                continue

            toplam += self.haber_isi(h, bugun)

        return round(toplam, 2)

    def kaba_tarihsel_ortalama(self, ilce_kodu: str, ilce_db: dict) -> float:
        """Nüfus-bazlı fallback (Bölüm 2.4 Katman B)"""
        ilce = ilce_db.get(ilce_kodu)
        if not ilce:
            return 1.0

        nufus = ilce.get("nufus", 10000)

        if ilce.get("buyuksehir_merkez"):
            baseline = nufus / 5000
        elif ilce.get("il_merkez"):
            baseline = nufus / 8000
        else:
            baseline = nufus / 12000

        return max(baseline, 0.5)

    def get_temperature(
        self,
        ilce_kodu: str,
        tarihsel_ortalama: Optional[float] = None,
        ilce_db: Optional[dict] = None,
    ) -> dict:
        """Sıcaklık oranı + seviye"""
        mevcut = self.calculate(ilce_kodu)

        if tarihsel_ortalama is None:
            if ilce_db:
                tarihsel_ortalama = self.kaba_tarihsel_ortalama(ilce_kodu, ilce_db)
            else:
                tarihsel_ortalama = 1.0

        if tarihsel_ortalama < 1:
            tarihsel_ortalama = 1

        orani = mevcut / tarihsel_ortalama

        return {
            "mevcut_isi": mevcut,
            "tarihsel_ortalama": round(tarihsel_ortalama, 2),
            "sicaklik_orani": round(orani, 2),
            "seviye": temperature_level(orani),
        }

    def get_active_events(self, ilce_kodu: str, min_agirlik: int = 8) -> list:
        """Yüksek ağırlıklı son 2 yıl olayları"""
        bugun = datetime.now(TR)
        cutoff = bugun - timedelta(days=730)

        haberler = self._load_haberler()
        active = []

        for h in haberler:
            if h.get("agirlik_puani", 0) < min_agirlik:
                continue
            if h.get("ilce", "").lower() != ilce_kodu.lower():
                continue

            tarih_str = h.get("tarih_referansi") or h.get("tarih")
            try:
                ht = datetime.fromisoformat(tarih_str.replace("Z", "+00:00"))
                if ht.tzinfo is None:
                    ht = ht.replace(tzinfo=TR)
                if ht < cutoff:
                    continue
            except (ValueError, AttributeError):
                continue

            active.append(
                {
                    "tarih": tarih_str,
                    "kategori": h.get("kategori"),
                    "alt_kategori": h.get("alt_kategori"),
                    "agirlik": h.get("agirlik_puani"),
                    "etki_tipi": h.get("etki_tipi"),
                    "ozet": h.get("ozet"),
                }
            )

        return active
