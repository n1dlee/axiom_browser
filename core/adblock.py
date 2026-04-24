"""
AXIOM Adblock — domain-level request interceptor.

Blocklist loading order
-----------------------
1. ``core/blocklist.txt`` alongside this module — the primary, user-editable
   list.  Lines starting with ``#`` are comments; all others are bare hostnames.
2. Built-in ``_FALLBACK_BLOCKLIST`` frozenset — used if the file is missing or
   unreadable (e.g. packaged executable without the file).

Allowlist
---------
Per-domain overrides can be added at runtime (not persisted to disk yet):

    interceptor.add_to_allowlist("example.com")
    interceptor.remove_from_allowlist("example.com")

An allowed host and all its subdomains bypass the blocklist entirely.
"""

import logging
from pathlib import Path

from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo

_log = logging.getLogger(__name__)

# Path to the external list, resolved relative to this source file so it works
# from both the repo root and a PyInstaller bundle (adjust _BLOCKLIST_PATH in
# the .spec if bundling).
_BLOCKLIST_PATH = Path(__file__).with_name("blocklist.txt")

# ---------------------------------------------------------------------------
# Minimal embedded fallback (used only when blocklist.txt is absent/unreadable)
# ---------------------------------------------------------------------------
_FALLBACK_BLOCKLIST: frozenset[str] = frozenset({
    "doubleclick.net", "googleadservices.com", "googlesyndication.com",
    "google-analytics.com", "googletagmanager.com", "adservice.google.com",
    "connect.facebook.net", "pixel.facebook.com", "analytics.facebook.com",
    "amazon-adsystem.com", "bat.bing.com", "clarity.ms",
    "scorecardresearch.com", "quantserve.com", "comscore.com",
    "hotjar.com", "mixpanel.com", "amplitude.com", "segment.com",
    "criteo.com", "taboola.com", "outbrain.com", "pubmatic.com",
    "rubiconproject.com", "openx.net", "ib.adnxs.com",
})


def _load_blocklist() -> frozenset[str]:
    """Load domains from *blocklist.txt*; fall back to the embedded set."""
    try:
        if _BLOCKLIST_PATH.is_file():
            domains: set[str] = set()
            with _BLOCKLIST_PATH.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if line and not line.startswith("#"):
                        domains.add(line.lower())
            _log.debug(
                "AdBlock: loaded %d domains from %s", len(domains), _BLOCKLIST_PATH
            )
            return frozenset(domains)
    except OSError as exc:
        _log.warning(
            "AdBlock: could not read %s (%s) — using built-in fallback list.",
            _BLOCKLIST_PATH, exc,
        )
    return _FALLBACK_BLOCKLIST


# Module-level load happens once at import time (O(1) per request thereafter).
_BLOCKLIST: frozenset[str] = _load_blocklist()


# ---------------------------------------------------------------------------
# Host extraction helpers
# ---------------------------------------------------------------------------

def _extract_host(url: str) -> str:
    """Return the bare lowercase hostname from *url*, or ``""`` on error."""
    try:
        no_scheme = url.split("://", 1)[-1]
        host = no_scheme.split("/")[0].split("?")[0].split(":")[0].lower()
        return host
    except Exception:
        return ""


def _is_blocked(host: str, blocklist: frozenset[str]) -> bool:
    """Return True if *host* or any of its parent domains is in *blocklist*."""
    if host in blocklist:
        return True
    parts = host.split(".")
    for i in range(1, len(parts) - 1):
        if ".".join(parts[i:]) in blocklist:
            return True
    return False


def _is_allowed(host: str, allowlist: frozenset[str]) -> bool:
    """Return True if *host* or any of its parent domains is in *allowlist*."""
    if host in allowlist:
        return True
    parts = host.split(".")
    for i in range(1, len(parts) - 1):
        if ".".join(parts[i:]) in allowlist:
            return True
    return False


# ---------------------------------------------------------------------------
# Interceptor
# ---------------------------------------------------------------------------

class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    """Blocks ad/tracker domains before they hit the network.

    Thread-safety note: ``interceptRequest`` is called from Qt's network
    thread.  ``_enabled``, ``_blocked_count``, and ``_allowlist`` are read/
    written from both the UI thread and the network thread.  The operations
    are all atomic at the Python GIL level, which is sufficient here.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._enabled: bool = True
        self._blocked_count: int = 0
        self._allowlist: set[str] = set()

    # ── QWebEngineUrlRequestInterceptor override ───────────────────────

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        if not self._enabled:
            return
        host = _extract_host(info.requestUrl().toString())
        if not host:
            return
        if _is_allowed(host, frozenset(self._allowlist)):
            return
        if _is_blocked(host, _BLOCKLIST):
            info.block(True)
            self._blocked_count += 1

    # ── Public API ─────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    def reset_count(self) -> None:
        self._blocked_count = 0

    # ── Allowlist management ───────────────────────────────────────────

    def add_to_allowlist(self, domain: str) -> None:
        """Allow *domain* and all its subdomains, bypassing the blocklist."""
        self._allowlist.add(domain.lower().strip())

    def remove_from_allowlist(self, domain: str) -> None:
        """Remove a previous allowlist entry (silently ignored if absent)."""
        self._allowlist.discard(domain.lower().strip())

    def get_allowlist(self) -> list[str]:
        """Return a sorted copy of the current allowlist."""
        return sorted(self._allowlist)
