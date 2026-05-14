from __future__ import annotations

from qt import QCheckBox, QComboBox, QVBoxLayout

from ui.panels.base_panel import BasePanel


class MapComponentSettingsPanel(BasePanel):
    def __init__(self, parent=None) -> None:
        super().__init__("Map Component", parent)
        layout: QVBoxLayout = self.layout()
        self.zone_type_combo = QComboBox(self)
        self.zone_type_combo.addItems(["blocked", "walkable", "plant", "zone callouts", "jump spot", "boost zone"])
        layout.addWidget(self.zone_type_combo)
        self.closed_cb = QCheckBox("Close Polygon", self)
        self.closed_cb.setChecked(True)
        layout.addWidget(self.closed_cb)
