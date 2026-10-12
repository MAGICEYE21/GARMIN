"""Daily summary JSON files for an agent that can't reach this Mac.

After every sync, run() writes into the export folder (Google Drive by default):
  YYYY-MM-DD.json  the summary for that day (rewritten while the day changes)
  latest.json      the newest summary, replaced on every run

The files hold health data and sync status only: no email, password or tokens.
Exporting never contacts Garmin, so it can't add to a rate limit.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from . import config, state, summary

log = logging.getLogger(__name__)

FOLDER_NAME = "Garmin Daily"
# Google Drive for desktop names the "My Drive" folder in the system language.
_MY_DRIVE_NAMES = ("My Drive", "האחסון שלי")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")


def export_dir() -> Path | None:
    """GARMIN_HEALTH_EXPORT_DIR if set, else "Garmin Daily" in Google Drive."""
    env = os.environ.get("GARMIN_HEALTH_EXPORT_DIR")
    if env:
        return Path(env).expanduser()
    cloud = Path.home() / "Library" / "CloudStorage"
    for account in sorted(cloud.glob("GoogleDrive-*")):
        for name in _MY_DRIVE_NAMES:
            if (account / name).is_dir():
                return account / name / FOLDER_NAME
    return None


def _sync_status() -> dict[str, Any]:
    """Safety brakes as plain facts, so the agent knows why data may be old."""
    s = state.load()
    return {
        "cooldown_until": s.get("cooldown_until"),
        "needs_interactive_login": bool(s.get("needs_interactive_login")),
        "reason": s.get("needs_interactive_login_reason"),
    }


def build(conn, day: date | None = None) -> dict[str, Any]:
    s = summary.build(conn, today=day)
    s["sync_status"] = _sync_status()
    s["text"] = summary.text(s)
    return s


def _dump(data: dict[str, Any]) -> str:
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    # Belt and braces: Garmin error messages can echo the login email.
    return _EMAIL_RE.sub("[redacted]", text)


def _write(path: Path, text: str) -> None:
    # Write next to the database first, then move, so Drive never uploads a
    # half-written file.
    fd, tmp = tempfile.mkstemp(dir=config.home(), suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, 0o644)
    shutil.move(tmp, path)


def _stale_days(conn, out: Path) -> list[date]:
    """Stored days whose file is missing or older than the data behind it.

    Comparing against the files themselves (not this run's work) means a run
    cut short by a rate limit still gets its days exported by the next run.
    """
    days = []
    for d, fetched_at in conn.execute("SELECT date, fetched_at FROM daily"):
        f = out / f"{d}.json"
        fetched = datetime.fromisoformat(fetched_at).timestamp()
        if not f.exists() or f.stat().st_mtime < fetched:
            days.append(date.fromisoformat(d))
    return days


def write(conn, today: date | None = None) -> Path | None:
    """Write today's file, latest.json, and any day file that is out of date."""
    out = export_dir()
    if out is None:
        log.info("Export skipped: no Google Drive folder (set GARMIN_HEALTH_EXPORT_DIR)")
        return None
    out.mkdir(parents=True, exist_ok=True)
    today = today or date.today()
    latest = _dump(build(conn, today))
    _write(out / f"{today.isoformat()}.json", latest)
    _write(out / "latest.json", latest)
    days = sorted(set(_stale_days(conn, out)) - {today})
    for day in days:
        _write(out / f"{day.isoformat()}.json", _dump(build(conn, day)))
    log.info("Exported %d summary file(s) to %s", len(days) + 1, out)
    return out


def run(conn) -> None:
    """Called after every sync; an export problem never fails the sync."""
    try:
        write(conn)
    except Exception:
        log.exception("Export failed")
