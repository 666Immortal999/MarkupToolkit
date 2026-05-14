"""Qt compatibility layer: prefer PyQt6, fallback to PySide6."""

try:
    from PyQt6.QtCore import QObject, Qt, Signal, QTimer, QPoint  # type: ignore[reportMissingImports]
    from PyQt6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut  # type: ignore[reportMissingImports]
    from PyQt6.QtWidgets import (  # type: ignore[reportMissingImports]
        QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
        QFileDialog, QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMenu, QMenuBar, QMessageBox,
        QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QSplitter, QStackedWidget,
        QStatusBar, QVBoxLayout, QWidget,
    )
except ImportError:
    from PySide6.QtCore import QObject, Qt, Signal, QTimer, QPoint  # type: ignore[reportMissingImports]
    from PySide6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut  # type: ignore[reportMissingImports]
    from PySide6.QtWidgets import (  # type: ignore[reportMissingImports]
        QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
        QFileDialog, QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMenu, QMenuBar, QMessageBox,
        QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QSplitter, QStackedWidget,
        QStatusBar, QVBoxLayout, QWidget,
    )
