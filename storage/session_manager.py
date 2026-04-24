import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


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
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {"tabs": [asdict(t) for t in tabs]}
        tmp_path = self._path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self._path)

    def restore_session(self) -> Optional[list[TabSession]]:
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tabs = [
                TabSession(
                    url=t["url"],
                    title=t["title"],
                    is_active=t.get("is_active", False),
                )
                for t in data.get("tabs", [])
            ]
            return tabs if tabs else None
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def clear_session(self) -> None:
        if os.path.exists(self._path):
            os.remove(self._path)
