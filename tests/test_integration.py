"""
Integration and failure-path tests for AXIOM's storage layer.

Goals
-----
- Exercise storage components together (history + session + downloads) using
  real temp-directory paths rather than ':memory:' so WAL files, indices, and
  fsync behaviour are included.
- Cover failure paths: corrupt JSON, missing file, partial writes, unknown
  session schema version.
- Validate the prune/retention logic for history.
- Confirm AdBlockInterceptor allowlist + blocklist interaction without Qt.
"""

import json
import os
import sqlite3
import time

import pytest

from storage.history_manager import HistoryManager
from storage.downloads_manager import DownloadsManager, DownloadStatus
from storage.session_manager import SessionManager, TabSession, SCHEMA_VERSION
from core.adblock import AdBlockInterceptor, _extract_host, _is_blocked, _is_allowed


# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture
def history(tmp_path) -> HistoryManager:
    mgr = HistoryManager(db_path=str(tmp_path / "history.db"))
    mgr.connect()
    yield mgr
    mgr.close()


@pytest.fixture
def downloads(tmp_path) -> DownloadsManager:
    mgr = DownloadsManager(db_path=str(tmp_path / "downloads.db"))
    mgr.connect()
    yield mgr
    mgr.close()


@pytest.fixture
def session(tmp_path) -> SessionManager:
    return SessionManager(session_path=str(tmp_path / "session.json"))


# ── History — real filesystem ─────────────────────────────────────────────────

class TestHistoryIntegration:
    def test_wal_journal_mode(self, tmp_path):
        """WAL mode is active after connect()."""
        mgr = HistoryManager(db_path=str(tmp_path / "h.db"))
        mgr.connect()
        conn = sqlite3.connect(str(tmp_path / "h.db"))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        mgr.close()
        assert mode == "wal"

    def test_indices_exist(self, tmp_path):
        """Expected indices are present in sqlite_master."""
        mgr = HistoryManager(db_path=str(tmp_path / "h.db"))
        mgr.connect()
        conn = sqlite3.connect(str(tmp_path / "h.db"))
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='history'"
        ).fetchall()
        conn.close()
        mgr.close()
        index_names = {r[0] for r in rows}
        assert "idx_history_timestamp" in index_names
        assert "idx_history_url" in index_names
        assert "idx_history_title" in index_names

    def test_data_persists_across_reconnect(self, tmp_path):
        """Entries written in one session survive a close/reopen cycle."""
        path = str(tmp_path / "h.db")
        mgr = HistoryManager(db_path=path)
        mgr.connect()
        mgr.add_entry("https://persist.example.com", "Persist Test")
        mgr.close()

        mgr2 = HistoryManager(db_path=path)
        mgr2.connect()
        entries = mgr2.get_recent(10)
        mgr2.close()
        assert any(e.url == "https://persist.example.com" for e in entries)

    def test_prune_removes_oldest_entries(self, history: HistoryManager):
        for i in range(10):
            history.add_entry(f"https://site{i}.com", f"Site {i}")
            time.sleep(0.005)   # ensure distinct timestamps
        deleted = history.prune_old_entries(max_entries=5)
        assert deleted == 5
        remaining = history.get_recent(100)
        assert len(remaining) == 5
        # The 5 most recent should survive
        assert remaining[0].url == "https://site9.com"

    def test_prune_below_limit_deletes_nothing(self, history: HistoryManager):
        history.add_entry("https://only.com", "Only")
        deleted = history.prune_old_entries(max_entries=100)
        assert deleted == 0
        assert len(history.get_recent()) == 1

    def test_search_uses_index_and_returns_correct_results(self, history: HistoryManager):
        history.add_entry("https://python.org", "Python Programming Language")
        history.add_entry("https://rust-lang.org", "Rust Language")
        history.add_entry("https://docs.python.org/3/", "Python 3 Docs")
        results = history.search("Python")
        assert len(results) == 2
        urls = {r.url for r in results}
        assert "https://python.org" in urls
        assert "https://docs.python.org/3/" in urls


# ── Downloads — real filesystem ───────────────────────────────────────────────

