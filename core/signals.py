from __future__ import annotations

from qt import QObject, Signal


class AppSignals(QObject):
    """Application-wide signals."""

    tool_changed = Signal(str)
