"""SQLite storage. Every write is an upsert, so re-running a sync is harmless.

Raw Garmin responses are kept in `raw` alongside the parsed `daily` columns,
so if Garmin changes a field name the columns can be rebuilt offline with
`garmin-health reparse` instead of re-downloading.
"""

from __future__ import annotations

import json
import os
import sqlite3
import zlib
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config

SCHEMA_VERSION = 2

DAILY_COLUMNS = [
    # sleep
    "sleep_score", "sleep_quality", "sleep_seconds", "deep_seconds",
    "light_seconds", "rem_seconds", "awake_seconds", "sleep_start", "sleep_end",
    # HRV
    "hrv_last_night", "hrv_weekly_avg", "hrv_status", "hrv_baseline_low",
    "hrv_baseline_high",
    # heart / body battery / stress / steps
    "resting_hr", "bb_high", "bb_low", "bb_charged", "bb_drained", "bb_wake",
    "stress_avg", "stress_max", "steps", "step_goal",
    # training
    "readiness_score", "readiness_level", "readiness_feedback",
    "training_status", "acute_load", "chronic_load", "acwr", "acwr_status",
    "vo2max_running", "vo2max_cycling",
    # blood oxygen (day and overnight)
    "spo2_avg", "spo2_low", "spo2_sleep_avg", "spo2_sleep_low",
]  # fmt: skip

ACTIVITY_COLUMNS = [
    "date", "start_local", "type", "name", "duration_s", "moving_s",
    "distance_m", "elevation_gain_m", "avg_hr", "max_hr", "calories",
    "training_load", "aerobic_te", "anaerobic_te", "vo2max",
]  # fmt: skip

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS daily (
    date TEXT PRIMARY KEY,
    {", ".join(DAILY_COLUMNS)},
    fetched_at TEXT NOT NULL,
    final INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS raw (
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    json TEXT,
    PRIMARY KEY (date, source)
);
CREATE TABLE IF NOT EXISTS activities (
    activity_id INTEGER PRIMARY KEY,
    {", ".join(ACTIVITY_COLUMNS)},
    summary_json TEXT,
    activity_json TEXT,
    details_z BLOB,
    splits_json TEXT,
    details_fetched_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS activities_date ON activities(date);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT,
    days_fetched INTEGER DEFAULT 0,
    activities_fetched INTEGER DEFAULT 0,
    message TEXT
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path or config.db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    conn = sqlite3.connect(path, timeout=30)
    if new:
        os.chmod(path, 0o600)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    # Columns added after a database was created; `reparse` fills them from raw.
    have = {r[1] for r in conn.execute("PRAGMA table_info(daily)")}
    for col in DAILY_COLUMNS:
        if col not in have:
            conn.execute(f"ALTER TABLE daily ADD COLUMN {col}")
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return conn


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---- meta -----------------------------------------------------------------


def set_meta(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, None if value is None else str(value)),
    )


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


# ---- daily ----------------------------------------------------------------


def save_raw(conn: sqlite3.Connection, day: str, source: str, payload: Any) -> None:
    conn.execute(
        "INSERT INTO raw(date, source, fetched_at, json) VALUES(?, ?, ?, ?) "
        "ON CONFLICT(date, source) DO UPDATE SET "
        "fetched_at=excluded.fetched_at, json=excluded.json",
        (day, source, now_iso(), json.dumps(payload)),
    )


def load_raw(conn: sqlite3.Connection, day: str) -> dict[str, Any]:
    rows = conn.execute("SELECT source, json FROM raw WHERE date=?", (day,))
    return {r["source"]: json.loads(r["json"]) if r["json"] else None for r in rows}


def upsert_daily(
    conn: sqlite3.Connection,
    day: str,
    values: dict[str, Any],
    *,
    final: bool,
    fetched_at: str | None = None,
) -> None:
    cols = DAILY_COLUMNS
    row = [values.get(c) for c in cols]
    placeholders = ", ".join("?" for _ in range(len(cols) + 3))
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols)
    conn.execute(
        f"INSERT INTO daily(date, {', '.join(cols)}, fetched_at, final) "
        f"VALUES({placeholders}) "
        f"ON CONFLICT(date) DO UPDATE SET {updates}, "
        "fetched_at=excluded.fetched_at, final=excluded.final",
        [day, *row, fetched_at or now_iso(), int(final)],
    )


