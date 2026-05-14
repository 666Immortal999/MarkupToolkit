from __future__ import annotations

from qt import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QSpinBox, Qt

from ui.panels.base_panel import BasePanel


class GridPanel(BasePanel):
    ROW_H = 26
    STEP_BTN = 32

    def __init__(self, grid_settings, parent=None) -> None:
        super().__init__("Grid", parent)
        self.grid_settings = grid_settings

        layout = self.layout()
        form = QGridLayout()
        form.setHorizontalSpacing(4)
        form.setVerticalSpacing(6)
        form.setColumnStretch(0, 0)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(2, 0)
        form.setColumnStretch(3, 0)

        self.enabled_cb = QCheckBox("Show Grid", self)
        self.enabled_cb.setChecked(self.grid_settings.enabled)
        self.magnet_cb = QCheckBox("Snap To Grid", self)
        self.magnet_cb.setChecked(self.grid_settings.magnet)
        self.border_cb = QCheckBox("Show Border", self)
        self.border_cb.setChecked(self.grid_settings.show_border)
        self.cols_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.cols_slider.setRange(8, 1024)
        self.cols_slider.setValue(self.grid_settings.columns)
        self.cols_slider.setEnabled(not self.grid_settings.lock_columns)
        self.cols_value = QLabel(str(self.grid_settings.columns), self)
        self.cols_dec_btn = QPushButton("-", self)
        self.cols_dec_btn.setFixedSize(self.STEP_BTN, self.STEP_BTN)
        self.cols_dec_btn.setFlat(True)
        self.cols_dec_btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; }")
        self.cols_inc_btn = QPushButton("+", self)
        self.cols_inc_btn.setFixedSize(self.STEP_BTN, self.STEP_BTN)
        self.cols_inc_btn.setFlat(True)
        self.cols_inc_btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; }")
        self.cols_lock = self._make_lock(self.cols_slider)
        self.cols_lock.setChecked(bool(self.grid_settings.lock_columns))
        self.cols_lock.setText("🔒" if self.cols_lock.isChecked() else "🔓")
        self.cols_slider.setEnabled(not self.cols_lock.isChecked())

        self.width_spin = QSpinBox(self)
        self.width_spin.setRange(1, 8)
        self.width_spin.setValue(self.grid_settings.border_width)
        self.width_spin.setFixedHeight(self.ROW_H)
        try:
            self.width_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        except Exception:
            pass
        self.width_lock = self._make_lock(self.width_spin)

        self.left_edit = self._make_edit(self.grid_settings.margins["left"])
        self.top_edit = self._make_edit(self.grid_settings.margins["top"])
        self.right_edit = self._make_edit(self.grid_settings.margins["right"])
        self.bottom_edit = self._make_edit(self.grid_settings.margins["bottom"])

        self.left_lock = self._make_lock(self.left_edit)
        self.top_lock = self._make_lock(self.top_edit)
        self.right_lock = self._make_lock(self.right_edit)
        self.bottom_lock = self._make_lock(self.bottom_edit)

        form.addWidget(self.enabled_cb, 0, 0, 1, 3)
        form.addWidget(self.magnet_cb, 1, 0, 1, 3)
        form.addWidget(self.border_cb, 2, 0, 1, 3)

        form.addWidget(QLabel("Columns"), 3, 0)
        form.addWidget(self.cols_value, 3, 1, 1, 3, alignment=Qt.AlignmentFlag.AlignRight)
        cols_row = QHBoxLayout()
        cols_row.setContentsMargins(0, 0, 8, 0)
        cols_row.setSpacing(6)
        cols_row.setStretch(0, 0)
        cols_row.setStretch(1, 1)
        cols_row.setStretch(2, 0)
        cols_row.setStretch(3, 0)
        cols_row.addWidget(self.cols_dec_btn, 0)
        cols_row.addWidget(self.cols_slider, 1)
        cols_row.addWidget(self.cols_inc_btn, 0)
        cols_row.addWidget(self.cols_lock, 0)
        form.addLayout(cols_row, 4, 0, 1, 4)

        self._add_row(form, 5, "Left", self.left_edit, self.left_lock)
        self._add_row(form, 6, "Top", self.top_edit, self.top_lock)
        self._add_row(form, 7, "Right", self.right_edit, self.right_lock)
        self._add_row(form, 8, "Bottom", self.bottom_edit, self.bottom_lock)
        self._add_row(form, 9, "Border Width", self.width_spin, self.width_lock)

        layout.addLayout(form)

        self.enabled_cb.toggled.connect(self._apply)
        self.magnet_cb.toggled.connect(self._apply)
        self.border_cb.toggled.connect(self._apply)
        self.cols_lock.clicked.connect(lambda: self._on_lock_toggled(self.cols_lock.isChecked()))
        self.cols_slider.valueChanged.connect(lambda v: self.cols_value.setText(str(v)))
        self.cols_dec_btn.clicked.connect(lambda: self.cols_slider.setValue(self.cols_slider.value() - 1))
        self.cols_inc_btn.clicked.connect(lambda: self.cols_slider.setValue(self.cols_slider.value() + 1))
        self.cols_slider.valueChanged.connect(self._apply)
        self.width_spin.valueChanged.connect(self._apply)
        self.left_edit.editingFinished.connect(self._apply)
        self.top_edit.editingFinished.connect(self._apply)
        self.right_edit.editingFinished.connect(self._apply)
        self.bottom_edit.editingFinished.connect(self._apply)

        self.grid_settings.subscribe(self._sync_from_state)

    def _make_edit(self, value: int) -> QLineEdit:
        edit = QLineEdit(str(value), self)
        edit.setFixedHeight(self.ROW_H)
        return edit

    def _make_lock(self, target_widget):
        # Open by default because fields are editable initially.
        btn = QPushButton("🔓", self)
        btn.setObjectName("LockButton")
        btn.setCheckable(True)
        btn.setChecked(False)
        btn.setFixedSize(self.ROW_H, self.ROW_H)
        btn.clicked.connect(lambda: self._toggle_lock(target_widget, btn))
        return btn

    def _add_row(self, form: QGridLayout, row: int, label: str, field, lock_btn: QPushButton) -> None:
        lbl = QLabel(label, self)
        lbl.setObjectName("GridRowLabel")
        lbl.setFixedHeight(self.ROW_H)
        form.addWidget(lbl, row, 0)
        form.addWidget(field, row, 1)
        form.addWidget(lock_btn, row, 2)

    def _toggle_lock(self, target_widget, lock_btn: QPushButton):
        locked = lock_btn.isChecked()
        target_widget.setEnabled(not locked)
        lock_btn.setText("🔒" if locked else "🔓")

    def _to_int(self, text: str) -> int:
        try:
            return max(0, int(text.strip() or "0"))
        except Exception:
            return 0

    def _on_lock_toggled(self, checked: bool) -> None:
        self.cols_slider.setEnabled(not checked)
        self.cols_dec_btn.setEnabled(not checked)
        self.cols_inc_btn.setEnabled(not checked)
        self._apply()

    def _apply(self, *_args) -> None:
        self.grid_settings.enabled = self.enabled_cb.isChecked()
        self.grid_settings.magnet = self.magnet_cb.isChecked()
        self.grid_settings.show_border = self.border_cb.isChecked()
        self.grid_settings.lock_columns = self.cols_lock.isChecked()
        self.grid_settings.columns = int(self.cols_slider.value())
        self.grid_settings.border_width = int(self.width_spin.value())
        self.grid_settings.set_margins(
            {
                "left": self._to_int(self.left_edit.text()),
                "top": self._to_int(self.top_edit.text()),
                "right": self._to_int(self.right_edit.text()),
                "bottom": self._to_int(self.bottom_edit.text()),
            }
        )

    def _sync_from_state(self) -> None:
        m = self.grid_settings.margins
        self.enabled_cb.setChecked(self.grid_settings.enabled)
        self.magnet_cb.setChecked(self.grid_settings.magnet)
        self.border_cb.setChecked(self.grid_settings.show_border)
        self.cols_lock.setChecked(bool(self.grid_settings.lock_columns))
        self.cols_lock.setText("🔒" if self.cols_lock.isChecked() else "🔓")
        self.cols_slider.setEnabled(not self.cols_lock.isChecked())
        self.cols_dec_btn.setEnabled(not self.cols_lock.isChecked())
        self.cols_inc_btn.setEnabled(not self.cols_lock.isChecked())
        self.cols_slider.setValue(int(self.grid_settings.columns))
        self.cols_value.setText(str(self.grid_settings.columns))
        self.width_spin.setValue(int(self.grid_settings.border_width))
        self.left_edit.setText(str(m["left"]))
        self.top_edit.setText(str(m["top"]))
        self.right_edit.setText(str(m["right"]))
        self.bottom_edit.setText(str(m["bottom"]))

    def get_state(self) -> dict:
        return {
            "enabled": self.enabled_cb.isChecked(),
            "magnet": self.magnet_cb.isChecked(),
            "show_border": self.border_cb.isChecked(),
            "lock_columns": self.cols_lock.isChecked(),
            "columns": int(self.cols_slider.value()),
            "border_width": int(self.width_spin.value()),
            "margins": {
                "left": self._to_int(self.left_edit.text()),
                "top": self._to_int(self.top_edit.text()),
                "right": self._to_int(self.right_edit.text()),
                "bottom": self._to_int(self.bottom_edit.text()),
            },
            "locks": {
                "left": self.left_lock.isChecked(),
                "top": self.top_lock.isChecked(),
                "right": self.right_lock.isChecked(),
                "bottom": self.bottom_lock.isChecked(),
                "border_width": self.width_lock.isChecked(),
            },
        }

    def apply_state(self, state: dict) -> None:
        self.enabled_cb.setChecked(bool(state.get("enabled", self.enabled_cb.isChecked())))
        self.magnet_cb.setChecked(bool(state.get("magnet", self.magnet_cb.isChecked())))
        self.border_cb.setChecked(bool(state.get("show_border", self.border_cb.isChecked())))
        lock_columns = bool(state.get("lock_columns", self.cols_lock.isChecked()))
        self.cols_lock.setChecked(lock_columns)
        self.cols_lock.setText("🔒" if lock_columns else "🔓")
        self.cols_slider.setEnabled(not lock_columns)
        self.cols_dec_btn.setEnabled(not lock_columns)
        self.cols_inc_btn.setEnabled(not lock_columns)

        self.cols_slider.setValue(max(8, min(1024, int(state.get("columns", self.cols_slider.value())))))
        self.width_spin.setValue(max(1, min(8, int(state.get("border_width", self.width_spin.value())))))

        margins = state.get("margins", {})
        self.left_edit.setText(str(int(margins.get("left", self._to_int(self.left_edit.text())))))
        self.top_edit.setText(str(int(margins.get("top", self._to_int(self.top_edit.text())))))
        self.right_edit.setText(str(int(margins.get("right", self._to_int(self.right_edit.text())))))
        self.bottom_edit.setText(str(int(margins.get("bottom", self._to_int(self.bottom_edit.text())))))

        locks = state.get("locks", {})
        for btn, field, key in (
            (self.left_lock, self.left_edit, "left"),
            (self.top_lock, self.top_edit, "top"),
            (self.right_lock, self.right_edit, "right"),
            (self.bottom_lock, self.bottom_edit, "bottom"),
            (self.width_lock, self.width_spin, "border_width"),
        ):
            locked = bool(locks.get(key, False))
            btn.setChecked(locked)
            btn.setText("🔒" if locked else "🔓")
            field.setEnabled(not locked)

        self._apply()
