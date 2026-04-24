import json
import os
from dataclasses import dataclass, asdict, field
from typing import Optional


def _bookmarks_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    data_dir = os.path.join(base, "Axiom")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "bookmarks.json")


@dataclass
class Bookmark:
    url: str
    title: str
    favicon_b64: str = field(default="")  # base64-encoded PNG, empty = use default icon


class BookmarksManager:
    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or _bookmarks_path()
        self._bookmarks: list[Bookmark] = []

    def load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._bookmarks = [
                Bookmark(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    favicon_b64=item.get("favicon_b64", ""),
                )
                for item in raw
                if item.get("url")
            ]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self._bookmarks = []

    def save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([asdict(b) for b in self._bookmarks], f, indent=2)
        except OSError:
            pass

    def add(self, url: str, title: str, favicon_b64: str = "") -> None:
        for b in self._bookmarks:
            if b.url == url:
                b.title = title
                b.favicon_b64 = favicon_b64
                self.save()
                return
        self._bookmarks.append(Bookmark(url=url, title=title, favicon_b64=favicon_b64))
        self.save()

    def remove(self, url: str) -> None:
        self._bookmarks = [b for b in self._bookmarks if b.url != url]
        self.save()

    def get_all(self) -> list[Bookmark]:
        return list(self._bookmarks)

    def contains(self, url: str) -> bool:
        return any(b.url == url for b in self._bookmarks)
