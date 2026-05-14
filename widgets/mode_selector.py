from __future__ import annotations

from qt import QPushButton, QHBoxLayout, QWidget

from core.tool_manager import ToolManager


class ModeSelector(QWidget):
    """Quick mode switcher similar to markup template top controls."""

    def __init__(self, tool_manager: ToolManager, parent=None) -> None:
        super().__init__(parent)
        self.tool_manager = tool_manager
        self._buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for tool in self.tool_manager.list_tools():
            btn = QPushButton(tool.display_name, self)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, tool_id=tool.id: self.tool_manager.set_active_tool(tool_id))
            layout.addWidget(btn)
            self._buttons[tool.id] = btn

        layout.addStretch(1)
        self.tool_manager.active_tool_changed.connect(self._on_tool_changed)

    def _on_tool_changed(self, tool) -> None:
        for tool_id, btn in self._buttons.items():
            btn.setChecked(tool_id == tool.id)
