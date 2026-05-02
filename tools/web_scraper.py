from __future__ import annotations
from typing import Any
import requests
from core.config import Config


class WebScraper:
    """Fetches and parses HTML from land registry, news, and gov sources."""

    def __init__(self, timeout: int = Config.REQUEST_TIMEOUT) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    def get(self, url: str) -> str:
        pass

    def parse_table(self, html: str, selector: str) -> list[dict]:
        pass

    def extract_text(self, html: str, selector: str) -> str:
        pass

    def close(self) -> None:
        pass
