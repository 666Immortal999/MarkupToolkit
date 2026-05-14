from __future__ import annotations

from qt import QHBoxLayout, QLabel, QPushButton, QStatusBar, QTimer, QWidget, Qt

from core.tool_manager import ToolManager


class ZoomDragLabel(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self._dragging = False
        self._start_x = 0
        self._on_drag_delta = None

    def set_drag_callback(self, callback) -> None:
        self._on_drag_delta = callback

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start_x = int(event.position().x())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._dragging and callable(self._on_drag_delta):
            x = int(event.position().x())
            dx = x - self._start_x
            if dx != 0:
                self._start_x = x
                self._on_drag_delta(dx)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)


class AppStatusBar(QStatusBar):
    def __init__(self, tool_manager: ToolManager, parent=None) -> None:
        super().__init__(parent)
        self.preset_state_label = QLabel("Preset: saved", self)
        self.preset_state_label.setStyleSheet("color: #3ecf6d; font-weight: 600;")
        self.preset_state_label.setContentsMargins(0, 0, 12, 0)
        self.addWidget(self.preset_state_label)

        self.zoom_widget = QWidget(self)
        zoom_layout = QHBoxLayout(self.zoom_widget)
        zoom_layout.setContentsMargins(0, 0, 12, 0)
        zoom_layout.setSpacing(6)

        self.zoom_out_btn = QPushButton("-", self.zoom_widget)
        self.zoom_out_btn.setFixedWidth(24)
        self.zoom_out_btn.setFlat(True)
        self.zoom_out_btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; }")
        self.zoom_label = ZoomDragLabel("100%", self.zoom_widget)
        self.zoom_label.setContentsMargins(2, 0, 2, 0)
        self.zoom_in_btn = QPushButton("+", self.zoom_widget)
        self.zoom_in_btn.setFixedWidth(24)
        self.zoom_in_btn.setFlat(True)
        self.zoom_in_btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; }")
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addWidget(self.zoom_in_btn)
        self.addWidget(self.zoom_widget)
        self.log_label = QLabel("", self)
        self.log_label.setContentsMargins(8, 0, 8, 0)
        self.addWidget(self.log_label, 1)
        self.mode_label = QLabel("Mode: -", self)
        self.addPermanentWidget(self.mode_label)
        tool_manager.active_tool_changed.connect(self._on_tool_changed)
        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self.clearMessage)

    def _on_tool_changed(self, tool) -> None:
        self.mode_label.setText(f"Mode: {tool.display_name}")

    def set_preset_saved_state(self, saved: bool) -> None:
        if saved:
            self.preset_state_label.setText("Preset: saved")
            self.preset_state_label.setStyleSheet("color: #3ecf6d; font-weight: 600;")
        else:
            self.preset_state_label.setText("Preset: not saved")
            self.preset_state_label.setStyleSheet("color: #ff5a5a; font-weight: 600;")

    def showMessage(self, message: str, timeout: int = 0) -> None:  # type: ignore[override]
        self.log_label.setText(str(message or ""))
        if timeout and timeout > 0:
            self._message_timer.start(int(timeout))
        else:
            self._message_timer.stop()

    def clearMessage(self) -> None:  # type: ignore[override]
        self.log_label.setText("")

    def set_zoom_percent(self, zoom: float) -> None:
        pct = int(round(max(1.0, min(10.0, float(zoom))) * 100.0))
        self.zoom_label.setText(f"{pct}%")

    def set_zoom_drag_callback(self, callback) -> None:
        self.zoom_label.set_drag_callback(callback)
