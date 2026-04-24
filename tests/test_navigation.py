import pytest
from core.navigation import NavigationManager, _DEFAULT_SEARCH_URL


@pytest.fixture
def nav() -> NavigationManager:
    return NavigationManager()


# ── URL resolution (default Google engine) ────────────────────────────────────

def test_resolve_full_url(nav: NavigationManager) -> None:
    assert nav.resolve_input("https://example.com") == "https://example.com"


def test_resolve_full_url_http(nav: NavigationManager) -> None:
    assert nav.resolve_input("http://example.com") == "http://example.com"


def test_resolve_bare_domain(nav: NavigationManager) -> None:
    assert nav.resolve_input("example.com") == "https://example.com"


def test_resolve_bare_domain_with_path(nav: NavigationManager) -> None:
    assert nav.resolve_input("example.com/path") == "https://example.com/path"


def test_resolve_search_query(nav: NavigationManager) -> None:
    result = nav.resolve_input("what is python")
    assert "google.com/search" in result
    assert "what" in result


def test_resolve_single_word_no_tld(nav: NavigationManager) -> None:
    result = nav.resolve_input("python")
    assert "google.com/search" in result


def test_resolve_localhost(nav: NavigationManager) -> None:
    result = nav.resolve_input("localhost:3000")
    assert "localhost:3000" in result
    assert result.startswith("http://")


def test_resolve_localhost_no_port(nav: NavigationManager) -> None:
    result = nav.resolve_input("localhost")
    assert "localhost" in result
    assert result.startswith("http://")


def test_resolve_strips_whitespace(nav: NavigationManager) -> None:
    assert nav.resolve_input("  google.com  ") == "https://google.com"


def test_resolve_file_url(nav: NavigationManager) -> None:
    assert nav.resolve_input("file:///path/to/file") == "file:///path/to/file"


def test_resolve_ftp_url(nav: NavigationManager) -> None:
    assert nav.resolve_input("ftp://files.example.com") == "ftp://files.example.com"


def test_normalize_adds_https(nav: NavigationManager) -> None:
    assert nav.normalize_url("example.com") == "https://example.com"


def test_normalize_preserves_https(nav: NavigationManager) -> None:
    assert nav.normalize_url("https://example.com") == "https://example.com"


def test_normalize_preserves_http(nav: NavigationManager) -> None:
    assert nav.normalize_url("http://example.com") == "http://example.com"


def test_search_url_encodes_spaces(nav: NavigationManager) -> None:
    result = nav.resolve_input("hello world")
    assert "hello+world" in result or "hello%20world" in result


def test_search_url_encodes_special_chars(nav: NavigationManager) -> None:
    result = nav.resolve_input("c++ tutorial")
    assert "google.com/search" in result
    assert " " not in result


def test_set_and_get_current_url(nav: NavigationManager) -> None:
    nav.set_current_url(0, "https://example.com")
    assert nav.get_current_url(0) == "https://example.com"


def test_get_current_url_unknown_tab(nav: NavigationManager) -> None:
    assert nav.get_current_url(999) is None


def test_remove_tab_cleans_up(nav: NavigationManager) -> None:
    nav.set_current_url(1, "https://example.com")
    nav.remove_tab(1)
    assert nav.get_current_url(1) is None


def test_remove_nonexistent_tab_no_error(nav: NavigationManager) -> None:
    nav.remove_tab(999)  # must not raise


# ── Custom search engine ───────────────────────────────────────────────────────

def test_custom_search_url_at_construction() -> None:
    """Search queries use the injected template, not the hard-coded Google URL."""
    custom = NavigationManager(search_url="https://duckduckgo.com/?q={}")
    result = custom.resolve_input("axiom browser")
    assert "duckduckgo.com" in result
    assert "google.com" not in result


def test_custom_search_url_encodes_query() -> None:
    custom = NavigationManager(search_url="https://search.example.com/q?q={}")
    result = custom.resolve_input("hello world")
    assert "search.example.com" in result
    assert "hello" in result
    assert " " not in result


def test_set_search_url_updates_at_runtime(nav: NavigationManager) -> None:
    """set_search_url() takes effect immediately for subsequent queries."""
    nav.set_search_url("https://bing.com/search?q={}")
    result = nav.resolve_input("python asyncio")
    assert "bing.com" in result
    assert "google.com" not in result


def test_invalid_search_url_fallback_to_google() -> None:
    """A template without '{}' must fall back to Google and not raise."""
    bad = NavigationManager(search_url="https://bad.example.com/no-placeholder")
    result = bad.resolve_input("test query")
    # Falls back to Google default
    assert "google.com/search" in result


def test_invalid_set_search_url_fallback(nav: NavigationManager) -> None:
    """set_search_url() with a bad template falls back without raising."""
    nav.set_search_url("https://broken.example.com/")
    result = nav.resolve_input("fallback test")
    assert "google.com/search" in result


def test_custom_search_url_does_not_affect_domain_resolution() -> None:
    """Bare domains still resolve to https://, regardless of search engine."""
    custom = NavigationManager(search_url="https://duckduckgo.com/?q={}")
    assert custom.resolve_input("example.com") == "https://example.com"
    assert custom.resolve_input("https://python.org") == "https://python.org"
