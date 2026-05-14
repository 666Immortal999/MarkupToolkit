from __future__ import annotations

from qt import QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from ui.panels.base_panel import BasePanel


class OCRFiltersPanel(BasePanel):
    def __init__(self, parent=None) -> None:
        super().__init__("OCR Filters", parent)
        layout: QVBoxLayout = self.layout()

        layout.addWidget(QLabel("Filter Type", self))
        self.filter_combo = QComboBox(self)
        self.filter_combo.addItems(["None", "Numbers", "Letters", "Color"])
        layout.addWidget(self.filter_combo)

        layout.addWidget(QLabel("Max Value", self))
        self.max_value_edit = QLineEdit(self)
        self.max_value_edit.setPlaceholderText("optional")
        layout.addWidget(self.max_value_edit)

        layout.addWidget(QLabel("Letters Language", self))
        self.lang_combo = QComboBox(self)
        self.lang_combo.addItems(["RU", "EN", "RU+EN"])
        layout.addWidget(self.lang_combo)

        self.postprocess_cb = QCheckBox("Postprocess", self)
        layout.addWidget(self.postprocess_cb)

        row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply", self)
        row.addStretch(1)
        row.addWidget(self.apply_btn)
        layout.addLayout(row)

    def get_state(self) -> dict:
        return {
            "filter": self.filter_combo.currentText(),
            "max_value": self.max_value_edit.text(),
            "lang": self.lang_combo.currentText(),
            "postprocess": self.postprocess_cb.isChecked(),
        }

    def apply_state(self, state: dict) -> None:
        if not isinstance(state, dict):
            return
        self.filter_combo.setCurrentText(str(state.get("filter", "None")))
        self.max_value_edit.setText(str(state.get("max_value", "")))
        self.lang_combo.setCurrentText(str(state.get("lang", "RU+EN")))
        self.postprocess_cb.setChecked(bool(state.get("postprocess", False)))
