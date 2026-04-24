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
    # Indices created separately so they are idempotent on re-connect.
    _INDEX_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_history_url       ON history(url)",
        "CREATE INDEX IF NOT EXISTS idx_history_title     ON history(title)",
    ]

    # Soft cap on stored rows; prune() enforces this on demand.
    DEFAULT_MAX_ENTRIES = 50_000

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self._db_path)
        # WAL mode: readers don't block writers; safer for concurrent access.
        self._conn.execute("PRAGMA journal_mode=WAL")
        # Retry for up to 5 s before raising OperationalError on lock contention.
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute(self._CREATE_SQL)
        for idx_sql in self._INDEX_SQL:
            self._conn.execute(idx_sql)
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

    def prune_old_entries(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> int:
        """Delete the oldest rows beyond *max_entries*.

        Returns the number of rows deleted.  Call this periodically (e.g. on
        startup or after long sessions) to keep the database from growing
        without bound.
        """
        assert self._conn is not None
        cur = self._conn.execute(
            "DELETE FROM history WHERE id NOT IN "
            "(SELECT id FROM history ORDER BY timestamp DESC LIMIT ?)",
            (max_entries,),
        )
        self._conn.commit()
        return cur.rowcount

    def close(self) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
