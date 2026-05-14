from __future__ import annotations

from qt import QListWidget, QHBoxLayout, QPushButton, QVBoxLayout, QComboBox

from core.tool_manager import ToolManager
from ui.panels.base_panel import BasePanel


class ToolSettingsPanel(BasePanel):
    def __init__(self, tool_manager: ToolManager, parent=None) -> None:
        super().__init__("Component List", parent)
        self.tool_manager = tool_manager

        layout: QVBoxLayout = self.layout()
        self.map_filter_combo = QComboBox(self)
        self.map_filter_combo.addItems(["all types", "blocked", "walkable", "plant", "zone callouts", "jump spot", "boost zone"])
        self.map_filter_combo.setVisible(False)
        layout.addWidget(self.map_filter_combo, 0)
        self.component_list = QListWidget(self)
        self.component_list.setFixedHeight(180)
        layout.addWidget(self.component_list, 0)

        row = QHBoxLayout()
        self.add_btn = QPushButton("Add", self)
        self.rename_btn = QPushButton("Rename", self)
        self.delete_btn = QPushButton("Delete", self)
        row.addWidget(self.add_btn)
        row.addWidget(self.rename_btn)
        row.addWidget(self.delete_btn)
        layout.addLayout(row)

        self.tool_manager.active_tool_changed.connect(self._on_tool_changed)

    def _on_tool_changed(self, tool) -> None:
        self.component_list.clear()

    def set_items(self, items: list[str]) -> None:
        self.component_list.clear()
        for text in items:
            self.component_list.addItem(text)

    def get_state(self) -> dict:
        return {
            "items": [self.component_list.item(i).text() for i in range(self.component_list.count())],
            "current_row": self.component_list.currentRow(),
        }

    def apply_state(self, state: dict) -> None:
        items = state.get("items")
        if isinstance(items, list):
            self.component_list.clear()
            for text in items:
                self.component_list.addItem(str(text))
        row = int(state.get("current_row", -1))
        if self.component_list.count() > 0 and row >= 0:
            self.component_list.setCurrentRow(min(row, self.component_list.count() - 1))
