from __future__ import annotations

from qt import QHBoxLayout, QPushButton, QVBoxLayout

from ui.panels.base_panel import BasePanel


class PointTypePanel(BasePanel):
    def __init__(self, parent=None) -> None:
        super().__init__("Point Type", parent)
        layout: QVBoxLayout = self.layout()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self.click_btn = QPushButton("Click", self)
        self.scroll_btn = QPushButton("Scroll", self)
        self.swap_btn = QPushButton("Swap", self)
        for b in (self.click_btn, self.scroll_btn, self.swap_btn):
            b.setCheckable(True)
            b.setObjectName("PointTypeButton")
            row.addWidget(b, 1)
        layout.addLayout(row)
        self._set_active("click")
        self.click_btn.clicked.connect(lambda: self._set_active("click"))
        self.scroll_btn.clicked.connect(lambda: self._set_active("scroll"))
        self.swap_btn.clicked.connect(lambda: self._set_active("swap"))

    def _set_active(self, kind: str) -> None:
        self.click_btn.setChecked(kind == "click")
        self.scroll_btn.setChecked(kind == "scroll")
        self.swap_btn.setChecked(kind == "swap")

    def selected_type(self) -> str:
        if self.scroll_btn.isChecked():
            return "scroll"
        if self.swap_btn.isChecked():
            return "swap"
        return "click"
