from __future__ import annotations

from typing import Dict, Optional, Type

from qt import QObject, Signal, QWidget

from tools.base_tool import BaseTool


class ToolManager(QObject):
    """Registers and switches tools."""

    active_tool_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._tools: Dict[str, BaseTool] = {}
        self._active_tool: Optional[BaseTool] = None

    def register_tool(self, tool_cls: Type[BaseTool]) -> None:
        tool = tool_cls()
        self._tools[tool.id] = tool

    def register_tools(self, tools: list[Type[BaseTool]]) -> None:
        for tool_cls in tools:
            self.register_tool(tool_cls)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    @property
    def active_tool(self) -> Optional[BaseTool]:
        return self._active_tool

    def set_active_tool(self, tool_id: str) -> None:
        tool = self._tools.get(tool_id)
        if tool is None or tool is self._active_tool:
            return
        if self._active_tool is not None:
            self._active_tool.deactivate()
        self._active_tool = tool
        self._active_tool.activate()
        self.active_tool_changed.emit(tool)

    def build_tool_settings_widget(self) -> QWidget:
        if self._active_tool is None:
            return QWidget()
        widget_cls = self._active_tool.settings_widget_class
        return widget_cls()
