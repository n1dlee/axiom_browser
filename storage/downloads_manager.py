import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DownloadStatus(Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"


@dataclass
class DownloadEntry:
    id: int
    filename: str
    source_url: str
    save_path: str
    status: DownloadStatus
    size_bytes: int
    timestamp: float


class DownloadsManager:
    _CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS downloads (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            filename   TEXT NOT NULL,
            source_url TEXT NOT NULL,
            save_path  TEXT NOT NULL DEFAULT '',
            status     TEXT NOT NULL DEFAULT 'pending',
            size_bytes INTEGER NOT NULL DEFAULT 0,
            timestamp  REAL NOT NULL
        )
    """
    _INDEX_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_downloads_timestamp ON downloads(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_downloads_status    ON downloads(status)",
    ]

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

    def add_download(
        self,
        filename: str,
        source_url: str,
        save_path: str = "",
        size_bytes: int = 0,
    ) -> int:
        assert self._conn is not None
        cur = self._conn.execute(
            "INSERT INTO downloads (filename, source_url, save_path, status, size_bytes, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (filename, source_url, save_path, DownloadStatus.PENDING.value, size_bytes, time.time()),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def update_status(self, download_id: int, status: DownloadStatus) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE downloads SET status = ? WHERE id = ?",
            (status.value, download_id),
        )
        self._conn.commit()

    def update_progress(self, download_id: int, size_bytes: int) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE downloads SET size_bytes = ?, status = ? WHERE id = ?",
            (size_bytes, DownloadStatus.IN_PROGRESS.value, download_id),
        )
        self._conn.commit()

    def get_all(self) -> list[DownloadEntry]:
        assert self._conn is not None
        cur = self._conn.execute(
            "SELECT id, filename, source_url, save_path, status, size_bytes, timestamp "
            "FROM downloads ORDER BY timestamp DESC"
        )
        return [
            DownloadEntry(
                id=r[0],
                filename=r[1],
                source_url=r[2],
                save_path=r[3],
                status=DownloadStatus(r[4]),
                size_bytes=r[5],
                timestamp=r[6],
            )
            for r in cur
        ]

    def close(self) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
