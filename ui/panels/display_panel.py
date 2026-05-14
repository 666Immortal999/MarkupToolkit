from __future__ import annotations

from qt import QCheckBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, Qt

from ui.panels.base_panel import BasePanel


class DisplayPanel(BasePanel):
    def __init__(self, parent=None) -> None:
        super().__init__("Display", parent)
        layout: QVBoxLayout = self.layout()

        self.show_overlay_cb = QCheckBox("Show Overlay", self)
        self.show_overlay_cb.setChecked(True)
        layout.addWidget(self.show_overlay_cb)

        self.show_labels_cb = QCheckBox("Show Component Names", self)
        self.show_labels_cb.setChecked(True)
        layout.addWidget(self.show_labels_cb)

        self.show_sizes_cb = QCheckBox("Show Sizes In Pixels", self)
        self.show_sizes_cb.setChecked(False)
        layout.addWidget(self.show_sizes_cb)
        self.show_hatch_cb = QCheckBox("Show Polygon Hatch", self)
        self.show_hatch_cb.setChecked(True)
        layout.addWidget(self.show_hatch_cb)

        self.point_size_label = QLabel("Point Size", self)
        layout.addWidget(self.point_size_label)
        self.point_size_value = QLabel(str(10), self)
        self.point_size_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.point_size_value)
        point_row = QHBoxLayout()
        point_row.setContentsMargins(0, 0, 8, 0)
        point_row.setSpacing(6)
        point_row.setStretch(0, 0)
        point_row.setStretch(1, 1)
        point_row.setStretch(2, 0)
        point_row.setStretch(3, 0)
        self.point_size_dec_btn = QPushButton("-", self)
        self.point_size_dec_btn.setFixedSize(32, 32)
        self.point_size_dec_btn.setFlat(True)
        self.point_size_dec_btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; }")
        point_row.addWidget(self.point_size_dec_btn, 0)
        self.point_size_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.point_size_slider.setRange(4, 32)
        self.point_size_slider.setValue(10)
        point_row.addWidget(self.point_size_slider, 1)
        self.point_size_inc_btn = QPushButton("+", self)
        self.point_size_inc_btn.setFixedSize(32, 32)
        self.point_size_inc_btn.setFlat(True)
        self.point_size_inc_btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; }")
        point_row.addWidget(self.point_size_inc_btn, 0)
        self.point_size_lock = QPushButton("🔓", self)
        self.point_size_lock.setObjectName("LockButton")
        self.point_size_lock.setCheckable(True)
        self.point_size_lock.setChecked(False)
        self.point_size_lock.setFixedSize(32, 32)
        self.point_size_lock.clicked.connect(self._on_point_size_lock_toggled)
        point_row.addWidget(self.point_size_lock, 0)
        layout.addLayout(point_row)

        self.point_size_dec_btn.clicked.connect(lambda: self.point_size_slider.setValue(self.point_size_slider.value() - 1))
        self.point_size_inc_btn.clicked.connect(lambda: self.point_size_slider.setValue(self.point_size_slider.value() + 1))
        self.point_size_slider.valueChanged.connect(lambda v: self.point_size_value.setText(str(int(v))))

        self.point_axis_magnet_cb = QCheckBox("Point Axis Magnet", self)
        self.point_axis_magnet_cb.setChecked(True)
        layout.addWidget(self.point_axis_magnet_cb)

        self.point_grid_coords_label = QLabel("Point Grid Coords: -", self)
        layout.addWidget(self.point_grid_coords_label)

    def get_state(self) -> dict:
        return {
            "show_overlay": self.show_overlay_cb.isChecked(),
            "show_labels": self.show_labels_cb.isChecked(),
            "show_sizes": self.show_sizes_cb.isChecked(),
            "show_hatch": self.show_hatch_cb.isChecked(),
            "point_size": self.point_size_slider.value(),
            "point_size_locked": self.point_size_lock.isChecked(),
            "point_axis_magnet": self.point_axis_magnet_cb.isChecked(),
        }

    def apply_state(self, state: dict) -> None:
        self.show_overlay_cb.setChecked(bool(state.get("show_overlay", self.show_overlay_cb.isChecked())))
        self.show_labels_cb.setChecked(bool(state.get("show_labels", self.show_labels_cb.isChecked())))
        self.show_sizes_cb.setChecked(bool(state.get("show_sizes", self.show_sizes_cb.isChecked())))
        self.show_hatch_cb.setChecked(bool(state.get("show_hatch", self.show_hatch_cb.isChecked())))
        self.point_size_slider.setValue(int(state.get("point_size", self.point_size_slider.value())))
        point_size_locked = bool(state.get("point_size_locked", self.point_size_lock.isChecked()))
        self.point_size_lock.setChecked(point_size_locked)
        self.point_size_lock.setText("🔒" if point_size_locked else "🔓")
        self.point_size_slider.setEnabled(not point_size_locked)
        self.point_size_dec_btn.setEnabled(not point_size_locked)
        self.point_size_inc_btn.setEnabled(not point_size_locked)
        self.point_axis_magnet_cb.setChecked(bool(state.get("point_axis_magnet", self.point_axis_magnet_cb.isChecked())))

    def set_point_grid_coords_text(self, text: str) -> None:
        self.point_grid_coords_label.setText(f"Point Grid Coords: {text or '-'}")

    def _on_point_size_lock_toggled(self) -> None:
        locked = self.point_size_lock.isChecked()
        self.point_size_lock.setText("🔒" if locked else "🔓")
        self.point_size_slider.setEnabled(not locked)
        self.point_size_dec_btn.setEnabled(not locked)
        self.point_size_inc_btn.setEnabled(not locked)
