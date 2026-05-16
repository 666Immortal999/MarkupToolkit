from __future__ import annotations

import argparse
import sys

from qt import QApplication

from core.constants import APP_NAME
from core.project_manager import ProjectManager
from core.theme_manager import ThemeManager
from core.tool_manager import ToolManager
from tools.registry import REGISTERED_TOOLS
from ui.main_window import MainWindow


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Start the app in fullscreen mode.",
    )
    args, _ = parser.parse_known_args(argv)
    return args


def run() -> None:
    args = _parse_args(sys.argv[1:])
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    theme_manager = ThemeManager()
    theme_manager.apply_theme(app, "dark")

    tool_manager = ToolManager()
    tool_manager.register_tools(REGISTERED_TOOLS)
    project_manager = ProjectManager()

    window = MainWindow(tool_manager=tool_manager, project_manager=project_manager, theme_manager=theme_manager)
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()

    if tool_manager.list_tools() and tool_manager.active_tool is None:
        tool_manager.set_active_tool(tool_manager.list_tools()[0].id)

    sys.exit(app.exec())
