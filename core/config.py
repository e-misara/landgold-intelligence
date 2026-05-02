from __future__ import annotations
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent


class Config:
    # ── API Keys ───────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY:    str = os.getenv("OPENAI_API_KEY", "")      # optional

    # ── Model ──────────────────────────────────────────────────────────────
    MODEL: str = os.getenv("MODEL", "claude-opus-4-7")

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: int = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

    # ── Paths ──────────────────────────────────────────────────────────────
    DATA_PATH:      Path = Path(os.getenv("DATA_PATH", str(BASE_DIR / "data")))
    LEADS_DIR:      Path = DATA_PATH / "leads"
    PROPERTIES_DIR: Path = DATA_PATH / "properties"
    NEWS_DIR:       Path = DATA_PATH / "news"
    REPORTS_DIR:    Path = DATA_PATH / "reports"

    # ── HTTP ───────────────────────────────────────────────────────────────
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    MAX_RETRIES:     int = int(os.getenv("MAX_RETRIES", "3"))

    # ── Behaviour ──────────────────────────────────────────────────────────
    APPROVAL_REQUIRED: bool = os.getenv("APPROVAL_REQUIRED", "true").lower() == "true"

    @classmethod
    def validate(cls) -> None:
        missing = []
        if not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if missing:
            raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")

    @classmethod
    def ensure_dirs(cls) -> None:
        for d in (cls.LEADS_DIR, cls.PROPERTIES_DIR, cls.NEWS_DIR, cls.REPORTS_DIR):
            d.mkdir(parents=True, exist_ok=True)
