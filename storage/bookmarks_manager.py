"""
Bookmarks storage — supports root-level bookmarks and one-level folders.

JSON format (v2)
----------------
[
  {"type": "url",    "url": "...", "title": "...", "favicon_b64": ""},
  {"type": "folder", "title": "Work", "children": [
      {"url": "...", "title": "...", "favicon_b64": ""},
      ...
  ]}
]

Backward-compat: items without a "type" key are treated as "url".
"""

import json
import logging
import os
from dataclasses import dataclass, asdict, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Union

_log = logging.getLogger(__name__)


def _bookmarks_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    data_dir = os.path.join(base, "Axiom")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "bookmarks.json")


def _chrome_bookmarks_path() -> str:
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(local, "Google", "Chrome", "User Data", "Default", "Bookmarks")
    if hasattr(os, "uname") and os.uname().sysname == "Darwin":
        return os.path.expanduser(
            "~/Library/Application Support/Google/Chrome/Default/Bookmarks"
        )
    return os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Bookmark:
    url: str
    title: str
    favicon_b64: str = field(default="")


@dataclass
class BookmarkFolder:
    title: str
    children: list[Bookmark] = field(default_factory=list)


# Top-level item is either a Bookmark or a BookmarkFolder.
BookmarkItem = Union[Bookmark, BookmarkFolder]


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _item_to_dict(item: BookmarkItem) -> dict:
    if isinstance(item, BookmarkFolder):
        return {
            "type": "folder",
            "title": item.title,
            "children": [asdict(c) for c in item.children],
        }
    return {"type": "url", **asdict(item)}


def _item_from_dict(d: dict) -> BookmarkItem:
    kind = d.get("type", "url")
    if kind == "folder":
        children = [
            Bookmark(url=c.get("url", ""), title=c.get("title", ""),
                     favicon_b64=c.get("favicon_b64", ""))
            for c in d.get("children", [])
            if c.get("url")
        ]
        return BookmarkFolder(title=d.get("title", "Folder"), children=children)
    return Bookmark(
        url=d.get("url", ""),
        title=d.get("title", ""),
        favicon_b64=d.get("favicon_b64", ""),
    )


# ---------------------------------------------------------------------------
# Chrome JSON parser
# ---------------------------------------------------------------------------

def _extract_chrome_folder(node: dict) -> BookmarkFolder | None:
    """Return a BookmarkFolder for a Chrome folder node, or None for a URL node."""
    if node.get("type") == "folder":
        children: list[Bookmark] = []
        for child in node.get("children", []):
            if child.get("type") == "url":
                url = child.get("url", "").strip()
                if url and not url.startswith("javascript:"):
                    children.append(Bookmark(url=url, title=child.get("name", url)))
            # nested folders → flatten into this folder (one level only)
            elif child.get("type") == "folder":
                for grandchild in child.get("children", []):
                    if grandchild.get("type") == "url":
                        url = grandchild.get("url", "").strip()
                        if url and not url.startswith("javascript:"):
                            children.append(Bookmark(url=url, title=grandchild.get("name", url)))
        if children:
            return BookmarkFolder(title=node.get("name", "Folder"), children=children)
    return None


def _extract_chrome_root_urls(node: dict) -> list[Bookmark]:
    """Return top-level URL bookmarks in a Chrome root (bookmark_bar / other)."""
    results: list[Bookmark] = []
    for child in node.get("children", []):
        if child.get("type") == "url":
            url = child.get("url", "").strip()
            if url and not url.startswith("javascript:"):
                results.append(Bookmark(url=url, title=child.get("name", url)))
    return results


def _extract_chrome_root_folders(node: dict) -> list[BookmarkFolder]:
    """Return folder nodes directly inside a Chrome root."""
    results: list[BookmarkFolder] = []
    for child in node.get("children", []):
        if child.get("type") == "folder":
            folder = _extract_chrome_folder(child)
            if folder:
                results.append(folder)
    return results


# ---------------------------------------------------------------------------
# Netscape HTML parser
# ---------------------------------------------------------------------------

