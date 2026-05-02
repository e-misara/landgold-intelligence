from __future__ import annotations
from pathlib import Path
from core.config import Config


class PDFGenerator:
    """Renders investment reports and lead summaries as PDFs."""

    def __init__(self, output_dir: Path = Config.REPORTS_DIR) -> None:
        self.output_dir = output_dir

    def render_report(self, data: dict, template: str = "report") -> Path:
        pass

    def render_lead_summary(self, lead: dict, analysis: dict) -> Path:
        pass

    def merge(self, paths: list[Path], output_name: str) -> Path:
        pass