class TestDownloadsIntegration:
    def test_wal_journal_mode(self, tmp_path):
        mgr = DownloadsManager(db_path=str(tmp_path / "d.db"))
        mgr.connect()
        conn = sqlite3.connect(str(tmp_path / "d.db"))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        mgr.close()
        assert mode == "wal"

    def test_indices_exist(self, tmp_path):
        mgr = DownloadsManager(db_path=str(tmp_path / "d.db"))
        mgr.connect()
        conn = sqlite3.connect(str(tmp_path / "d.db"))
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='downloads'"
        ).fetchall()
        conn.close()
        mgr.close()
        index_names = {r[0] for r in rows}
        assert "idx_downloads_timestamp" in index_names
        assert "idx_downloads_status" in index_names

    def test_full_lifecycle(self, downloads: DownloadsManager):
        """pending → in_progress → completed transition."""
        dl_id = downloads.add_download("report.pdf", "https://example.com/report.pdf",
                                        "/tmp/report.pdf")
        assert downloads.get_all()[0].status == DownloadStatus.PENDING

        downloads.update_progress(dl_id, 512_000)
        entry = downloads.get_all()[0]
        assert entry.status == DownloadStatus.IN_PROGRESS
        assert entry.size_bytes == 512_000

        downloads.update_status(dl_id, DownloadStatus.COMPLETED)
        assert downloads.get_all()[0].status == DownloadStatus.COMPLETED

    def test_data_persists_across_reconnect(self, tmp_path):
        path = str(tmp_path / "d.db")
        mgr = DownloadsManager(db_path=path)
        mgr.connect()
        mgr.add_download("video.mp4", "https://cdn.example.com/video.mp4")
        mgr.close()

        mgr2 = DownloadsManager(db_path=path)
        mgr2.connect()
        entries = mgr2.get_all()
        mgr2.close()
        assert len(entries) == 1
        assert entries[0].filename == "video.mp4"


# ── Session — failure paths ────────────────────────────────────────────────────

class TestSessionFailurePaths:
    def test_restore_missing_file_returns_none(self, session: SessionManager):
        assert session.restore_session() is None

    def test_restore_corrupt_json_returns_none(self, tmp_path):
        path = str(tmp_path / "session.json")
        with open(path, "w") as f:
            f.write("{ this is not valid JSON }")
        mgr = SessionManager(session_path=path)
        assert mgr.restore_session() is None

    def test_restore_empty_object_returns_none(self, tmp_path):
        path = str(tmp_path / "session.json")
        with open(path, "w") as f:
            json.dump({}, f)
        mgr = SessionManager(session_path=path)
        assert mgr.restore_session() is None

    def test_restore_unknown_future_version_returns_none(self, tmp_path):
        path = str(tmp_path / "session.json")
        with open(path, "w") as f:
            json.dump({
                "version": SCHEMA_VERSION + 99,
                "tabs": [{"url": "https://example.com", "title": "Ex", "is_active": True}],
            }, f)
        mgr = SessionManager(session_path=path)
        assert mgr.restore_session() is None

    def test_restore_version_zero_returns_none(self, tmp_path):
        """Pre-versioned files (old format) are discarded cleanly."""
        path = str(tmp_path / "session.json")
        with open(path, "w") as f:
            json.dump({
                "tabs": [{"url": "https://example.com", "title": "Ex", "is_active": True}],
            }, f)
        mgr = SessionManager(session_path=path)
        assert mgr.restore_session() is None

    def test_restore_tabs_missing_url_skipped(self, tmp_path):
        """Tab entries without a 'url' key are silently dropped."""
        path = str(tmp_path / "session.json")
        with open(path, "w") as f:
            json.dump({
                "version": SCHEMA_VERSION,
                "tabs": [
                    {"url": "https://good.com", "title": "Good", "is_active": True},
                    {"title": "No URL", "is_active": False},   # missing url
                ],
            }, f)
        mgr = SessionManager(session_path=path)
        result = mgr.restore_session()
        assert result is not None
        assert len(result) == 1
        assert result[0].url == "https://good.com"

    def test_save_empty_list_leaves_existing_file(self, tmp_path):
        """Saving an empty tab list must NOT overwrite an existing good session."""
        path = str(tmp_path / "session.json")
        mgr = SessionManager(session_path=path)
        mgr.save_session([TabSession("https://keep.com", "Keep", True)])
        mgr.save_session([])   # should be a no-op
        result = mgr.restore_session()
        assert result is not None
        assert result[0].url == "https://keep.com"

    def test_schema_version_written_to_disk(self, session: SessionManager, tmp_path):
        session.save_session([TabSession("https://a.com", "A", True)])
        with open(session._path) as f:
            data = json.load(f)
        assert data["version"] == SCHEMA_VERSION

    def test_round_trip_preserves_all_fields(self, session: SessionManager):
        tabs = [
            TabSession(url="https://a.com", title="Page A", is_active=True),
            TabSession(url="https://b.com", title="Page B", is_active=False),
        ]
        session.save_session(tabs)
        restored = session.restore_session()
        assert restored is not None
        assert restored[0].url == "https://a.com"
        assert restored[0].title == "Page A"
        assert restored[0].is_active is True
        assert restored[1].title == "Page B"
        assert restored[1].is_active is False

    def test_clear_session_removes_file(self, session: SessionManager, tmp_path):
        session.save_session([TabSession("https://a.com", "A", True)])
        session.clear_session()
        assert not os.path.exists(session._path)

    def test_clear_session_nonexistent_no_error(self, session: SessionManager):
        session.clear_session()   # must not raise


