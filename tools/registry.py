from tools.base_runtime_tool import BaseRuntimeTool
from tools.controls_tool.tool import ControlsTool
from tools.map_tool.tool import MapTool
from tools.spray_tool.tool import SprayTool
from tools.ui_boxes_tool.tool import UIBoxesTool

REGISTERED_TOOLS = [BaseRuntimeTool, MapTool, SprayTool, UIBoxesTool, ControlsTool]
