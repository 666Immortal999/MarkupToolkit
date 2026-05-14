from qt import QVBoxLayout, QWidget


class UIBoxesOverlay(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        QVBoxLayout(self)
