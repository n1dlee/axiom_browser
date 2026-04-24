import base64
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSizePolicy, QScrollArea, QMenu,
)

from storage.bookmarks_manager import Bookmark

MAX_CHIP_TITLE = 18

_MENU_QSS = """
QMenu {
    background: #111120;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 4px;
    color: #F2F2F2;
    font-size: 12px;
}
QMenu::item {
    padding: 7px 22px 7px 12px;
    border-radius: 4px;
    background: transparent;
}
QMenu::item:selected {
    background: #20203A;
    color: #4F8EFF;
}
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.07);
    margin: 3px 8px;
}
"""


class AxiomBookmarksBar(QWidget):
    navigate_requested    = pyqtSignal(str)   # url
    bookmark_removed      = pyqtSignal(str)   # url
    add_bookmark_requested = pyqtSignal()      # request to bookmark the current page

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setObjectName("bookmarks-bar")
        self.setFixedHeight(30)
        self._chips: list[tuple[str, QPushButton]] = []  # (url, btn)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 0, 4, 0)
        outer.setSpacing(0)

        # Scrollable chip area
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._scroll.setFixedHeight(30)
        self._scroll.setWidgetResizable(True)

        self._chip_container = QWidget()
        self._chip_container.setObjectName("bookmarks-bar")
        self._chip_layout = QHBoxLayout(self._chip_container)
        self._chip_layout.setContentsMargins(0, 0, 0, 0)
        self._chip_layout.setSpacing(2)
        self._chip_layout.addStretch(1)

        # Right-click on empty bar area → "Add current page"
        self._chip_container.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._chip_container.customContextMenuRequested.connect(self._show_bar_context_menu)

        self._scroll.setWidget(self._chip_container)

        outer.addWidget(self._scroll)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_bookmarks(self, bookmarks: list[Bookmark]) -> None:
        self._clear_chips()
        for bm in bookmarks:
            self._add_chip(bm)

    def add_bookmark(self, bm: Bookmark) -> None:
        for url, _ in self._chips:
            if url == bm.url:
                return
        self._add_chip(bm)

    def remove_bookmark(self, url: str) -> None:
        for stored_url, btn in list(self._chips):
            if stored_url == url:
                self._chip_layout.removeWidget(btn)
                btn.deleteLater()
                self._chips.remove((stored_url, btn))
                break

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear_chips(self) -> None:
        for _, btn in self._chips:
            self._chip_layout.removeWidget(btn)
            btn.deleteLater()
        self._chips.clear()

    def _add_chip(self, bm: Bookmark) -> None:
        label = self._truncate(bm.title or bm.url)
        btn = QPushButton(label)
        btn.setObjectName("bookmark-chip")
        btn.setToolTip(f"{bm.title}\n{bm.url}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setFixedHeight(24)

        if bm.favicon_b64:
            try:
                raw = base64.b64decode(bm.favicon_b64)
                pm = QPixmap()
                pm.loadFromData(QByteArray(raw))
                if not pm.isNull():
                    btn.setIcon(QIcon(pm.scaled(14, 14, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
                    btn.setIconSize(pm.size())
            except Exception:
                pass

        url = bm.url
        btn.clicked.connect(lambda _, u=url: self.navigate_requested.emit(u))
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda pos, u=url, b=btn: self._show_chip_context_menu(pos, u, b))

        # Insert before the trailing stretch
        stretch_idx = self._chip_layout.count() - 1
        self._chip_layout.insertWidget(stretch_idx, btn)
        self._chips.append((url, btn))

    def _show_chip_context_menu(self, pos, url: str, btn: QPushButton) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)
        open_act = QAction("Open", self)
        open_act.triggered.connect(lambda: self.navigate_requested.emit(url))
        remove_act = QAction("Remove bookmark", self)
        remove_act.triggered.connect(lambda: self._on_remove(url))
        menu.addAction(open_act)
        menu.addSeparator()
        menu.addAction(remove_act)
        menu.exec(btn.mapToGlobal(pos))

    def _show_bar_context_menu(self, pos) -> None:
        """Context menu for right-clicking on the empty bookmarks bar area."""
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)
        add_act = QAction("Add current page", self)
        add_act.triggered.connect(self.add_bookmark_requested.emit)
        menu.addAction(add_act)
        menu.exec(self._chip_container.mapToGlobal(pos))

    def _on_remove(self, url: str) -> None:
        self.remove_bookmark(url)
        self.bookmark_removed.emit(url)

    def _truncate(self, text: str) -> str:
        return text[:MAX_CHIP_TITLE] + "…" if len(text) > MAX_CHIP_TITLE else text
