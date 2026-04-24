"""
Bookmarks bar — URL chips and folder chips in a single horizontal row.

Folders render as dropdown buttons (click → menu of children).
Overflow items go behind the » button at the right edge.
"""

import base64
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt, QByteArray, QSize
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSizePolicy, QMenu, QInputDialog,
    QMessageBox,
)

from storage.bookmarks_manager import Bookmark, BookmarkFolder, BookmarkItem

MAX_CHIP_TITLE = 18
_OVERFLOW_BTN_W = 34   # pixels reserved for the » button

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
QMenu::item:disabled {
    color: rgba(242,242,242,0.30);
}
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.07);
    margin: 3px 8px;
}
"""


# ---------------------------------------------------------------------------
# Internal chip data container
# ---------------------------------------------------------------------------

@dataclass
class _Chip:
    item: BookmarkItem
    btn: QPushButton


# ---------------------------------------------------------------------------
# AxiomBookmarksBar
# ---------------------------------------------------------------------------

class AxiomBookmarksBar(QWidget):
    navigate_requested    = pyqtSignal(str)   # url
    bookmark_removed      = pyqtSignal(str)   # url
    add_bookmark_requested = pyqtSignal()      # user wants to bookmark current page (root)
    add_to_folder_requested = pyqtSignal(str)  # user wants to bookmark current page into folder (title)
    folder_created        = pyqtSignal(str)   # new folder title
    folder_deleted        = pyqtSignal(str)   # folder title
    folder_renamed        = pyqtSignal(str, str)  # (old_title, new_title)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("bookmarks-bar")
        self.setFixedHeight(30)
        self._chips: list[_Chip] = []
        self._hidden_items: list[BookmarkItem] = []
        self._setup_ui()

    # ── Setup ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 0, 4, 0)
        self._layout.setSpacing(2)

        # » overflow button — shown only when chips overflow
        self._overflow_btn = QPushButton("»")
        self._overflow_btn.setObjectName("bookmark-chip")
        self._overflow_btn.setFixedSize(_OVERFLOW_BTN_W, 24)
        self._overflow_btn.setToolTip("More bookmarks")
        self._overflow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._overflow_btn.setVisible(False)
        self._overflow_btn.clicked.connect(self._show_overflow_menu)

        # Stretch keeps chips left-aligned; overflow btn stays at far right
        self._layout.addStretch(1)
        self._layout.addWidget(self._overflow_btn)

        # Right-click on empty bar area
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_bar_context_menu)

    # ── Public API ─────────────────────────────────────────────────────

    def load_bookmarks(self, items: list[BookmarkItem]) -> None:
        """Replace all chips with the supplied list (Bookmarks and/or Folders)."""
        self._clear_chips()
        for item in items:
            self._add_chip(item, update=False)
        self._update_visible_chips()

    def add_item(self, item: BookmarkItem) -> None:
        """Append a single bookmark or folder chip (skips exact duplicates)."""
        if isinstance(item, Bookmark):
            if any(isinstance(c.item, Bookmark) and c.item.url == item.url
                   for c in self._chips):
                return
        elif isinstance(item, BookmarkFolder):
            if any(isinstance(c.item, BookmarkFolder) and c.item.title == item.title
                   for c in self._chips):
                return
        self._add_chip(item, update=True)

    # Backward-compatible alias used by older call sites
    def add_bookmark(self, bm: Bookmark) -> None:
        self.add_item(bm)

    def remove_bookmark(self, url: str) -> None:
        for chip in list(self._chips):
            if isinstance(chip.item, Bookmark) and chip.item.url == url:
                self._layout.removeWidget(chip.btn)
                chip.btn.deleteLater()
                self._chips.remove(chip)
                break
        self._update_visible_chips()

    # ── Layout / overflow ──────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_visible_chips()

    def _update_visible_chips(self) -> None:
        if not self._chips:
            self._overflow_btn.setVisible(False)
            return

        available = self.width() - 12   # subtract left+right margins
        used = 0
        first_hidden = len(self._chips)

        for i, chip in enumerate(self._chips):
            chip_w = chip.btn.sizeHint().width() + 2   # +2 for spacing
            remaining = len(self._chips) - i - 1
            reserve = _OVERFLOW_BTN_W + 2 if remaining > 0 else 0
            if used + chip_w + reserve <= available:
                used += chip_w
            else:
                first_hidden = i
                break

        for i, chip in enumerate(self._chips):
            chip.btn.setVisible(i < first_hidden)

        has_overflow = first_hidden < len(self._chips)
        self._overflow_btn.setVisible(has_overflow)
        self._hidden_items = [c.item for c in self._chips[first_hidden:]]

    # ── Internal chip helpers ──────────────────────────────────────────

    def _clear_chips(self) -> None:
        for chip in self._chips:
            self._layout.removeWidget(chip.btn)
            chip.btn.deleteLater()
        self._chips.clear()

    def _add_chip(self, item: BookmarkItem, *, update: bool = True) -> None:
        if isinstance(item, BookmarkFolder):
            btn = self._make_folder_btn(item)
        else:
            btn = self._make_url_btn(item)

        # Insert before the stretch (stretch is at count-2, overflow at count-1)
        insert_at = self._layout.count() - 2
        self._layout.insertWidget(insert_at, btn)
        self._chips.append(_Chip(item=item, btn=btn))

        if update:
            self._update_visible_chips()

    # ── Button factories ───────────────────────────────────────────────

    def _make_url_btn(self, bm: Bookmark) -> QPushButton:
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
                    btn.setIcon(QIcon(pm.scaled(
                        14, 14,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )))
                    btn.setIconSize(QSize(14, 14))
            except Exception:
                pass

        url = bm.url
        btn.clicked.connect(lambda _, u=url: self.navigate_requested.emit(u))
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, u=url, b=btn: self._show_url_chip_menu(pos, u, b)
        )
        return btn

    def _make_folder_btn(self, folder: BookmarkFolder) -> QPushButton:
        label = "\U0001f4c1 " + self._truncate(folder.title) + " \u25be"
        btn = QPushButton(label)
        btn.setObjectName("bookmark-chip")
        btn.setToolTip(f"Folder: {folder.title}  ({len(folder.children)} items)")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setFixedHeight(24)

        btn.clicked.connect(lambda _, f=folder, b=btn: self._show_folder_dropdown(f, b))
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, f=folder, b=btn: self._show_folder_chip_menu(pos, f, b)
        )
        return btn

    # ── Context / dropdown menus ───────────────────────────────────────

    def _show_folder_dropdown(self, folder: BookmarkFolder, btn: QPushButton) -> None:
        """Left-click on a folder chip — show its children."""
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)
        if folder.children:
            for bm in folder.children:
                act = QAction(self._truncate(bm.title or bm.url), self)
                act.setToolTip(bm.url)
                act.triggered.connect(lambda _, u=bm.url: self.navigate_requested.emit(u))
                menu.addAction(act)
        else:
            no_act = QAction("(empty folder)", self)
            no_act.setEnabled(False)
            menu.addAction(no_act)
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _show_url_chip_menu(self, pos, url: str, btn: QPushButton) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)
        open_act   = QAction("Open", self)
        remove_act = QAction("Remove bookmark", self)
        open_act.triggered.connect(lambda: self.navigate_requested.emit(url))
        remove_act.triggered.connect(lambda: self._on_remove_url(url))
        menu.addAction(open_act)
        menu.addSeparator()
        menu.addAction(remove_act)
        menu.exec(btn.mapToGlobal(pos))

    def _show_folder_chip_menu(self, pos, folder: BookmarkFolder, btn: QPushButton) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)
        rename_act = QAction("Rename folder\u2026", self)
        delete_act = QAction("Delete folder", self)
        rename_act.triggered.connect(lambda: self._on_rename_folder(folder.title))
        delete_act.triggered.connect(lambda: self._on_delete_folder(folder.title))
        menu.addAction(rename_act)
        menu.addSeparator()
        menu.addAction(delete_act)
        menu.exec(btn.mapToGlobal(pos))

    def _show_overflow_menu(self) -> None:
        """» button dropdown — shows all items that didn't fit in the bar."""
        if not self._hidden_items:
            return
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)
        for item in self._hidden_items:
            if isinstance(item, Bookmark):
                act = QAction(self._truncate(item.title or item.url), self)
                act.setToolTip(item.url)
                act.triggered.connect(lambda _, u=item.url: self.navigate_requested.emit(u))
                menu.addAction(act)
            elif isinstance(item, BookmarkFolder):
                sub = menu.addMenu("\U0001f4c1 " + self._truncate(item.title))
                sub.setStyleSheet(_MENU_QSS)
                if item.children:
                    for bm in item.children:
                        act = QAction(self._truncate(bm.title or bm.url), self)
                        act.setToolTip(bm.url)
                        act.triggered.connect(lambda _, u=bm.url: self.navigate_requested.emit(u))
                        sub.addAction(act)
                else:
                    no_act = QAction("(empty)", self)
                    no_act.setEnabled(False)
                    sub.addAction(no_act)
        btn_rect = self._overflow_btn.rect()
        menu.exec(self._overflow_btn.mapToGlobal(btn_rect.bottomLeft()))

    def _show_bar_context_menu(self, pos) -> None:
        """Right-click on empty bar area."""
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)

        add_act = QAction("Add current page", self)
        add_act.triggered.connect(self.add_bookmark_requested.emit)
        menu.addAction(add_act)

        # "Add current page to folder" — only when at least one folder exists
        all_folders: list[BookmarkFolder] = []
        for chip in self._chips:
            if isinstance(chip.item, BookmarkFolder):
                all_folders.append(chip.item)
        for item in self._hidden_items:
            if isinstance(item, BookmarkFolder):
                all_folders.append(item)

        if all_folders:
            folder_sub = menu.addMenu("Add current page to folder")
            folder_sub.setStyleSheet(_MENU_QSS)
            for folder in all_folders:
                act = QAction(folder.title, self)
                act.triggered.connect(
                    lambda _, ft=folder.title: self.add_to_folder_requested.emit(ft)
                )
                folder_sub.addAction(act)

        menu.addSeparator()
        new_folder_act = QAction("New folder\u2026", self)
        new_folder_act.triggered.connect(self._on_create_folder)
        menu.addAction(new_folder_act)

        menu.exec(self.mapToGlobal(pos))

    # ── Folder action handlers ─────────────────────────────────────────

    def _on_remove_url(self, url: str) -> None:
        self.remove_bookmark(url)
        self.bookmark_removed.emit(url)

    def _on_create_folder(self) -> None:
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            self.folder_created.emit(name.strip())

    def _on_rename_folder(self, old_title: str) -> None:
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "New name:", text=old_title
        )
        if ok and new_name.strip() and new_name.strip() != old_title:
            self.folder_renamed.emit(old_title, new_name.strip())

    def _on_delete_folder(self, title: str) -> None:
        reply = QMessageBox.question(
            self,
            "Delete Folder",
            f'Delete "{title}" and all its bookmarks?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.folder_deleted.emit(title)

    # ── Utility ────────────────────────────────────────────────────────

    def _truncate(self, text: str) -> str:
        return text[:MAX_CHIP_TITLE] + "\u2026" if len(text) > MAX_CHIP_TITLE else text
