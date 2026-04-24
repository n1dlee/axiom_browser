from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLineEdit, QSizePolicy, QFrame,
)


class AxiomAddressBar(QWidget):
    navigate_requested = pyqtSignal(str)
    back_requested = pyqtSignal()
    forward_requested = pyqtSignal()
    reload_requested = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbar")
        self._is_loading = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(4)

        self._back_btn = self._nav_btn("←", "Go back  (Alt+Left)")
        self._forward_btn = self._nav_btn("→", "Go forward  (Alt+Right)")
        self._reload_btn = self._nav_btn("↻", "Reload  (F5)")
        self._back_btn.setEnabled(False)
        self._forward_btn.setEnabled(False)

        # Thin vertical divider
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background: rgba(100,120,255,0.18);")

        self._url_input = QLineEdit()
        self._url_input.setObjectName("omnibox")
        self._url_input.setPlaceholderText("Search or enter URL…")
        self._url_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._url_input.setFixedHeight(32)

        layout.addWidget(self._back_btn)
        layout.addWidget(self._forward_btn)
        layout.addWidget(self._reload_btn)
        layout.addSpacing(4)
        layout.addWidget(sep)
        layout.addSpacing(6)
        layout.addWidget(self._url_input)

    def _nav_btn(self, symbol: str, tooltip: str) -> QPushButton:
        btn = QPushButton(symbol)
        btn.setObjectName("nav-btn")
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _connect_signals(self) -> None:
        self._back_btn.clicked.connect(self.back_requested)
        self._forward_btn.clicked.connect(self.forward_requested)
        self._reload_btn.clicked.connect(self._on_reload_clicked)
        self._url_input.returnPressed.connect(self._on_return_pressed)

    def _on_return_pressed(self) -> None:
        text = self._url_input.text().strip()
        if text:
            self.navigate_requested.emit(text)

    def _on_reload_clicked(self) -> None:
        self.reload_requested.emit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_url(self, url: str) -> None:
        if not self._url_input.hasFocus():
            self._url_input.setText(url)

    def set_loading(self, loading: bool) -> None:
        self._is_loading = loading
        self._reload_btn.setText("✕" if loading else "↻")
        self._reload_btn.setToolTip("Stop" if loading else "Reload  (F5)")

    def set_back_enabled(self, enabled: bool) -> None:
        self._back_btn.setEnabled(enabled)

    def set_forward_enabled(self, enabled: bool) -> None:
        self._forward_btn.setEnabled(enabled)
