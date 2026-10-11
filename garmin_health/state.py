"""Small JSON state file that survives between runs.

It holds the safety brakes that keep the account from being locked:
  * cooldown_until: no Garmin requests before this time (set after 429s)
  * consecutive_login_failures: counts failed runs; past the limit we stop
    trying credential logins until you log in by hand
  * needs_interactive_login: set when MFA is required or the limit is hit
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from . import config


def _path():
    return config.home() / "state.json"


def load() -> dict[str, Any]:
    try:
        return json.loads(_path().read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(state: dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, p)


def update(**changes: Any) -> dict[str, Any]:
    s = load()
    for k, v in changes.items():
        if v is None:
            s.pop(k, None)
        else:
            s[k] = v
    save(s)
    return s


def cooldown_until() -> datetime | None:
    v = load().get("cooldown_until")
    return datetime.fromisoformat(v) if v else None
