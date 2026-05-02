from __future__ import annotations
import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "data" / "reports"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_FMT  = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_root(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(level)

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(_FMT, _DATEFMT))

    # File
    fh = logging.FileHandler(LOG_DIR / "landgold.log", encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(_FMT, _DATEFMT))

    root.addHandler(ch)
    root.addHandler(fh)
    _configured = True


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    configure_root(level)
    return logging.getLogger(name)
