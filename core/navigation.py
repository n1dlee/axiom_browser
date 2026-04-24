import logging
import re
from urllib.parse import quote_plus

_log = logging.getLogger(__name__)

_DEFAULT_SEARCH_URL = "https://www.google.com/search?q={}"

_SCHEME_RE    = re.compile(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://')
_LOCALHOST_RE = re.compile(r'^localhost(:\d+)?(/.*)?$')
_DOMAIN_RE    = re.compile(r'^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(/.*)?$')


class NavigationManager:
    """Resolves user input to navigable URLs and tracks the current URL per tab.

    The *search_url* template must contain a single ``{}`` placeholder which
    will be replaced with a percent-encoded query string.  An invalid template
    (missing the placeholder) is rejected at construction/update time with a
    logged warning and falls back to Google.
    """

    def __init__(self, search_url: str = _DEFAULT_SEARCH_URL) -> None:
        self._current_urls: dict[int, str] = {}
        self._search_url = self._validated_search_url(search_url)

    # ── Search URL management ──────────────────────────────────────────

    @staticmethod
    def _validated_search_url(template: str) -> str:
        """Return *template* if it contains ``{}``; otherwise log a warning and
        fall back to the default Google template."""
        if "{}" not in template:
            _log.warning(
                "Invalid search URL template %r — missing '{}' placeholder. "
                "Falling back to Google.",
                template,
            )
            return _DEFAULT_SEARCH_URL
        return template

    def set_search_url(self, template: str) -> None:
        """Update the active search URL template (e.g. when the user changes
        their preferred search engine in Settings)."""
        self._search_url = self._validated_search_url(template)

    # ── Input resolution ───────────────────────────────────────────────

    def resolve_input(self, text: str) -> str:
        text = text.strip()
        if not text:
            return self._search_url.format("")
        if _SCHEME_RE.match(text):
            return text
        if _LOCALHOST_RE.match(text):
            return "http://" + text
        if _DOMAIN_RE.match(text) and " " not in text:
            return "https://" + text
        return self._build_search_url(text)

    def normalize_url(self, url: str) -> str:
        url = url.strip()
        if not _SCHEME_RE.match(url):
            return "https://" + url
        return url

    # ── Per-tab URL state ──────────────────────────────────────────────

    def set_current_url(self, tab_id: int, url: str) -> None:
        self._current_urls[tab_id] = url

    def get_current_url(self, tab_id: int) -> str | None:
        return self._current_urls.get(tab_id)

    def remove_tab(self, tab_id: int) -> None:
        self._current_urls.pop(tab_id, None)

    # ── Internal ───────────────────────────────────────────────────────

    def _build_search_url(self, query: str) -> str:
        return self._search_url.format(quote_plus(query))
