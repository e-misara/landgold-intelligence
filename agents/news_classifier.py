"""
Tradia Haber Sınıflandırıcı — Haiku 4.5 tabanlı.

Kullanım:
    from agents.news_classifier import NewsClassifier
    clf = NewsClassifier()
    result = clf.classify_news({"baslik": "...", "kaynak": "...", "tarih": "...", "metin": "..."})
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import anthropic

# Geçerli kategoriler (20 + BELIRSIZ)
VALID_CATEGORIES = {
    "imar-degisikligi", "ulasim-iyilestirme", "saglik-tesisi", "egitim-tesisi",
    "sanayi-yatirim", "turizm-yatirim", "kamulastirma", "ihale-ilani",
    "donusum-ilani", "yabanci-satis", "mega-proje", "dogal-afet",
    "ekonomik-karar", "sosyal-tesis", "yatirim-tesvik", "yargi-karari",
    "dogal-olay", "vergi-harc-degisikligi", "demografik-haber",
    "guvenlik-suc", "BELIRSIZ",
}

# Geçerli alt-kategoriler — sistem promptuyla senkronize
VALID_ALT_KATEGORILER: dict[str, set[str]] = {
    "imar-degisikligi":        {"yogunluk-artisi", "yogunluk-azalisi", "kullanim-degisikligi", "plan-iptali"},
    "ulasim-iyilestirme":      {"acilis", "temel-atma", "ihale-acildi", "genisleme", "iptal-erteleme"},
    "saglik-tesisi":           {"sehir-hastanesi-acilis", "ozel-hastane-acilis", "hastane-tasinma-kapanma", "saglik-kompleksi"},
    "egitim-tesisi":           {"universite-kampus", "fakulte-tasinma", "yurt-yapimi", "okul-ihale"},
    "sanayi-yatirim":          {"osb-genisleme-acilis", "fabrika-acilis", "lojistik-depo", "fabrika-kapanma"},
    "turizm-yatirim":          {"otel-acilis", "marina-acilis", "turizm-bolge-ilani", "muze-acilis"},
    "kamulastirma":            {"acele-kamulastirma", "kamulastirma-itiraz", "kamulastirma-iptal"},
    "ihale-ilani":             {"mega-proje-ihale", "yol-ihale", "bina-ihale"},
    "donusum-ilani":           {"riskli-alan-ilan", "donusum-baslangic", "donusum-tamamlanma"},
    "yabanci-satis":           {"vatandaslik-sart-degisikligi", "ulke-kisitlamasi", "bolgesel-yasak"},
    "mega-proje":              {"mega-acilis", "mega-temel-atma", "mega-aciklanma", "mega-iptal-rafa-kaldirma"},
    "dogal-afet":              {"deprem-aktif", "sel-tasilgi", "yangin", "risk-bolgesi-ilan"},
    "ekonomik-karar":          {"politika-faizi", "konut-kredisi", "kkm-degisiklik", "kdv-konut"},
    "sosyal-tesis":            {"avm-acilis", "park-acilis", "kultur-merkezi"},
    "yatirim-tesvik":          {"bolge-tesvik-degisikligi", "vergi-muafiyet", "tesvik-paketi"},
    "yargi-karari":            {"imar-plan-iptali", "acele-kamulastirma-iptal", "insaat-yikim-karari", "yatirim-koruma-karari"},
    "dogal-olay":              {"koruma-alani-ilani", "taskin-bolgesi", "erozyon-yasagi"},
    "vergi-harc-degisikligi":  {"kdv-oran-degisikligi", "rayic-bedel-artisi", "tapu-harci", "degerli-konut-vergisi"},
    "demografik-haber":        {"goc-girisi", "goc-cikisi", "yabanci-yatirimci-cekilmesi", "multeci-yogunluk"},
    "guvenlik-suc":            {"suc-orani-artis", "asayis-iyilesme", "gettolasma"},
    "BELIRSIZ":                set(),
}

VALID_ETKI_TIPLERI = {
    "pozitif-talep", "pozitif-arz-azaltici",
    "negatif-talep", "negatif-arz-arttirici",
    "karma", "notr",
}

VALID_ETKI_BUYUKLUKLERI = {"kucuk", "orta", "buyuk", "cok-buyuk"}
VALID_GUVENILIRLIK = {"resmi", "yari-resmi", "haber", "soylenti"}

# Zorunlu çıktı alanları
REQUIRED_FIELDS = {
    "il", "ilce", "mahalle", "etkilened_ek_ilceler",
    "kategori", "etki_tipi", "etki_buyuklugu", "agirlik_puani",
}

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "docs" / "havuz" / "SINIFLANDIRICI_SYSTEM_PROMPT.md"

USER_PROMPT_TEMPLATE = """\
HABER:

Başlık: {baslik}
Kaynak: {kaynak}
Tarih: {tarih}
Metin: {metin}

