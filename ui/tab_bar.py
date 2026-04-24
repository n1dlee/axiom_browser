from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QTabBar, QSizePolicy, QMenu,
)

MAX_TITLE_LEN = 28

# Dark context-menu style (matches AXIOM theme)
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
    color: rgba(242,242,242,0.25);
}
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.07);
    margin: 3px 8px;
}
"""


class AxiomTabBar(QWidget):
    tab_changed = pyqtSignal(int)
    tab_close_requested = pyqtSignal(int)
    new_tab_requested = pyqtSignal()

    # Context-menu actions
    tab_duplicate_requested    = pyqtSignal(int)   # tab_id
    tab_close_others_requested = pyqtSignal(int)   # tab_id to keep
    tab_close_right_requested  = pyqtSignal(int)   # tab_id (close everything to its right)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setObjectName("tab-strip")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(40)
        self._programmatic_change = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(0)

        self._tab_bar = QTabBar()
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setMovable(True)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
        self._tab_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._tab_bar.setFixedHeight(40)
        self._tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._apply_tab_styles()

        self._new_btn = QPushButton("+")
        self._new_btn.setObjectName("new-tab-btn")
        self._new_btn.setFixedSize(28, 28)
        self._new_btn.setToolTip("New tab  (Ctrl+T)")
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # stretch=1 on tab bar → expands and fills all space
        # stretch=0 on new btn → stays compact at right edge
        layout.addWidget(self._tab_bar, 1)
        layout.addSpacing(4)
        layout.addWidget(self._new_btn, 0)
        layout.addSpacing(4)

    def _apply_tab_styles(self) -> None:
        from ui.theme import (
            SURFACE_2, SURFACE_ACTIVE, TEXT_PRIMARY, TEXT_SECONDARY,
            ACCENT, BORDER_STRONG, FONT_FAMILY,
        )
        self._tab_bar.setStyleSheet(f"""
QTabBar {{
    background: transparent;
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SECONDARY};
    padding: 0px 18px;
    min-width: 110px;
    max-width: 230px;
    min-height: 38px;
    max-height: 38px;
    font-size: 12px;
    font-family: {FONT_FAMILY};
    font-weight: 400;
    border: none;
    border-bottom: 2px solid transparent;
    margin: 0px;
}}
QTabBar::tab:selected {{
    background: {SURFACE_ACTIVE};
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT};
    font-weight: 500;
}}
QTabBar::tab:hover:!selected {{
    background: {SURFACE_2};
    color: rgba(200,215,255,0.88);
    border-bottom: 2px solid {BORDER_STRONG};
}}
QTabBar::close-button {{
    subcontrol-position: right;
    width: 13px;
    height: 13px;
    margin-right: 2px;
    border-radius: 6px;
}}
QTabBar::close-button:hover {{
    background: rgba(255,61,90,0.22);
}}
""")

    def _connect_signals(self) -> None:
        def _on_current_changed(index: int) -> None:
            if self._programmatic_change:
                return
            tab_id = self._tab_bar.tabData(index)
            if tab_id is not None:
                self.tab_changed.emit(tab_id)

        def _on_close_requested(index: int) -> None:
            tab_id = self._tab_bar.tabData(index)
            if tab_id is not None:
                self.tab_close_requested.emit(tab_id)

        self._tab_bar.currentChanged.connect(_on_current_changed)
        self._tab_bar.tabCloseRequested.connect(_on_close_requested)
        self._tab_bar.customContextMenuRequested.connect(self._on_tab_context_menu)
        self._new_btn.clicked.connect(self.new_tab_requested)

    # ------------------------------------------------------------------
    # Right-click context menu
    # ------------------------------------------------------------------

    def _on_tab_context_menu(self, pos: QPoint) -> None:
        index = self._tab_bar.tabAt(pos)
        if index < 0:
            return
        tab_id = self._tab_bar.tabData(index)
        if tab_id is None:
            return

        total_tabs = self._tab_bar.count()
        is_last = (index == total_tabs - 1)

        menu = QMenu(self._tab_bar)
        menu.setStyleSheet(_MENU_QSS)

        dup_act = menu.addAction("Duplicate Tab")
        menu.addSeparator()
        close_act = menu.addAction("Close Tab")
        close_others_act = menu.addAction("Close Other Tabs")
        close_right_act  = menu.addAction("Close Tabs to the Right")

        # Disable when not applicable
        if total_tabs <= 1:
            close_others_act.setEnabled(False)
        if is_last:
            close_right_act.setEnabled(False)

        action = menu.exec(self._tab_bar.mapToGlobal(pos))
        if action is None:
            return
        if action == dup_act:
            self.tab_duplicate_requested.emit(tab_id)
        elif action == close_act:
            self.tab_close_requested.emit(tab_id)
        elif action == close_others_act:
            self.tab_close_others_requested.emit(tab_id)
        elif action == close_right_act:
            self.tab_close_right_requested.emit(tab_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_tab(self, tab_id: int, title: str) -> None:
        index = self._tab_bar.addTab(self._truncate(title))
        self._tab_bar.setTabData(index, tab_id)

    def remove_tab(self, tab_id: int) -> None:
        index = self._find_index(tab_id)
        if index >= 0:
            self._tab_bar.removeTab(index)

    def update_tab_title(self, tab_id: int, title: str) -> None:
        index = self._find_index(tab_id)
        if index >= 0:
            self._tab_bar.setTabText(index, self._truncate(title))

    def update_tab_icon(self, tab_id: int, icon: QIcon) -> None:
        index = self._find_index(tab_id)
        if index >= 0:
            self._tab_bar.setTabIcon(index, icon)

    def set_active_tab(self, tab_id: int) -> None:
        index = self._find_index(tab_id)
        if index >= 0:
            self._programmatic_change = True
            try:
                self._tab_bar.setCurrentIndex(index)
            finally:
                self._programmatic_change = False

    def get_tab_ids_after(self, tab_id: int) -> list[int]:
        """Return all tab IDs that appear after tab_id in the tab strip."""
        index = self._find_index(tab_id)
        if index < 0:
            return []
        result = []
        for i in range(index + 1, self._tab_bar.count()):
            tid = self._tab_bar.tabData(i)
            if tid is not None:
                result.append(tid)
        return result

    def get_all_tab_ids(self) -> list[int]:
        """Return all tab IDs in display order."""
        return [
            self._tab_bar.tabData(i)
            for i in range(self._tab_bar.count())
            if self._tab_bar.tabData(i) is not None
        ]

    def _find_index(self, tab_id: int) -> int:
        for i in range(self._tab_bar.count()):
            if self._tab_bar.tabData(i) == tab_id:
                return i
        return -1

    def _truncate(self, title: str) -> str:
        return title[:MAX_TITLE_LEN] + "…" if len(title) > MAX_TITLE_LEN else title
