from tools.base_tool import BaseTool
from .overlay import MapOverlay
from .widgets import MapSettingsWidget


class MapTool(BaseTool):
    id = "map"
    display_name = "Map Tool"
    overlay_class = MapOverlay
    settings_widget_class = MapSettingsWidget