Bu haberi sınıflandır. Sadece JSON çıktısı ver."""


class ClassificationError(Exception):
    pass


class NewsClassifier:
    """Haiku 4.5 ile haber sınıflandırıcı."""

    MODEL = "claude-haiku-4-5-20251001"
    MAX_TOKENS = 800

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY bulunamadı")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._system_prompt = self._load_system_prompt()

    # ── Public API ─────────────────────────────────────────────────────────

    def classify_news(self, haber: dict[str, Any]) -> dict[str, Any]:
        """Tek haberi sınıflandırır. Gerekli alanlar: baslik, kaynak, tarih, metin."""
        user_prompt = USER_PROMPT_TEMPLATE.format(
            baslik=haber.get("baslik") or haber.get("title", ""),
            kaynak=haber.get("kaynak") or haber.get("source", ""),
            tarih=haber.get("tarih") or haber.get("published", ""),
            metin=haber.get("metin") or haber.get("summary", ""),
        )

        message = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = message.content[0].text.strip()
        classification = self._parse_json(raw_text)
        self._validate_classification(classification)

        # Giriş meta verilerini sonuca ekle
        classification["_input_baslik"] = haber.get("baslik", "")
        classification["_model"] = self.MODEL
        classification["_input_tokens"] = message.usage.input_tokens
        classification["_output_tokens"] = message.usage.output_tokens

        return classification

    def classify_batch(
        self, haberler: list[dict[str, Any]], max_concurrent: int = 10
    ) -> list[dict[str, Any]]:
        """Haber listesini asyncio ile paralel sınıflandırır."""
        return asyncio.run(self._classify_batch_async(haberler, max_concurrent))

    # ── Internal ───────────────────────────────────────────────────────────

    async def _classify_batch_async(
        self, haberler: list[dict], max_concurrent: int
    ) -> list[dict]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _one(haber: dict) -> dict | None:
            async with semaphore:
                try:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, self.classify_news, haber)
                except Exception as exc:
                    print(f"[NewsClassifier] batch hata '{haber.get('baslik','?')[:40]}': {exc}")
                    return None

        tasks = [_one(h) for h in haberler]
        results = await asyncio.gather(*tasks)
        # Hata olanları (None) listeden çıkar
        return [r for r in results if r is not None]

    def _load_system_prompt(self) -> str:
        if not SYSTEM_PROMPT_PATH.exists():
            raise FileNotFoundError(f"System prompt bulunamadı: {SYSTEM_PROMPT_PATH}")
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()

    def _parse_json(self, text: str) -> dict:
        """Model çıktısından JSON bloğunu çıkarır ve parse eder."""
        # Bazen ```json ... ``` bloğu içinde gelir
        if "```" in text:
            start = text.find("{", text.find("```"))
            end = text.rfind("}") + 1
            text = text[start:end]

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ClassificationError(f"JSON parse hatası: {exc}\nRaw: {text[:200]}") from exc

    def _validate_classification(self, c: dict) -> None:
        """Zorunlu alan varlığı ve değer geçerliliği kontrolü."""
        # Zorunlu alan kontrolü (etkilened_ek_ilceler typo toleransı dahil)
        mandatory = {"kategori", "etki_tipi", "etki_buyuklugu", "agirlik_puani"}
        missing = mandatory - set(c.keys())
        if missing:
            raise ClassificationError(f"Eksik zorunlu alanlar: {missing}")

        # Kategori geçerlilik
        if c["kategori"] not in VALID_CATEGORIES:
            raise ClassificationError(
                f"Geçersiz kategori: '{c['kategori']}'. "
                f"Geçerliler: {sorted(VALID_CATEGORIES)}"
            )

        # Etki tipi geçerlilik
        if c["etki_tipi"] not in VALID_ETKI_TIPLERI:
            raise ClassificationError(f"Geçersiz etki_tipi: '{c['etki_tipi']}'")

        # Etki büyüklüğü
        if c["etki_buyuklugu"] not in VALID_ETKI_BUYUKLUKLERI:
            raise ClassificationError(f"Geçersiz etki_buyuklugu: '{c['etki_buyuklugu']}'")

        # Ağırlık puanı 0-10
        try:
            puan = float(c["agirlik_puani"])
        except (TypeError, ValueError) as exc:
            raise ClassificationError(f"agirlik_puani sayısal olmalı") from exc
        if not (0 <= puan <= 10):
            raise ClassificationError(f"agirlik_puani 0-10 aralığında olmalı, gelen: {puan}")

        # Alt-kategori soft kontrolü — sözlükte yoksa None'a çek, hata fırlatmaz
        kategori = c.get("kategori")
        alt = c.get("alt_kategori")
        if alt is not None and kategori in VALID_ALT_KATEGORILER:
            valid_set = VALID_ALT_KATEGORILER[kategori]
            if valid_set and alt not in valid_set:
                print(f"⚠️  Alt-kategori sözlükte yok: {kategori} / {alt!r} → None'a çekildi")
                c["alt_kategori"] = None
