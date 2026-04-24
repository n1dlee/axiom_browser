import base64
import logging
import os
from typing import Optional

from PyQt6.QtCore import QTimer, QUrl, Qt

_log = logging.getLogger(__name__)
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut, QIcon, QPixmap
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QSplitter,
)

from core.engine import BrowserEngine
from core.tab_manager import TabManager
from core.navigation import NavigationManager
from core.adblock import AdBlockInterceptor
from storage.cache_manager import CacheManager
from storage.history_manager import HistoryManager
from storage.downloads_manager import DownloadsManager, DownloadStatus
from storage.session_manager import SessionManager, TabSession
from storage.bookmarks_manager import BookmarksManager, Bookmark
from system.settings_manager import SettingsManager
from system.resource_manager import ResourceManager
from ui.tab_bar import AxiomTabBar
from ui.address_bar import AxiomAddressBar
from ui.content_view import AxiomContentView
from ui.bookmarks_bar import AxiomBookmarksBar
from ui.devtools_panel import AxiomDevToolsPanel
from ui.settings_page import AxiomSettingsPage
from ui.history_page import AxiomHistoryPage
from ui.downloads_page import AxiomDownloadsPage
from ui.download_bar import AxiomDownloadBar
from ui.sidebar import AxiomSidebar
from ui.theme import build_global_qss, BG

_SPECIAL_URLS = frozenset({"axiom://settings", "axiom://history", "axiom://downloads"})


def _downloads_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Downloads")


def _data_path(filename: str) -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    data_dir = os.path.join(base, "Axiom")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)


class AxiomMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._settings = SettingsManager()
        self._settings.load()           # load early so nav manager gets the right URL

        self._engine = BrowserEngine()
        self._tab_mgr = TabManager(parent=self)
        # Inject the user's preferred search engine URL at construction time
        # so resolve_input() never silently falls back to the hard-coded default.
        _search_url = self._settings.get(
            "search.engine_url", "https://www.google.com/search?q={}"
        )
        self._nav_mgr = NavigationManager(search_url=_search_url)
        self._history = HistoryManager(db_path=_data_path("history.db"))
        self._downloads = DownloadsManager(db_path=_data_path("downloads.db"))
        self._session = SessionManager()
        self._bookmarks = BookmarksManager()
        self._adblock: AdBlockInterceptor

        self._sidebar: AxiomSidebar
        self._tab_bar: AxiomTabBar
        self._address_bar: AxiomAddressBar
        self._bookmarks_bar: AxiomBookmarksBar
        self._devtools_panel: AxiomDevToolsPanel
        self._download_bar: AxiomDownloadBar
        self._stack: QStackedWidget

        # _views holds AxiomContentView or any special page widget
        self._views: dict[int, QWidget] = {}

        # Special tab tracking: axiom://xxx → tab_id
        self._special_tabs: dict[str, int] = {}
        # Quick reference to settings page for signal wiring refresh
        self._settings_page: Optional[AxiomSettingsPage] = None
        # Recently-closed URLs for Ctrl+Shift+T (max 25 entries)
        self._closed_tabs_stack: list[str] = []

        self._resource_mgr: ResourceManager

        self._initialize()

    # ──────────────────────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────────────────────

    def _initialize(self) -> None:
        # settings already loaded in __init__ before NavigationManager construction
        self._bookmarks.load()

        self._adblock = AdBlockInterceptor()
        self._adblock.enabled = self._settings.get("adblock_enabled", True)

        profile = self._engine.initialize(interceptor=self._adblock)

        download_dir = self._settings.get("downloads.save_directory") or _downloads_dir()
        self._engine.set_download_path(download_dir)
        profile.downloadRequested.connect(self._on_download_requested)

        cache_mgr = CacheManager(profile)
        cache_mgr.configure(max_size_mb=self._settings.get("performance.max_cache_mb", 256))

        self._history.connect()
        self._downloads.connect()

        self._setup_ui()
        self._wire_signals()
        self._restore_or_new_tab()
        self._register_shortcuts()

        self._resource_mgr = ResourceManager(self._tab_mgr)
        timer = QTimer(self)
        timer.setInterval(30_000)
        timer.timeout.connect(self._check_memory_pressure)
        timer.start()

        self.show()

    def _setup_ui(self) -> None:
        self.setWindowTitle("AXIOM")
        self.resize(
            self._settings.get("window.width", 1280),
            self._settings.get("window.height", 820),
        )
        self.setMinimumSize(
            self._settings.get("window.min_width", 960),
            self._settings.get("window.min_height", 640),
        )
        self.setStyleSheet(build_global_qss())

        # ── Root: horizontal split (sidebar | browser area) ──────────
        root = QWidget()
        root.setObjectName("root")
        root.setStyleSheet(f"QWidget#root {{ background: {BG}; }}")
        self.setCentralWidget(root)

        h_layout = QHBoxLayout(root)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # Sidebar
        self._sidebar = AxiomSidebar(self._adblock)
        h_layout.addWidget(self._sidebar)

        # ── Right area: vertical stack ───────────────────────────────
        right = QWidget()
        right.setObjectName("browser-area")
        v_layout = QVBoxLayout(right)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        self._tab_bar = AxiomTabBar()
        v_layout.addWidget(self._tab_bar)

        self._address_bar = AxiomAddressBar()
        v_layout.addWidget(self._address_bar)

        bar_visible = self._settings.get("bookmarks_bar_visible", True)
        self._bookmarks_bar = AxiomBookmarksBar()
        self._bookmarks_bar.setVisible(bar_visible)
        self._bookmarks_bar.load_bookmarks(self._bookmarks.get_all())
        v_layout.addWidget(self._bookmarks_bar)

        self._stack = QStackedWidget()
        self._devtools_panel = AxiomDevToolsPanel()
        self._devtools_panel.setMinimumHeight(200)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._stack)
        splitter.addWidget(self._devtools_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([600, 300])
        splitter.setChildrenCollapsible(False)
        self._content_splitter = splitter
        v_layout.addWidget(splitter)

        # Download shelf — sits at the very bottom, hidden until a download starts
        self._download_bar = AxiomDownloadBar()
        v_layout.addWidget(self._download_bar)

        h_layout.addWidget(right, 1)

        # Sync sidebar active states
        self._sidebar.set_bookmarks_active(bar_visible)

    def _wire_signals(self) -> None:
        # Tab manager
        self._tab_mgr.tab_created.connect(self._on_tab_created)
        self._tab_mgr.tab_closed.connect(self._on_tab_closed)
        self._tab_mgr.tab_switched.connect(self._on_tab_switched)
        self._tab_mgr.tab_suspended.connect(self._on_tab_suspended)
        self._tab_mgr.tab_resumed.connect(self._on_tab_resumed)

        # Tab bar — standard
        self._tab_bar.tab_changed.connect(self._on_tab_bar_changed)
        self._tab_bar.tab_close_requested.connect(self._on_close_requested)
        self._tab_bar.new_tab_requested.connect(self._on_new_tab_requested)

        # Tab bar — context menu actions
        self._tab_bar.tab_duplicate_requested.connect(self._on_tab_duplicate)
        self._tab_bar.tab_close_others_requested.connect(self._on_tab_close_others)
        self._tab_bar.tab_close_right_requested.connect(self._on_tab_close_right)

        # Address bar
        self._address_bar.navigate_requested.connect(self._on_navigate)
        self._address_bar.back_requested.connect(self._on_back)
        self._address_bar.forward_requested.connect(self._on_forward)
        self._address_bar.reload_requested.connect(self._on_reload)

        # Sidebar
        self._sidebar.bookmarks_toggled.connect(self._on_bookmarks_bar_toggled)
        self._sidebar.settings_requested.connect(self._on_settings_requested)
        self._sidebar.adblock_toggled.connect(self._on_adblock_toggled)
        self._sidebar.history_requested.connect(self._on_history_requested)
        self._sidebar.downloads_requested.connect(self._on_downloads_requested)

        # Bookmarks bar
        self._bookmarks_bar.navigate_requested.connect(self._on_navigate)
        self._bookmarks_bar.bookmark_removed.connect(self._on_bookmark_removed)
        self._bookmarks_bar.add_bookmark_requested.connect(self._add_current_bookmark)

        # Download bar
        self._download_bar.open_downloads_page.connect(self._on_downloads_requested)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_F12),       self).activated.connect(self._toggle_devtools)
        QShortcut(QKeySequence("Ctrl+D"),             self).activated.connect(self._add_current_bookmark)
        QShortcut(QKeySequence("Ctrl+Shift+B"),       self).activated.connect(self._toggle_bookmarks_bar)
        QShortcut(QKeySequence("Ctrl+T"),             self).activated.connect(self._on_new_tab_requested)
        QShortcut(QKeySequence("Ctrl+Shift+T"),       self).activated.connect(self._reopen_closed_tab)
        QShortcut(QKeySequence("Ctrl+W"),             self).activated.connect(self._close_active_tab)
        QShortcut(QKeySequence(Qt.Key.Key_F5),        self).activated.connect(self._on_reload)
        QShortcut(QKeySequence("Ctrl+H"),             self).activated.connect(self._on_history_requested)
        QShortcut(QKeySequence("Ctrl+J"),             self).activated.connect(self._on_downloads_requested)

    def _restore_or_new_tab(self) -> None:
        should_restore = self._settings.get("startup.restore_session", True)
        restored: Optional[list[TabSession]] = None
        if should_restore:
            restored = self._session.restore_session()
        if restored:
            active_id: Optional[int] = None
            for ts in restored:
                # Don't restore special tabs — open home page instead
                url = ts.url if ts.url not in _SPECIAL_URLS else self._settings.get("startup.home_url", "https://www.google.com")
                tab_id = self._tab_mgr.create_tab(url)
                # Restore the saved title immediately so the tab strip is
                # readable before the page finishes loading (async title
                # updates from the engine will overwrite this once loaded).
                if ts.title:
                    self._tab_bar.update_tab_title(tab_id, ts.title)
                self._tab_mgr.switch_to(tab_id)
                self._tab_bar.set_active_tab(tab_id)
                if ts.is_active:
                    active_id = tab_id
            if active_id is not None:
                self._tab_mgr.switch_to(active_id)
                self._tab_bar.set_active_tab(active_id)
        else:
            home = self._settings.get("startup.home_url", "https://www.google.com")
            tab_id = self._tab_mgr.create_tab(home)
            self._tab_mgr.switch_to(tab_id)
            self._tab_bar.set_active_tab(tab_id)

    def _create_view(self, tab_id: int, url: str) -> AxiomContentView:
        view = AxiomContentView(tab_id, self._engine.profile, parent=self._stack)
        view.page_title_changed.connect(self._on_title_changed)
        view.page_url_changed.connect(self._on_url_changed)
        view.page_load_finished.connect(self._on_load_finished)
        view.page_icon_changed.connect(self._on_icon_changed)
        # Middle-click / Ctrl+click / target=_blank → open in background tab
        view.new_window_needed.connect(lambda v=view: self._on_new_window_needed(v))
        self._stack.addWidget(view)
        self._views[tab_id] = view
        if url:
            view.navigate(url)
        return view

    def _create_special_view(self, tab_id: int, url: str) -> QWidget:
        """Create the appropriate widget for an axiom:// URL."""
        if url == "axiom://settings":
            page: QWidget = AxiomSettingsPage(self._adblock, self._settings, parent=self._stack)
            assert isinstance(page, AxiomSettingsPage)
            page.home_url_changed.connect(self._on_home_url_changed)
            page.search_engine_changed.connect(self._on_search_engine_changed)
            page.adblock_toggled.connect(self._on_adblock_toggled)
            page.restore_session_toggled.connect(self._on_restore_session_toggled)
            page.bookmarks_bar_toggled.connect(self._on_bookmarks_bar_toggled)
            self._settings_page = page
            title = "Settings"

        elif url == "axiom://history":
            page = AxiomHistoryPage(self._history, parent=self._stack)
            assert isinstance(page, AxiomHistoryPage)
            page.navigate_requested.connect(self._on_navigate)
            title = "History"

        elif url == "axiom://downloads":
            page = AxiomDownloadsPage(self._downloads, parent=self._stack)
            title = "Downloads"

        else:
            raise ValueError(f"Unknown special URL: {url}")

        self._stack.addWidget(page)
        self._views[tab_id] = page
        self._special_tabs[url] = tab_id
        self._tab_bar.update_tab_title(tab_id, title)
        return page

    # ──────────────────────────────────────────────────────────────────
    # Special tab helpers
    # ──────────────────────────────────────────────────────────────────

    def _open_special_tab(self, url: str) -> None:
        """Switch to an existing axiom:// tab or create a new one."""
        tab_id = self._special_tabs.get(url)
        if tab_id is not None and tab_id in self._views:
            self._tab_mgr.switch_to(tab_id)
            self._tab_bar.set_active_tab(tab_id)
            return
        new_id = self._tab_mgr.create_tab(url)
        self._tab_mgr.switch_to(new_id)
        self._tab_bar.set_active_tab(new_id)

    def _open_settings_tab(self) -> None:
        self._open_special_tab("axiom://settings")

    # ──────────────────────────────────────────────────────────────────
    # TabManager slots
    # ──────────────────────────────────────────────────────────────────

    def _on_tab_created(self, tab_id: int, url: str) -> None:
        self._tab_bar.add_tab(tab_id, "New Tab")
        if url in _SPECIAL_URLS:
            self._create_special_view(tab_id, url)
        else:
            self._create_view(tab_id, url)

    def _on_tab_closed(self, tab_id: int) -> None:
        # Clear special tab tracking
        for url, tid in list(self._special_tabs.items()):
            if tid == tab_id:
                del self._special_tabs[url]
                if url == "axiom://settings":
                    self._settings_page = None
                break

        self._tab_bar.remove_tab(tab_id)
        view = self._views.pop(tab_id, None)
        if view:
            self._stack.removeWidget(view)
            view.deleteLater()
        self._nav_mgr.remove_tab(tab_id)
        active_id = self._tab_mgr.get_active_tab_id()
        if active_id is not None and active_id in self._views:
            self._stack.setCurrentWidget(self._views[active_id])
            self._tab_bar.set_active_tab(active_id)

    def _on_tab_switched(self, tab_id: int) -> None:
        if tab_id not in self._views:
            return
        self._stack.setCurrentWidget(self._views[tab_id])
        self._tab_bar.set_active_tab(tab_id)

        special_url = next(
            (u for u, tid in self._special_tabs.items() if tid == tab_id), None
        )
        if special_url is not None:
            # Special page: show its URL, disable nav buttons, refresh content
            self._address_bar.update_url(special_url)
            self._address_bar.set_back_enabled(False)
            self._address_bar.set_forward_enabled(False)
            self._address_bar.set_loading(False)
            view = self._views[tab_id]
            if isinstance(view, AxiomSettingsPage):
                view.refresh(self._bookmarks_bar.isVisible())
            elif isinstance(view, AxiomHistoryPage):
                view.refresh()
            elif isinstance(view, AxiomDownloadsPage):
                view.refresh()
        else:
            url = self._nav_mgr.get_current_url(tab_id) or ""
            self._address_bar.update_url(url)
            self._update_nav_buttons(tab_id)
            view = self._views[tab_id]
            if self._devtools_panel.is_open() and isinstance(view, AxiomContentView):
                self._devtools_panel.open_for(self._engine.profile, view.page())

    def _on_tab_suspended(self, tab_id: int) -> None:
        view = self._views.get(tab_id)
        if isinstance(view, AxiomContentView):
            view.suspend()

    def _on_tab_resumed(self, tab_id: int) -> None:
        view = self._views.get(tab_id)
        if isinstance(view, AxiomContentView):
            view.resume()

    # ──────────────────────────────────────────────────────────────────
    # Tab bar slots
    # ──────────────────────────────────────────────────────────────────

    def _on_tab_bar_changed(self, tab_id: int) -> None:
        self._tab_mgr.switch_to(tab_id)

    def _on_close_requested(self, tab_id: int) -> None:
        if self._tab_mgr.get_tab_count() <= 1:
            self.close()
            return
        # Save URL so Ctrl+Shift+T can reopen it (skip special axiom:// pages)
        if tab_id not in self._special_tabs.values():
            url = self._nav_mgr.get_current_url(tab_id) or ""
            if url and url not in ("about:blank", ""):
                self._closed_tabs_stack.append(url)
                if len(self._closed_tabs_stack) > 25:
                    self._closed_tabs_stack.pop(0)
        self._tab_mgr.close_tab(tab_id)

    def _on_new_tab_requested(self) -> None:
        home = self._settings.get("startup.home_url", "https://www.google.com")
        tab_id = self._tab_mgr.create_tab(home)
        self._tab_mgr.switch_to(tab_id)
        self._tab_bar.set_active_tab(tab_id)

    def _close_active_tab(self) -> None:
        active_id = self._tab_mgr.get_active_tab_id()
        if active_id is not None:
            self._on_close_requested(active_id)

    def _reopen_closed_tab(self) -> None:
        """Ctrl+Shift+T — reopen the most recently closed tab."""
        if not self._closed_tabs_stack:
            return
        url = self._closed_tabs_stack.pop()
        tab_id = self._tab_mgr.create_tab(url)
        self._tab_mgr.switch_to(tab_id)
        self._tab_bar.set_active_tab(tab_id)

    def _on_tab_duplicate(self, tab_id: int) -> None:
        view = self._views.get(tab_id)
        if isinstance(view, AxiomContentView):
            url = self._nav_mgr.get_current_url(tab_id) or view.url().toString()
        else:
            url = self._settings.get("startup.home_url", "https://www.google.com")
        if url and url not in ("about:blank", ""):
            new_id = self._tab_mgr.create_tab(url)
            self._tab_mgr.switch_to(new_id)
            self._tab_bar.set_active_tab(new_id)

    def _on_tab_close_others(self, keep_tab_id: int) -> None:
        all_tabs = self._tab_mgr.get_all_tabs()
        for tab in all_tabs:
            if tab.tab_id != keep_tab_id:
                self._tab_mgr.close_tab(tab.tab_id)

    def _on_tab_close_right(self, tab_id: int) -> None:
        for tid in self._tab_bar.get_tab_ids_after(tab_id):
            self._tab_mgr.close_tab(tid)

    def _on_new_window_needed(self, requesting_view: AxiomContentView) -> None:
        """
        Called synchronously when the Chromium engine wants a new tab/window
        (middle-click, Ctrl+click, target="_blank", window.open()).
        Creates a background tab and hands its QWebEnginePage back to Chromium.
        Does NOT switch focus — the tab appears in the strip silently.
        """
        tab_id = self._tab_mgr.create_tab("")   # synchronous: _on_tab_created runs now
        new_view = self._views.get(tab_id)
        if isinstance(new_view, AxiomContentView):
            requesting_view.accept_new_page(new_view.page())

    # ──────────────────────────────────────────────────────────────────
    # Address bar slots
    # ──────────────────────────────────────────────────────────────────

    def _on_navigate(self, text: str) -> None:
        # Special internal URLs
        clean = text.strip().lower()
        if clean in _SPECIAL_URLS:
            self._open_special_tab(clean)
            return

        active_id = self._tab_mgr.get_active_tab_id()
        if active_id is None:
            return

        url = self._nav_mgr.resolve_input(text)

        view = self._views.get(active_id)
        if isinstance(view, AxiomContentView):
            self._address_bar.set_loading(True)
            view.navigate(url)
        else:
            # Can't navigate a special page (e.g. settings) — open new tab
            new_id = self._tab_mgr.create_tab(url)
            self._tab_mgr.switch_to(new_id)
            self._tab_bar.set_active_tab(new_id)

    def _on_back(self) -> None:
        active_id = self._tab_mgr.get_active_tab_id()
        view = self._views.get(active_id) if active_id is not None else None
        if isinstance(view, AxiomContentView):
            view.back()

    def _on_forward(self) -> None:
        active_id = self._tab_mgr.get_active_tab_id()
        view = self._views.get(active_id) if active_id is not None else None
        if isinstance(view, AxiomContentView):
            view.forward()

    def _on_reload(self) -> None:
        active_id = self._tab_mgr.get_active_tab_id()
        view = self._views.get(active_id) if active_id is not None else None
        if isinstance(view, AxiomContentView):
            if view.page().isLoading():
                view.stop()
            else:
                view.reload()

    # ──────────────────────────────────────────────────────────────────
    # Content view slots
    # ──────────────────────────────────────────────────────────────────

    def _on_title_changed(self, tab_id: int, title: str) -> None:
        if title:
            self._tab_mgr.update_tab(tab_id, title=title)
            self._tab_bar.update_tab_title(tab_id, title)

    def _on_url_changed(self, tab_id: int, url: QUrl) -> None:
        url_str = url.toString()
        self._nav_mgr.set_current_url(tab_id, url_str)
        if tab_id == self._tab_mgr.get_active_tab_id():
            self._address_bar.update_url(url_str)
            self._update_nav_buttons(tab_id)
        if url_str and url_str != "about:blank":
            tab = self._tab_mgr.get_tab(tab_id)
            self._history.add_entry(url_str, tab.title if tab else "")

    def _on_load_finished(self, tab_id: int, ok: bool) -> None:
        if tab_id == self._tab_mgr.get_active_tab_id():
            self._address_bar.set_loading(False)
            self._update_nav_buttons(tab_id)

    def _on_icon_changed(self, tab_id: int) -> None:
        view = self._views.get(tab_id)
        if not isinstance(view, AxiomContentView):
            return
        icon: QIcon = view.icon()
        if not icon.isNull():
            self._tab_bar.update_tab_icon(tab_id, icon)

    def _update_nav_buttons(self, tab_id: int) -> None:
        view = self._views.get(tab_id)
        if isinstance(view, AxiomContentView):
            h = view.page().history()
            self._address_bar.set_back_enabled(h.canGoBack())
            self._address_bar.set_forward_enabled(h.canGoForward())
        else:
            # Special page — no navigation history
            self._address_bar.set_back_enabled(False)
            self._address_bar.set_forward_enabled(False)

    # ──────────────────────────────────────────────────────────────────
    # Bookmarks
    # ──────────────────────────────────────────────────────────────────

    def _on_bookmark_removed(self, url: str) -> None:
        self._bookmarks.remove(url)

    def _add_current_bookmark(self) -> None:
        active_id = self._tab_mgr.get_active_tab_id()
        if active_id is None:
            return
        view = self._views.get(active_id)
        if not isinstance(view, AxiomContentView):
            return
        url = self._nav_mgr.get_current_url(active_id) or view.url().toString()
        if not url or url == "about:blank":
            return
        tab = self._tab_mgr.get_tab(active_id)
        title = tab.title if tab else url

        favicon_b64 = ""
        icon: QIcon = view.icon()
        if not icon.isNull():
            px: QPixmap = icon.pixmap(16, 16)
            if not px.isNull():
                from PyQt6.QtCore import QBuffer, QIODeviceBase
                buf = QBuffer()
                buf.open(QIODeviceBase.OpenModeFlag.WriteOnly)
                px.save(buf, "PNG")
                favicon_b64 = base64.b64encode(bytes(buf.data())).decode("ascii")

        self._bookmarks.add(url, title, favicon_b64)
        self._bookmarks_bar.add_bookmark(Bookmark(url=url, title=title, favicon_b64=favicon_b64))

        if not self._bookmarks_bar.isVisible():
            self._on_bookmarks_bar_toggled(True)

    def _toggle_bookmarks_bar(self) -> None:
        self._on_bookmarks_bar_toggled(not self._bookmarks_bar.isVisible())

    def _on_bookmarks_bar_toggled(self, visible: bool) -> None:
        self._bookmarks_bar.setVisible(visible)
        self._sidebar.set_bookmarks_active(visible)
        self._settings.set("bookmarks_bar_visible", visible)
        # Keep settings page in sync if currently open
        settings_id = self._special_tabs.get("axiom://settings")
        if settings_id is not None and self._settings_page is not None:
            self._settings_page.refresh(visible)

    # ──────────────────────────────────────────────────────────────────
    # DevTools
    # ──────────────────────────────────────────────────────────────────

    def _toggle_devtools(self) -> None:
        if self._devtools_panel.is_open():
            self._devtools_panel.close_panel()
        else:
            active_id = self._tab_mgr.get_active_tab_id()
            view = self._views.get(active_id) if active_id is not None else None
            if isinstance(view, AxiomContentView):
                self._devtools_panel.open_for(self._engine.profile, view.page())

    # ──────────────────────────────────────────────────────────────────
    # Adblock
    # ──────────────────────────────────────────────────────────────────

    def _on_adblock_toggled(self, enabled: bool) -> None:
        self._adblock.enabled = enabled
        self._settings.set("adblock_enabled", enabled)

    # ──────────────────────────────────────────────────────────────────
    # Settings handlers (from AxiomSettingsPage signals)
    # ──────────────────────────────────────────────────────────────────

    def _on_settings_requested(self) -> None:
        self._open_special_tab("axiom://settings")

    def _on_history_requested(self) -> None:
        self._open_special_tab("axiom://history")

    def _on_downloads_requested(self) -> None:
        self._open_special_tab("axiom://downloads")

    def _on_home_url_changed(self, url: str) -> None:
        self._settings.set("startup.home_url", url)

    def _on_search_engine_changed(self, url: str) -> None:
        self._settings.set("search.engine_url", url)
        # Keep NavigationManager in sync so searches use the new engine immediately.
        self._nav_mgr.set_search_url(url)

    def _on_restore_session_toggled(self, enabled: bool) -> None:
        self._settings.set("startup.restore_session", enabled)

    # ──────────────────────────────────────────────────────────────────
    # Downloads
    # ──────────────────────────────────────────────────────────────────

    def _on_download_requested(self, download: QWebEngineDownloadRequest) -> None:
        download_dir = self._settings.get("downloads.save_directory") or _downloads_dir()
        filename = download.suggestedFileName()
        save_path = os.path.join(download_dir, filename)
        download.setDownloadDirectory(download_dir)
        download.setDownloadFileName(filename)

        # Accept the download — must happen before reading back paths
        download.accept()

        # Record in persistent DB
        dl_id = self._downloads.add_download(
            filename=filename,
            source_url=download.url().toString(),
            save_path=save_path,
        )
        download.receivedBytesChanged.connect(
            lambda: self._downloads.update_progress(dl_id, download.receivedBytes())
        )
        download.isFinishedChanged.connect(
            lambda: self._downloads.update_status(dl_id, self._dl_status(download))
        )

        # Show live progress in the download bar
        self._download_bar.add_download(download)

    def _dl_status(self, download: QWebEngineDownloadRequest) -> DownloadStatus:
        state = download.state()
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            return DownloadStatus.COMPLETED
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            return DownloadStatus.CANCELLED
        return DownloadStatus.FAILED

    # ──────────────────────────────────────────────────────────────────
    # Memory management
    # ──────────────────────────────────────────────────────────────────

    def _check_memory_pressure(self) -> None:
        if self._resource_mgr.should_suspend_tabs():
            for tab_id in self._resource_mgr.get_suspension_candidates()[:2]:
                self._tab_mgr.suspend_tab(tab_id)

    # ──────────────────────────────────────────────────────────────────
    # Window lifecycle
    # ──────────────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        all_tabs = self._tab_mgr.get_all_tabs()
        active_id = self._tab_mgr.get_active_tab_id()
        sessions = [
            TabSession(url=t.url, title=t.title, is_active=(t.tab_id == active_id))
            for t in all_tabs
            if t.url not in _SPECIAL_URLS   # don't persist internal pages
        ]
        try:
            self._session.save_session(sessions)
        except OSError as exc:
            # Non-fatal: log so it shows up in crash reports / log files.
            # Don't block the close — the user expects the window to close.
            _log.error("Failed to save session to disk: %s", exc)

        self._history.close()
        self._downloads.close()

        self._settings.set("window.width", self.width())
        self._settings.set("window.height", self.height())
        try:
            self._settings.save()
        except OSError as exc:
            _log.error("Failed to save settings to disk: %s", exc)

        event.accept()
