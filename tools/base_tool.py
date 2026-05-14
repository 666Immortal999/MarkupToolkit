from __future__ import annotations

from abc import ABC

from qt import QWidget


class BaseTool(ABC):
    id = "base"
    display_name = "Base"
    overlay_class = QWidget
    settings_widget_class = QWidget

    def activate(self) -> None:
        pass

    def deactivate(self) -> None:
        pass

    def on_mouse_press(self, event) -> None:
        pass

    def on_mouse_move(self, event) -> None:
        pass

    def on_mouse_release(self, event) -> None:
        pass

    def draw(self, painter) -> None:
        pass
