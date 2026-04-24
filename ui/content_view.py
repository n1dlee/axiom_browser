from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView


class _AxiomPage(QWebEnginePage):
    """
    Custom QWebEnginePage that routes new-window / new-tab requests
    (middle-click, Ctrl+click, target="_blank", window.open()) back to
    the owning view via a factory callback so the main window can open
    a proper background tab.
    """

    def __init__(self, profile: QWebEngineProfile, parent=None) -> None:
        super().__init__(profile, parent)
        self._factory: Optional[Callable[[], Optional[QWebEnginePage]]] = None

    def set_factory(self, factory: Callable[[], Optional[QWebEnginePage]]) -> None:
        self._factory = factory

    def createWindow(
        self, win_type: "QWebEnginePage.WebWindowType"
    ) -> Optional[QWebEnginePage]:
        if self._factory is not None:
            return self._factory()
        return None


class AxiomContentView(QWebEngineView):
    page_title_changed = pyqtSignal(int, str)   # tab_id, title
    page_url_changed   = pyqtSignal(int, QUrl)  # tab_id, url
    page_load_finished = pyqtSignal(int, bool)  # tab_id, ok
    page_icon_changed  = pyqtSignal(int)         # tab_id

    # Emitted when the page requests a new tab (middle / Ctrl+click, _blank).
    # The main window must respond synchronously by calling accept_new_page().
    new_window_needed = pyqtSignal()

    def __init__(
        self,
        tab_id: int,
        profile: QWebEngineProfile,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._tab_id = tab_id
        self._profile = profile
        self._pending_new_page: Optional[QWebEnginePage] = None
        self._setup_page(profile)
        self._connect_signals()

    # ── Setup ─────────────────────────────────────────────────────────

    def _setup_page(self, profile: QWebEngineProfile) -> None:
        page = _AxiomPage(profile, self)
        page.set_factory(self._on_new_page_requested)
        self.setPage(page)

    def _connect_signals(self) -> None:
        self.titleChanged.connect(self._on_title_changed)
        self.urlChanged.connect(self._on_url_changed)
        self.loadFinished.connect(self._on_load_finished)
        self.iconChanged.connect(self._on_icon_changed)

    # ── New-window plumbing ───────────────────────────────────────────

    def _on_new_page_requested(self) -> Optional[QWebEnginePage]:
        """
        Called synchronously by _AxiomPage.createWindow().
        Emits new_window_needed — the connected slot in main_window is
        also called synchronously (Qt direct connection) and must call
        accept_new_page() before returning so we can hand the page back
        to Chromium.
        """
        self._pending_new_page = None
        self.new_window_needed.emit()
        return self._pending_new_page

    def accept_new_page(self, page: QWebEnginePage) -> None:
        """Called by main_window in response to new_window_needed."""
        self._pending_new_page = page

    # ── Signal forwarders ─────────────────────────────────────────────

    def _on_title_changed(self, title: str) -> None:
        self.page_title_changed.emit(self._tab_id, title)

    def _on_url_changed(self, url: QUrl) -> None:
        self.page_url_changed.emit(self._tab_id, url)

    def _on_load_finished(self, ok: bool) -> None:
        self.page_load_finished.emit(self._tab_id, ok)

    def _on_icon_changed(self) -> None:
        self.page_icon_changed.emit(self._tab_id)

    # ── Public API ────────────────────────────────────────────────────

    def navigate(self, url: str) -> None:
        self.load(QUrl(url))

    def suspend(self) -> None:
        self.page().setLifecycleState(QWebEnginePage.LifecycleState.Discarded)

    def resume(self) -> None:
        self.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)

    @property
    def tab_id(self) -> int:
        return self._tab_id
