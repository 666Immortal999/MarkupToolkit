from __future__ import annotations

from pathlib import Path

from qt import QApplication


class ThemeManager:
    def __init__(self) -> None:
        self._styles_dir = Path(__file__).resolve().parents[1] / "resources" / "styles"

    def apply_theme(self, app: QApplication, theme_name: str) -> None:
        qss_path = self._styles_dir / f"{theme_name}.qss"
        if qss_path.exists():
            app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
