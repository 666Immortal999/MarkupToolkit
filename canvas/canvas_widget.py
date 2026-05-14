from __future__ import annotations

from dataclasses import dataclass, field

from qt import QVBoxLayout, QWidget

from core.tool_manager import ToolManager
from canvas.capture_view import CaptureView
from canvas.overlay_layer import OverlayLayer


@dataclass
class GridSettings:
    enabled: bool = False
    magnet: bool = False
    show_border: bool = True
    columns: int = 24
    lock_columns: bool = False
    border_width: int = 2
    margins: dict[str, int] = field(default_factory=lambda: {"left": 0, "top": 0, "right": 0, "bottom": 0})

    def __post_init__(self) -> None:
        self._listeners: list = []

    def subscribe(self, callback) -> None:
        self._listeners.append(callback)

    def notify(self) -> None:
        for cb in self._listeners:
            cb()

    def set_margins(self, margins: dict[str, int]) -> None:
        self.margins = {k: max(0, int(v)) for k, v in margins.items()}
        self.notify()


class CanvasWidget(QWidget):
    def __init__(self, tool_manager: ToolManager, parent=None) -> None:
        super().__init__(parent)
        self.tool_manager = tool_manager
        self.grid_settings = GridSettings()

        self.capture = CaptureView(self)
        self.capture.attach_grid_settings(self.grid_settings)
        self.overlay = OverlayLayer(self.capture)

        layout = QVBoxLayout(self)
        # No extra padding around markup zone.
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.capture)

        self.capture.setLayout(QVBoxLayout())
        self.capture.layout().setContentsMargins(0, 0, 0, 0)
        self.capture.layout().addWidget(self.overlay)

        self.grid_settings.subscribe(self.capture.update)
        self.tool_manager.active_tool_changed.connect(self._on_tool_changed)
        self._markup_components = []

    def _on_tool_changed(self, tool) -> None:
        self.overlay.set_overlay(tool.overlay_class())

    def set_capture_aspect_ratio(self, ratio: float | None) -> None:
        self.capture.set_aspect_ratio(ratio)

    def set_capture_pixmap(self, pixmap) -> None:
        self.capture.set_captured_pixmap(pixmap)

    def set_markup_components(self, components) -> None:
        self._markup_components = list(components or [])
        self.capture.set_markup_components(self._markup_components)
