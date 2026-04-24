import os
from typing import Optional

from PyQt6.QtWebEngineCore import QWebEngineProfile


def _default_cache_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "Axiom", "cache")


class CacheManager:
    DEFAULT_MAX_SIZE_MB = 256

    def __init__(self, profile: QWebEngineProfile) -> None:
        self._profile = profile

    def configure(
        self,
        cache_path: Optional[str] = None,
        max_size_mb: int = DEFAULT_MAX_SIZE_MB,
    ) -> None:
        path = cache_path or _default_cache_path()
        os.makedirs(path, exist_ok=True)
        self._profile.setCachePath(path)
        self._profile.setHttpCacheMaximumSize(max_size_mb * 1024 * 1024)
        self._profile.setHttpCacheType(
            QWebEngineProfile.HttpCacheType.DiskHttpCache
        )

    def clear_cache(self) -> None:
        self._profile.clearHttpCache()

    def get_cache_path(self) -> str:
        return self._profile.cachePath()
