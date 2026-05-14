from tools.base_tool import BaseTool
from qt import QVBoxLayout, QWidget


class BaseOverlay(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        QVBoxLayout(self)


class BaseSettingsWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        QVBoxLayout(self)


class BaseRuntimeTool(BaseTool):
    id = "base"
    display_name = "Base"
    overlay_class = BaseOverlay
    settings_widget_class = BaseSettingsWidget