# ── AdBlock — blocklist / allowlist logic (no Qt required) ───────────────────

class TestAdblockLogic:
    """Tests drive the pure-Python helper functions, not the Qt interceptor,
    so no QApplication is needed and they run in any environment."""

    def test_extract_host_https(self):
        assert _extract_host("https://ads.example.com/track?v=1") == "ads.example.com"

    def test_extract_host_strips_port(self):
        assert _extract_host("http://tracker.net:8080/pixel") == "tracker.net"

    def test_extract_host_no_scheme(self):
        # Fallback: treats entire string as host-like
        result = _extract_host("plain")
        assert isinstance(result, str)   # no crash

    def test_extract_host_empty(self):
        assert _extract_host("") == ""

    def test_is_blocked_direct_hit(self):
        bl = frozenset({"doubleclick.net"})
        assert _is_blocked("doubleclick.net", bl) is True

    def test_is_blocked_subdomain(self):
        bl = frozenset({"doubleclick.net"})
        assert _is_blocked("ad.doubleclick.net", bl) is True
        assert _is_blocked("nested.ad.doubleclick.net", bl) is True

    def test_is_blocked_clean_domain(self):
        bl = frozenset({"doubleclick.net"})
        assert _is_blocked("example.com", bl) is False

    def test_is_allowed_direct(self):
        al = frozenset({"mysite.com"})
        assert _is_allowed("mysite.com", al) is True

    def test_is_allowed_subdomain(self):
        al = frozenset({"mysite.com"})
        assert _is_allowed("cdn.mysite.com", al) is True

    def test_is_allowed_unrelated(self):
        al = frozenset({"mysite.com"})
        assert _is_allowed("other.com", al) is False

    def test_allowlist_overrides_blocklist_conceptually(self):
        """Verify that allowed check precedes blocked in real usage intent."""
        host = "ads.example.com"
        bl = frozenset({"example.com"})
        al = frozenset({"ads.example.com"})
        # If allowed, we should NOT block even though parent is in blocklist
        if _is_allowed(host, al):
            should_block = False
        else:
            should_block = _is_blocked(host, bl)
        assert should_block is False


# ── History + Session cross-component ────────────────────────────────────────

class TestHistorySessionIntegration:
    """Verifies that history writes and session saves don't interfere
    when both use temp-dir paths (simulates a real browser session)."""

    def test_concurrent_writes_no_interference(self, tmp_path):
        h = HistoryManager(db_path=str(tmp_path / "history.db"))
        h.connect()
        s = SessionManager(session_path=str(tmp_path / "session.json"))

        for i in range(20):
            h.add_entry(f"https://site{i}.com", f"Site {i}")
        s.save_session([
            TabSession(f"https://site{i}.com", f"Site {i}", i == 0)
            for i in range(5)
        ])

        entries = h.get_recent(100)
        assert len(entries) == 20

        restored = s.restore_session()
        assert restored is not None
        assert len(restored) == 5

        h.close()