def daily_status(conn: sqlite3.Connection) -> dict[str, bool]:
    """date -> final flag, for every stored day."""
    return {r[0]: bool(r[1]) for r in conn.execute("SELECT date, final FROM daily")}


def days_missing_sources(conn: sqlite3.Connection, sources: list[str]) -> list[str]:
    """Stored days (newest first) that lack a raw response for any of `sources`."""
    marks = ", ".join("?" for _ in sources)
    rows = conn.execute(
        f"SELECT d.date FROM daily d WHERE (SELECT COUNT(*) FROM raw r WHERE r.date = d.date "
        f"AND r.source IN ({marks})) < ? ORDER BY d.date DESC",
        [*sources, len(sources)],
    )
    return [r[0] for r in rows]


def daily_range(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM daily WHERE date BETWEEN ? AND ? ORDER BY date", (start, end)
    )
    return [dict(r) for r in rows]


# ---- activities -----------------------------------------------------------


def upsert_activity(
    conn: sqlite3.Connection, activity_id: int, values: dict[str, Any], summary: Any
) -> None:
    cols = ACTIVITY_COLUMNS
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols)
    conn.execute(
        f"INSERT INTO activities(activity_id, {', '.join(cols)}, summary_json, "
        f"updated_at) VALUES({', '.join('?' for _ in range(len(cols) + 3))}) "
        f"ON CONFLICT(activity_id) DO UPDATE SET {updates}, "
        "summary_json=excluded.summary_json, updated_at=excluded.updated_at",
        [activity_id, *[values.get(c) for c in cols], json.dumps(summary), now_iso()],
    )


def activities_missing_details(conn: sqlite3.Connection, ids: Iterable[int]) -> list[int]:
    ids = list(ids)
    if not ids:
        return []
    have = {
        r[0]
        for r in conn.execute(
            f"SELECT activity_id FROM activities WHERE details_fetched_at IS NOT NULL "
            f"AND activity_id IN ({', '.join('?' for _ in ids)})",
            ids,
        )
    }
    return [i for i in ids if i not in have]


def save_activity_details(
    conn: sqlite3.Connection,
    activity_id: int,
    *,
    activity: Any,
    splits: Any,
    details: Any,
) -> None:
    conn.execute(
        "UPDATE activities SET activity_json=?, splits_json=?, details_z=?, "
        "details_fetched_at=? WHERE activity_id=?",
        (
            json.dumps(activity),
            json.dumps(splits),
            zlib.compress(json.dumps(details).encode()) if details is not None else None,
            now_iso(),
            activity_id,
        ),
    )


def load_activity_details(conn: sqlite3.Connection, activity_id: int) -> Any:
    row = conn.execute(
        "SELECT details_z FROM activities WHERE activity_id=?", (activity_id,)
    ).fetchone()
    if not row or row[0] is None:
        return None
    return json.loads(zlib.decompress(row[0]))


def activities_range(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    rows = conn.execute(
        f"SELECT activity_id, {', '.join(ACTIVITY_COLUMNS)} FROM activities "
        "WHERE date BETWEEN ? AND ? ORDER BY start_local",
        (start, end),
    )
    return [dict(r) for r in rows]


# ---- runs -----------------------------------------------------------------


def start_run(conn: sqlite3.Connection) -> int:
    cur = conn.execute("INSERT INTO runs(started_at) VALUES(?)", (now_iso(),))
    conn.commit()
    return cur.lastrowid


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    *,
    days: int = 0,
    activities: int = 0,
    message: str | None = None,
) -> None:
    conn.execute(
        "UPDATE runs SET finished_at=?, status=?, days_fetched=?, "
        "activities_fetched=?, message=? WHERE id=?",
        (now_iso(), status, days, activities, message, run_id),
    )
    conn.commit()


def last_run(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None
