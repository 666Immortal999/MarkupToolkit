from __future__ import annotations

from typing import Optional

from qt import Qt, QWidget


class OverlayLayer(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active_overlay: Optional[QWidget] = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")

    def set_overlay(self, overlay: QWidget) -> None:
        if self._active_overlay is not None:
            self._active_overlay.setParent(None)
            self._active_overlay.deleteLater()
        self._active_overlay = overlay
        self._active_overlay.setParent(self)
        self._active_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._active_overlay.setStyleSheet("background: transparent;")
        self._active_overlay.setGeometry(self.rect())
        self._active_overlay.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._active_overlay is not None:
            self._active_overlay.setGeometry(self.rect())
