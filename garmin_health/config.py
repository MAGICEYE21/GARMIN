"""Paths and tunables. Everything can be overridden with environment variables."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "garmin-health"
KEYCHAIN_SERVICE = "garmin-health"
KEYCHAIN_EMAIL_ACCOUNT = "__email__"


def _default_home() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def _default_logs() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_NAME
    return home() / "logs"


def home() -> Path:
    return Path(os.environ.get("GARMIN_HEALTH_HOME", _default_home())).expanduser()


def db_path() -> Path:
    return Path(os.environ.get("GARMIN_HEALTH_DB", home() / "health.db")).expanduser()


def token_dir() -> Path:
    return Path(os.environ.get("GARMIN_HEALTH_TOKENS", home() / "tokens")).expanduser()


def log_dir() -> Path:
    return Path(os.environ.get("GARMIN_HEALTH_LOGS", _default_logs())).expanduser()


def lock_path() -> Path:
    return home() / "sync.lock"


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


# How far back the first run (and gap detection) reaches.
BACKFILL_DAYS = _int("GARMIN_HEALTH_BACKFILL_DAYS", 90)
# Data whose last watch sync is older than this is flagged as stale.
STALE_HOURS = _int("GARMIN_HEALTH_STALE_HOURS", 12)
# Pause between API calls so a 90-day backfill doesn't hammer Garmin.
REQUEST_DELAY = _float("GARMIN_HEALTH_REQUEST_DELAY", 1.0)
# Activity detail charts (GPS/HR/pace time series). Set to 0 to skip.
FETCH_ACTIVITY_DETAILS = os.environ.get("GARMIN_HEALTH_ACTIVITY_DETAILS", "1") != "0"

WEB_HOST = os.environ.get("GARMIN_HEALTH_HOST", "127.0.0.1")
WEB_PORT = _int("GARMIN_HEALTH_PORT", 8765)


def ensure_dirs() -> None:
    """Create the data, token and log directories, owner-only."""
    for d in (home(), token_dir(), log_dir()):
        d.mkdir(parents=True, exist_ok=True)
        os.chmod(d, 0o700)
