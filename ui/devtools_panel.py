from typing import Optional

from PyQt6.QtCore import QObject
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from ui.theme import SURFACE_1, SEPARATOR


class AxiomDevToolsPanel(QWidget):
    """
    Real Chromium DevTools docked panel.

    Usage:
        panel.open_for(profile, page)   # show and attach to a page
        panel.close_panel()             # hide
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._profile: Optional[QWebEngineProfile] = None
        self._devtools_view: Optional[QWebEngineView] = None
        self._devtools_page: Optional[QWebEnginePage] = None
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._placeholder = QWidget()
        self._placeholder.setStyleSheet(f"background: {SURFACE_1}; border-top: 1px solid {SEPARATOR};")
        layout.addWidget(self._placeholder)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_for(self, profile: QWebEngineProfile, page: QWebEnginePage) -> None:
        """Attach DevTools to the given page and show the panel."""
        self._profile = profile

        # Reuse or create the devtools view
        if self._devtools_view is None:
            self._devtools_view = QWebEngineView(self)
            self._devtools_page = QWebEnginePage(profile, self._devtools_view)
            self._devtools_view.setPage(self._devtools_page)
            self.layout().replaceWidget(self._placeholder, self._devtools_view)
            self._placeholder.hide()

        # Point inspector at the new page
        self._devtools_page.setInspectedPage(page)  # type: ignore[union-attr]
        self.show()

    def close_panel(self) -> None:
        self.hide()

    def is_open(self) -> bool:
        return self.isVisible()
