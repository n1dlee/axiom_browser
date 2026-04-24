import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import Optional

_log = logging.getLogger(__name__)

# Bump this whenever the on-disk format changes incompatibly so older files
# can be migrated or cleanly discarded rather than causing silent breakage.
SCHEMA_VERSION = 1


@dataclass
class TabSession:
    url: str
    title: str
    is_active: bool


def _default_session_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "Axiom", "session.json")


class SessionManager:
    def __init__(self, session_path: Optional[str] = None) -> None:
        self._path = session_path or _default_session_path()

    def save_session(self, tabs: list[TabSession]) -> None:
        """Persist *tabs* atomically via a temp-file rename.

        Raises ``OSError`` on write failure so the caller can decide how to
        surface the error (log it, show a status message, etc.).
        """
        if not tabs:
            # Nothing useful to save — leave any existing file in place so a
            # restart with an empty window doesn't wipe a good previous session.
            return
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {
            "version": SCHEMA_VERSION,
            "tabs": [asdict(t) for t in tabs],
        }
        tmp_path = self._path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self._path)

    def restore_session(self) -> Optional[list[TabSession]]:
        """Return saved tabs, or *None* if no session exists / file is corrupt.

        Handles forward-compatibility by accepting any ``version >= 1`` schema;
        unknown future keys are ignored.  Downgrade (version > SCHEMA_VERSION)
        is logged and treated as corrupt so we don't silently mis-parse data.
        """
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)

            version = data.get("version", 0)
            if not isinstance(version, int) or version < 1:
                _log.warning(
                    "Session file at %s has unknown version %r — discarding.",
                    self._path, version,
                )
                return None
            if version > SCHEMA_VERSION:
                _log.warning(
                    "Session file version %d is newer than supported %d — discarding.",
                    version, SCHEMA_VERSION,
                )
                return None

            tabs = [
                TabSession(
                    url=t["url"],
                    title=t.get("title", ""),
                    is_active=t.get("is_active", False),
                )
                for t in data.get("tabs", [])
                if isinstance(t, dict) and t.get("url")
            ]
            return tabs if tabs else None

        except (json.JSONDecodeError, KeyError, TypeError, OSError) as exc:
            _log.warning("Failed to parse session file %s: %s", self._path, exc)
            return None

    def clear_session(self) -> None:
        try:
            if os.path.exists(self._path):
                os.remove(self._path)
        except OSError as exc:
            _log.warning("Could not remove session file %s: %s", self._path, exc)
