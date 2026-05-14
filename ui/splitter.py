from __future__ import annotations

from qt import QSplitter, Qt


class WorkspaceSplitter(QSplitter):
    def __init__(self, left, right, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.addWidget(left)
        self.addWidget(right)
        self.setHandleWidth(7)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 0)
        self.setSizes([1000, 400])