class _NetscapeParser(HTMLParser):
    """Parses Netscape Bookmark File Format (Chrome/Firefox HTML export).

    Handles both top-level <A> tags and <A> tags nested inside <DL> sections
    introduced by <H3> folder headings.
    """

    def __init__(self):
        super().__init__()
        self._items: list[BookmarkItem] = []
        self._current_folder: BookmarkFolder | None = None
        self._in_a = False
        self._current_url = ""
        self._current_title = ""

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag == "h3":
            # Start of a folder
            self._current_folder = BookmarkFolder(title="")
        elif tag == "a":
            attr_dict = dict(attrs)
            self._current_url = attr_dict.get("href", "").strip()
            self._in_a = bool(self._current_url)
            self._current_title = ""

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag == "h3":
            pass  # title filled in handle_data
        elif tag == "dl":
            if self._current_folder is not None:
                if self._current_folder.children:
                    self._items.append(self._current_folder)
                self._current_folder = None
        elif tag == "a" and self._in_a:
            url   = self._current_url
            title = self._current_title.strip() or url
            if url and not url.startswith("javascript:"):
                bm = Bookmark(url=url, title=title)
                if self._current_folder is not None:
                    self._current_folder.children.append(bm)
                else:
                    self._items.append(bm)
            self._in_a = False
            self._current_url = ""

    def handle_data(self, data: str):
        if self._in_a:
            self._current_title += data
        elif (self._current_folder is not None
              and not self._current_folder.title):
            self._current_folder.title = data.strip() or "Folder"

    @property
    def items(self) -> list[BookmarkItem]:
        return self._items


# ---------------------------------------------------------------------------
# BookmarksManager
# ---------------------------------------------------------------------------

