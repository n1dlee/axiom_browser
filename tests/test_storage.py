import os
import time
import pytest

from storage.history_manager import HistoryManager, HistoryEntry
from storage.downloads_manager import DownloadsManager, DownloadStatus, DownloadEntry
from storage.session_manager import SessionManager, TabSession


# ── HistoryManager ────────────────────────────────────────────────────────────

@pytest.fixture
def history() -> HistoryManager:
    mgr = HistoryManager(db_path=":memory:")
    mgr.connect()
    yield mgr
    mgr.close()


def test_history_add_entry_returns_id(history: HistoryManager) -> None:
    row_id = history.add_entry("https://example.com", "Example")
    assert isinstance(row_id, int)
    assert row_id >= 1


def test_history_get_recent_empty(history: HistoryManager) -> None:
    assert history.get_recent() == []


def test_history_add_and_get_recent(history: HistoryManager) -> None:
    history.add_entry("https://a.com", "A")
    history.add_entry("https://b.com", "B")
    entries = history.get_recent(10)
    assert len(entries) == 2


def test_history_ordered_by_time_desc(history: HistoryManager) -> None:
    history.add_entry("https://first.com", "First")
    time.sleep(0.01)
    history.add_entry("https://second.com", "Second")
    entries = history.get_recent(10)
    assert entries[0].url == "https://second.com"
    assert entries[1].url == "https://first.com"


def test_history_get_recent_limit(history: HistoryManager) -> None:
    for i in range(5):
        history.add_entry(f"https://site{i}.com", f"Site {i}")
    entries = history.get_recent(3)
    assert len(entries) == 3


def test_history_search_by_url(history: HistoryManager) -> None:
    history.add_entry("https://python.org", "Python")
    history.add_entry("https://rust-lang.org", "Rust")
    results = history.search("python")
    assert len(results) == 1
    assert results[0].url == "https://python.org"


def test_history_search_by_title(history: HistoryManager) -> None:
    history.add_entry("https://a.com", "Amazing Page")
    history.add_entry("https://b.com", "Boring Page")
    results = history.search("Amazing")
    assert len(results) == 1


def test_history_search_no_results(history: HistoryManager) -> None:
    history.add_entry("https://example.com", "Example")
    assert history.search("zzznomatch") == []


def test_history_clear(history: HistoryManager) -> None:
    history.add_entry("https://example.com", "Example")
    history.clear()
    assert history.get_recent() == []


def test_history_entry_fields(history: HistoryManager) -> None:
    history.add_entry("https://example.com", "My Title")
    entry = history.get_recent(1)[0]
    assert entry.url == "https://example.com"
    assert entry.title == "My Title"
    assert entry.timestamp > 0
    assert isinstance(entry.id, int)


# ── DownloadsManager ──────────────────────────────────────────────────────────

@pytest.fixture
def downloads() -> DownloadsManager:
    mgr = DownloadsManager(db_path=":memory:")
    mgr.connect()
    yield mgr
    mgr.close()


def test_downloads_add_returns_id(downloads: DownloadsManager) -> None:
    row_id = downloads.add_download("file.zip", "https://example.com/file.zip")
    assert isinstance(row_id, int)
    assert row_id >= 1


def test_downloads_initial_status_is_pending(downloads: DownloadsManager) -> None:
    row_id = downloads.add_download("file.zip", "https://x.com/file.zip")
    entries = downloads.get_all()
    assert entries[0].status == DownloadStatus.PENDING


def test_downloads_update_status_completed(downloads: DownloadsManager) -> None:
    row_id = downloads.add_download("file.zip", "https://x.com/file.zip")
    downloads.update_status(row_id, DownloadStatus.COMPLETED)
    entries = downloads.get_all()
    assert entries[0].status == DownloadStatus.COMPLETED


def test_downloads_update_status_failed(downloads: DownloadsManager) -> None:
    row_id = downloads.add_download("file.zip", "https://x.com/file.zip")
    downloads.update_status(row_id, DownloadStatus.FAILED)
    assert downloads.get_all()[0].status == DownloadStatus.FAILED


def test_downloads_update_progress(downloads: DownloadsManager) -> None:
    row_id = downloads.add_download("big.zip", "https://x.com/big.zip")
    downloads.update_progress(row_id, 1024 * 1024)
    entry = downloads.get_all()[0]
    assert entry.size_bytes == 1024 * 1024
    assert entry.status == DownloadStatus.IN_PROGRESS


def test_downloads_get_all_multiple(downloads: DownloadsManager) -> None:
    downloads.add_download("a.zip", "https://x.com/a")
    downloads.add_download("b.zip", "https://x.com/b")
    entries = downloads.get_all()
    assert len(entries) == 2


def test_downloads_ordered_by_time_desc(downloads: DownloadsManager) -> None:
    downloads.add_download("a.zip", "https://x.com/a")
    time.sleep(0.01)
    downloads.add_download("b.zip", "https://x.com/b")
    entries = downloads.get_all()
    assert entries[0].filename == "b.zip"


def test_downloads_entry_fields(downloads: DownloadsManager) -> None:
    row_id = downloads.add_download("doc.pdf", "https://x.com/doc.pdf", "/downloads/doc.pdf", 2048)
    entry = downloads.get_all()[0]
    assert entry.filename == "doc.pdf"
    assert entry.source_url == "https://x.com/doc.pdf"
    assert entry.save_path == "/downloads/doc.pdf"
    assert entry.size_bytes == 2048
    assert entry.timestamp > 0


# ── SessionManager ────────────────────────────────────────────────────────────

@pytest.fixture
def session(tmp_path) -> SessionManager:
    return SessionManager(session_path=str(tmp_path / "session.json"))


def test_session_restore_nonexistent_returns_none(session: SessionManager) -> None:
    assert session.restore_session() is None


def test_session_save_and_restore(session: SessionManager) -> None:
    tabs = [
        TabSession(url="https://a.com", title="A", is_active=True),
        TabSession(url="https://b.com", title="B", is_active=False),
    ]
    session.save_session(tabs)
    restored = session.restore_session()
    assert restored is not None
    assert len(restored) == 2
    assert restored[0].url == "https://a.com"
    assert restored[0].title == "A"
    assert restored[0].is_active is True
    assert restored[1].is_active is False


def test_session_restore_preserves_order(session: SessionManager) -> None:
    tabs = [TabSession(f"https://site{i}.com", f"Site {i}", i == 0) for i in range(4)]
    session.save_session(tabs)
    restored = session.restore_session()
    assert restored is not None
    assert [t.url for t in restored] == [f"https://site{i}.com" for i in range(4)]


def test_session_clear(session: SessionManager) -> None:
    session.save_session([TabSession("https://a.com", "A", True)])
    session.clear_session()
    assert session.restore_session() is None


def test_session_clear_nonexistent_no_error(session: SessionManager) -> None:
    session.clear_session()  # must not raise


def test_session_empty_tabs_list(session: SessionManager) -> None:
    session.save_session([])
    restored = session.restore_session()
    assert restored is None


def test_session_overwrite(session: SessionManager) -> None:
    session.save_session([TabSession("https://old.com", "Old", True)])
    session.save_session([TabSession("https://new.com", "New", True)])
    restored = session.restore_session()
    assert restored is not None
    assert restored[0].url == "https://new.com"
