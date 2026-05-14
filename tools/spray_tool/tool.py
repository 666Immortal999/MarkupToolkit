from tools.base_tool import BaseTool
from .overlay import SprayOverlay
from .widgets import SpraySettingsWidget


class SprayTool(BaseTool):
    id = "spray"
    display_name = "Spray Tool"
    overlay_class = SprayOverlay
    settings_widget_class = SpraySettingsWidget
