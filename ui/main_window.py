from __future__ import annotations

from pathlib import Path

from core.constants import DEFAULT_SIZE, WINDOW_TITLE
from core.project_manager import ProjectManager
from core.settings_manager import SettingsManager
from core.theme_manager import ThemeManager
from core.tool_manager import ToolManager
from core.window_capture import list_task_windows
from core.wgc_capture import WgcHwndCapture
from qt import QApplication, QFileDialog, QInputDialog, QKeySequence, QMainWindow, QMessageBox, QPixmap, QShortcut, QTimer
from ui.menu_bar import AppMenuBar
from ui.workspace import Workspace
from widgets.status_bar import AppStatusBar
from canvas.capture_view import CaptureView


class MainWindow(QMainWindow):
    def __init__(self, tool_manager: ToolManager, project_manager: ProjectManager, theme_manager: ThemeManager) -> None:
        super().__init__()
        self.tool_manager = tool_manager
        self.project_manager = project_manager
        self.theme_manager = theme_manager
        self.capture_fps = 30
        self.capture_mode = "fallback"
        self.current_theme = "dark"
        self.current_aspect_label = "Free"
        self.auto_aspect_from_source = True
        self.selected_hwnd = 0
        self._window_title_by_hwnd: dict[int, str] = {}
        self.wgc = WgcHwndCapture()
        self.settings = SettingsManager()
        self._saving_settings_in_progress = False
        self._last_valid_capture = QPixmap()
        self._last_minimized_state = False
        self._opened_file_path = ""
        self._opened_image = QPixmap()
        self._last_opened_file_path = ""
        self._restore_last_opened_file = False

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*DEFAULT_SIZE)

        self._menu = AppMenuBar(self.tool_manager, self)
        self.setMenuBar(self._menu)
        self._menu.set_current_capture_fps(self.capture_fps)
        self._menu.set_current_capture_mode(self.capture_mode)
        self._menu.set_current_aspect_label(self.current_aspect_label)
        self._menu.set_current_hwnd(self.selected_hwnd)

        self.workspace = Workspace(self.tool_manager, self)
        self.setCentralWidget(self.workspace)

        self._status = AppStatusBar(self.tool_manager, self)
        self.setStatusBar(self._status)
        self._status.zoom_out_btn.clicked.connect(self._zoom_out)
        self._status.zoom_in_btn.clicked.connect(self._zoom_in)
        self._status.set_zoom_drag_callback(self._on_zoom_drag_delta)
        self._status.set_zoom_percent(self.workspace.canvas.capture.get_zoom())

        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._update_capture_frame)
        self._capture_timer.timeout.connect(self._sync_zoom_status)
        self._apply_capture_fps()
        self._close_opened_file_shortcut = QShortcut(QKeySequence("Esc"), self)
        self._close_opened_file_shortcut.activated.connect(self.close_opened_file)
        self.refresh_windows()
        self._load_settings()

    def _apply_capture_fps(self) -> None:
        if int(self.capture_fps) <= 0:
            self._capture_timer.stop()
            return
        interval_ms = max(1, int(round(1000.0 / max(1, int(self.capture_fps)))))
        self._capture_timer.start(interval_ms)

    def _apply_source_aspect(self, width: int, height: int) -> None:
        # Always follow real source aspect of selected window.
        self.workspace.canvas.set_capture_aspect_ratio(max(1, width) / max(1, height))

    def _update_capture_frame(self) -> None:
        if not self._opened_image.isNull():
            self.workspace.canvas.set_capture_pixmap(self._opened_image)
            return
        if not self.selected_hwnd:
            # Ensure preview can show explicit "no window capture" state.
            self.workspace.canvas.set_capture_pixmap(QPixmap())
            return

        # Always attempt capture even for minimized windows to keep stream forced/live.
        self._last_minimized_state = False

        if self.capture_mode == "wgc":
            frame = self.wgc.get_latest_qimage()
            if frame is not None and not frame.isNull():
                self._apply_source_aspect(frame.width(), frame.height())
                pix = QPixmap.fromImage(frame)
                if not pix.isNull() and pix.width() > 2 and pix.height() > 2:
                    self._last_valid_capture = pix
                    self.workspace.canvas.set_capture_pixmap(pix)
                    return
            self.workspace.canvas.set_capture_pixmap(QPixmap())
            return

        screen = self.windowHandle().screen() if self.windowHandle() else QApplication.primaryScreen()
        if screen is None:
            return
        pixmap = screen.grabWindow(int(self.selected_hwnd))
        if pixmap and not pixmap.isNull() and pixmap.width() > 2 and pixmap.height() > 2:
            self._apply_source_aspect(pixmap.width(), pixmap.height())
            self._last_valid_capture = pixmap
            self.workspace.canvas.set_capture_pixmap(pixmap)
            return
        self.workspace.canvas.set_capture_pixmap(QPixmap())

    def fit_game_window(self) -> None:
        capture_view = self.workspace.canvas.capture
        current_ratio = getattr(capture_view, "_aspect_ratio", None)
        if current_ratio is None:
            # Free mode already fills the markup zone as much as possible.
            self.statusBar().showMessage("Fit Game Window: Free aspect already uses maximum capture area", 2000)
            return
        ratio = max(1e-9, float(current_ratio))

        right_w = max(int(self.workspace.right_panel.width()), int(self.workspace.right_panel.minimumWidth()))
        handle_w = 9
        left_margin = right_margin = 0
        top_margin = bottom_margin = 0
        cw = self.centralWidget()
        if cw is not None and cw.layout() is not None:
            m = cw.layout().contentsMargins()
            left_margin, top_margin, right_margin, bottom_margin = m.left(), m.top(), m.right(), m.bottom()

        capture_pad = int(CaptureView.PADDING) * 2

        # Window frame + menu/status bars overhead (outside central layout).
        non_client_w = max(0, self.frameGeometry().width() - self.width())
        non_client_h = max(0, self.frameGeometry().height() - self.height())

        avail = self.screen().availableGeometry() if self.screen() is not None else QApplication.primaryScreen().availableGeometry()
        max_win_w = max(640, int(avail.width() * 0.98))
        max_win_h = max(480, int(avail.height() * 0.94))

        chrome_w = non_client_w + left_margin + right_margin + right_w + handle_w
        chrome_h = non_client_h + top_margin + bottom_margin
        max_left_w = max(1, max_win_w - chrome_w)
        max_left_h = max(1, max_win_h - chrome_h)

        # Resize only the "other" dimension:
        # if LR is touching, adjust app height; if TB is touching, adjust app width.
        current_left_w = max(1, int(self.workspace.canvas.width()))
        current_left_h = max(1, int(self.workspace.canvas.height()))
        avail_capture_w = max(1, current_left_w - capture_pad)
        avail_capture_h = max(1, current_left_h - capture_pad)
        required_h_for_current_w = max(1, int(round(avail_capture_w / ratio)))
        required_w_for_current_h = max(1, int(round(avail_capture_h * ratio)))
        eps = 1

        def _capture_fit_error() -> tuple[int, int]:
            # Returns (horizontal_slack, vertical_slack) for current geometry.
            self.workspace.canvas.updateGeometry()
            capture_view.updateGeometry()
            self.workspace.updateGeometry()
            self.centralWidget().updateGeometry() if self.centralWidget() is not None else None
            avail_w = max(1, int(self.workspace.canvas.width()) - capture_pad)
            avail_h = max(1, int(self.workspace.canvas.height()) - capture_pad)
            need_h = max(1, int(round(avail_w / ratio)))
            need_w = max(1, int(round(avail_h * ratio)))
            return max(0, avail_w - need_w), max(0, avail_h - need_h)

        def _solve_target_window_size() -> tuple[int, int] | None:
            # Deterministic geometry solve using current real canvas size.
            # For fixed right panel and splitter, left area scales linearly with main window size.
            cur_win_w = max(1, int(self.width()))
            cur_win_h = max(1, int(self.height()))
            cur_left_w = max(1, int(self.workspace.canvas.width()))
            cur_left_h = max(1, int(self.workspace.canvas.height()))
            if cur_left_w <= 1 or cur_left_h <= 1:
                return None

            # Required left dimension for a tight fit of current ratio.
            req_left_h = max(1, int(round((max(1, cur_left_w - capture_pad) / ratio) + capture_pad)))
            req_left_w = max(1, int(round((max(1, cur_left_h - capture_pad) * ratio) + capture_pad)))

            h_slack, v_slack = _capture_fit_error()
            # Keep one dimension fixed; change only the opposite pair.
            if v_slack > h_slack:
                # Vertical gap dominates: adjust window height only.
                scale_y = cur_left_h / float(cur_win_h)
                if scale_y <= 1e-9:
                    return None
                target_h = int(round(req_left_h / scale_y))
                target_h = max(480, min(target_h, max_win_h))
                return cur_win_w, target_h
            if h_slack > 0:
                # Horizontal gap dominates: adjust window width only.
                scale_x = cur_left_w / float(cur_win_w)
                if scale_x <= 1e-9:
                    return None
                target_w = int(round(req_left_w / scale_x))
                target_w = max(640, min(target_w, max_win_w))
                return target_w, cur_win_h
            return cur_win_w, cur_win_h

        if avail_capture_h > required_h_for_current_w + eps:
            # Vertical slack exists -> keep width, shrink/expand height only.
            target_left_w = min(current_left_w, max_left_w)
            # Recompute using potentially clamped width so vertical fit stays exact.
            avail_w_from_target = max(1, target_left_w - capture_pad)
            target_left_h = max(1, int(round(avail_w_from_target / ratio)) + capture_pad)
            target_left_h = min(target_left_h, max_left_h)
            target_win_w = self.width()
            base_target_h = chrome_h + target_left_h
            best_h = base_target_h
            best_err = None
            for delta in (-2, -1, 0, 1, 2):
                cand_h = max(480, min(base_target_h + delta, max_win_h))
                self.resize(target_win_w, cand_h)
                _, v_slack = _capture_fit_error()
                err = abs(v_slack)
                if best_err is None or err < best_err:
                    best_err = err
                    best_h = cand_h
            target_win_h = best_h
        elif avail_capture_w > required_w_for_current_h + eps:
            # Horizontal slack exists -> keep height, shrink/expand width only.
            target_left_h = min(current_left_h, max_left_h)
            # Recompute using potentially clamped height so horizontal fit stays exact.
            avail_h_from_target = max(1, target_left_h - capture_pad)
            target_left_w = max(1, int(round(avail_h_from_target * ratio)) + capture_pad)
            target_left_w = min(target_left_w, max_left_w)
            base_target_w = chrome_w + target_left_w
            target_win_h = self.height()
            best_w = base_target_w
            best_err = None
            for delta in (-2, -1, 0, 1, 2):
                cand_w = max(640, min(base_target_w + delta, max_win_w))
                self.resize(cand_w, target_win_h)
                h_slack, _ = _capture_fit_error()
                err = abs(h_slack)
                if best_err is None or err < best_err:
                    best_err = err
                    best_w = cand_w
            target_win_w = best_w
        else:
            # Already tight (or almost tight due to rounding): no resize needed.
            self.statusBar().showMessage("Fit Game Window: capture is already tightly fitted", 2000)
            return

        target_win_w = max(640, min(target_win_w, max_win_w))
        target_win_h = max(480, min(target_win_h, max_win_h))
        solved = _solve_target_window_size()
        if solved is not None:
            target_win_w, target_win_h = solved
        self.resize(target_win_w, target_win_h)
        self.statusBar().showMessage(
            f"Fit Game Window -> window {target_win_w}x{target_win_h}",
            2000,
        )

    def set_capture_fps(self, value: int) -> None:
        self.capture_fps = max(0, int(value))
        self._apply_capture_fps()
        if hasattr(self, "_menu"):
            self._menu.set_current_capture_fps(self.capture_fps)
        if self.capture_fps <= 0:
            self.statusBar().showMessage("Capture stopped", 1500)
        else:
            self.statusBar().showMessage(f"Capture FPS: {self.capture_fps}", 1500)

    def set_capture_fps_custom(self) -> None:
        value, ok = QInputDialog.getInt(self, "Capture FPS", "FPS:", int(self.capture_fps), 1, 240, 1)
        if ok:
            self.set_capture_fps(value)

    def set_aspect(self, label: str) -> None:
        # Aspect is source-driven when file or external window capture is active.
        if (not self._opened_image.isNull()) or bool(self.selected_hwnd):
            self.statusBar().showMessage("Aspect is locked while capture source is active", 1800)
            if hasattr(self, "_menu"):
                self._menu.set_current_aspect_label(self.current_aspect_label)
            return
        ratio_map = {
            "16:9": 16 / 9,
            "16:10": 16 / 10,
            "4:3": 4 / 3,
            "3:2": 3 / 2,
            "1:1": 1.0,
            "21:9": 21 / 9,
            "Free": None,
        }
        if label == "Custom...":
            raw, ok = QInputDialog.getText(self, "Custom Aspect", "Enter ratio W:H (example 5:4) or float:")
            if not ok or not raw.strip():
                return
            s = raw.strip().replace(" ", "")
            try:
                ratio = float(s.split(":", 1)[0]) / float(s.split(":", 1)[1]) if ":" in s else float(s)
                if ratio <= 0:
                    raise ValueError
            except Exception:
                self.statusBar().showMessage("Invalid custom aspect", 1500)
                return
            self.workspace.canvas.set_capture_aspect_ratio(ratio)
            self.current_aspect_label = f"Custom ({ratio:.3f})"
            self.auto_aspect_from_source = False
            if hasattr(self, "_menu"):
                self._menu.set_current_aspect_label(self.current_aspect_label)
            self.statusBar().showMessage(f"Aspect: {self.current_aspect_label}", 1500)
            return

        self.workspace.canvas.set_capture_aspect_ratio(ratio_map.get(label, None))
        self.current_aspect_label = label
        self.auto_aspect_from_source = label == "Free"
        if hasattr(self, "_menu"):
            self._menu.set_current_aspect_label(self.current_aspect_label)
        self.statusBar().showMessage(f"Aspect: {label}", 1500)

    def set_capture_mode(self, mode: str) -> None:
        self.capture_mode = mode if mode in {"fallback", "wgc"} else "fallback"
        if self.capture_mode == "wgc" and self.selected_hwnd:
            self.wgc.start(self.selected_hwnd, self._window_title_by_hwnd.get(self.selected_hwnd))
        else:
            self.wgc.stop()
        if hasattr(self, "_menu"):
            self._menu.set_current_capture_mode(self.capture_mode)
        self.statusBar().showMessage(f"Capture Mode: {self.capture_mode}", 1500)

    def refresh_windows(self) -> None:
        windows = list_task_windows()
        self._window_title_by_hwnd = {w.hwnd: w.title for w in windows}
        self._menu.rebuild_window_list([(w.hwnd, w.title) for w in windows])
        self._menu.set_current_hwnd(self.selected_hwnd)
        self.statusBar().showMessage(f"Windows found: {len(windows)}", 1500)

    def select_window(self, hwnd: int) -> None:
        self.wgc.stop()
        self.selected_hwnd = int(hwnd)
        self._last_valid_capture = QPixmap()
        self._last_minimized_state = False
        self._opened_file_path = ""
        self._opened_image = QPixmap()
        self.workspace.canvas.set_capture_pixmap(QPixmap())
        if self.capture_fps <= 0:
            self.capture_fps = 30
            self._apply_capture_fps()
        if self.capture_mode == "wgc":
            self.wgc.start(self.selected_hwnd, self._window_title_by_hwnd.get(self.selected_hwnd))
        if hasattr(self, "_menu"):
            self._menu.set_current_hwnd(self.selected_hwnd)
        self.statusBar().showMessage(f"Selected window HWND: {self.selected_hwnd}", 1500)

    def set_theme_dark(self) -> None:
        self.theme_manager.apply_theme(QApplication.instance(), "dark")
        self.current_theme = "dark"
        if hasattr(self._menu, "set_theme_toggle_state"):
            self._menu.set_theme_toggle_state("dark")

    def set_theme_light(self) -> None:
        self.theme_manager.apply_theme(QApplication.instance(), "light")
        self.current_theme = "light"
        if hasattr(self._menu, "set_theme_toggle_state"):
            self._menu.set_theme_toggle_state("light")

    def toggle_theme(self) -> None:
        if str(self.current_theme).lower() == "light":
            self.set_theme_dark()
        else:
            self.set_theme_light()

    def clear_selected_window(self) -> None:
        self.selected_hwnd = 0
        self.wgc.stop()
        self.workspace.canvas.set_capture_pixmap(QPixmap())
        if hasattr(self, "_menu"):
            self._menu.set_current_hwnd(0)
        self.statusBar().showMessage("Selected window cleared", 1500)


    def open_image_file(self) -> None:
        start_dir = ""
        if self._last_opened_file_path:
            try:
                start_dir = str(Path(self._last_opened_file_path).parent)
            except Exception:
                start_dir = ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;All Files (*.*)",
        )
        if not path:
            return
        pix = QPixmap(path)
        if pix.isNull():
            self.statusBar().showMessage("Failed to open image", 2000)
            return
        self._opened_file_path = path
        self._last_opened_file_path = path
        self._restore_last_opened_file = True
        self._opened_image = pix
        self._apply_source_aspect(pix.width(), pix.height())
        self.workspace.canvas.set_capture_pixmap(pix)
        self._save_settings()
        self.statusBar().showMessage(f"Opened image: {path}", 2000)

    def close_opened_file(self) -> None:
        if self._opened_image.isNull():
            return
        # User explicitly closed file: keep path for next Open dialog, but disable auto-restore on startup.
        self._restore_last_opened_file = False
        self._opened_file_path = ""
        self._opened_image = QPixmap()
        self._update_capture_frame()
        self._save_settings()
        self.statusBar().showMessage("Opened file closed", 1500)

    def _collect_settings(self) -> dict:
        return {
            "theme": self.current_theme,
            "capture_fps": int(self.capture_fps),
            "capture_mode": self.capture_mode,
            "aspect_label": self.current_aspect_label,
            "auto_aspect_from_source": bool(self.auto_aspect_from_source),
            "selected_hwnd": int(self.selected_hwnd),
            "active_tool_id": getattr(self.tool_manager.active_tool, "id", ""),
            "workspace": self.workspace.get_state(),
            "last_opened_file_path": self._last_opened_file_path,
            "restore_last_opened_file": bool(self._restore_last_opened_file),
        }

    def _load_settings(self) -> None:
        data = self.settings.load()
        if not data:
            return
        self.set_capture_fps(int(data.get("capture_fps", self.capture_fps)))
        self.set_capture_mode(str(data.get("capture_mode", self.capture_mode)))
        theme = str(data.get("theme", self.current_theme))
        if theme == "light":
            self.set_theme_light()
        else:
            self.set_theme_dark()

        aspect = str(data.get("aspect_label", self.current_aspect_label))
        if aspect.startswith("Custom (") and aspect.endswith(")"):
            try:
                ratio = float(aspect[len("Custom ("):-1])
                self.workspace.canvas.set_capture_aspect_ratio(ratio)
                self.current_aspect_label = aspect
                self.auto_aspect_from_source = False
            except Exception:
                self.set_aspect("Free")
        else:
            self.set_aspect(aspect if aspect else "Free")

        self.workspace.apply_state(data.get("workspace", {}))
        restored_opened_file = False
        self._last_opened_file_path = str(data.get("last_opened_file_path", "") or "")
        if "restore_last_opened_file" in data:
            self._restore_last_opened_file = bool(data.get("restore_last_opened_file", False))
        else:
            self._restore_last_opened_file = bool(self._last_opened_file_path)
        if self._restore_last_opened_file and self._last_opened_file_path:
            p = Path(self._last_opened_file_path)
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self._opened_file_path = str(p)
                    self._opened_image = pix
                    self._apply_source_aspect(pix.width(), pix.height())
                    self.workspace.canvas.set_capture_pixmap(pix)
                    restored_opened_file = True
        saved_tool_id = str(data.get("active_tool_id", "")).strip()
        available_ids = {t.id for t in self.tool_manager.list_tools()}
        if saved_tool_id and saved_tool_id in available_ids:
            self.tool_manager.set_active_tool(saved_tool_id)
        hwnd = int(data.get("selected_hwnd", 0))
        if hwnd and not restored_opened_file:
            self.select_window(hwnd)

    def _save_settings(self) -> None:
        if self._saving_settings_in_progress:
            return
        self._saving_settings_in_progress = True
        try:
            self.settings.save(self._collect_settings())
        finally:
            self._saving_settings_in_progress = False

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.workspace.has_unsaved_changes():
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Unsaved Preset")
            msg.setText("Current preset has unsaved changes.")
            msg.setInformativeText("Save changes before exiting?")
            msg.setStandardButtons(
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            )
            msg.setDefaultButton(QMessageBox.StandardButton.Save)
            choice = msg.exec()
            if choice == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if choice == QMessageBox.StandardButton.Save:
                self.workspace._save_current_mode_markup()
        self._save_settings()
        super().closeEvent(event)

    def file_new(self) -> None:
        self.statusBar().showMessage("New Project", 1500)

    def file_open(self) -> None:
        self.statusBar().showMessage("Open Project", 1500)

    def file_save(self) -> None:
        self._save_settings()
        self.statusBar().showMessage("Save Project", 1500)

    def help_about(self) -> None:
        self.statusBar().showMessage("Markup Toolkit", 1500)

    def reset_zoom(self) -> None:
        self.workspace.canvas.capture.reset_zoom()
        self._sync_zoom_status()
        self.statusBar().showMessage("Zoom reset", 1500)

    def _zoom_in(self) -> None:
        cv = self.workspace.canvas.capture
        cv.set_zoom(cv.get_zoom() + 0.1)
        self._sync_zoom_status()

    def _zoom_out(self) -> None:
        cv = self.workspace.canvas.capture
        cv.set_zoom(cv.get_zoom() - 0.1)
        self._sync_zoom_status()

    def _on_zoom_drag_delta(self, dx: int) -> None:
        cv = self.workspace.canvas.capture
        cv.set_zoom(cv.get_zoom() + (float(dx) * 0.01))
        self._sync_zoom_status()

    def _sync_zoom_status(self) -> None:
        sb = self.statusBar()
        if sb is not None and hasattr(sb, "set_zoom_percent"):
            sb.set_zoom_percent(self.workspace.canvas.capture.get_zoom())
