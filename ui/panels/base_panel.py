from __future__ import annotations

from qt import QLabel, QFrame, QHBoxLayout, QMenu, QPushButton, QVBoxLayout, QWidget, Qt


class BasePanel(QWidget):
    COLLAPSED_CARD_HEIGHT = 46

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self._panel_title = title
        self._collapsed = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 6, 0, 0)
        root_layout.setSpacing(0)

        self.card = QFrame(self)
        self.card.setObjectName("PanelCard")
        self.card.setFrameShape(QFrame.Shape.StyledPanel)
        self.card.setFrameShadow(QFrame.Shadow.Plain)
        root_layout.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)

        self.header = QWidget(self.card)
        self.header.setFixedHeight(26)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.collapse_btn = QPushButton("▾", self.header)
        self.collapse_btn.setObjectName("PanelCollapseButton")
        self.collapse_btn.setFixedSize(22, 22)
        self.collapse_btn.clicked.connect(self.toggle_collapsed)
        header_layout.addWidget(self.collapse_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self.title_label = QLabel(title, self.header)
        self.title_label.setObjectName("PanelTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.title_label.setFixedHeight(26)
        header_layout.addWidget(self.title_label, 1)

        self.reorder_btn = QPushButton("≡", self.header)
        self.reorder_btn.setObjectName("PanelReorderButton")
        self.reorder_btn.setFixedSize(22, 22)
        self.reorder_btn.clicked.connect(self._show_reorder_menu)
        header_layout.addWidget(self.reorder_btn, 0, Qt.AlignmentFlag.AlignRight)
        card_layout.addWidget(self.header)

        self.content = QWidget(self.card)
        self._layout = QVBoxLayout(self.content)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(8)
        card_layout.addWidget(self.content)

        self._move_up_cb = None
        self._move_down_cb = None

    def set_reorder_callbacks(self, move_up_cb, move_down_cb) -> None:
        self._move_up_cb = move_up_cb
        self._move_down_cb = move_down_cb

    def _show_reorder_menu(self) -> None:
        menu = QMenu(self)
        up_action = menu.addAction("Move Up")
        down_action = menu.addAction("Move Down")
        chosen = menu.exec(self.reorder_btn.mapToGlobal(self.reorder_btn.rect().bottomLeft()))
        if chosen == up_action and callable(self._move_up_cb):
            self._move_up_cb()
        elif chosen == down_action and callable(self._move_down_cb):
            self._move_down_cb()

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = bool(collapsed)
        self.content.setVisible(not self._collapsed)
        self.collapse_btn.setText("▸" if self._collapsed else "▾")
        if self._collapsed:
            self.card.setMinimumHeight(self.COLLAPSED_CARD_HEIGHT)
            self.card.setMaximumHeight(self.COLLAPSED_CARD_HEIGHT)
        else:
            self.card.setMinimumHeight(0)
            self.card.setMaximumHeight(16777215)
        self.updateGeometry()

    def is_collapsed(self) -> bool:
        return self._collapsed

    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._layout
