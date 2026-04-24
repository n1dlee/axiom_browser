import re
from urllib.parse import quote_plus

SEARCH_URL_TEMPLATE = "https://www.google.com/search?q={}"

_SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://')
_LOCALHOST_RE = re.compile(r'^localhost(:\d+)?(/.*)?$')
_DOMAIN_RE = re.compile(r'^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(/.*)?$')


class NavigationManager:
    def __init__(self) -> None:
        self._current_urls: dict[int, str] = {}

    def resolve_input(self, text: str) -> str:
        text = text.strip()
        if not text:
            return SEARCH_URL_TEMPLATE.format("")
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

    def set_current_url(self, tab_id: int, url: str) -> None:
        self._current_urls[tab_id] = url

    def get_current_url(self, tab_id: int) -> str | None:
        return self._current_urls.get(tab_id)

    def remove_tab(self, tab_id: int) -> None:
        self._current_urls.pop(tab_id, None)

    def _build_search_url(self, query: str) -> str:
        return SEARCH_URL_TEMPLATE.format(quote_plus(query))
