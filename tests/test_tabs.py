import pytest
from pytestqt.qtbot import QtBot

from core.tab_manager import TabManager, TabState


@pytest.fixture
def tab_mgr(qtbot: QtBot) -> TabManager:
    return TabManager()


# ── Creation ──────────────────────────────────────────────────────────────────

def test_create_tab_returns_zero(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab("https://example.com")
    assert tab_id == 0


def test_create_tab_increments_ids(tab_mgr: TabManager) -> None:
    ids = [tab_mgr.create_tab(f"https://site{i}.com") for i in range(3)]
    assert ids == [0, 1, 2]


def test_create_tab_count(tab_mgr: TabManager) -> None:
    tab_mgr.create_tab()
    tab_mgr.create_tab()
    assert tab_mgr.get_tab_count() == 2


def test_create_tab_empty_url(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    tab = tab_mgr.get_tab(tab_id)
    assert tab is not None
    assert tab.url == ""


def test_create_tab_stores_url(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab("https://example.com")
    tab = tab_mgr.get_tab(tab_id)
    assert tab is not None
    assert tab.url == "https://example.com"


def test_create_tab_default_title(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    assert tab_mgr.get_tab(tab_id).title == "New Tab"


def test_create_tab_not_suspended(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    assert tab_mgr.get_tab(tab_id).suspended is False


# ── Closing ───────────────────────────────────────────────────────────────────

def test_close_tab_reduces_count(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    tab_mgr.close_tab(tab_id)
    assert tab_mgr.get_tab_count() == 0


def test_close_tab_removes_tab(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    tab_mgr.close_tab(tab_id)
    assert tab_mgr.get_tab(tab_id) is None


def test_close_nonexistent_tab_no_error(tab_mgr: TabManager) -> None:
    tab_mgr.close_tab(999)  # must not raise
    assert tab_mgr.get_tab_count() == 0


def test_close_active_tab_clears_active(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    tab_mgr.switch_to(tab_id)
    tab_mgr.close_tab(tab_id)
    assert tab_mgr.get_active_tab_id() is None


def test_close_active_tab_switches_to_remaining(tab_mgr: TabManager) -> None:
    tab_id_a = tab_mgr.create_tab()
    tab_id_b = tab_mgr.create_tab()
    tab_mgr.switch_to(tab_id_a)
    tab_mgr.close_tab(tab_id_a)
    assert tab_mgr.get_active_tab_id() == tab_id_b


# ── Switching ─────────────────────────────────────────────────────────────────

def test_switch_tab_sets_active(tab_mgr: TabManager) -> None:
    tab_mgr.create_tab()
    tab_mgr.create_tab()
    tab_mgr.switch_to(1)
    assert tab_mgr.get_active_tab_id() == 1


def test_switch_to_first_tab(tab_mgr: TabManager) -> None:
    tab_mgr.create_tab()
    tab_mgr.create_tab()
    tab_mgr.switch_to(0)
    assert tab_mgr.get_active_tab_id() == 0


def test_switch_nonexistent_tab_no_change(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    tab_mgr.switch_to(tab_id)
    tab_mgr.switch_to(999)
    assert tab_mgr.get_active_tab_id() == tab_id


# ── Suspension ────────────────────────────────────────────────────────────────

def test_suspend_tab(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    tab_mgr.suspend_tab(tab_id)
    assert tab_mgr.get_tab(tab_id).suspended is True


def test_resume_tab(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    tab_mgr.suspend_tab(tab_id)
    tab_mgr.resume_tab(tab_id)
    assert tab_mgr.get_tab(tab_id).suspended is False


def test_suspend_nonexistent_tab_no_error(tab_mgr: TabManager) -> None:
    tab_mgr.suspend_tab(999)  # must not raise


def test_resume_nonexistent_tab_no_error(tab_mgr: TabManager) -> None:
    tab_mgr.resume_tab(999)  # must not raise


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_tab_url(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab("https://old.com")
    tab_mgr.update_tab(tab_id, url="https://new.com")
    assert tab_mgr.get_tab(tab_id).url == "https://new.com"


def test_update_tab_title(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab()
    tab_mgr.update_tab(tab_id, title="My Page")
    assert tab_mgr.get_tab(tab_id).title == "My Page"


def test_update_tab_empty_values_no_change(tab_mgr: TabManager) -> None:
    tab_id = tab_mgr.create_tab("https://example.com")
    tab_mgr.update_tab(tab_id, url="", title="")
    assert tab_mgr.get_tab(tab_id).url == "https://example.com"


# ── Queries ───────────────────────────────────────────────────────────────────

def test_get_all_tabs_empty(tab_mgr: TabManager) -> None:
    assert tab_mgr.get_all_tabs() == []


def test_get_all_tabs_returns_all(tab_mgr: TabManager) -> None:
    tab_mgr.create_tab()
    tab_mgr.create_tab()
    assert len(tab_mgr.get_all_tabs()) == 2


def test_get_active_tab_id_none_initially(tab_mgr: TabManager) -> None:
    assert tab_mgr.get_active_tab_id() is None


# ── Signals ───────────────────────────────────────────────────────────────────

def test_tab_created_signal(tab_mgr: TabManager, qtbot: QtBot) -> None:
    with qtbot.waitSignal(tab_mgr.tab_created, timeout=1000) as blocker:
        tab_mgr.create_tab("https://example.com")
    assert blocker.args[0] == 0
    assert blocker.args[1] == "https://example.com"


def test_tab_closed_signal(tab_mgr: TabManager, qtbot: QtBot) -> None:
    tab_id = tab_mgr.create_tab()
    with qtbot.waitSignal(tab_mgr.tab_closed, timeout=1000) as blocker:
        tab_mgr.close_tab(tab_id)
    assert blocker.args[0] == tab_id


def test_tab_switched_signal(tab_mgr: TabManager, qtbot: QtBot) -> None:
    tab_id = tab_mgr.create_tab()
    with qtbot.waitSignal(tab_mgr.tab_switched, timeout=1000) as blocker:
        tab_mgr.switch_to(tab_id)
    assert blocker.args[0] == tab_id


def test_tab_suspended_signal(tab_mgr: TabManager, qtbot: QtBot) -> None:
    tab_id = tab_mgr.create_tab()
    with qtbot.waitSignal(tab_mgr.tab_suspended, timeout=1000) as blocker:
        tab_mgr.suspend_tab(tab_id)
    assert blocker.args[0] == tab_id


def test_tab_resumed_signal(tab_mgr: TabManager, qtbot: QtBot) -> None:
    tab_id = tab_mgr.create_tab()
    tab_mgr.suspend_tab(tab_id)
    with qtbot.waitSignal(tab_mgr.tab_resumed, timeout=1000) as blocker:
        tab_mgr.resume_tab(tab_id)
    assert blocker.args[0] == tab_id
