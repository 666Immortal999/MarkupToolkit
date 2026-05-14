from __future__ import annotations
import copy

from qt import QColor, QFrame, QInputDialog, QMenu, QPainter, QPen, Qt, QPoint


class CaptureView(QFrame):
    PADDING = 20
    EMPTY_CLICK_NEAR_PAD = 10

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("CaptureView")
        self._aspect_ratio: float | None = None
        self.capture_rect: tuple[int, int, int, int] = (0, 0, 0, 0)
        self._captured_pixmap = None
        self._grid = None
        self._drag_edge: str | None = None
        self._view_zoom = 1.0
        self._pan_x = 0
        self._pan_y = 0
        self._pan_active = False
        self._pan_start: tuple[int, int] | None = None
        self._pan_origin: tuple[int, int] | None = None
        self._markup_components = []
        self._selected_component: int = -1
        self._drag_component: int = -1
        self._drag_mode: str | None = None
        self._drag_offset = (0, 0)
        self._drag_polygon_vertex: tuple[int, int] | None = None
        self._drag_polygon_edge: tuple[int, int] | None = None
        self._drag_polygon_edge_state: dict | None = None
        self._on_components_changed = None
        self._on_empty_click = None
        self._show_overlay = True
        self._show_component_labels = True
        self._show_component_sizes = False
        self._show_polygon_hatch = True
        self._point_size = 10
        self._point_axis_magnet = True
        self._axis_snap_x_source: int | None = None
        self._axis_snap_y_source: int | None = None
        self._undo_stack: list[list[dict]] = []
        self._redo_stack: list[list[dict]] = []
        self._visible_component_indices: set[int] | None = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def attach_grid_settings(self, grid_settings) -> None:
        self._grid = grid_settings

    def set_aspect_ratio(self, ratio: float | None) -> None:
        self._aspect_ratio = ratio if ratio and ratio > 0 else None
        self.update()

    def set_component_display_options(
        self,
        *,
        show_overlay: bool,
        show_labels: bool,
        show_sizes: bool,
        point_size: int = 10,
        point_axis_magnet: bool = True,
        show_hatch: bool = True,
    ) -> None:
        self._show_overlay = bool(show_overlay)
        self._show_component_labels = bool(show_labels)
        self._show_component_sizes = bool(show_sizes)
        self._point_size = max(4, min(32, int(point_size)))
        self._point_axis_magnet = bool(point_axis_magnet)
        self._show_polygon_hatch = bool(show_hatch)
        self.update()

    def set_captured_pixmap(self, pixmap) -> None:
        self._captured_pixmap = pixmap
        self.update()

    def get_captured_pixmap(self):
        return self._captured_pixmap

    def set_markup_components(self, components) -> None:
        self._markup_components = list(components or [])
        if self._selected_component >= len(self._markup_components):
            self._selected_component = -1
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.update()

    def set_components_changed_callback(self, callback) -> None:
        self._on_components_changed = callback

    def set_empty_click_callback(self, callback) -> None:
        self._on_empty_click = callback

    def get_markup_components(self):
        return self._markup_components

    def get_selected_component_index(self) -> int:
        return self._selected_component

    def set_visible_component_indices(self, indices: list[int] | None) -> None:
        if indices is None:
            self._visible_component_indices = None
        else:
            self._visible_component_indices = {int(i) for i in indices if int(i) >= 0}
        self.update()

    def clear_selected_component(self) -> None:
        if self._selected_component < 0:
            return
        self._selected_component = -1
        self._emit_components_changed()
        self.update()

    def rename_component(self, row: int, name: str) -> None:
        if 0 <= row < len(self._markup_components):
            self._push_undo()
            self._markup_components[row].name = name
            self._emit_components_changed()
            self.update()

    def remove_component(self, row: int) -> None:
        if 0 <= row < len(self._markup_components):
            self._push_undo()
            del self._markup_components[row]
            if self._selected_component == row:
                self._selected_component = -1
            self._emit_components_changed()
            self.update()

    def add_component(self, name: str) -> None:
        self._push_undo()
        cls = type("Component", (), {})
        c = cls()
        c.name, c.x, c.y, c.w, c.h = name, 0.4, 0.4, 0.2, 0.15
        c.lock_move = False
        c.lock_size = False
        c.lock_aspect = False
        self._markup_components.append(c)
        self._selected_component = len(self._markup_components) - 1
        self._emit_components_changed()
        self.update()

    def _emit_components_changed(self) -> None:
        if callable(self._on_components_changed):
            self._on_components_changed(self._markup_components, self._selected_component)

    def _snapshot(self) -> list[dict]:
        out: list[dict] = []
        for c in self._markup_components:
            out.append(
                {
                    "name": str(getattr(c, "name", "")),
                    "x": float(getattr(c, "x", 0.0)),
                    "y": float(getattr(c, "y", 0.0)),
                    "w": float(getattr(c, "w", 0.0)),
                    "h": float(getattr(c, "h", 0.0)),
                    "lock_move": bool(getattr(c, "lock_move", False)),
                    "lock_size": bool(getattr(c, "lock_size", False)),
                    "lock_aspect": bool(getattr(c, "lock_aspect", False)),
                    "point_type": str(getattr(c, "point_type", "")),
                    "ocr_filter": str(getattr(c, "ocr_filter", "none")),
                    "ocr_max_value": getattr(c, "ocr_max_value", None),
                    "ocr_letters_lang": str(getattr(c, "ocr_letters_lang", "ru+en")),
                    "ocr_postprocess": bool(getattr(c, "ocr_postprocess", False)),
                    "shape_type": str(getattr(c, "shape_type", "")),
                    "zone_type": str(getattr(c, "zone_type", "")),
                    "polygon_closed": bool(getattr(c, "polygon_closed", True)),
                    "polygon_points": copy.deepcopy(getattr(c, "polygon_points", None)),
                }
            )
        return out

    def _restore_snapshot(self, snap: list[dict]) -> None:
        self._markup_components = []
        for d in snap:
            cls = type("Component", (), {})
            c = cls()
            c.name = d["name"]
            c.x = d["x"]
            c.y = d["y"]
            c.w = d["w"]
            c.h = d["h"]
            c.lock_move = d["lock_move"]
            c.lock_size = d["lock_size"]
            c.lock_aspect = d["lock_aspect"]
            c.point_type = str(d.get("point_type", ""))
            c.ocr_filter = str(d.get("ocr_filter", "none"))
            c.ocr_max_value = d.get("ocr_max_value", None)
            c.ocr_letters_lang = str(d.get("ocr_letters_lang", "ru+en"))
            c.ocr_postprocess = bool(d.get("ocr_postprocess", False))
            c.shape_type = str(d.get("shape_type", ""))
            c.zone_type = str(d.get("zone_type", ""))
            c.polygon_closed = bool(d.get("polygon_closed", True))
            poly = d.get("polygon_points", None)
            if isinstance(poly, list):
                c.polygon_points = copy.deepcopy(poly)
            self._markup_components.append(c)
        self._selected_component = -1
        self._emit_components_changed()
        self.update()

    def _push_undo(self) -> None:
        self._undo_stack.append(copy.deepcopy(self._snapshot()))
        if len(self._undo_stack) > 100:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(copy.deepcopy(self._snapshot()))
        snap = self._undo_stack.pop()
        self._restore_snapshot(snap)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(copy.deepcopy(self._snapshot()))
        snap = self._redo_stack.pop()
        self._restore_snapshot(snap)
        return True

    def get_history_state(self) -> dict:
        return {
            "undo": copy.deepcopy(self._undo_stack),
            "redo": copy.deepcopy(self._redo_stack),
        }

    def set_history_state(self, state: dict | None) -> None:
        if not isinstance(state, dict):
            self._undo_stack = []
            self._redo_stack = []
            return
        undo = state.get("undo", [])
        redo = state.get("redo", [])
        self._undo_stack = copy.deepcopy(undo) if isinstance(undo, list) else []
        self._redo_stack = copy.deepcopy(redo) if isinstance(redo, list) else []

    def _component_rect(self, comp):
        ix, iy, iw, ih = self._inner_rect()
        poly = getattr(comp, "polygon_points", None)
        if isinstance(poly, list) and poly:
            pts = []
            for p in poly:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    pts.append((int(ix + float(p[0]) * iw), int(iy + float(p[1]) * ih)))
            if pts:
                min_x = min(p[0] for p in pts)
                min_y = min(p[1] for p in pts)
                max_x = max(p[0] for p in pts)
                max_y = max(p[1] for p in pts)
                return min_x, min_y, max(1, max_x - min_x), max(1, max_y - min_y)
        if str(getattr(comp, "point_type", "")):
            cx = int(ix + float(getattr(comp, "x", 0.5)) * iw)
            cy = int(iy + float(getattr(comp, "y", 0.5)) * ih)
            radius_px = max(2, int(self._point_size))
            dpx = radius_px * 2
            return cx - radius_px, cy - radius_px, dpx, dpx
        cx = int(ix + comp.x * iw)
        cy = int(iy + comp.y * ih)
        cw = max(1, int(comp.w * iw))
        ch = max(1, int(comp.h * ih))
        return cx, cy, cw, ch

    def _hit_component(self, px: int, py: int, pad: int = 6):
        stack = self._hit_component_stack(px, py, pad=pad)
        return stack[0] if stack else -1

    def _hit_component_stack(self, px: int, py: int, pad: int = 6) -> list[int]:
        hits: list[int] = []
        for i in range(len(self._markup_components) - 1, -1, -1):
            if self._visible_component_indices is not None and i not in self._visible_component_indices:
                continue
            comp = self._markup_components[i]
            poly = getattr(comp, "polygon_points", None)
            if isinstance(poly, list) and len(poly) >= 3:
                ix, iy, iw, ih = self._inner_rect()
                pts = []
                for p in poly:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        pts.append(QPoint(int(ix + float(p[0]) * iw), int(iy + float(p[1]) * ih)))
                if len(pts) >= 3 and self._point_in_polygon(px, py, pts):
                    hits.append(i)
                continue
            cx, cy, cw, ch = self._component_rect(comp)
            if (cx - pad) <= px <= (cx + cw + pad) and (cy - pad) <= py <= (cy + ch + pad):
                hits.append(i)
        return hits

    def _point_in_polygon(self, x: int, y: int, points: list[QPoint]) -> bool:
        inside = False
        n = len(points)
        j = n - 1
        for i in range(n):
            xi, yi = points[i].x(), points[i].y()
            xj, yj = points[j].x(), points[j].y()
            dy = (yj - yi)
            if abs(dy) < 1e-9:
                j = i
                continue
            intersects = ((yi > y) != (yj > y)) and (x < ((xj - xi) * (y - yi) / dy) + xi)
            if intersects:
                inside = not inside
            j = i
        return inside

    def _point_in_capture_rect(self, px: int, py: int) -> bool:
        x, y, w, h = self.capture_rect
        return x <= px <= x + w and y <= py <= y + h

    def _polygon_screen_points(self, comp) -> list[QPoint]:
        ix, iy, iw, ih = self._inner_rect()
        pts: list[QPoint] = []
        poly = getattr(comp, "polygon_points", None)
        if not isinstance(poly, list):
            return pts
        for p in poly:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                pts.append(QPoint(int(ix + float(p[0]) * iw), int(iy + float(p[1]) * ih)))
        return pts

    def _polygon_label_pos(self, points: list[QPoint]) -> tuple[int, int]:
        if not points:
            return 0, 0
        area2 = 0.0
        cx_acc = 0.0
        cy_acc = 0.0
        n = len(points)
        for i in range(n):
            p1 = points[i]
            p2 = points[(i + 1) % n]
            cross = (p1.x() * p2.y()) - (p2.x() * p1.y())
            area2 += cross
            cx_acc += (p1.x() + p2.x()) * cross
            cy_acc += (p1.y() + p2.y()) * cross
        if abs(area2) > 1e-6:
            cx = int(round(cx_acc / (3.0 * area2)))
            cy = int(round(cy_acc / (3.0 * area2)))
            if self._point_in_polygon(cx, cy, points):
                return cx, cy
        return int(round(sum(p.x() for p in points) / len(points))), int(round(sum(p.y() for p in points) / len(points)))

    def _distance_to_segment(self, px: int, py: int, a: QPoint, b: QPoint) -> float:
        ax, ay = float(a.x()), float(a.y())
        bx, by = float(b.x()), float(b.y())
        dx = bx - ax
        dy = by - ay
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        sx = ax + t * dx
        sy = ay + t * dy
        return ((px - sx) ** 2 + (py - sy) ** 2) ** 0.5

    def _line_intersection(
        self,
        a1x: float,
        a1y: float,
        a2x: float,
        a2y: float,
        b1x: float,
        b1y: float,
        b2x: float,
        b2y: float,
    ) -> tuple[float, float] | None:
        adx = a2x - a1x
        ady = a2y - a1y
        bdx = b2x - b1x
        bdy = b2y - b1y
        den = (adx * bdy) - (ady * bdx)
        if abs(den) < 1e-9:
            return None
        t = ((b1x - a1x) * bdy - (b1y - a1y) * bdx) / den
        return (a1x + (adx * t), a1y + (ady * t))

    def _quantize(self, value: float, step: float) -> float:
        if step <= 1e-12:
            return value
        return round(value / step) * step

    def _hit_polygon_edge(self, px: int, py: int, pad: int = 7) -> tuple[int, int] | None:
        best: tuple[int, int] | None = None
        best_dist = float(pad + 1)
        for ci in range(len(self._markup_components) - 1, -1, -1):
            if self._visible_component_indices is not None and ci not in self._visible_component_indices:
                continue
            comp = self._markup_components[ci]
            qpts = self._polygon_screen_points(comp)
            if len(qpts) < 2:
                continue
            edge_count = len(qpts) if bool(getattr(comp, "polygon_closed", True)) and len(qpts) >= 3 else len(qpts) - 1
            for ei in range(edge_count):
                a = qpts[ei]
                b = qpts[(ei + 1) % len(qpts)]
                dist = self._distance_to_segment(px, py, a, b)
                if dist <= pad and dist < best_dist:
                    best = (ci, ei)
                    best_dist = dist
        return best

    def _cursor_for_polygon_edge(self, ci: int, ei: int):
        if not (0 <= ci < len(self._markup_components)):
            return Qt.CursorShape.SizeAllCursor
        qpts = self._polygon_screen_points(self._markup_components[ci])
        if len(qpts) < 2:
            return Qt.CursorShape.SizeAllCursor
        a = qpts[ei]
        b = qpts[(ei + 1) % len(qpts)]
        # Resize direction should follow edge movement axis (edge normal), not edge direction.
        dx = float(b.x() - a.x())
        dy = float(b.y() - a.y())
        n_dx = -dy
        n_dy = dx
        if abs(n_dx) < 1e-9 and abs(n_dy) < 1e-9:
            return Qt.CursorShape.SizeAllCursor
        length = (n_dx * n_dx + n_dy * n_dy) ** 0.5
        ux = n_dx / length
        uy = n_dy / length
        # Pick by best directional match to avoid threshold flicker near boundaries.
        # Each tuple: (axis unit vector, cursor).
        candidates = (
            ((1.0, 0.0), Qt.CursorShape.SizeHorCursor),
            ((0.0, 1.0), Qt.CursorShape.SizeVerCursor),
            ((2 ** -0.5, 2 ** -0.5), Qt.CursorShape.SizeFDiagCursor),
            ((2 ** -0.5, -(2 ** -0.5)), Qt.CursorShape.SizeBDiagCursor),
        )
        best_cursor = Qt.CursorShape.SizeAllCursor
        best_score = -1.0
        for (ax, ay), cursor in candidates:
            score = abs((ux * ax) + (uy * ay))
            if score > best_score:
                best_score = score
                best_cursor = cursor
        return best_cursor

    def _hit_component_mode(self, idx: int, px: int, py: int, pad: int = 10) -> str:
        comp = self._markup_components[idx]
        poly = getattr(comp, "polygon_points", None)
        if isinstance(poly, list) and poly:
            return "move"
        if str(getattr(comp, "point_type", "")):
            return "none" if bool(getattr(comp, "lock_move", False)) else "move"
        cx, cy, cw, ch = self._component_rect(comp)
        lock_size = bool(getattr(comp, "lock_size", False))
        lock_move = bool(getattr(comp, "lock_move", False))
        near_l = abs(px - cx) <= pad
        near_r = abs(px - (cx + cw)) <= pad
        near_t = abs(py - cy) <= pad
        near_b = abs(py - (cy + ch)) <= pad
        if not lock_size and near_l and near_t:
            return "top_left"
        if not lock_size and near_r and near_t:
            return "top_right"
        if not lock_size and near_r and near_b:
            return "bottom_right"
        if not lock_size and near_l and near_b:
            return "bottom_left"
        if not lock_size and near_l:
            return "left"
        if not lock_size and near_r:
            return "right"
        if not lock_size and near_t:
            return "top"
        if not lock_size and near_b:
            return "bottom"
        if not lock_move:
            return "move"
        return "none"

    def _cursor_for_mode(self, mode: str | None):
        if mode in {"left", "right"}:
            return Qt.CursorShape.SizeHorCursor
        if mode in {"top", "bottom"}:
            return Qt.CursorShape.SizeVerCursor
        if mode in {"top_left", "bottom_right"}:
            return Qt.CursorShape.SizeFDiagCursor
        if mode in {"top_right", "bottom_left"}:
            return Qt.CursorShape.SizeBDiagCursor
        if mode == "move":
            return Qt.CursorShape.SizeAllCursor
        if mode == "radius":
            return Qt.CursorShape.SizeAllCursor
        return None

    def _hit_polygon_vertex(self, px: int, py: int, pad: int = 8) -> tuple[int, int] | None:
        ix, iy, iw, ih = self._inner_rect()
        for ci in range(len(self._markup_components) - 1, -1, -1):
            comp = self._markup_components[ci]
            poly = getattr(comp, "polygon_points", None)
            if not isinstance(poly, list) or not poly:
                continue
            for vi, p in enumerate(poly):
                if not (isinstance(p, (list, tuple)) and len(p) >= 2):
                    continue
                vx = int(ix + float(p[0]) * iw)
                vy = int(iy + float(p[1]) * ih)
                if abs(px - vx) <= pad and abs(py - vy) <= pad:
                    return ci, vi
        return None

    def reset_zoom(self) -> None:
        self._view_zoom = 1.0
        self._pan_x = 0
        self._pan_y = 0
        self.update()

    def get_zoom(self) -> float:
        return max(1.0, min(10.0, float(self._view_zoom)))

    def set_zoom(self, zoom: float) -> None:
        self._view_zoom = max(1.0, min(10.0, float(zoom)))
        self._pan_x = 0
        self._pan_y = 0
        self.update()

    def _is_zoomed(self) -> bool:
        return self._view_zoom > 1.000001

    def _base_rect(self) -> tuple[int, int, int, int, int, int]:
        width = max(1, self.width())
        height = max(1, self.height())
        zone_x1 = self.PADDING
        zone_y1 = self.PADDING
        zone_x2 = max(zone_x1 + 1, width - self.PADDING)
        zone_y2 = max(zone_y1 + 1, height - self.PADDING)
        zone_w = max(1, zone_x2 - zone_x1)
        zone_h = max(1, zone_y2 - zone_y1)

        if self._aspect_ratio is None:
            base_w, base_h = zone_w, zone_h
        else:
            fit_h = int(zone_w / self._aspect_ratio)
            if fit_h <= zone_h:
                base_w, base_h = zone_w, max(1, fit_h)
            else:
                base_h = zone_h
                base_w = max(1, int(zone_h * self._aspect_ratio))

        base_x = zone_x1 + (zone_w - base_w) // 2
        base_y = zone_y1 + (zone_h - base_h) // 2
        return zone_x1, zone_y1, zone_x2, zone_y2, base_x, base_y

    def _fit_capture_rect(self) -> tuple[int, int, int, int]:
        zone_x1, zone_y1, zone_x2, zone_y2, base_x, base_y = self._base_rect()
        zone_w = max(1, zone_x2 - zone_x1)
        zone_h = max(1, zone_y2 - zone_y1)

        width = max(1, self.width())
        height = max(1, self.height())
        avail_w = max(1, width - self.PADDING * 2)
        avail_h = max(1, height - self.PADDING * 2)

        if self._aspect_ratio is None:
            base_w, base_h = avail_w, avail_h
        else:
            fit_h = int(avail_w / self._aspect_ratio)
            if fit_h <= avail_h:
                base_w, base_h = avail_w, max(1, fit_h)
            else:
                base_h = avail_h
                base_w = max(1, int(avail_h * self._aspect_ratio))

        zoom = max(1.0, min(10.0, float(self._view_zoom)))
        if zoom <= 1.000001:
            # No zoom: keep capture window centered and disable any accumulated pan.
            self._view_zoom = 1.0
            self._pan_x = 0
            self._pan_y = 0
            return base_x, base_y, base_w, base_h
        vw = max(1, int(round(base_w * zoom)))
        vh = max(1, int(round(base_h * zoom)))

        if vw <= zone_w:
            # If there is free horizontal space in markup zone, keep centered on X.
            x = zone_x1 + (zone_w - vw) // 2
            self._pan_x = x - base_x
        else:
            min_x = zone_x2 - vw
            max_x = zone_x1
            x = int(max(min_x, min(max_x, base_x + int(self._pan_x))))
            self._pan_x = x - base_x

        if vh <= zone_h:
            # If there is free vertical space in markup zone, keep centered on Y.
            y = zone_y1 + (zone_h - vh) // 2
            self._pan_y = y - base_y
        else:
            min_y = zone_y2 - vh
            max_y = zone_y1
            y = int(max(min_y, min(max_y, base_y + int(self._pan_y))))
            self._pan_y = y - base_y

        return x, y, vw, vh

    def _inner_rect(self) -> tuple[int, int, int, int]:
        x, y, w, h = self.capture_rect
        if self._grid is None:
            return x, y, w, h
        m = self._grid.margins
        ix = x + m["left"]
        iy = y + m["top"]
        iw = max(1, w - m["left"] - m["right"])
        ih = max(1, h - m["top"] - m["bottom"])
        return ix, iy, iw, ih

    def _zone_mode_style(self, mode: str) -> dict:
        m = str(mode or "blocked").strip().lower() or "blocked"
        styles = {
            "blocked": {"outline": "#e74c3c", "active_outline": "#ff8a80", "fill": "#6f1d1b"},
            "walkable": {"outline": "#2ecc71", "active_outline": "#7dff9b", "fill": "#1e5631"},
            "plant": {"outline": "#f39c12", "active_outline": "#ffd166", "fill": "#7a4f10"},
            "zone callouts": {"outline": "#3498db", "active_outline": "#7fc8ff", "fill": "#103d5c"},
            "jump spot": {"outline": "#9b59b6", "active_outline": "#d6b3ff", "fill": "#4b2e83"},
            "boost zone": {"outline": "#1abc9c", "active_outline": "#8af5e0", "fill": "#0c4f45"},
        }
        return styles.get(m, styles["blocked"])

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self.capture_rect = self._fit_capture_rect()
        x, y, w, h = self.capture_rect

        painter = QPainter(self)
        try:
            painter.fillRect(self.rect(), QColor("#0f0f0f"))
            painter.setBrush(QColor("#2c3e50"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(x, y, w, h)

            if self._captured_pixmap is not None and not self._captured_pixmap.isNull():
                scaled = self._captured_pixmap.scaled(
                    w,
                    h,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                sx = x + (w - scaled.width()) // 2
                sy = y + (h - scaled.height()) // 2
                painter.setClipRect(x, y, w, h)
                painter.drawPixmap(sx, sy, scaled)
                painter.setClipping(False)

            if self._grid is not None:
                ix, iy, iw, ih = self._inner_rect()
                if self._grid.enabled:
                    cols = max(2, self._grid.columns)
                    step = iw / float(cols)
                    painter.setPen(QPen(QColor("#2e455a"), 1))
                    for i in range(cols + 1):
                        gx = int(round(ix + i * step))
                        painter.drawLine(gx, iy, gx, iy + ih)
                    rows = max(1, int(ih / max(1.0, step)))
                    for j in range(rows + 1):
                        gy = int(round(iy + j * step))
                        if gy > iy + ih:
                            break
                        painter.drawLine(ix, gy, ix + iw, gy)

                if self._show_overlay and self._markup_components:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    for i, comp in enumerate(self._markup_components):
                        if self._visible_component_indices is not None and i not in self._visible_component_indices:
                            continue
                        cx, cy, cw, ch = self._component_rect(comp)
                        ptype = str(getattr(comp, "point_type", ""))
                        if ptype:
                            color = {"click": "#ff4b4b", "scroll": "#43d67c", "swap": "#4a86ff"}.get(ptype, "#ff6565")
                            if i == self._axis_snap_x_source or i == self._axis_snap_y_source:
                                pen_color = QColor("#ffd24a")
                                fill_color = QColor("#ffec99")
                            elif i == self._selected_component:
                                pen_color = QColor("#5aa9ff")
                                fill_color = QColor(color)
                            else:
                                pen_color = QColor(color)
                                fill_color = QColor(color)
                            painter.setPen(QPen(pen_color, 2))
                            painter.setBrush(fill_color)
                            painter.drawEllipse(cx, cy, cw, ch)
                            painter.setBrush(Qt.BrushStyle.NoBrush)
                        else:
                            mode_style = self._zone_mode_style(str(getattr(comp, "zone_type", "blocked")))
                            outline = QColor(mode_style["active_outline"] if i == self._selected_component else mode_style["outline"])
                            fill = QColor(mode_style["fill"])
                            painter.setPen(QPen(outline, 2))
                            poly = getattr(comp, "polygon_points", None)
                            if isinstance(poly, list) and len(poly) >= 2:
                                qpts = self._polygon_screen_points(comp)
                                if len(qpts) >= 2:
                                    if self._show_polygon_hatch and bool(getattr(comp, "polygon_closed", True)) and len(qpts) >= 3:
                                        painter.setBrush(QColor(fill.red(), fill.green(), fill.blue(), 60))
                                    else:
                                        painter.setBrush(Qt.BrushStyle.NoBrush)
                                    if bool(getattr(comp, "polygon_closed", True)) and len(qpts) >= 3:
                                        painter.drawPolygon(qpts)
                                    else:
                                        painter.drawPolyline(qpts)
                                    default_pen = QPen(outline, 2)
                                    for ei in range(len(qpts) - 1):
                                        a = qpts[ei]
                                        b = qpts[ei + 1]
                                        highlight = False
                                        if self._drag_polygon_edge is not None and self._drag_polygon_edge == (i, ei):
                                            highlight = True
                                        if self._drag_polygon_vertex is not None and self._drag_polygon_vertex[0] == i:
                                            _, v_idx = self._drag_polygon_vertex
                                            if ei == v_idx or ei == ((v_idx - 1) % len(qpts)):
                                                highlight = abs(a.x() - b.x()) <= 1 or abs(a.y() - b.y()) <= 1
                                        painter.setPen(QPen(QColor("#ffd24a"), 3) if highlight else default_pen)
                                        painter.drawLine(a, b)
                                    if bool(getattr(comp, "polygon_closed", True)) and len(qpts) >= 3:
                                        a = qpts[-1]
                                        b = qpts[0]
                                        closing_idx = len(qpts) - 1
                                        highlight = False
                                        if self._drag_polygon_edge is not None and self._drag_polygon_edge == (i, closing_idx):
                                            highlight = True
                                        if self._drag_polygon_vertex is not None and self._drag_polygon_vertex[0] == i:
                                            _, v_idx = self._drag_polygon_vertex
                                            if closing_idx == v_idx or closing_idx == ((v_idx - 1) % len(qpts)):
                                                highlight = abs(a.x() - b.x()) <= 1 or abs(a.y() - b.y()) <= 1
                                        painter.setPen(QPen(QColor("#ffd24a"), 3) if highlight else default_pen)
                                        painter.drawLine(a, b)
                                    painter.setPen(default_pen)
                                    for vp in qpts:
                                        painter.setBrush(QColor("#f5f7fa") if i == self._selected_component else QColor("#ffffff"))
                                        painter.drawEllipse(vp, 4, 4)
                                    painter.setBrush(Qt.BrushStyle.NoBrush)
                                else:
                                    painter.drawRect(cx, cy, cw, ch)
                            else:
                                painter.drawRect(cx, cy, cw, ch)
                        if self._show_component_labels:
                            painter.setPen(QPen(QColor("#ffffff"), 1))
                            text_w = max(24, len(comp.name) * 7)
                            poly = getattr(comp, "polygon_points", None)
                            if isinstance(poly, list) and len(poly) >= 3 and not ptype:
                                qpts = self._polygon_screen_points(comp)
                                tx, ty = self._polygon_label_pos(qpts)
                                text_x = int(tx - (text_w + 8) / 2)
                                text_y = int(ty - 7)
                                painter.fillRect(text_x, text_y, text_w + 8, 16, QColor(0, 0, 0, 165))
                                painter.drawText(text_x + 4, text_y + 12, comp.name)
                            else:
                                # Contrast tag for readable labels on bright captures.
                                painter.fillRect(cx + 2, max(0, cy - 18), text_w + 8, 14, QColor(0, 0, 0, 160))
                                painter.drawText(cx + 4, max(12, cy - 6), comp.name)
                        if self._show_component_sizes and not ptype:
                            painter.setPen(QPen(QColor("#ffffff"), 1))
                            size_text = f"{cw} x {ch} px"
                            text_w = max(44, len(size_text) * 7)
                            text_y = cy + ch + 2
                            painter.fillRect(cx + 2, text_y, text_w + 8, 14, QColor(0, 0, 0, 160))
                            painter.drawText(cx + 4, text_y + 12, size_text)

                    if (
                        self._selected_component >= 0
                        and self._selected_component < len(self._markup_components)
                        and str(getattr(self._markup_components[self._selected_component], "point_type", ""))
                    ):
                        sel = self._markup_components[self._selected_component]
                        sx, sy, sw, sh = self._component_rect(sel)
                        scx = sx + sw // 2
                        scy = sy + sh // 2
                        # Show selected point coordinates below the point in grid blocks.
                        cols = max(2, int(getattr(self._grid, "columns", 24) if self._grid else 24))
                        step_nx = 1.0 / float(cols)
                        step_ny = (iw / float(cols)) / max(1.0, float(ih))
                        gx = float(getattr(sel, "x", 0.0)) / max(1e-9, step_nx)
                        gy = float(getattr(sel, "y", 0.0)) / max(1e-9, step_ny)
                        coords_text = f"X={gx:.2f}, Y={gy:.2f} blocks"
                        painter.setPen(QPen(QColor("#ffffff"), 1))
                        text_w = max(120, len(coords_text) * 7 + 8)
                        text_x = int(scx - text_w // 2)
                        text_y = int(scy + max(10, sh // 2) + 8)
                        painter.fillRect(text_x, text_y, text_w, 18, QColor(0, 0, 0, 170))
                        painter.drawText(text_x + 4, text_y + 13, coords_text)

                        # Visual guides: show which point axes are used for snap.
                        painter.setPen(QPen(QColor("#ffd24a"), 1, Qt.PenStyle.DashLine))
                        if self._axis_snap_x_source is not None and 0 <= self._axis_snap_x_source < len(self._markup_components):
                            src = self._markup_components[self._axis_snap_x_source]
                            tx, ty, tw, th = self._component_rect(src)
                            tcx = tx + tw // 2
                            painter.drawLine(tcx, iy, tcx, iy + ih)
                        if self._axis_snap_y_source is not None and 0 <= self._axis_snap_y_source < len(self._markup_components):
                            src = self._markup_components[self._axis_snap_y_source]
                            tx, ty, tw, th = self._component_rect(src)
                            tcy = ty + th // 2
                            painter.drawLine(ix, tcy, ix + iw, tcy)

            # Draw capture frame border before grid border so grid border can stay on top.
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#d0d0d0"), 2))
            painter.drawRect(x, y, w, h)
            if self._grid is not None and self._grid.show_border:
                ix, iy, iw, ih = self._inner_rect()
                painter.setPen(QPen(QColor("#ffcc66"), max(1, self._grid.border_width)))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(ix, iy, iw, ih)
        finally:
            painter.end()

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return

        old_x, old_y, old_w, old_h = self.capture_rect
        mx = event.position().x()
        my = event.position().y()
        fx = 0.5 if old_w <= 0 else (mx - old_x) / float(old_w)
        fy = 0.5 if old_h <= 0 else (my - old_y) / float(old_h)

        old_zoom = self._view_zoom
        step = 1.1 if delta > 0 else (1.0 / 1.1)
        self._view_zoom = max(1.0, min(10.0, old_zoom * step))
        if self._view_zoom == old_zoom:
            return

        zone_x1, zone_y1, zone_x2, zone_y2, base_x, base_y = self._base_rect()
        zone_w = max(1, zone_x2 - zone_x1)
        zone_h = max(1, zone_y2 - zone_y1)
        width = max(1, self.width())
        height = max(1, self.height())
        avail_w = max(1, width - self.PADDING * 2)
        avail_h = max(1, height - self.PADDING * 2)

        if self._aspect_ratio is None:
            base_w, base_h = avail_w, avail_h
        else:
            fit_h = int(avail_w / self._aspect_ratio)
            if fit_h <= avail_h:
                base_w, base_h = avail_w, max(1, fit_h)
            else:
                base_h = avail_h
                base_w = max(1, int(avail_h * self._aspect_ratio))

        new_w = max(1, int(round(base_w * self._view_zoom)))
        new_h = max(1, int(round(base_h * self._view_zoom)))

        desired_x = int(round(mx - fx * new_w))
        desired_y = int(round(my - fy * new_h))

        # Keep centered on the axis that does not overflow the viewport during wheel zoom.
        # Manual middle-button pan can still move within available slack in _fit_capture_rect.
        self._pan_x = 0 if new_w <= zone_w else (desired_x - base_x)
        self._pan_y = 0 if new_h <= zone_h else (desired_y - base_y)
        self.capture_rect = self._fit_capture_rect()

        event.accept()
        self.update()

    def _hit_edge(self, px: int, py: int) -> str | None:
        if self._grid is None or not self._grid.show_border:
            return None
        ix, iy, iw, ih = self._inner_rect()
        pad = 10
        near_left = abs(px - ix) <= pad
        near_right = abs(px - (ix + iw)) <= pad
        near_top = abs(py - iy) <= pad
        near_bottom = abs(py - (iy + ih)) <= pad
        if near_left and near_top:
            return "top_left"
        if near_right and near_top:
            return "top_right"
        if near_right and near_bottom:
            return "bottom_right"
        if near_left and near_bottom:
            return "bottom_left"
        if near_left and iy - pad <= py <= iy + ih + pad:
            return "left"
        if near_right and iy - pad <= py <= iy + ih + pad:
            return "right"
        if near_top and ix - pad <= px <= ix + iw + pad:
            return "top"
        if near_bottom and ix - pad <= px <= ix + iw + pad:
            return "bottom"
        return None

    def _set_cursor_for_edge(self, edge: str | None) -> None:
        if edge in {"left", "right"}:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge in {"top", "bottom"}:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge in {"top_left", "bottom_right"}:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in {"top_right", "bottom_left"}:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            if not self._is_zoomed():
                return
            self._pan_active = True
            self._pan_start = (int(event.position().x()), int(event.position().y()))
            self._pan_origin = (int(self._pan_x), int(self._pan_y))
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        mouse_x = float(event.position().x())
        mouse_y = float(event.position().y())
        px = int(mouse_x)
        py = int(mouse_y)
        if event.button() == Qt.MouseButton.RightButton:
            if not self._point_in_capture_rect(px, py):
                return
            hit = self._hit_component(px, py, pad=2)
            if hit >= 0:
                self._selected_component = hit
                menu = QMenu(self)
                rename_action = menu.addAction("Rename")
                dup_action = menu.addAction("Duplicate")
                del_action = menu.addAction("Delete")
                is_point = bool(str(getattr(self._markup_components[hit], "point_type", "")))
                lock_move = menu.addAction(f"{'Unlock' if bool(getattr(self._markup_components[hit], 'lock_move', False)) else 'Lock'} Move")
                lock_size = None if is_point else menu.addAction(f"{'Unlock' if bool(getattr(self._markup_components[hit], 'lock_size', False)) else 'Lock'} Resize")
                lock_aspect = None if is_point else menu.addAction(f"{'Unlock' if bool(getattr(self._markup_components[hit], 'lock_aspect', False)) else 'Lock'} Aspect")
                chosen = menu.exec(event.globalPosition().toPoint())
                if chosen == rename_action:
                    cur = self._markup_components[hit].name
                    name, ok = QInputDialog.getText(self, "Rename Component", "Name:", text=cur)
                    if ok and name.strip():
                        self._push_undo()
                        self._markup_components[hit].name = name.strip()
                        self._emit_components_changed()
                elif chosen == dup_action:
                    self._push_undo()
                    src = self._markup_components[hit]
                    cls = type("Component", (), {})
                    c = cls()
                    c.name = f"{src.name} Copy"
                    c.x = min(0.95, src.x + 0.02)
                    c.y = min(0.95, src.y + 0.02)
                    c.w = src.w
                    c.h = src.h
                    c.lock_move = bool(getattr(src, "lock_move", False))
                    c.lock_size = bool(getattr(src, "lock_size", False))
                    c.lock_aspect = bool(getattr(src, "lock_aspect", False))
                    c.point_type = str(getattr(src, "point_type", ""))
                    c.ocr_filter = str(getattr(src, "ocr_filter", "none"))
                    c.ocr_max_value = getattr(src, "ocr_max_value", None)
                    c.ocr_letters_lang = str(getattr(src, "ocr_letters_lang", "ru+en"))
                    c.ocr_postprocess = bool(getattr(src, "ocr_postprocess", False))
                    c.shape_type = str(getattr(src, "shape_type", ""))
                    c.zone_type = str(getattr(src, "zone_type", ""))
                    c.polygon_closed = bool(getattr(src, "polygon_closed", True))
                    poly = getattr(src, "polygon_points", None)
                    if isinstance(poly, list):
                        c.polygon_points = copy.deepcopy(poly)
                    self._markup_components.append(c)
                    self._selected_component = len(self._markup_components) - 1
                    self._emit_components_changed()
                elif chosen == del_action:
                    self.remove_component(hit)
                elif chosen == lock_move:
                    self._push_undo()
                    self._markup_components[hit].lock_move = not bool(getattr(self._markup_components[hit], "lock_move", False))
                    self._emit_components_changed()
                elif lock_size is not None and chosen == lock_size:
                    self._push_undo()
                    self._markup_components[hit].lock_size = not bool(getattr(self._markup_components[hit], "lock_size", False))
                    self._emit_components_changed()
                elif lock_aspect is not None and chosen == lock_aspect:
                    self._push_undo()
                    self._markup_components[hit].lock_aspect = not bool(getattr(self._markup_components[hit], "lock_aspect", False))
                    self._emit_components_changed()
                self.update()
            elif callable(self._on_empty_click):
                near_hit = self._hit_component(px, py, pad=self.EMPTY_CLICK_NEAR_PAD)
                if near_hit < 0:
                    self._on_empty_click("right", px, py)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self._grid is not None and self._grid.show_border:
                self._drag_edge = self._hit_edge(int(event.position().x()), int(event.position().y()))
                self._set_cursor_for_edge(self._drag_edge)
            else:
                self._drag_edge = None
            if self._drag_edge is None:
                vhit = self._hit_polygon_vertex(px, py, pad=8)
                if vhit is not None:
                    self._selected_component = vhit[0]
                    self._drag_polygon_vertex = vhit
                    self._drag_component = -1
                    self._drag_mode = None
                    self._push_undo()
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                    self._emit_components_changed()
                    self.update()
                    super().mousePressEvent(event)
                    return
                ehit = self._hit_polygon_edge(px, py, pad=7)
                if ehit is not None:
                    self._selected_component = ehit[0]
                    self._drag_polygon_edge = ehit
                    self._drag_polygon_edge_state = None
                    self._drag_polygon_vertex = None
                    self._drag_component = -1
                    self._drag_mode = None
                    self._push_undo()
                    ci, ei = ehit
                    comp = self._markup_components[ci]
                    poly = getattr(comp, "polygon_points", None)
                    if isinstance(poly, list) and len(poly) >= 3:
                        vi1 = ei
                        vi2 = (ei + 1) % len(poly)
                        prev_idx = (vi1 - 1) % len(poly)
                        next_idx = (vi2 + 1) % len(poly)
                        p0 = poly[prev_idx]
                        p1 = poly[vi1]
                        p2 = poly[vi2]
                        p3 = poly[next_idx]
                        if all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in (p0, p1, p2, p3)):
                            ix, iy, iw, ih = self._inner_rect()
                            s0x, s0y = ix + float(p0[0]) * iw, iy + float(p0[1]) * ih
                            s1x, s1y = ix + float(p1[0]) * iw, iy + float(p1[1]) * ih
                            s2x, s2y = ix + float(p2[0]) * iw, iy + float(p2[1]) * ih
                            s3x, s3y = ix + float(p3[0]) * iw, iy + float(p3[1]) * ih
                            ex = s2x - s1x
                            ey = s2y - s1y
                            elen = (ex * ex + ey * ey) ** 0.5
                            if elen > 1e-6:
                                nx = -ey / elen
                                ny = ex / elen
                                self._drag_polygon_edge_state = {
                                    "ci": ci,
                                    "ei": ei,
                                    "vi1": vi1,
                                    "vi2": vi2,
                                    "ix": ix,
                                    "iy": iy,
                                    "iw": iw,
                                    "ih": ih,
                                    "mouse_start": (mouse_x, mouse_y),
                                    "s0": (s0x, s0y),
                                    "s1": (s1x, s1y),
                                    "s2": (s2x, s2y),
                                    "s3": (s3x, s3y),
                                    "normal": (nx, ny),
                                }
                    self.setCursor(self._cursor_for_polygon_edge(*ehit))
                    self._emit_components_changed()
                    self.update()
                    super().mousePressEvent(event)
                    return
                hit = self._hit_component(px, py, pad=2)
                if hit >= 0:
                    hit_stack = self._hit_component_stack(px, py, pad=2)
                    if len(hit_stack) > 1:
                        if self._selected_component in hit_stack:
                            cur_i = hit_stack.index(self._selected_component)
                            hit = hit_stack[(cur_i + 1) % len(hit_stack)]
                        else:
                            hit = hit_stack[0]
                    if hit != self._selected_component:
                        self._selected_component = hit
                        self._drag_component = -1
                        self._drag_mode = None
                        self._emit_components_changed()
                        self.update()
                        super().mousePressEvent(event)
                        return
                    self._selected_component = hit
                    self._drag_mode = self._hit_component_mode(hit, px, py)
                    if self._drag_mode == "none":
                        self._drag_component = -1
                        self._emit_components_changed()
                        self.update()
                        super().mousePressEvent(event)
                        return
                    self._drag_component = hit
                    self._push_undo()
                    cshape = self._cursor_for_mode(self._drag_mode)
                    if cshape is not None:
                        self.setCursor(cshape)
                    cx, cy, cw, ch = self._component_rect(self._markup_components[hit])
                    if str(getattr(self._markup_components[hit], "point_type", "")):
                        # For points, center follows cursor directly.
                        self._drag_offset = (0, 0)
                    else:
                        self._drag_offset = (px - cx, py - cy)
                    self._emit_components_changed()
                    self.update()
                elif callable(self._on_empty_click):
                    near_hit = self._hit_component(px, py, pad=self.EMPTY_CLICK_NEAR_PAD)
                    if near_hit < 0:
                        self._on_empty_click("left", px, py)
        else:
            self._drag_edge = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        mouse_x = float(event.position().x())
        mouse_y = float(event.position().y())
        px = int(mouse_x)
        py = int(mouse_y)
        buttons = event.buttons()

        # Safety: if release happened outside widget, clear stale drag/pan states.
        if self._pan_active and not (buttons & Qt.MouseButton.MiddleButton):
            self._pan_active = False
            self._pan_start = None
            self._pan_origin = None
        if (self._drag_edge is not None or self._drag_component >= 0 or self._drag_polygon_edge is not None) and not (buttons & Qt.MouseButton.LeftButton):
            self._drag_edge = None
            self._drag_component = -1
            self._drag_mode = None
            self._drag_polygon_edge = None
            self._drag_polygon_edge_state = None
            self._axis_snap_x_source = None
            self._axis_snap_y_source = None

        if self._pan_active and self._pan_start and self._pan_origin:
            if not self._is_zoomed():
                self._pan_active = False
                self._pan_start = None
                self._pan_origin = None
                self._pan_x = 0
                self._pan_y = 0
                self.unsetCursor()
                self.update()
                return
            sx, sy = self._pan_start
            ox, oy = self._pan_origin
            self._pan_x = ox + (px - sx)
            self._pan_y = oy + (py - sy)
            self.update()
            return

        if self._grid is not None and self._grid.show_border and self._drag_edge:
            x, y, w, h = self.capture_rect
            m = dict(self._grid.margins)
            if self._drag_edge in {"left", "top_left", "bottom_left"}:
                m["left"] = max(0, min(w - 20, px - x))
            if self._drag_edge in {"right", "top_right", "bottom_right"}:
                m["right"] = max(0, min(w - 20, x + w - px))
            if self._drag_edge in {"top", "top_left", "top_right"}:
                m["top"] = max(0, min(h - 20, py - y))
            if self._drag_edge in {"bottom", "bottom_left", "bottom_right"}:
                m["bottom"] = max(0, min(h - 20, y + h - py))
            self._grid.set_margins(m)
            self._set_cursor_for_edge(self._drag_edge)
            self.update()
            return

        if self._drag_component >= 0 and self._drag_mode:
            ix, iy, iw, ih = self._inner_rect()
            comp = self._markup_components[self._drag_component]
            cx, cy, cw, ch = self._component_rect(comp)
            min_px = 8
            cols = max(2, int(getattr(self._grid, "columns", 24) if self._grid else 24))
            step_x = 1.0 / float(cols)
            step_y = (iw / float(cols)) / max(1.0, float(ih))

            def snapx(v: float) -> float:
                if not (self._grid and getattr(self._grid, "magnet", False)):
                    return v
                return max(0.0, min(1.0, round(v / step_x) * step_x))

            def snapy(v: float) -> float:
                if not (self._grid and getattr(self._grid, "magnet", False)):
                    return v
                return max(0.0, min(1.0, round(v / step_y) * step_y))

            if self._drag_mode == "move":
                if bool(getattr(comp, "lock_move", False)):
                    return
                poly = getattr(comp, "polygon_points", None)
                if isinstance(poly, list) and poly and not str(getattr(comp, "point_type", "")):
                    if self._grid and getattr(self._grid, "magnet", False):
                        cols = max(2, int(getattr(self._grid, "columns", 24)))
                        step_x = 1.0 / float(cols)
                        step_y = (iw / float(cols)) / max(1.0, float(ih))
                    else:
                        step_x = 0.0
                        step_y = 0.0
                    prev_cx = float(getattr(comp, "x", 0.0))
                    prev_cy = float(getattr(comp, "y", 0.0))
                    nx = (px - self._drag_offset[0] - ix) / max(1, iw)
                    ny = (py - self._drag_offset[1] - iy) / max(1, ih)
                    if step_x > 0:
                        nx = round(nx / step_x) * step_x
                    if step_y > 0:
                        ny = round(ny / step_y) * step_y
                    nx = max(0.0, min(1.0 - comp.w, nx))
                    ny = max(0.0, min(1.0 - comp.h, ny))
                    dx = nx - prev_cx
                    dy = ny - prev_cy
                    moved = []
                    for pt in poly:
                        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                            moved.append([
                                max(0.0, min(1.0, float(pt[0]) + dx)),
                                max(0.0, min(1.0, float(pt[1]) + dy)),
                            ])
                    comp.polygon_points = moved
                    comp.x = nx
                    comp.y = ny
                    self._emit_components_changed()
                    self.update()
                    return
                if str(getattr(comp, "point_type", "")):
                    center_x = px
                    center_y = py
                    nx = snapx((center_x - ix) / max(1, iw))
                    ny = snapy((center_y - iy) / max(1, ih))
                    self._axis_snap_x_source = None
                    self._axis_snap_y_source = None
                    if self._point_axis_magnet:
                        snap_px = max(6, int(round(self._point_size * 0.8)))
                        snap_nx = snap_px / max(1.0, float(iw))
                        snap_ny = snap_px / max(1.0, float(ih))
                        best_x = None
                        best_dx = None
                        best_x_idx = None
                        best_y = None
                        best_dy = None
                        best_y_idx = None
                        for i, other in enumerate(self._markup_components):
                            if i == self._drag_component or not str(getattr(other, "point_type", "")):
                                continue
                            ox = float(getattr(other, "x", 0.5))
                            oy = float(getattr(other, "y", 0.5))
                            dx = abs(nx - ox)
                            dy = abs(ny - oy)
                            if dx <= snap_nx and (best_dx is None or dx < best_dx):
                                best_dx = dx
                                best_x = ox
                                best_x_idx = i
                            if dy <= snap_ny and (best_dy is None or dy < best_dy):
                                best_dy = dy
                                best_y = oy
                                best_y_idx = i
                        if best_x is not None:
                            nx = best_x
                            self._axis_snap_x_source = best_x_idx
                        if best_y is not None:
                            ny = best_y
                            self._axis_snap_y_source = best_y_idx
                    comp.x = max(0.0, min(1.0, nx))
                    comp.y = max(0.0, min(1.0, ny))
                else:
                    nx = (px - self._drag_offset[0] - ix) / max(1, iw)
                    ny = (py - self._drag_offset[1] - iy) / max(1, ih)
                    nx = snapx(nx)
                    ny = snapy(ny)
                    comp.x = max(0.0, min(1.0 - comp.w, nx))
                    comp.y = max(0.0, min(1.0 - comp.h, ny))
            else:
                if bool(getattr(comp, "lock_size", False)):
                    return
                old_ratio = max(1e-9, comp.w / max(1e-9, comp.h))
                x1, y1, x2, y2 = cx, cy, cx + cw, cy + ch
                if "left" in self._drag_mode:
                    x1 = min(x2 - min_px, max(ix, px))
                if "right" in self._drag_mode:
                    x2 = max(x1 + min_px, min(ix + iw, px))
                if "top" in self._drag_mode:
                    y1 = min(y2 - min_px, max(iy, py))
                if "bottom" in self._drag_mode:
                    y2 = max(y1 + min_px, min(iy + ih, py))
                nx1 = snapx((x1 - ix) / max(1, iw))
                ny1 = snapy((y1 - iy) / max(1, ih))
                nx2 = snapx((x2 - ix) / max(1, iw))
                ny2 = snapy((y2 - iy) / max(1, ih))
                nx1, nx2 = (nx1, nx2) if nx1 <= nx2 else (nx2, nx1)
                ny1, ny2 = (ny1, ny2) if ny1 <= ny2 else (ny2, ny1)
                if bool(getattr(comp, "lock_aspect", False)):
                    w = max(min_px / max(1, iw), nx2 - nx1)
                    h = max(min_px / max(1, ih), ny2 - ny1)
                    cur_ratio = w / max(1e-9, h)
                    if cur_ratio > old_ratio:
                        w = h * old_ratio
                    else:
                        h = w / old_ratio
                    nx2 = nx1 + w
                    ny2 = ny1 + h
                comp.x = max(0.0, min(1.0, nx1))
                comp.y = max(0.0, min(1.0, ny1))
                comp.w = max(min_px / max(1, iw), min(1.0, nx2 - nx1))
                comp.h = max(min_px / max(1, ih), min(1.0, ny2 - ny1))
                comp.w = min(comp.w, 1.0 - comp.x)
                comp.h = min(comp.h, 1.0 - comp.y)
            self._emit_components_changed()
            self.update()
            return

        if self._drag_polygon_edge is not None and (buttons & Qt.MouseButton.LeftButton):
            ci, ei = self._drag_polygon_edge
            if 0 <= ci < len(self._markup_components):
                comp = self._markup_components[ci]
                poly = getattr(comp, "polygon_points", None)
                state = self._drag_polygon_edge_state
                if isinstance(poly, list) and len(poly) >= 3 and isinstance(state, dict):
                    vi1 = int(state.get("vi1", -1))
                    vi2 = int(state.get("vi2", -1))
                    if 0 <= vi1 < len(poly) and 0 <= vi2 < len(poly):
                        s0x, s0y = state["s0"]
                        s1x, s1y = state["s1"]
                        s2x, s2y = state["s2"]
                        s3x, s3y = state["s3"]
                        msx, msy = state["mouse_start"]
                        nx, ny = state["normal"]
                        ix = float(state["ix"])
                        iy = float(state["iy"])
                        iw = max(1.0, float(state["iw"]))
                        ih = max(1.0, float(state["ih"]))
                        drag = ((mouse_x - msx) * nx) + ((mouse_y - msy) * ny)
                        m1x = s1x + nx * drag
                        m1y = s1y + ny * drag
                        m2x = s2x + nx * drag
                        m2y = s2y + ny * drag
                        n1 = self._line_intersection(s0x, s0y, s1x, s1y, m1x, m1y, m2x, m2y)
                        n2 = self._line_intersection(s2x, s2y, s3x, s3y, m1x, m1y, m2x, m2y)
                        if n1 is not None and n2 is not None:
                            p1x = max(0.0, min(1.0, (n1[0] - ix) / iw))
                            p1y = max(0.0, min(1.0, (n1[1] - iy) / ih))
                            p2x = max(0.0, min(1.0, (n2[0] - ix) / iw))
                            p2y = max(0.0, min(1.0, (n2[1] - iy) / ih))
                            if self._grid and getattr(self._grid, "magnet", False):
                                cols = max(2, int(getattr(self._grid, "columns", 24)))
                                step_x = 1.0 / float(cols)
                                step_y = (iw / float(cols)) / ih
                                p1x = self._quantize(p1x, step_x)
                                p1y = self._quantize(p1y, step_y)
                                p2x = self._quantize(p2x, step_x)
                                p2y = self._quantize(p2y, step_y)
                            poly[vi1] = [max(0.0, min(1.0, p1x)), max(0.0, min(1.0, p1y))]
                            poly[vi2] = [max(0.0, min(1.0, p2x)), max(0.0, min(1.0, p2y))]
                            comp.polygon_points = poly
                            xs = [float(p[0]) for p in poly if isinstance(p, (list, tuple)) and len(p) >= 2]
                            ys = [float(p[1]) for p in poly if isinstance(p, (list, tuple)) and len(p) >= 2]
                            if xs and ys:
                                comp.x = max(0.0, min(1.0, min(xs)))
                                comp.y = max(0.0, min(1.0, min(ys)))
                                comp.w = max(0.01, min(1.0, max(xs) - min(xs)))
                                comp.h = max(0.01, min(1.0, max(ys) - min(ys)))
                            self.setCursor(self._cursor_for_polygon_edge(ci, ei))
                            self._emit_components_changed()
                            self.update()
                            return

        if self._drag_polygon_vertex is not None and (buttons & Qt.MouseButton.LeftButton):
            ci, vi = self._drag_polygon_vertex
            if 0 <= ci < len(self._markup_components):
                comp = self._markup_components[ci]
                poly = getattr(comp, "polygon_points", None)
                if isinstance(poly, list) and 0 <= vi < len(poly):
                    ix, iy, iw, ih = self._inner_rect()
                    nx = (px - ix) / max(1, iw)
                    ny = (py - iy) / max(1, ih)
                    if self._grid and getattr(self._grid, "magnet", False):
                        cols = max(2, int(getattr(self._grid, "columns", 24)))
                        step_x = 1.0 / float(cols)
                        step_y = (iw / float(cols)) / max(1.0, float(ih))
                        nx = round(nx / step_x) * step_x
                        ny = round(ny / step_y) * step_y
                    self._axis_snap_x_source = None
                    self._axis_snap_y_source = None
                    if self._point_axis_magnet:
                        snap_px = max(6, int(round(self._point_size * 0.8)))
                        snap_nx = snap_px / max(1.0, float(iw))
                        snap_ny = snap_px / max(1.0, float(ih))
                        best_x = None
                        best_dx = None
                        best_x_idx = None
                        best_y = None
                        best_dy = None
                        best_y_idx = None
                        for oi, other in enumerate(self._markup_components):
                            other_poly = getattr(other, "polygon_points", None)
                            if not isinstance(other_poly, list):
                                continue
                            for ov, pt in enumerate(other_poly):
                                if not (isinstance(pt, (list, tuple)) and len(pt) >= 2):
                                    continue
                                if oi == ci and ov == vi:
                                    continue
                                ox = float(pt[0])
                                oy = float(pt[1])
                                dx = abs(nx - ox)
                                dy = abs(ny - oy)
                                if dx <= snap_nx and (best_dx is None or dx < best_dx):
                                    best_dx = dx
                                    best_x = ox
                                    best_x_idx = oi
                                if dy <= snap_ny and (best_dy is None or dy < best_dy):
                                    best_dy = dy
                                    best_y = oy
                                    best_y_idx = oi
                        if best_x is not None:
                            nx = best_x
                            self._axis_snap_x_source = best_x_idx
                        if best_y is not None:
                            ny = best_y
                            self._axis_snap_y_source = best_y_idx
                    poly[vi] = [max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))]
                    comp.polygon_points = poly
                    xs = [float(p[0]) for p in poly if isinstance(p, (list, tuple)) and len(p) >= 2]
                    ys = [float(p[1]) for p in poly if isinstance(p, (list, tuple)) and len(p) >= 2]
                    if xs and ys:
                        comp.x = max(0.0, min(1.0, min(xs)))
                        comp.y = max(0.0, min(1.0, min(ys)))
                        comp.w = max(0.01, min(1.0, max(xs) - min(xs)))
                        comp.h = max(0.01, min(1.0, max(ys) - min(ys)))
                    self._emit_components_changed()
                    self.update()
                    return

        if self._grid is not None and self._grid.show_border:
            edge = self._hit_edge(px, py)
            if edge is not None:
                self._set_cursor_for_edge(edge)
                return
        if self._hit_polygon_vertex(px, py, pad=8) is not None:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            return
        ehit = self._hit_polygon_edge(px, py, pad=7)
        if ehit is not None:
            self.setCursor(self._cursor_for_polygon_edge(*ehit))
            return
        hit = self._selected_component if 0 <= self._selected_component < len(self._markup_components) else -1
        if hit >= 0:
            mode = self._hit_component_mode(hit, px, py)
            cshape = self._cursor_for_mode(mode)
            if cshape is not None:
                self.setCursor(cshape)
                return
        self.unsetCursor()

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        # Prevent cursor/state lock when pointer leaves widget while dragging.
        self._drag_edge = None
        self._drag_component = -1
        self._drag_mode = None
        self._drag_polygon_vertex = None
        self._drag_polygon_edge = None
        self._drag_polygon_edge_state = None
        if not self._pan_active:
            self.unsetCursor()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_active = False
            self._pan_start = None
            self._pan_origin = None
            self.unsetCursor()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_edge = None
            self._drag_component = -1
            self._drag_mode = None
            self._drag_polygon_vertex = None
            self._drag_polygon_edge = None
            self._drag_polygon_edge_state = None
            self._axis_snap_x_source = None
            self._axis_snap_y_source = None
            self._set_cursor_for_edge(None)
        super().mouseReleaseEvent(event)



