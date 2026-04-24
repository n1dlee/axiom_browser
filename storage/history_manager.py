import sqlite3
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class HistoryEntry:
    id: int
    url: str
    title: str
    timestamp: float


class HistoryManager:
    _CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            url       TEXT NOT NULL,
            title     TEXT NOT NULL DEFAULT '',
            timestamp REAL NOT NULL
        )
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(self._CREATE_SQL)
        self._conn.commit()

    def add_entry(self, url: str, title: str = "") -> int:
        assert self._conn is not None
        cur = self._conn.execute(
            "INSERT INTO history (url, title, timestamp) VALUES (?, ?, ?)",
            (url, title, time.time()),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_recent(self, limit: int = 100) -> list[HistoryEntry]:
        assert self._conn is not None
        cur = self._conn.execute(
            "SELECT id, url, title, timestamp FROM history ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [HistoryEntry(id=r[0], url=r[1], title=r[2], timestamp=r[3]) for r in cur]

    def search(self, query: str) -> list[HistoryEntry]:
        assert self._conn is not None
        pattern = f"%{query}%"
        cur = self._conn.execute(
            "SELECT id, url, title, timestamp FROM history "
            "WHERE url LIKE ? OR title LIKE ? ORDER BY timestamp DESC",
            (pattern, pattern),
        )
        return [HistoryEntry(id=r[0], url=r[1], title=r[2], timestamp=r[3]) for r in cur]

    def clear(self) -> None:
        assert self._conn is not None
        self._conn.execute("DELETE FROM history")
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
