import json
import os
from copy import deepcopy
from typing import Any, Optional

DEFAULT_SETTINGS: dict = {
    "window": {
        "width": 1280,
        "height": 820,
        "min_width": 960,
        "min_height": 640,
    },
    "startup": {
        "restore_session": True,
        "home_url": "https://www.google.com",
    },
    "search": {
        "engine_url": "https://www.google.com/search?q={}",
    },
    "performance": {
        "suspend_idle_seconds": 300,
        "memory_threshold_percent": 80,
        "max_cache_mb": 256,
    },
    "downloads": {
        "save_directory": "",
    },
    "bookmarks_bar_visible": True,
    "adblock_enabled": True,
}


def _default_settings_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "Axiom", "settings.json")


class SettingsManager:
    def __init__(self, settings_path: Optional[str] = None) -> None:
        self._path = settings_path or _default_settings_path()
        self._data: dict = deepcopy(DEFAULT_SETTINGS)

    def load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self._deep_merge(self._data, saved)
        except (json.JSONDecodeError, IOError):
            pass

    def save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split(".")
        node = self._data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    def set(self, key_path: str, value: Any) -> None:
        keys = key_path.split(".")
        node = self._data
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value

    def _deep_merge(self, base: dict, override: dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
