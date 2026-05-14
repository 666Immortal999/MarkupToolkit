from tools.base_tool import BaseTool
from .overlay import UIBoxesOverlay
from .widgets import UIBoxesSettingsWidget


class UIBoxesTool(BaseTool):
    id = "ui_boxes"
    display_name = "UI Boxes Tool"
    overlay_class = UIBoxesOverlay
    settings_widget_class = UIBoxesSettingsWidget
