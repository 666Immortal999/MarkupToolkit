from __future__ import annotations

from qt import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout

from ui.panels.base_panel import BasePanel


class SubPresetsPanel(BasePanel):
    def __init__(self, parent=None) -> None:
        super().__init__("Sub Preset", parent)
        layout: QVBoxLayout = self.layout()

        self.combo = QComboBox(self)
        self.combo.setMinimumHeight(24)
        layout.addWidget(self.combo)

        row = QHBoxLayout()
        self.new_btn = QPushButton("New", self)
        self.rename_btn = QPushButton("Rename", self)
        self.delete_btn = QPushButton("Delete", self)
        row.addWidget(self.new_btn)
        row.addWidget(self.rename_btn)
        row.addWidget(self.delete_btn)
        layout.addLayout(row)

    def get_state(self) -> dict:
        return {
            "items": [self.combo.itemText(i) for i in range(self.combo.count())],
            "current_index": self.combo.currentIndex(),
        }

    def apply_state(self, state: dict) -> None:
        idx = int(state.get("current_index", 0))
        if self.combo.count():
            self.combo.setCurrentIndex(max(0, min(idx, self.combo.count() - 1)))

    def set_items(self, items: list[str]) -> None:
        current = self.combo.currentText()
        self.combo.clear()
        self.combo.addItems(items or [])
        idx = self.combo.findText(current)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

