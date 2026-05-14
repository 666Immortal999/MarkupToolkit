from __future__ import annotations

from qt import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget, Qt, QTimer

from ui.panels.base_panel import BasePanel


class PreviewPanel(BasePanel):
    def __init__(self, parent=None) -> None:
        super().__init__("Preview", parent)
        layout: QVBoxLayout = self.layout()

        row = QWidget(self)
        row_l = QVBoxLayout(row)
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.setSpacing(6)

        self.toggle_btn = QPushButton("Hide Preview", self)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        row_l.addWidget(self.toggle_btn)

        self.postprocess_btn = QPushButton("Show Postprocess", self)
        self.postprocess_btn.setCheckable(True)
        self.postprocess_btn.setChecked(False)
        row_l.addWidget(self.postprocess_btn)
        layout.addWidget(row)

        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(180)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.preview_label.setScaledContents(False)
        self.preview_label.setText("No Preview")
        self.preview_label.setObjectName("PreviewLabel")
        layout.addWidget(self.preview_label)
        self._preview_aspect_ratio = 1.0
        self._last_geom = (-1, -1)
        self._sync_preview_geometry()
        # Ensure geometry is applied once the initial layout pass
        # finishes after app startup.
        QTimer.singleShot(0, self._sync_preview_geometry)

    def set_preview_aspect_ratio(self, ratio: float | None) -> None:
        r = float(ratio) if ratio and ratio > 0 else 1.0
        if abs(self._preview_aspect_ratio - r) < 1e-9:
            return
        self._preview_aspect_ratio = r
        self._sync_preview_geometry()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._sync_preview_geometry()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._sync_preview_geometry()
        QTimer.singleShot(0, self._sync_preview_geometry)

    def _sync_preview_geometry(self) -> None:
        if not self.preview_label.isVisible():
            return
        # Width is fully controlled by parent layout and must stay unchanged.
        width_px = max(120, self.preview_label.width())
        height_px = max(120, int(round(width_px / max(1e-9, self._preview_aspect_ratio))))
        geom = (-1, height_px)
        if geom == self._last_geom:
            return
        self._last_geom = geom
        self.preview_label.setMinimumHeight(height_px)
        self.preview_label.setMaximumHeight(height_px)

    def get_state(self) -> dict:
        return {
            "visible": self.toggle_btn.isChecked(),
            "postprocess": self.postprocess_btn.isChecked(),
        }

    def apply_state(self, state: dict) -> None:
        if not isinstance(state, dict):
            return
        if "visible" in state:
            self.toggle_btn.setChecked(bool(state.get("visible")))
        if "postprocess" in state:
            self.postprocess_btn.setChecked(bool(state.get("postprocess")))
