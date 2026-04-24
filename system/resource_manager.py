import os
import time
from typing import TYPE_CHECKING

import psutil

if TYPE_CHECKING:
    from core.tab_manager import TabManager

SUSPENSION_IDLE_SECONDS: int = 300
MEMORY_THRESHOLD_PERCENT: float = 80.0


class ResourceManager:
    def __init__(self, tab_manager: "TabManager", threshold: float = MEMORY_THRESHOLD_PERCENT) -> None:
        self._tab_manager = tab_manager
        self._threshold = threshold

    def get_memory_usage_percent(self) -> float:
        return psutil.virtual_memory().percent

    def get_process_memory_mb(self) -> float:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    def should_suspend_tabs(self) -> bool:
        return self.get_memory_usage_percent() > self._threshold

    def get_suspension_candidates(self) -> list[int]:
        active_id = self._tab_manager.get_active_tab_id()
        now = time.time()
        candidates: list[tuple[int, float]] = []

        for tab in self._tab_manager.get_all_tabs():
            if tab.tab_id == active_id:
                continue
            if tab.suspended:
                continue
            idle_seconds = now - tab.last_active
            if idle_seconds > SUSPENSION_IDLE_SECONDS:
                candidates.append((tab.tab_id, idle_seconds))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in candidates]
