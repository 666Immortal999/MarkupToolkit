from __future__ import annotations

from qt import QHBoxLayout, QPushButton, QVBoxLayout

from ui.panels.base_panel import BasePanel


class MapShapePanel(BasePanel):
    def __init__(self, parent=None) -> None:
        super().__init__("Map Shape", parent)
        layout: QVBoxLayout = self.layout()
        row = QHBoxLayout()
        self.polygon_btn = QPushButton("Polygon", self)
        self.box_btn = QPushButton("Box", self)
        self.circle_btn = QPushButton("Circle", self)
        for b in (self.polygon_btn, self.box_btn, self.circle_btn):
            b.setCheckable(True)
            b.setObjectName("PointTypeButton")
            row.addWidget(b, 1)
        layout.addLayout(row)
        self._set_active("polygon")
        self.polygon_btn.clicked.connect(lambda: self._set_active("polygon"))
        self.box_btn.clicked.connect(lambda: self._set_active("box"))
        self.circle_btn.clicked.connect(lambda: self._set_active("circle"))

    def _set_active(self, shape: str) -> None:
        self.polygon_btn.setChecked(shape == "polygon")
        self.box_btn.setChecked(shape == "box")
        self.circle_btn.setChecked(shape == "circle")

    def selected_shape(self) -> str:
        if self.box_btn.isChecked():
            return "box"
        if self.circle_btn.isChecked():
            return "circle"
        return "polygon"
