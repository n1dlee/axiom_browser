import time
from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass
class TabState:
    tab_id: int
    url: str
    title: str
    suspended: bool = False
    last_active: float = field(default_factory=time.time)


class TabManager(QObject):
    tab_created = pyqtSignal(int, str)       # tab_id, url
    tab_closed = pyqtSignal(int)             # tab_id
    tab_switched = pyqtSignal(int)           # tab_id
    tab_suspended = pyqtSignal(int)          # tab_id
    tab_resumed = pyqtSignal(int)            # tab_id
    tab_updated = pyqtSignal(int, str, str)  # tab_id, url, title

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._tabs: dict[int, TabState] = {}
        self._active_tab_id: Optional[int] = None
        self._next_id: int = 0

    def create_tab(self, url: str = "") -> int:
        tab_id = self._next_id
        self._next_id += 1
        self._tabs[tab_id] = TabState(tab_id=tab_id, url=url, title="New Tab")
        self.tab_created.emit(tab_id, url)
        return tab_id

    def close_tab(self, tab_id: int) -> None:
        if tab_id not in self._tabs:
            return
        del self._tabs[tab_id]
        if self._active_tab_id == tab_id:
            remaining = list(self._tabs.keys())
            self._active_tab_id = remaining[-1] if remaining else None
        self.tab_closed.emit(tab_id)

    def switch_to(self, tab_id: int) -> None:
        if tab_id not in self._tabs:
            return
        self._active_tab_id = tab_id
        self._tabs[tab_id].last_active = time.time()
        self.tab_switched.emit(tab_id)

    def suspend_tab(self, tab_id: int) -> None:
        if tab_id not in self._tabs:
            return
        self._tabs[tab_id].suspended = True
        self.tab_suspended.emit(tab_id)

    def resume_tab(self, tab_id: int) -> None:
        if tab_id not in self._tabs:
            return
        self._tabs[tab_id].suspended = False
        self._tabs[tab_id].last_active = time.time()
        self.tab_resumed.emit(tab_id)

    def update_tab(self, tab_id: int, url: str = "", title: str = "") -> None:
        if tab_id not in self._tabs:
            return
        if url:
            self._tabs[tab_id].url = url
        if title:
            self._tabs[tab_id].title = title
        self.tab_updated.emit(tab_id, self._tabs[tab_id].url, self._tabs[tab_id].title)

    def get_all_tabs(self) -> list[TabState]:
        return list(self._tabs.values())

    def get_active_tab_id(self) -> Optional[int]:
        return self._active_tab_id

    def get_tab_count(self) -> int:
        return len(self._tabs)

    def get_tab(self, tab_id: int) -> Optional[TabState]:
        return self._tabs.get(tab_id)
