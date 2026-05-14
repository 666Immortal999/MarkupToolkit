from __future__ import annotations

from qt import QColor, QFrame, QHBoxLayout, QImage, QInputDialog, QLabel, QMessageBox, QPainter, QPixmap, QPushButton, QScrollArea, QTimer, QVBoxLayout, Qt, QWidget

from canvas.canvas_widget import CanvasWidget
from core.tool_manager import ToolManager
from ui.panels.grid_panel import GridPanel
from ui.panels.display_panel import DisplayPanel
from ui.panels.presets_panel import PresetsPanel
from ui.panels.subpresets_panel import SubPresetsPanel
from ui.panels.tool_settings_panel import ToolSettingsPanel
from ui.panels.preview_panel import PreviewPanel
from ui.panels.ocr_filters_panel import OCRFiltersPanel
from ui.panels.point_type_panel import PointTypePanel
from ui.panels.point_settings_panel import PointSettingsPanel
from ui.panels.map_shape_panel import MapShapePanel
from ui.panels.map_component_settings_panel import MapComponentSettingsPanel
from ui.splitter import WorkspaceSplitter
from tools.ui_boxes_tool.controller import apply_ui_boxes_mode, reset_ui_boxes_mode, save_ui_boxes_mode
from tools.ui_boxes_tool.runtime import UIBoxesRuntime
from tools.ui_boxes_tool.data import (
    create_subpreset,
    delete_interface,
    delete_subpreset,
    rename_interface,
    rename_subpreset,
    upsert_interface,
)
from tools.controls_tool.data import load_controls_presets
from tools.controls_tool.data import save_controls_points
from tools.spray_tool.data import load_spray_presets, save_spray_pattern
from tools.map_tool.data import load_map_presets
from tools.map_tool.data import save_map_preset


