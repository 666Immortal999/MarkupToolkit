from __future__ import annotations

from core.tool_manager import ToolManager
from qt import QAction, QMenuBar, QPushButton, Qt


class AppMenuBar(QMenuBar):
    def __init__(self, tool_manager: ToolManager, parent=None) -> None:
        super().__init__(parent)
        self.tool_manager = tool_manager
        self.host = parent
        self.window_actions: list[QAction] = []
        self._fps_actions: dict[int, QAction] = {}
        self._aspect_actions: dict[str, QAction] = {}
        self._capture_mode_actions: dict[str, QAction] = {}
        self._window_action_by_hwnd: dict[int, QAction] = {}
        self._markup_mode_actions: dict[str, QAction] = {}

        self._build_file_menu()
        self._build_view_menu()
        self._build_settings_menu()
        self._build_aspect_menu()
        self._build_window_menu()
        self._build_markup_mode_menu()
        self._build_help_menu()
        self._build_right_theme_menu()
        self.tool_manager.active_tool_changed.connect(self._on_tool_changed)

    def _cb(self, name: str):
        return getattr(self.host, name, lambda *args, **kwargs: None)

    def _fit_menu_width(self, menu) -> None:
        texts = [a.text() for a in menu.actions() if a.text()]
        if not texts:
            return
        fm = self.fontMetrics()
        longest = max(fm.horizontalAdvance(t) for t in texts)
        width = longest + 48
        menu.setMinimumWidth(width)
        menu.setMaximumWidth(width)

    def _build_file_menu(self) -> None:
        file_menu = self.addMenu("File")
        file_menu.addAction("New Project", self._cb("file_new"))
        file_menu.addAction("Open Project", self._cb("file_open"))
        file_menu.addAction("Open Image...", self._cb("open_image_file"))
        file_menu.addAction("Close Opened File", self._cb("close_opened_file"))
        file_menu.addAction("Save Project", self._cb("file_save"))
        file_menu.addSeparator()
        file_menu.addAction("Exit", self._cb("close"))
        self._fit_menu_width(file_menu)

    def _build_view_menu(self) -> None:
        view = self.addMenu("View")
        view.addAction("Fit Game Window", self._cb("fit_game_window"))
        view.addAction("Reset Zoom", self._cb("reset_zoom"))
        view.addSeparator()
        view.addAction("Toggle Fullscreen", self._cb("toggle_fullscreen"))
        self._fit_menu_width(view)

    def _build_settings_menu(self) -> None:
        self.settings_menu = self.addMenu("Settings")
        fps_menu = self.settings_menu.addMenu("Capture FPS")
        a = fps_menu.addAction("Stop", lambda: self._cb("set_capture_fps")(0))
        a.setCheckable(True)
        self._fps_actions[0] = a
        fps_menu.addSeparator()
        for fps in (12, 24, 30, 60):
            a = fps_menu.addAction(f"{fps}", lambda v=fps: self._cb("set_capture_fps")(v))
            a.setCheckable(True)
            self._fps_actions[int(fps)] = a
        fps_menu.addSeparator()
        fps_menu.addAction("Custom...", self._cb("set_capture_fps_custom"))
        self._fit_menu_width(fps_menu)
        self._fit_menu_width(self.settings_menu)

    def _build_aspect_menu(self) -> None:
        self.aspect_menu = self.addMenu("Aspect")
        a = self.aspect_menu.addAction("Free", lambda: self._cb("set_aspect")("Free"))
        a.setCheckable(True)
        self._aspect_actions["Free"] = a
        self.aspect_menu.addSeparator()
        for label in ["16:9", "16:10", "4:3", "3:2", "1:1", "21:9"]:
            a = self.aspect_menu.addAction(label, lambda l=label: self._cb("set_aspect")(l))
            a.setCheckable(True)
            self._aspect_actions[str(label)] = a
        self.aspect_menu.addSeparator()
        a = self.aspect_menu.addAction("Custom...", lambda: self._cb("set_aspect")("Custom..."))
        a.setCheckable(True)
        self._aspect_actions["Custom..."] = a
        self._fit_menu_width(self.aspect_menu)

    def _build_window_menu(self) -> None:
        self.window_menu = self.addMenu("Window")
        self.capture_mode_menu = self.window_menu.addMenu("Capture Mode")
        a = self.capture_mode_menu.addAction("Fallback (current)", lambda: self._cb("set_capture_mode")("fallback"))
        a.setCheckable(True)
        self._capture_mode_actions["fallback"] = a
        a = self.capture_mode_menu.addAction("WGC HWND (scaffold)", lambda: self._cb("set_capture_mode")("wgc"))
        a.setCheckable(True)
        self._capture_mode_actions["wgc"] = a
        self.window_menu.addSeparator()
        self.window_menu.addAction("Refresh Windows", self._cb("refresh_windows"))
        self.window_menu.addAction("Clear Selected Window", self._cb("clear_selected_window"))
        self.window_menu.addSeparator()
        self._fit_menu_width(self.capture_mode_menu)
        self._fit_menu_width(self.window_menu)

    def rebuild_window_list(self, windows: list[tuple[int, str]]) -> None:
        for action in self.window_actions:
            self.window_menu.removeAction(action)
        self.window_actions.clear()
        self._window_action_by_hwnd.clear()

        for hwnd, title in windows:
            action = QAction(title, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, h=hwnd: self._cb("select_window")(h))
            self.window_menu.addAction(action)
            self.window_actions.append(action)
            self._window_action_by_hwnd[int(hwnd)] = action

        self._fit_menu_width(self.window_menu)

    def _build_markup_mode_menu(self) -> None:
        self.mode_menu = self.addMenu("Markup Mode")
        for tool in self.tool_manager.list_tools():
            action = QAction(tool.display_name, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, tool_id=tool.id: self.tool_manager.set_active_tool(tool_id))
            self.mode_menu.addAction(action)
            self._markup_mode_actions[str(tool.id)] = action
        self._fit_menu_width(self.mode_menu)

    def _build_help_menu(self) -> None:
        help_menu = self.addMenu("Help")
        help_menu.addAction("About", self._cb("help_about"))
        self._fit_menu_width(help_menu)

    def _build_right_theme_menu(self) -> None:
        self.theme_toggle_btn = self._create_theme_toggle_button()
        self.setCornerWidget(self.theme_toggle_btn, corner=Qt.Corner.TopRightCorner)

    def _create_theme_toggle_button(self):
        btn = QPushButton("🌙", self)
        btn.setFlat(True)
        btn.setCheckable(True)
        btn.setToolTip("Toggle Theme")
        btn.clicked.connect(self._cb("toggle_theme"))
        return btn

    def _set_checked(self, mapping: dict, key) -> None:
        for k, action in mapping.items():
            action.setChecked(k == key)

    def set_current_capture_fps(self, fps: int) -> None:
        selected = int(fps) if int(fps) in self._fps_actions else None
        self._set_checked(self._fps_actions, selected)

    def set_current_aspect_label(self, label: str) -> None:
        txt = str(label or "")
        if txt.startswith("Custom ("):
            self._set_checked(self._aspect_actions, "Custom...")
        else:
            self._set_checked(self._aspect_actions, txt)

    def set_current_capture_mode(self, mode: str) -> None:
        self._set_checked(self._capture_mode_actions, str(mode))

    def set_current_hwnd(self, hwnd: int) -> None:
        self._set_checked(self._window_action_by_hwnd, int(hwnd))

    def _on_tool_changed(self, tool) -> None:
        self._set_checked(self._markup_mode_actions, str(getattr(tool, "id", "")))

    def set_theme_toggle_state(self, theme_name: str) -> None:
        is_light = str(theme_name).strip().lower() == "light"
        if hasattr(self, "theme_toggle_btn"):
            self.theme_toggle_btn.setChecked(is_light)
            self.theme_toggle_btn.setText("☀" if is_light else "🌙")
