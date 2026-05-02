from __future__ import annotations

SUPPORTED_LANGS = ("en", "ru", "ar", "tr")


class Translator:
    """Translates text between supported languages via Claude or DeepL fallback."""

    def __init__(self, provider: str = "claude") -> None:
        self.provider = provider

    def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        pass

    def detect_language(self, text: str) -> str:
        pass

    def batch_translate(self, texts: list[str], target_lang: str) -> list[str]:
        pass
