from tools.base_tool import BaseTool
from .overlay import ControlsOverlay
from .widgets import ControlsSettingsWidget


class ControlsTool(BaseTool):
    id = "controls"
    display_name = "Controls Tool"
    overlay_class = ControlsOverlay
    settings_widget_class = ControlsSettingsWidget