class Workspace(QWidget):
    _COMPONENT_TOOL_IDS = {"ui_boxes", "controls", "spray", "map"}

    def __init__(self, tool_manager: ToolManager, parent=None) -> None:
        super().__init__(parent)
        self.tool_manager = tool_manager
        self._applying_mode_data = False
        self._mode_states: dict[str, dict] = {}
        self._has_unsaved_changes = False
        self._unsaved_by_key: dict[tuple[str, str, str], bool] = {}
        self._mode_markup_cache: dict[tuple[str, str, str], dict] = {}
        self._active_mode_key: tuple[str, str, str] | None = None
        self._map_visible_indices: list[int] = []

        self.canvas = CanvasWidget(self.tool_manager, self)
        self.ui_boxes_runtime = UIBoxesRuntime(self.canvas.capture)
        self.canvas.capture.set_components_changed_callback(self._on_canvas_components_changed)
        self.canvas.capture.set_empty_click_callback(self._on_canvas_empty_click)
        self.presets = PresetsPanel(self)
        self.subpresets = SubPresetsPanel(self)
        self.grid = GridPanel(self.canvas.grid_settings, self)
        self.display = DisplayPanel(self)
        self.preview = PreviewPanel(self)
        self.ocr_filters = OCRFiltersPanel(self)
        self.point_type = PointTypePanel(self)
        self.point_settings = PointSettingsPanel(self)
        self.map_shape = MapShapePanel(self)
        self.map_component_settings = MapComponentSettingsPanel(self)
        self.tool_settings = ToolSettingsPanel(self.tool_manager, self)
        self._panel_order_ids = ["presets", "subpresets", "tool_settings", "grid", "display", "preview", "ocr_filters", "point_type", "point_settings", "map_shape", "map_component_settings"]
        self._panels_by_id = {
            "presets": self.presets,
            "subpresets": self.subpresets,
            "tool_settings": self.tool_settings,
            "grid": self.grid,
            "display": self.display,
            "preview": self.preview,
            "ocr_filters": self.ocr_filters,
            "point_type": self.point_type,
            "point_settings": self.point_settings,
            "map_shape": self.map_shape,
            "map_component_settings": self.map_component_settings,
        }
        self._wire_autosave()
        self._wire_panel_actions()
        self.tool_manager.active_tool_changed.connect(self._on_tool_changed)
        self.presets.combo.currentTextChanged.connect(self._on_mode_selector_changed)
        self.subpresets.combo.currentTextChanged.connect(self._on_mode_selector_changed)
        self.presets.combo.currentTextChanged.connect(lambda *_: self._refresh_unsaved_status_for_current_selection())
        self.subpresets.combo.currentTextChanged.connect(lambda *_: self._refresh_unsaved_status_for_current_selection())
        self.display.show_overlay_cb.toggled.connect(self._on_display_changed)
        self.display.show_labels_cb.toggled.connect(self._on_display_changed)
        self.display.show_sizes_cb.toggled.connect(self._on_display_changed)
        self.display.show_hatch_cb.toggled.connect(self._on_display_changed)
        self.display.point_size_slider.valueChanged.connect(self._on_display_changed)
        self.display.point_axis_magnet_cb.toggled.connect(self._on_display_changed)
        self.preview.toggle_btn.toggled.connect(self._update_preview)
        self.preview.postprocess_btn.toggled.connect(self._update_preview)
        self.preview.toggle_btn.toggled.connect(lambda *_: self._sync_preview_ui_state())
        self.preview.postprocess_btn.toggled.connect(lambda *_: self._sync_preview_ui_state())
        self.tool_settings.component_list.currentRowChanged.connect(lambda *_: self._update_preview())
        self.tool_settings.component_list.currentRowChanged.connect(lambda *_: self._load_ocr_from_selected())
        self.tool_settings.component_list.currentRowChanged.connect(lambda *_: self._sync_map_component_panels())
        self.map_component_settings.zone_type_combo.currentTextChanged.connect(lambda *_: self._apply_map_component_settings())
        self.map_component_settings.closed_cb.toggled.connect(lambda *_: self._apply_map_component_settings())
        self.tool_settings.map_filter_combo.currentTextChanged.connect(lambda *_: self._refresh_map_component_list())
        self.ocr_filters.apply_btn.clicked.connect(self._apply_ocr_to_selected)

        self.right_panel = QFrame(self)
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setMinimumWidth(360)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        header = QLabel("Control Panel", self.right_panel)
        header.setObjectName("ControlPanelHeader")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFixedHeight(34)
        right_layout.addWidget(header, 0)

        scroll = QScrollArea(self.right_panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_host = QWidget(scroll)
        content_layout = QVBoxLayout(content_host)
        content_layout.setContentsMargins(10, 14, 10, 12)
        content_layout.setSpacing(12)
        self._panel_host_layout = content_layout
        self._rebuild_panel_layout()
        content_layout.addStretch(1)
        scroll.setWidget(content_host)
        right_layout.addWidget(scroll, 1)

        footer = QWidget(self.right_panel)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 8, 10, 10)
        footer_layout.setSpacing(6)
        self.footer_buttons: dict[str, QPushButton] = {}
        for label in ("Undo", "Redo", "Save", "Reset", "Exit"):
            btn = QPushButton(label, footer)
            self.footer_buttons[label] = btn
            if label == "Exit":
                btn.clicked.connect(self.window().close)
            footer_layout.addWidget(btn)
        right_layout.addWidget(footer, 0)
        self._set_unsaved_changes(False)
        self.footer_buttons["Save"].clicked.connect(self._save_current_mode_markup)
        self.footer_buttons["Reset"].clicked.connect(self._reset_current_mode_markup)
        self.footer_buttons["Undo"].clicked.connect(self._undo_current_mode_markup)
        self.footer_buttons["Redo"].clicked.connect(self._redo_current_mode_markup)
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.start(250)
        self._setup_panel_controls()

        splitter = WorkspaceSplitter(self.canvas, self.right_panel, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(splitter)

    def _on_tool_changed(self, _tool) -> None:
        self._snapshot_current_mode_markup_state()
        self._apply_mode_data()
        self._refresh_unsaved_status_for_current_selection()
        self._apply_current_mode_panel_state()
        self._update_actions_enabled()
        self._apply_display_options()

    def _on_mode_selector_changed(self, *_args) -> None:
        self._snapshot_current_mode_markup_state()
        self._apply_mode_data()

    def _setup_panel_controls(self) -> None:
        for panel_id, panel in self._panels_by_id.items():
            panel.set_reorder_callbacks(
                lambda pid=panel_id: self._move_panel(pid, -1),
                lambda pid=panel_id: self._move_panel(pid, 1),
            )

    def _rebuild_panel_layout(self) -> None:
        while self._panel_host_layout.count() > 0:
            it = self._panel_host_layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(self._panel_host_layout.parentWidget())
        for panel_id in self._panel_order_ids:
            panel = self._panels_by_id.get(panel_id)
            if panel is not None:
                self._panel_host_layout.addWidget(panel)
        self._panel_host_layout.addStretch(1)

    def _move_panel(self, panel_id: str, delta: int) -> None:
        if panel_id not in self._panel_order_ids:
            return
        idx = self._panel_order_ids.index(panel_id)
        new_idx = max(0, min(len(self._panel_order_ids) - 1, idx + delta))
        if new_idx == idx:
            return
        self._panel_order_ids.pop(idx)
        self._panel_order_ids.insert(new_idx, panel_id)
        self._rebuild_panel_layout()
        self._snapshot_current_mode_panel_state()
        cb = getattr(self.window(), "_save_settings", None)
        if callable(cb):
            cb()

    def _apply_mode_data(self) -> None:
        if self._applying_mode_data:
            return
        self._applying_mode_data = True
        try:
            tool = self.tool_manager.active_tool
            if tool is None:
                self._active_mode_key = None
                return
            if tool.id != "ui_boxes":
                if tool.id == "map":
                    self.display.setVisible(True)
                    self.display.show_sizes_cb.setVisible(True)
                    self.display.show_hatch_cb.setVisible(True)
                    self.display.point_size_label.setVisible(False)
                    self.display.point_size_value.setVisible(False)
                    self.display.point_size_slider.setVisible(False)
                    self.display.point_size_dec_btn.setVisible(False)
                    self.display.point_size_inc_btn.setVisible(False)
                    self.display.point_size_lock.setVisible(False)
                    self.display.point_grid_coords_label.setVisible(False)
                    self.display.point_axis_magnet_cb.setVisible(False)
                    self.preview.setVisible(False)
                    self.ocr_filters.setVisible(False)
                    self.point_type.setVisible(False)
                    self.point_settings.setVisible(False)
                    self.map_shape.setVisible(True)
                    self.map_component_settings.setVisible(True)
                    self.tool_settings.map_filter_combo.setVisible(True)
                    maps = load_map_presets()
                    presets = sorted(maps.keys())
                    self.presets.set_items(presets)
                    preset_name = self.presets.combo.currentText() or (presets[0] if presets else "")
                    sub_map = maps.get(preset_name, {})
                    subpresets = sorted(sub_map.keys())
                    self.subpresets.set_items(subpresets)
                    subpreset_name = self.subpresets.combo.currentText() or (subpresets[0] if subpresets else "")
                    comps = list(sub_map.get(subpreset_name, []))
                    comps = self._resolve_mode_components(tool.id, preset_name, subpreset_name, comps)
                    self.tool_settings.set_items([c.name for c in comps])
                    self.ui_boxes_runtime.set_components(comps)
                    self._apply_cached_history(tool.id, preset_name, subpreset_name)
                    self._active_mode_key = (str(tool.id), str(preset_name).strip(), str(subpreset_name).strip())
                    self._refresh_map_component_list()
                    self._sync_map_component_panels()
                    self._refresh_unsaved_status_for_current_selection()
                    return
                if tool.id not in {"controls", "spray"}:
                    self._apply_non_component_mode_ui()
                    return
                if tool.id == "spray":
                    self.display.setVisible(True)
                    self.display.show_sizes_cb.setVisible(False)
                    self.display.show_hatch_cb.setVisible(False)
                    self.display.show_sizes_cb.setChecked(False)
                    self.display.point_size_label.setVisible(True)
                    self.display.point_size_value.setVisible(True)
                    self.display.point_size_slider.setVisible(True)
                    self.display.point_size_dec_btn.setVisible(True)
                    self.display.point_size_inc_btn.setVisible(True)
                    self.display.point_size_lock.setVisible(True)
                    self.display.point_grid_coords_label.setVisible(False)
                    self.display.point_axis_magnet_cb.setVisible(False)
                    self.preview.setVisible(False)
                    self.ocr_filters.setVisible(False)
                    self.point_type.setVisible(False)
                    self.point_settings.setVisible(False)
                    self.map_shape.setVisible(False)
                    self.map_component_settings.setVisible(False)
                    self.tool_settings.map_filter_combo.setVisible(False)
                    spray = load_spray_presets()
                    presets = sorted(spray.keys())
                    self.presets.set_items(presets)
                    preset_name = self.presets.combo.currentText() or (presets[0] if presets else "")
                    sub_map = spray.get(preset_name, {})
                    subpresets = sorted(sub_map.keys())
                    self.subpresets.set_items(subpresets)
                    subpreset_name = self.subpresets.combo.currentText() or (subpresets[0] if subpresets else "")
                    raw_points = list(sub_map.get(subpreset_name, []))
                    comps = self._spray_to_canvas_components(raw_points)
                    comps = self._resolve_mode_components(tool.id, preset_name, subpreset_name, comps)
                    self.tool_settings.set_items([c.name for c in comps])
                    self.ui_boxes_runtime.set_components(comps)
                    self.canvas.capture.set_visible_component_indices(None)
                    self._apply_cached_history(tool.id, preset_name, subpreset_name)
                    self._active_mode_key = (str(tool.id), str(preset_name).strip(), str(subpreset_name).strip())
                    self._refresh_unsaved_status_for_current_selection()
                    return
                self.display.setVisible(True)
                self.display.show_sizes_cb.setVisible(False)
                self.display.show_hatch_cb.setVisible(False)
                self.display.show_sizes_cb.setChecked(False)
                self.display.point_size_label.setVisible(True)
                self.display.point_size_value.setVisible(True)
                self.display.point_size_slider.setVisible(True)
                self.display.point_size_dec_btn.setVisible(True)
                self.display.point_size_inc_btn.setVisible(True)
                self.display.point_size_lock.setVisible(True)
                self.display.point_grid_coords_label.setVisible(True)
                self.display.point_axis_magnet_cb.setVisible(True)
                self.preview.setVisible(False)
                self.ocr_filters.setVisible(False)
                self.point_type.setVisible(True)
                self.point_settings.setVisible(True)
                self.map_shape.setVisible(False)
                self.map_component_settings.setVisible(False)
                self.tool_settings.map_filter_combo.setVisible(False)
                controls = load_controls_presets()
                presets = sorted(controls.keys())
                self.presets.set_items(presets)
                preset_name = self.presets.combo.currentText() or (presets[0] if presets else "")
                sub_map = controls.get(preset_name, {})
                subpresets = sorted(sub_map.keys())
                self.subpresets.set_items(subpresets)
                subpreset_name = self.subpresets.combo.currentText() or (subpresets[0] if subpresets else "")
                comps = list(sub_map.get(subpreset_name, []))
                comps = self._resolve_mode_components(tool.id, preset_name, subpreset_name, comps)
                self.tool_settings.set_items([c.name for c in comps])
                self.ui_boxes_runtime.set_components(comps)
                self.canvas.capture.set_visible_component_indices(None)
                self._apply_cached_history(tool.id, preset_name, subpreset_name)
                self._active_mode_key = (str(tool.id), str(preset_name).strip(), str(subpreset_name).strip())
                self._refresh_unsaved_status_for_current_selection()
                return
            self.display.setVisible(True)
            self.display.show_sizes_cb.setVisible(True)
            self.display.show_hatch_cb.setVisible(False)
            self.display.point_size_label.setVisible(False)
            self.display.point_size_value.setVisible(False)
            self.display.point_size_slider.setVisible(False)
            self.display.point_size_dec_btn.setVisible(False)
            self.display.point_size_inc_btn.setVisible(False)
            self.display.point_size_lock.setVisible(False)
            self.display.point_grid_coords_label.setVisible(False)
            self.display.point_axis_magnet_cb.setVisible(False)
            self.preview.setVisible(True)
            # Keep preview panel recoverable in UI Boxes even if a stale mode
            # state or previous mode left it collapsed/hidden.
            self.preview.set_collapsed(False)
            if not self.preview.toggle_btn.isChecked():
                self.preview.toggle_btn.setChecked(True)
            self.ocr_filters.setVisible(True)
            self.point_type.setVisible(False)
            self.point_settings.setVisible(False)
            self.map_shape.setVisible(False)
            self.map_component_settings.setVisible(False)
            self.tool_settings.map_filter_combo.setVisible(False)
            apply_ui_boxes_mode(self)
            self.canvas.capture.set_visible_component_indices(None)
            preset_name = self.presets.combo.currentText().strip()
            subpreset_name = self.subpresets.combo.currentText().strip()
            self._apply_cached_history("ui_boxes", preset_name, subpreset_name)
            self._active_mode_key = ("ui_boxes", str(preset_name).strip(), str(subpreset_name).strip())
            self._refresh_unsaved_status_for_current_selection()
        finally:
            self._applying_mode_data = False

    def _apply_non_component_mode_ui(self) -> None:
        self.presets.set_items([])
        self.subpresets.set_items([])
        self.tool_settings.set_items([])
        self.ui_boxes_runtime.set_components([])
        self.canvas.capture.set_visible_component_indices(None)
        self.display.setVisible(False)
        self.preview.setVisible(False)
        self.ocr_filters.setVisible(False)
        self.point_type.setVisible(False)
        self.point_settings.setVisible(False)
        self.map_shape.setVisible(False)
        self.map_component_settings.setVisible(False)
        self.tool_settings.map_filter_combo.setVisible(False)
        self._active_mode_key = None

    def _spray_to_canvas_components(self, points: list[object]) -> list[object]:
        ix, iy, iw, ih = self.canvas.capture._inner_rect()
        w = max(1.0, float(iw))
        h = max(1.0, float(ih))
        out: list[object] = []
        for i, p in enumerate(points):
            dx = float(getattr(p, "x", 0.0))
            dy = float(getattr(p, "y", 0.0))
            c = type("SprayPoint", (), {})()
            c.name = str(getattr(p, "name", f"spray_{i + 1:02d}"))
            c.x = max(0.0, min(1.0, 0.5 + (dx / w)))
            c.y = max(0.0, min(1.0, 0.5 + (dy / h)))
            c.w = 0.02
            c.h = 0.02
            c.point_type = "spray"
            out.append(c)
        return out

    def _canvas_components_to_spray(self, points: list[object]) -> list[object]:
        ix, iy, iw, ih = self.canvas.capture._inner_rect()
        w = max(1.0, float(iw))
        h = max(1.0, float(ih))
        out: list[object] = []
        for i, p in enumerate(points):
            nx = float(getattr(p, "x", 0.5))
            ny = float(getattr(p, "y", 0.5))
            c = type("SprayPointRaw", (), {})()
            c.name = str(getattr(p, "name", f"spray_{i + 1:02d}"))
            c.x = int(round((nx - 0.5) * w))
            c.y = int(round((ny - 0.5) * h))
            out.append(c)
        return out

    def _apply_display_options(self, *_args) -> None:
        tool = self.tool_manager.active_tool
        axis_magnet_enabled = self.display.point_axis_magnet_cb.isChecked()
        if tool is not None and tool.id == "spray":
            axis_magnet_enabled = False
        self.canvas.capture.set_component_display_options(
            show_overlay=self.display.show_overlay_cb.isChecked(),
            show_labels=self.display.show_labels_cb.isChecked(),
            show_sizes=self.display.show_sizes_cb.isChecked(),
            point_size=self.display.point_size_slider.value(),
            point_axis_magnet=axis_magnet_enabled,
            show_hatch=self.display.show_hatch_cb.isChecked(),
        )

    def _on_display_changed(self, *_args) -> None:
        if self._applying_mode_data:
            return
        self._apply_display_options()
        self._snapshot_current_mode_panel_state()
        wnd = self.window()
        # Hard-persist display and mode states immediately to avoid event-order loss.
        settings_obj = getattr(wnd, "settings", None)
        if settings_obj is not None and hasattr(settings_obj, "load") and hasattr(settings_obj, "save"):
            try:
                data = settings_obj.load() or {}
                if not isinstance(data, dict):
                    data = {}
                ws = data.get("workspace", {})
                if not isinstance(ws, dict):
                    ws = {}
                ws["mode_states"] = self._mode_states
                data["workspace"] = ws
                settings_obj.save(data)
            except Exception:
                pass
        cb = getattr(wnd, "_save_settings", None)
        if callable(cb):
            cb()

    def _update_preview(self, *_args) -> None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id != "ui_boxes":
            self.preview.preview_label.setText("No Preview")
            self.preview.preview_label.setPixmap(QPixmap())
            return
        if not self.preview.toggle_btn.isChecked():
            self.preview.preview_label.setText("Preview Hidden")
            self.preview.preview_label.setPixmap(QPixmap())
            return
        if not self.preview.preview_label.isVisible():
            return

        pix = self.canvas.capture.get_captured_pixmap()
        comps = self.ui_boxes_runtime.get_components() or []
        row = self.tool_settings.component_list.currentRow()
        if row < 0:
            row = self.canvas.capture.get_selected_component_index()
        if pix is None or pix.isNull():
            if hasattr(self.preview, "set_preview_aspect_ratio"):
                self.preview.set_preview_aspect_ratio(None)
            self._set_preview_placeholder("No broadcast window", black_bg=True)
            return
        if row < 0 or row >= len(comps):
            if hasattr(self.preview, "set_preview_aspect_ratio"):
                self.preview.set_preview_aspect_ratio(None)
            self._set_preview_placeholder("Box is not selected", black_bg=True)
            return

        c = comps[row]
        pw, ph = pix.width(), pix.height()
        x = max(0, min(pw - 1, int(c.x * pw)))
        y = max(0, min(ph - 1, int(c.y * ph)))
        w = max(1, min(pw - x, int(c.w * pw)))
        h = max(1, min(ph - y, int(c.h * ph)))
        if hasattr(self.preview, "set_preview_aspect_ratio"):
            self.preview.set_preview_aspect_ratio(max(1e-9, float(w) / max(1e-9, float(h))))
        if hasattr(self.preview, "_sync_preview_geometry"):
            self.preview._sync_preview_geometry()
        crop = pix.copy(x, y, w, h)
        if self.preview.postprocess_btn.isChecked():
            img = crop.toImage().convertToFormat(QImage.Format.Format_Grayscale8 if hasattr(QImage, "Format") else QImage.Format_Grayscale8)
            crop = QPixmap.fromImage(img)

        target_size = self.preview.preview_label.contentsRect().size()
        target_w = max(80, target_size.width())
        target_h = max(80, target_size.height())
        if target_w <= 1 or target_h <= 1:
            return
        # Do not distort/crop the image itself; preview widget geometry handles fit.
        scaled = crop.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.preview_label.setPixmap(scaled)
        self.preview.preview_label.setText("")

    def _set_preview_placeholder(self, text: str, black_bg: bool) -> None:
        if black_bg:
            w = max(120, self.preview.preview_label.width() - 8)
            h = max(120, self.preview.preview_label.height() - 8)
            pm = QPixmap(w, h)
            pm.fill(QColor(0, 0, 0))
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setPen(QColor(235, 235, 235))
            painter.drawText(pm.rect(), int(Qt.AlignmentFlag.AlignCenter), text)
            painter.end()
            self.preview.preview_label.setPixmap(pm)
            self.preview.preview_label.setText("")
            return
        self.preview.preview_label.setText(text)
        self.preview.preview_label.setPixmap(QPixmap())

    def _sync_preview_ui_state(self) -> None:
        visible = self.preview.toggle_btn.isChecked()
        self.preview.toggle_btn.setText("Hide Preview" if visible else "Show Preview")
        self.preview.postprocess_btn.setText(
            "Show Original" if self.preview.postprocess_btn.isChecked() else "Show Postprocess"
        )
        self.preview.preview_label.setVisible(visible)
        self.preview.postprocess_btn.setEnabled(visible)
        if hasattr(self.preview, "_sync_preview_geometry"):
            self.preview._sync_preview_geometry()
        self.preview.layout().invalidate()
        self.preview.updateGeometry()
        QTimer.singleShot(0, self.preview.updateGeometry)
        self._snapshot_current_mode_panel_state()
        cb = getattr(self.window(), "_save_settings", None)
        if callable(cb):
            cb()
        refresh_capture = getattr(self.window(), "_update_capture_frame", None)
        if callable(refresh_capture):
            refresh_capture()
        self._update_preview()

    def has_unsaved_changes(self) -> bool:
        return bool(self._has_unsaved_changes)

    def _current_preset_key(self) -> tuple[str, str, str] | None:
        tool = self.tool_manager.active_tool
        if tool is None:
            return None
        if tool.id not in self._COMPONENT_TOOL_IDS:
            return None
        preset_name = self.presets.combo.currentText().strip()
        subpreset_name = self.subpresets.combo.currentText().strip()
        if not preset_name or not subpreset_name:
            return None
        return (str(tool.id), preset_name, subpreset_name)

    def _refresh_unsaved_status_for_current_selection(self) -> None:
        key = self._current_preset_key()
        dirty = self._unsaved_by_key.get(key, False) if key is not None else False
        self._set_unsaved_changes(dirty)

    def _set_unsaved_changes(self, dirty: bool) -> None:
        self._has_unsaved_changes = bool(dirty)
        key = self._current_preset_key()
        if key is not None:
            self._unsaved_by_key[key] = self._has_unsaved_changes
        bar = getattr(self.window(), "statusBar", None)
        sb = bar() if callable(bar) else None
        if sb is not None and hasattr(sb, "set_preset_saved_state"):
            sb.set_preset_saved_state(not self._has_unsaved_changes)

    def _load_ocr_from_selected(self) -> None:
        comps = self.ui_boxes_runtime.get_components() or []
        row = self.tool_settings.component_list.currentRow()
        if row < 0:
            row = self.canvas.capture.get_selected_component_index()
        if row < 0 or row >= len(comps):
            self.ocr_filters.apply_state({})
            return
        c = comps[row]
        f = str(getattr(c, "ocr_filter", "none")).lower()
        filt_label = {"none": "None", "number": "Numbers", "numbers": "Numbers", "letters": "Letters", "color": "Color"}.get(f, "None")
        lang = str(getattr(c, "ocr_letters_lang", "ru+en")).lower()
        lang_label = {"ru": "RU", "en": "EN", "ru+en": "RU+EN"}.get(lang, "RU+EN")
        self.ocr_filters.apply_state(
            {
                "filter": filt_label,
                "max_value": "" if getattr(c, "ocr_max_value", None) is None else str(getattr(c, "ocr_max_value", "")),
                "lang": lang_label,
                "postprocess": bool(getattr(c, "ocr_postprocess", False)),
            }
        )

    def _apply_ocr_to_selected(self) -> None:
        comps = self.ui_boxes_runtime.get_components() or []
        row = self.tool_settings.component_list.currentRow()
        if row < 0:
            row = self.canvas.capture.get_selected_component_index()
        if row < 0 or row >= len(comps):
            return
        c = comps[row]
        filt = self.ocr_filters.filter_combo.currentText()
        c.ocr_filter = {"None": "none", "Numbers": "number", "Letters": "letters", "Color": "color"}.get(filt, "none")
        text = self.ocr_filters.max_value_edit.text().strip()
        c.ocr_max_value = int(text) if text.isdigit() else None
        c.ocr_letters_lang = {"RU": "ru", "EN": "en", "RU+EN": "ru+en"}.get(self.ocr_filters.lang_combo.currentText(), "ru+en")
        c.ocr_postprocess = bool(self.ocr_filters.postprocess_cb.isChecked())
        self.canvas.capture.update()
        self._set_unsaved_changes(True)

    def _sync_map_component_panels(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id != "map":
            self.canvas.capture.set_visible_component_indices(None)
            return
        comps = self.ui_boxes_runtime.get_components() or []
        row = self.tool_settings.component_list.currentRow()
        if 0 <= row < len(self._map_visible_indices):
            row = self._map_visible_indices[row]
        if row < 0:
            row = self.canvas.capture.get_selected_component_index()
        if row < 0 or row >= len(comps):
            return
        c = comps[row]
        shape = str(getattr(c, "shape_type", "polygon")).lower()
        self.map_shape._set_active(shape if shape in {"polygon", "box", "circle"} else "polygon")
        zt = str(getattr(c, "zone_type", "blocked")).lower()
        idx = self.map_component_settings.zone_type_combo.findText(zt)
        if idx >= 0:
            self.map_component_settings.zone_type_combo.setCurrentIndex(idx)
        self.map_component_settings.closed_cb.setChecked(bool(getattr(c, "polygon_closed", True)))

    def _apply_map_component_settings(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id != "map":
            return
        comps = self.ui_boxes_runtime.get_components() or []
        row = self.tool_settings.component_list.currentRow()
        if 0 <= row < len(self._map_visible_indices):
            row = self._map_visible_indices[row]
        if row < 0:
            row = self.canvas.capture.get_selected_component_index()
        if row < 0 or row >= len(comps):
            return
        c = comps[row]
        c.zone_type = self.map_component_settings.zone_type_combo.currentText().strip().lower()
        c.polygon_closed = bool(self.map_component_settings.closed_cb.isChecked())
        self.canvas.capture.update()
        self._set_unsaved_changes(True)

    def get_state(self) -> dict:
        self._snapshot_current_mode_panel_state()
        return {
            "mode_states": self._mode_states,
            "grid": self.grid.get_state(),
        }

    def apply_state(self, state: dict) -> None:
        mode_states = state.get("mode_states", {})
        self._mode_states = dict(mode_states) if isinstance(mode_states, dict) else {}
        # Global grid state shared across all markup modes.
        global_grid = state.get("grid", {})
        if isinstance(global_grid, dict) and global_grid:
            self.grid.apply_state(global_grid)
        else:
            # Backward compatibility: migrate grid from any legacy per-mode state.
            migrated_grid = None
            if isinstance(self._mode_states, dict):
                for mode_key in ("ui_boxes", "controls"):
                    mode_state = self._mode_states.get(mode_key, {})
                    if isinstance(mode_state, dict):
                        candidate = mode_state.get("grid", {})
                        if isinstance(candidate, dict) and candidate:
                            migrated_grid = candidate
                            break
                if migrated_grid is None:
                    for mode_state in self._mode_states.values():
                        if isinstance(mode_state, dict):
                            candidate = mode_state.get("grid", {})
                            if isinstance(candidate, dict) and candidate:
                                migrated_grid = candidate
                                break
            if migrated_grid is not None:
                self.grid.apply_state(migrated_grid)
        self._apply_current_mode_panel_state()

    def _wire_autosave(self) -> None:
        def persist_now() -> None:
            wnd = self.window()
            settings_obj = getattr(wnd, "settings", None)
            if settings_obj is not None and hasattr(settings_obj, "load") and hasattr(settings_obj, "save"):
                try:
                    data = settings_obj.load() or {}
                    if not isinstance(data, dict):
                        data = {}
                    ws = data.get("workspace", {})
                    if not isinstance(ws, dict):
                        ws = {}
                    ws["mode_states"] = self._mode_states
                    data["workspace"] = ws
                    settings_obj.save(data)
                except Exception:
                    pass

        def trigger_save() -> None:
            if self._applying_mode_data:
                return
            self._snapshot_current_mode_panel_state()
            persist_now()
            cb = getattr(self.window(), "_save_settings", None)
            if callable(cb):
                cb()

        self.presets.combo.currentIndexChanged.connect(lambda *_: trigger_save())
        self.subpresets.combo.currentIndexChanged.connect(lambda *_: trigger_save())
        self.grid.enabled_cb.toggled.connect(lambda *_: trigger_save())
        self.grid.magnet_cb.toggled.connect(lambda *_: trigger_save())
        self.grid.border_cb.toggled.connect(lambda *_: trigger_save())
        self.grid.cols_lock.clicked.connect(lambda *_: trigger_save())
        self.grid.cols_slider.valueChanged.connect(lambda *_: trigger_save())
        self.grid.width_spin.valueChanged.connect(lambda *_: trigger_save())
        self.grid.left_edit.editingFinished.connect(trigger_save)
        self.grid.top_edit.editingFinished.connect(trigger_save)
        self.grid.right_edit.editingFinished.connect(trigger_save)
        self.grid.bottom_edit.editingFinished.connect(trigger_save)
        self.grid.left_lock.clicked.connect(lambda *_: trigger_save())
        self.grid.top_lock.clicked.connect(lambda *_: trigger_save())
        self.grid.right_lock.clicked.connect(lambda *_: trigger_save())
        self.grid.bottom_lock.clicked.connect(lambda *_: trigger_save())
        self.grid.width_lock.clicked.connect(lambda *_: trigger_save())
        self.display.show_overlay_cb.toggled.connect(lambda *_: trigger_save())
        self.display.show_labels_cb.toggled.connect(lambda *_: trigger_save())
        self.display.show_sizes_cb.toggled.connect(lambda *_: trigger_save())
        self.display.show_hatch_cb.toggled.connect(lambda *_: trigger_save())
        self.display.point_size_slider.valueChanged.connect(lambda *_: trigger_save())
        self.display.point_size_lock.clicked.connect(lambda *_: trigger_save())
        self.display.point_axis_magnet_cb.toggled.connect(lambda *_: trigger_save())
        self.preview.toggle_btn.toggled.connect(lambda *_: trigger_save())
        self.preview.postprocess_btn.toggled.connect(lambda *_: trigger_save())
        self.ocr_filters.filter_combo.currentIndexChanged.connect(lambda *_: trigger_save())
        self.ocr_filters.lang_combo.currentIndexChanged.connect(lambda *_: trigger_save())
        self.ocr_filters.max_value_edit.editingFinished.connect(trigger_save)
        self.ocr_filters.postprocess_cb.toggled.connect(lambda *_: trigger_save())
        for panel in self._panels_by_id.values():
            panel.collapse_btn.clicked.connect(lambda *_: trigger_save())

    def _wire_panel_actions(self) -> None:
        self.presets.new_btn.clicked.connect(self._new_preset)
        self.presets.rename_btn.clicked.connect(self._rename_preset)
        self.presets.delete_btn.clicked.connect(self._delete_preset)
        self.subpresets.new_btn.clicked.connect(self._new_subpreset)
        self.subpresets.rename_btn.clicked.connect(self._rename_subpreset)
        self.subpresets.delete_btn.clicked.connect(self._delete_subpreset)
        self.tool_settings.add_btn.clicked.connect(self._add_component)
        self.tool_settings.rename_btn.clicked.connect(self._rename_component)
        self.tool_settings.delete_btn.clicked.connect(self._delete_component)
        self._update_actions_enabled()

    def _update_actions_enabled(self) -> None:
        tool = self.tool_manager.active_tool
        editable = bool(tool is not None and tool.id in self._COMPONENT_TOOL_IDS)
        for btn in (
            self.presets.new_btn, self.presets.rename_btn, self.presets.delete_btn,
            self.subpresets.new_btn, self.subpresets.rename_btn, self.subpresets.delete_btn,
            self.tool_settings.add_btn, self.tool_settings.rename_btn, self.tool_settings.delete_btn,
        ):
            btn.setEnabled(editable)

    def _require_editable_mode(self) -> bool:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id not in self._COMPONENT_TOOL_IDS:
            QMessageBox.information(self, "Unavailable", "Actions are available only in UI Boxes and Controls modes.")
            return False
        return True

    def _new_preset(self) -> None:
        if not self._require_editable_mode():
            return
        name, ok = QInputDialog.getText(self, "New Preset", "Preset name:", text="new_preset")
        name = name.strip()
        if not ok or not name:
            return
        if self.presets.combo.findText(name) >= 0:
            return
        upsert_interface(name)
        self._apply_mode_data()
        self.presets.combo.setCurrentText(name)
        # New preset -> clean canvas (empty default subpreset)
        create_subpreset(name, "default", [])
        self._apply_mode_data()
        self._set_unsaved_changes(False)

    def _rename_preset(self) -> None:
        if not self._require_editable_mode():
            return
        idx = self.presets.combo.currentIndex()
        if idx < 0:
            return
        cur = self.presets.combo.currentText()
        name, ok = QInputDialog.getText(self, "Rename Preset", "Preset name:", text=cur)
        name = name.strip()
        if not ok or not name:
            return
        if rename_interface(cur, name):
            self._apply_mode_data()
            self.presets.combo.setCurrentText(name)
            self._set_unsaved_changes(False)

    def _delete_preset(self) -> None:
        if not self._require_editable_mode():
            return
        cur = self.presets.combo.currentText().strip()
        if not cur:
            return
        if delete_interface(cur):
            self._apply_mode_data()
            self._set_unsaved_changes(False)
            self._snapshot_current_mode_panel_state()
            cb = getattr(self.window(), "_save_settings", None)
            if callable(cb):
                cb()

    def _new_subpreset(self) -> None:
        if not self._require_editable_mode():
            return
        name, ok = QInputDialog.getText(self, "New Sub Preset", "Sub preset name:", text="new_subpreset")
        name = name.strip()
        if not ok or not name:
            return
        if self.subpresets.combo.findText(name) >= 0:
            return
        iface = self.presets.combo.currentText().strip()
        current_comps = list(self.ui_boxes_runtime.get_components() or [])
        # New subpreset -> copy current markup.
        create_subpreset(iface, name, current_comps)
        self._apply_mode_data()
        self.subpresets.combo.setCurrentText(name)
        self._set_unsaved_changes(False)

    def _rename_subpreset(self) -> None:
        if not self._require_editable_mode():
            return
        idx = self.subpresets.combo.currentIndex()
        if idx < 0:
            return
        cur = self.subpresets.combo.currentText()
        name, ok = QInputDialog.getText(self, "Rename Sub Preset", "Sub preset name:", text=cur)
        name = name.strip()
        if not ok or not name:
            return
        iface = self.presets.combo.currentText().strip()
        if rename_subpreset(iface, cur, name):
            self._apply_mode_data()
            self.subpresets.combo.setCurrentText(name)
            self._set_unsaved_changes(False)

    def _delete_subpreset(self) -> None:
        if not self._require_editable_mode():
            return
        iface = self.presets.combo.currentText().strip()
        sub = self.subpresets.combo.currentText().strip()
        if not iface or not sub:
            return
        if delete_subpreset(iface, sub):
            self._apply_mode_data()
            self._set_unsaved_changes(False)
            self._snapshot_current_mode_panel_state()
            cb = getattr(self.window(), "_save_settings", None)
            if callable(cb):
                cb()

    def _add_component(self) -> None:
        if not self._require_editable_mode():
            return
        name, ok = QInputDialog.getText(self, "Add Component", "Component name:", text="new_item")
        name = name.strip()
        if not ok or not name:
            return
        if self.tool_manager.active_tool and self.tool_manager.active_tool.id == "controls":
            self.ui_boxes_runtime.add_component(name)
            comps = self.ui_boxes_runtime.get_components()
            if comps:
                c = comps[-1]
                c.w = 0.02
                c.h = 0.02
                c.point_type = self.point_type.selected_type()
                self.canvas.capture.update()
            return
        self.ui_boxes_runtime.add_component(name)

    def _on_canvas_empty_click(self, button: str, px: int, py: int) -> None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id not in self._COMPONENT_TOOL_IDS:
            return
        if button == "left":
            self.canvas.capture.clear_selected_component()
            return
        if button != "right":
            return

        name, ok = QInputDialog.getText(self, "Create Component", "Component name:", text="new_item")
        name = name.strip()
        if not ok or not name:
            return

        self.ui_boxes_runtime.add_component(name)
        comps = self.ui_boxes_runtime.get_components() or []
        if not comps:
            return
        c = comps[-1]
        ix, iy, iw, ih = self.canvas.capture._inner_rect()
        nx = max(0.0, min(1.0, (float(px) - float(ix)) / max(1.0, float(iw))))
        ny = max(0.0, min(1.0, (float(py) - float(iy)) / max(1.0, float(ih))))

        if tool.id == "map":
            shape = self.map_shape.selected_shape()
            c.shape_type = str(shape)
            c.zone_type = "blocked"
            c.polygon_closed = True
            if shape == "circle":
                c.x = nx
                c.y = ny
                c.w = 0.02
                c.h = 0.02
                c.point_type = "click"
                c.polygon_points = []
            elif shape == "box":
                box_w = 0.08
                box_h = 0.06
                c.x = max(0.0, min(1.0 - box_w, nx - box_w * 0.5))
                c.y = max(0.0, min(1.0 - box_h, ny - box_h * 0.5))
                c.w = box_w
                c.h = box_h
                c.point_type = ""
                c.polygon_points = [[c.x, c.y], [c.x + c.w, c.y], [c.x + c.w, c.y + c.h], [c.x, c.y + c.h]]
            else:
                # Default polygon seed around click; user can refine in map editor later.
                r = 0.04
                c.x = max(0.0, min(1.0, nx))
                c.y = max(0.0, min(1.0, ny))
                c.w = 0.08
                c.h = 0.08
                c.point_type = ""
                c.polygon_points = [
                    [max(0.0, min(1.0, nx - r)), max(0.0, min(1.0, ny - r))],
                    [max(0.0, min(1.0, nx + r)), max(0.0, min(1.0, ny - r))],
                    [max(0.0, min(1.0, nx + r)), max(0.0, min(1.0, ny + r))],
                    [max(0.0, min(1.0, nx - r)), max(0.0, min(1.0, ny + r))],
                ]
        elif tool.id == "controls":
            c.x = nx
            c.y = ny
            c.w = 0.02
            c.h = 0.02
            c.point_type = self.point_type.selected_type()
        elif tool.id == "spray":
            c.x = nx
            c.y = ny
            c.w = 0.02
            c.h = 0.02
            c.point_type = "spray"
        else:
            c.w = max(0.02, min(0.4, float(getattr(c, "w", 0.2))))
            c.h = max(0.02, min(0.4, float(getattr(c, "h", 0.15))))
            c.x = max(0.0, min(1.0 - c.w, nx - c.w * 0.5))
            c.y = max(0.0, min(1.0 - c.h, ny - c.h * 0.5))

        self.canvas.capture._emit_components_changed()
        self.canvas.capture.update()

    def _rename_component(self) -> None:
        if not self._require_editable_mode():
            return
        row = self.tool_settings.component_list.currentRow()
        tool = self.tool_manager.active_tool
        if tool is not None and tool.id == "map" and 0 <= row < len(self._map_visible_indices):
            row = self._map_visible_indices[row]
        if row < 0:
            return
        item = self.tool_settings.component_list.item(row)
        cur = item.text() if item is not None else ""
        name, ok = QInputDialog.getText(self, "Rename Component", "Component name:", text=cur)
        name = name.strip()
        if not ok or not name or item is None:
            return
        self.ui_boxes_runtime.rename_component(row, name)

    def _delete_component(self) -> None:
        if not self._require_editable_mode():
            return
        row = self.tool_settings.component_list.currentRow()
        tool = self.tool_manager.active_tool
        if tool is not None and tool.id == "map" and 0 <= row < len(self._map_visible_indices):
            row = self._map_visible_indices[row]
        if row >= 0:
            self.ui_boxes_runtime.remove_component(row)

    def _on_canvas_components_changed(self, components, selected_index: int) -> None:
        tool = self.tool_manager.active_tool
        if tool is not None and tool.id == "map":
            self._refresh_map_component_list()
        else:
            self._map_visible_indices = []
            names = [c.name for c in components]
            self.tool_settings.set_items(names)
            if 0 <= selected_index < self.tool_settings.component_list.count():
                self.tool_settings.component_list.setCurrentRow(selected_index)
        self._update_controls_point_grid_coords(components, selected_index)
        self._update_preview()
        if not self._applying_mode_data:
            self._set_unsaved_changes(True)

    def _update_controls_point_grid_coords(self, components, selected_index: int) -> None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id != "controls":
            return
        if selected_index < 0 or selected_index >= len(components):
            self.display.set_point_grid_coords_text("-")
            return
        comp = components[selected_index]
        if not str(getattr(comp, "point_type", "")):
            self.display.set_point_grid_coords_text("-")
            return
        cols = max(2, int(getattr(self.canvas.grid_settings, "columns", 24)))
        ix, iy, iw, ih = self.canvas.capture._inner_rect()
        # Keep same visual block size as grid draw: step from columns and inner width.
        step_px = max(1.0, float(iw) / float(cols))
        row_step_n = step_px / max(1.0, float(ih))
        gx = float(getattr(comp, "x", 0.0)) / max(1e-9, 1.0 / float(cols))
        gy = float(getattr(comp, "y", 0.0)) / max(1e-9, row_step_n)
        self.display.set_point_grid_coords_text(f"X={gx:.2f}, Y={gy:.2f} blocks")

    def _save_current_mode_markup(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None:
            return
        if tool.id == "ui_boxes":
            if save_ui_boxes_mode(self):
                QMessageBox.information(self, "Saved", "UI Boxes markup saved.")
                self._apply_mode_data()
                self._set_unsaved_changes(False)
                self._drop_cached_markup_for_current_key()
        elif tool.id == "controls":
            interface_name = self.presets.combo.currentText().strip()
            preset_name = self.subpresets.combo.currentText().strip()
            if interface_name and preset_name:
                save_controls_points(interface_name, preset_name, list(self.ui_boxes_runtime.get_components() or []))
                QMessageBox.information(self, "Saved", "Controls points saved.")
                self._apply_mode_data()
                self._set_unsaved_changes(False)
                self._drop_cached_markup_for_current_key()
        elif tool.id == "spray":
            weapon_id = self.presets.combo.currentText().strip()
            pattern_key = self.subpresets.combo.currentText().strip()
            if weapon_id and pattern_key:
                comps = list(self.ui_boxes_runtime.get_components() or [])
                raw_points = self._canvas_components_to_spray(comps)
                if save_spray_pattern(weapon_id, pattern_key, raw_points):
                    QMessageBox.information(self, "Saved", "Spray pattern saved.")
                    self._apply_mode_data()
                    self._set_unsaved_changes(False)
                    self._drop_cached_markup_for_current_key()
        elif tool.id == "map":
            preset_name = self.presets.combo.currentText().strip()
            subpreset_name = self.subpresets.combo.currentText().strip()
            if preset_name and subpreset_name:
                comps = list(self.ui_boxes_runtime.get_components() or [])
                ix, iy, iw, ih = self.canvas.capture._inner_rect()
                if save_map_preset(preset_name, subpreset_name, comps, (int(iw), int(ih))):
                    QMessageBox.information(self, "Saved", "Map markup saved.")
                    self._apply_mode_data()
                    self._set_unsaved_changes(False)
                    self._drop_cached_markup_for_current_key()
        cb = getattr(self.window(), "_save_settings", None)
        if callable(cb):
            cb()

    def _reset_current_mode_markup(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None:
            return
        mode_key = self._current_mode_data_key()
        if mode_key is None:
            return
        self._mode_markup_cache.pop(mode_key, None)
        self._unsaved_by_key[mode_key] = False
        if tool.id == "ui_boxes":
            if reset_ui_boxes_mode(self):
                QMessageBox.information(self, "Reset", "UI Boxes markup restored from last save.")
        else:
            self._apply_mode_data()
            QMessageBox.information(self, "Reset", f"{tool.display_name} markup restored from last saved data.")
        self._set_unsaved_changes(False)

    def _undo_current_mode_markup(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id not in self._COMPONENT_TOOL_IDS:
            return
        self.ui_boxes_runtime.undo()

    def _redo_current_mode_markup(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id not in self._COMPONENT_TOOL_IDS:
            return
        self.ui_boxes_runtime.redo()

    def _current_mode_data_key(self) -> tuple[str, str, str] | None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id not in self._COMPONENT_TOOL_IDS:
            return None
        return (
            str(tool.id),
            str(self.presets.combo.currentText() or "").strip(),
            str(self.subpresets.combo.currentText() or "").strip(),
        )

    def _snapshot_current_mode_markup_state(self) -> None:
        key = self._active_mode_key
        if key is None:
            return
        components = list(self.ui_boxes_runtime.get_components() or [])
        self._mode_markup_cache[key] = {
            "components": components,
            "history": self.canvas.capture.get_history_state(),
        }

    def _resolve_mode_components(self, tool_id: str, preset_name: str, subpreset_name: str, default_components: list[object]) -> list[object]:
        key = (str(tool_id), str(preset_name).strip(), str(subpreset_name).strip())
        cached = self._mode_markup_cache.get(key)
        if isinstance(cached, dict):
            comps = cached.get("components")
            if isinstance(comps, list):
                return list(comps)
        return default_components

    def _apply_cached_history(self, tool_id: str, preset_name: str, subpreset_name: str) -> None:
        key = (str(tool_id), str(preset_name).strip(), str(subpreset_name).strip())
        cached = self._mode_markup_cache.get(key)
        if isinstance(cached, dict):
            self.canvas.capture.set_history_state(cached.get("history"))
        else:
            self.canvas.capture.set_history_state(None)

    def _drop_cached_markup_for_current_key(self) -> None:
        key = self._current_mode_data_key()
        if key is not None:
            self._mode_markup_cache.pop(key, None)

    def _snapshot_current_mode_panel_state(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None:
            return
        # Persist UI preferences for every markup mode.
        # Keep settings merged so autosave of one widget does not erase other keys.
        prev = self._mode_states.get(tool.id, {})
        state = dict(prev) if isinstance(prev, dict) else {}
        state.update({
            "presets": self.presets.get_state(),
            "subpresets": self.subpresets.get_state(),
            "panel_order": list(self._panel_order_ids),
            "panel_collapsed": {pid: self._panels_by_id[pid].is_collapsed() for pid in self._panel_order_ids if pid in self._panels_by_id},
        })
        if tool.id in self._COMPONENT_TOOL_IDS:
            state["display"] = self.display.get_state()
        if tool.id == "ui_boxes":
            state["preview"] = self.preview.get_state()
            state["ocr_filters"] = self.ocr_filters.get_state()
        self._mode_states[tool.id] = state

    def _apply_current_mode_panel_state(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None:
            return
        mode_state = self._mode_states.get(tool.id, {})
        if not isinstance(mode_state, dict):
            return
        self.presets.apply_state(mode_state.get("presets", {}))
        self.subpresets.apply_state(mode_state.get("subpresets", {}))
        if tool.id in self._COMPONENT_TOOL_IDS:
            self.display.apply_state(mode_state.get("display", {}))
        if tool.id == "ui_boxes":
            self.preview.apply_state(mode_state.get("preview", {}))
            self.ocr_filters.apply_state(mode_state.get("ocr_filters", {}))
        order = mode_state.get("panel_order", [])
        if isinstance(order, list):
            valid = [pid for pid in order if pid in self._panels_by_id]
            missing = [pid for pid in self._panel_order_ids if pid not in valid]
            self._panel_order_ids = valid + missing
            self._rebuild_panel_layout()
        collapsed = mode_state.get("panel_collapsed", {})
        if isinstance(collapsed, dict):
            for pid, is_col in collapsed.items():
                panel = self._panels_by_id.get(str(pid))
                if panel is not None:
                    panel.set_collapsed(bool(is_col))
        self._sync_preview_ui_state()
    def _refresh_map_component_list(self) -> None:
        tool = self.tool_manager.active_tool
        if tool is None or tool.id != "map":
            return
        comps = self.ui_boxes_runtime.get_components() or []
        selected_idx = self.canvas.capture.get_selected_component_index()
        filter_mode = str(self.tool_settings.map_filter_combo.currentText() or "all types").strip().lower()
        zone_order = {"blocked": 0, "walkable": 1, "plant": 2, "zone callouts": 3, "jump spot": 4, "boost zone": 5}
        ordered = sorted(
            list(enumerate(comps)),
            key=lambda pair: (
                zone_order.get(str(getattr(pair[1], "zone_type", "blocked")).strip().lower(), 99),
                str(getattr(pair[1], "name", "")).strip().lower(),
            ),
        )
        visible = []
        names = []
        for idx, c in ordered:
            zt = str(getattr(c, "zone_type", "blocked")).strip().lower() or "blocked"
            if filter_mode != "all types" and zt != filter_mode:
                continue
            visible.append(idx)
            names.append(f"[{zt}] {str(getattr(c, 'name', ''))}")
        self._map_visible_indices = visible
        self.canvas.capture.set_visible_component_indices(visible)
        self.tool_settings.set_items(names)
        if selected_idx in visible:
            self.tool_settings.component_list.setCurrentRow(visible.index(selected_idx))