class BookmarksManager:
    def __init__(self, path: str | None = None) -> None:
        self._path = path or _bookmarks_path()
        self._items: list[BookmarkItem] = []

    # ── Persistence ───────────────────────────────────────────────────

    def load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._items = [
                _item_from_dict(d) for d in raw
                if isinstance(d, dict) and (d.get("url") or d.get("type") == "folder")
            ]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self._items = []

    def save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([_item_to_dict(i) for i in self._items], f, indent=2)
        except OSError as exc:
            _log.error("Failed to save bookmarks: %s", exc)

    # ── Root-level queries ────────────────────────────────────────────

    def get_all(self) -> list[BookmarkItem]:
        """All top-level items (bookmarks and folders)."""
        return list(self._items)

    def get_flat(self) -> list[Bookmark]:
        """All URL bookmarks, folders flattened."""
        out: list[Bookmark] = []
        for item in self._items:
            if isinstance(item, Bookmark):
                out.append(item)
            else:
                out.extend(item.children)
        return out

    def contains(self, url: str) -> bool:
        for item in self._items:
            if isinstance(item, Bookmark) and item.url == url:
                return True
            if isinstance(item, BookmarkFolder):
                if any(c.url == url for c in item.children):
                    return True
        return False

    # ── Bookmark CRUD ─────────────────────────────────────────────────

    def add(self, url: str, title: str, favicon_b64: str = "",
            folder_title: str = "") -> None:
        """Add or update a URL bookmark, optionally inside a named folder."""
        if folder_title:
            folder = self._find_folder(folder_title)
            if folder is None:
                folder = BookmarkFolder(title=folder_title)
                self._items.append(folder)
            for bm in folder.children:
                if bm.url == url:
                    bm.title = title
                    bm.favicon_b64 = favicon_b64
                    self.save()
                    return
            folder.children.append(Bookmark(url=url, title=title, favicon_b64=favicon_b64))
        else:
            for item in self._items:
                if isinstance(item, Bookmark) and item.url == url:
                    item.title = title
                    item.favicon_b64 = favicon_b64
                    self.save()
                    return
            self._items.append(Bookmark(url=url, title=title, favicon_b64=favicon_b64))
        self.save()

    def remove(self, url: str) -> None:
        """Remove a URL bookmark from root or any folder."""
        self._items = [
            i for i in self._items
            if not (isinstance(i, Bookmark) and i.url == url)
        ]
        for item in self._items:
            if isinstance(item, BookmarkFolder):
                item.children = [c for c in item.children if c.url != url]
        self.save()

    # ── Folder CRUD ───────────────────────────────────────────────────

    def add_folder(self, title: str) -> BookmarkFolder:
        """Create and return a new empty folder (no-op if already exists)."""
        existing = self._find_folder(title)
        if existing:
            return existing
        folder = BookmarkFolder(title=title)
        self._items.append(folder)
        self.save()
        return folder

    def remove_folder(self, title: str) -> None:
        """Delete a folder and all its contents."""
        self._items = [
            i for i in self._items
            if not (isinstance(i, BookmarkFolder) and i.title == title)
        ]
        self.save()

    def rename_folder(self, old_title: str, new_title: str) -> bool:
        """Rename a folder. Returns True on success."""
        folder = self._find_folder(old_title)
        if folder is None:
            return False
        folder.title = new_title
        self.save()
        return True

    def get_folder(self, title: str) -> BookmarkFolder | None:
        return self._find_folder(title)

    def get_folder_names(self) -> list[str]:
        return [i.title for i in self._items if isinstance(i, BookmarkFolder)]

    # ── Import / Export ───────────────────────────────────────────────

    def import_from_chrome(self) -> list[BookmarkItem]:
        """Import Chrome bookmarks preserving folder structure.

        Returns the list of newly-added items (skips duplicates).
        """
        chrome_path = _chrome_bookmarks_path()
        if not os.path.exists(chrome_path):
            raise FileNotFoundError(
                f"Chrome Bookmarks file not found:\n{chrome_path}\n\n"
                "Make sure Google Chrome is installed and opened at least once."
            )

        with open(chrome_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        roots = data.get("roots")
        if not isinstance(roots, dict):
            raise ValueError("Unexpected Chrome Bookmarks format.")

        added: list[BookmarkItem] = []
        existing_urls = self._all_urls()
        existing_folders = {i.title for i in self._items if isinstance(i, BookmarkFolder)}

        for root_key in ("bookmark_bar", "other", "synced"):
            root_node = roots.get(root_key, {})

            # Top-level URL bookmarks
            for bm in _extract_chrome_root_urls(root_node):
                if bm.url not in existing_urls:
                    self._items.append(bm)
                    existing_urls.add(bm.url)
                    added.append(bm)

            # Folders
            for folder in _extract_chrome_root_folders(root_node):
                if folder.title not in existing_folders:
                    self._items.append(folder)
                    existing_folders.add(folder.title)
                    added.append(folder)
                else:
                    # Merge new URLs into existing folder
                    target = self._find_folder(folder.title)
                    if target:
                        for child in folder.children:
                            if child.url not in existing_urls:
                                target.children.append(child)
                                existing_urls.add(child.url)

        if added:
            self.save()
        _log.info("Chrome import: %d new items added.", len(added))
        return added

    def import_from_html(self, html_path: str) -> list[BookmarkItem]:
        """Parse a Netscape Bookmark HTML file.

        Returns newly-added items (skips duplicates).
        """
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()

        parser = _NetscapeParser()
        parser.feed(html)

        added: list[BookmarkItem] = []
        existing_urls = self._all_urls()
        existing_folders = {i.title for i in self._items if isinstance(i, BookmarkFolder)}

        for item in parser.items:
            if isinstance(item, Bookmark):
                if item.url not in existing_urls:
                    self._items.append(item)
                    existing_urls.add(item.url)
                    added.append(item)
            elif isinstance(item, BookmarkFolder):
                new_children = [c for c in item.children if c.url not in existing_urls]
                if item.title not in existing_folders:
                    folder = BookmarkFolder(title=item.title, children=new_children)
                    self._items.append(folder)
                    existing_folders.add(item.title)
                    added.append(folder)
                else:
                    target = self._find_folder(item.title)
                    if target:
                        target.children.extend(new_children)
                for c in new_children:
                    existing_urls.add(c.url)

        if added:
            self.save()
        _log.info("HTML import: %d new items added.", len(added))
        return added

    def export_to_html(self, html_path: str) -> int:
        """Export as Netscape Bookmark HTML (readable by all browsers)."""
        lines = [
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            "<!-- This is an automatically generated file. DO NOT EDIT! -->",
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            "<TITLE>Bookmarks</TITLE>",
            "<H1>Bookmarks</H1>",
            "<DL><p>",
        ]
        count = 0
        for item in self._items:
            if isinstance(item, Bookmark):
                lines.append(self._bm_to_html(item, indent=4))
                count += 1
            elif isinstance(item, BookmarkFolder):
                folder_title = item.title.replace("&", "&amp;").replace("<", "&lt;")
                lines.append(f"    <DT><H3>{folder_title}</H3>")
                lines.append("    <DL><p>")
                for child in item.children:
                    lines.append(self._bm_to_html(child, indent=8))
                    count += 1
                lines.append("    </DL><p>")
        lines.append("</DL><p>")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        _log.info("Exported %d bookmarks to %s", count, html_path)
        return count

    # ── Internal ──────────────────────────────────────────────────────

    def _find_folder(self, title: str) -> BookmarkFolder | None:
        for item in self._items:
            if isinstance(item, BookmarkFolder) and item.title == title:
                return item
        return None

    def _all_urls(self) -> set[str]:
        urls: set[str] = set()
        for item in self._items:
            if isinstance(item, Bookmark):
                urls.add(item.url)
            elif isinstance(item, BookmarkFolder):
                urls.update(c.url for c in item.children)
        return urls

    @staticmethod
    def _bm_to_html(bm: Bookmark, indent: int = 4) -> str:
        title = bm.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        url   = bm.url.replace('"', "%22")
        return " " * indent + f'<DT><A HREF="{url}">{title}</A>'
