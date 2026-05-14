from __future__ import annotations

from qt import QLabel, QVBoxLayout

from ui.panels.base_panel import BasePanel


class PointSettingsPanel(BasePanel):
    def __init__(self, parent=None) -> None:
        super().__init__("Point Settings", parent)
        layout: QVBoxLayout = self.layout()
        layout.addWidget(QLabel("Coming soon", self))
