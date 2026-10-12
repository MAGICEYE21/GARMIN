"""Fetch missing days from Garmin Connect into SQLite.

Which days get fetched:
  * every day in the backfill window (default: today and the 90 days before)
    that has no row yet: this is the first-run backfill and gap filling
  * every stored day not yet marked `final`, which always includes today
A day is final once it was fetched after the watch had synced past the end
of that day, so its numbers won't change anymore.

Days are fetched newest first and committed one by one, so an interrupted
run (rate limit, network, sleep) keeps what it got and the next run resumes.
"""

from __future__ import annotations

import fcntl
import json
import logging
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from datetime import time as dtime
from typing import Any

from garminconnect import GarminConnectTooManyRequestsError

from . import auth, config, credentials, db, export, extract
from .retry import MfaRequired, classify, with_backoff

log = logging.getLogger(__name__)

# source name -> how to fetch it for one day
SOURCES: dict[str, Callable[[Any, str], Any]] = {
    "summary": lambda api, d: api.get_user_summary(d),
    "sleep": lambda api, d: api.get_sleep_data(d),
    "hrv": lambda api, d: api.get_hrv_data(d),
    "readiness": lambda api, d: api.get_training_readiness(d),
    "training_status": lambda api, d: api.get_training_status(d),
    "max_metrics": lambda api, d: api.get_max_metrics(d),
}

# How long after midnight the watch must have synced for a day to be final.
FINAL_SYNC_MARGIN = timedelta(hours=2)
# Without a known sync time, treat a day as final after this long.
FINAL_FALLBACK_AGE = timedelta(hours=48)


class AlreadyRunning(RuntimeError):
    pass


def _end_of_day(day: date) -> datetime:
    return datetime.combine(day + timedelta(days=1), dtime(0)).astimezone()


def is_final(day: date, last_sync: datetime | None, now: datetime) -> bool:
    end = _end_of_day(day)
    if last_sync is None:
        return now >= end + FINAL_FALLBACK_AGE
    return last_sync >= end + FINAL_SYNC_MARGIN


def days_to_fetch(
    stored: dict[str, bool],
    today: date,
    backfill_days: int,
    *,
    since: date | None = None,
    refetch: bool = False,
) -> list[date]:
    start = since or today - timedelta(days=backfill_days)
    window = [start + timedelta(days=i) for i in range((today - start).days + 1)]
    todo = {d for d in window if refetch or not stored.get(d.isoformat(), False)}
    # Non-final days older than the window (e.g. after a long outage) too.
    todo |= {
        date.fromisoformat(d) for d, final in stored.items() if not final and d <= today.isoformat()
    }
    return sorted(todo, reverse=True)


def _fetch(fn: Callable[[], Any], what: str, sleep) -> Any:
    """Call Garmin; retry transient errors; None for 'no data' style errors."""
    try:
        return with_backoff(fn, what=what, retry_auth=False, sleep=sleep)
    except Exception as e:
        if classify(e) is None and not isinstance(e, MfaRequired):
            log.debug("%s: no data (%s)", what, e)
            return None
        raise


def notify(message: str) -> None:
    """Best-effort macOS notification so a stuck login doesn't go unnoticed."""
    if sys.platform != "darwin":
        return
    script = f'display notification "{message}" with title "Garmin health sync"'
    try:
        subprocess.run(["osascript", "-e", script], timeout=10, check=False)
    except Exception:
        pass


def sync(
    conn,
    *,
    connect: Callable[[], Any] | None = None,
    today: date | None = None,
    since: date | None = None,
    refetch: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    request_delay: float | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    delay = config.REQUEST_DELAY if request_delay is None else request_delay
    api = (connect or auth.connect)()

    def paced(fn, what):
        result = _fetch(fn, what, sleep)
        if delay:
            sleep(delay)
        return result

    # 1. When did the watch last sync?
    last_used = paced(lambda: api.get_device_last_used(), "device last used")
    summary_today = paced(lambda: api.get_user_summary(today.isoformat()), "summary")
    last_sync = extract.parse_last_sync(last_used, summary_today)
    db.set_meta(conn, "last_sync", last_sync.isoformat() if last_sync else None)
    db.set_meta(conn, "last_device", extract.dig(last_used, "lastUsedDeviceName"))
    conn.commit()
    log.info("Last watch sync: %s", last_sync)

    # Fitness age changes about weekly, so one request per run (not per day).
    try:
        fa = paced(lambda: api.get_fitnessage_data(today.isoformat()), "fitness age")
        if extract.parse_fitness_age(fa):
            db.set_meta(conn, "fitness_age", json.dumps(fa))
            conn.commit()
    except GarminConnectTooManyRequestsError:
        raise
    except Exception as e:  # not worth failing the run over
        log.warning("Fitness age unavailable: %s", e)

    days = days_to_fetch(
        db.daily_status(conn), today, config.BACKFILL_DAYS, since=since, refetch=refetch
    )
    log.info("Fetching %d day(s): %s .. %s", len(days), days[-1], days[0])

    # 2. Activities over the same span (plus a couple of days for late uploads).
    act_start = min(min(days), today - timedelta(days=2))
    activities = (
        paced(
            lambda: api.get_activities_by_date(act_start.isoformat(), today.isoformat()),
            "activities",
        )
        or []
    )
    for a in activities:
        if isinstance(a, dict) and a.get("activityId"):
            db.upsert_activity(conn, int(a["activityId"]), extract.parse_activity(a), a)
    conn.commit()

    # 3. Daily metrics, newest first, committed per day.
    now = datetime.now().astimezone()
    for i, day in enumerate(days, 1):
        ds = day.isoformat()
        raw = {}
        for source, fn in SOURCES.items():
            raw[source] = paced(lambda fn=fn: fn(api, ds), f"{source} {ds}")
            db.save_raw(conn, ds, source, raw[source])
        db.upsert_daily(conn, ds, extract.parse_day(raw), final=is_final(day, last_sync, now))
        conn.commit()
        if i % 10 == 0:
            log.info("  %d/%d days done", i, len(days))

    # 4. Full details for activities we haven't detailed yet.
    ids = [int(a["activityId"]) for a in activities if isinstance(a, dict) and a.get("activityId")]
    detailed = 0
    for aid in db.activities_missing_details(conn, ids):
        activity = paced(lambda: api.get_activity(aid), f"activity {aid}")
        splits = paced(lambda: api.get_activity_splits(aid), f"splits {aid}")
        details = (
            paced(lambda: api.get_activity_details(aid), f"details {aid}")
            if config.FETCH_ACTIVITY_DETAILS
            else None
        )
        db.save_activity_details(conn, aid, activity=activity, splits=splits, details=details)
        conn.commit()
        detailed += 1

    db.set_meta(conn, "last_success", db.now_iso())
    conn.commit()
    return {"days": len(days), "activities": len(activities), "detailed": detailed}


def run(*, force: bool = False, since: date | None = None, refetch: bool = False) -> int:
    """Entry point for launchd/CLI. Returns a process exit code."""
    config.ensure_dirs()
    lock = open(config.lock_path(), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.warning("Another sync is already running; exiting.")
        return 0

    conn = db.connect()
    run_id = db.start_run(conn)
    try:
        result = sync(
            conn,
            connect=lambda: auth.connect(interactive=False, force=force),
            since=since,
            refetch=refetch,
        )
    except auth.LoginBlocked as e:
        log.warning("Skipped: %s", e)
        cooldown = "cooldown" in str(e).lower()
        if not cooldown:
            notify("Garmin login needed: run bin/garmin-health login")
        db.finish_run(conn, run_id, "skipped" if cooldown else "login_needed", message=str(e))
        return 0 if cooldown else 3
    except (MfaRequired, credentials.CredentialsMissing) as e:
        msg = f"{e}. Run `bin/garmin-health login` in Terminal."
        log.error(msg)
        notify("Garmin login needed: run bin/garmin-health login")
        db.finish_run(conn, run_id, "login_needed", message=msg)
        return 3
    except GarminConnectTooManyRequestsError as e:
        auth.set_rate_limit_cooldown()
        log.error("Rate limited by Garmin, stopping; progress is saved. %s", e)
        db.finish_run(conn, run_id, "rate_limited", message=str(e)[:500])
        return 2
    except Exception as e:
        log.exception("Sync failed")
        db.finish_run(conn, run_id, "error", message=f"{type(e).__name__}: {e}"[:500])
        return 1
    else:
        log.info(
            "Sync OK: %d day(s), %d activities listed, %d new activity details",
            result["days"],
            result["activities"],
            result["detailed"],
        )
        db.finish_run(
            conn, run_id, "ok", days=result["days"], activities=result["activities"]
        )
        return 0
    finally:
        # Even after a failed run, so the agent sees the current sync status.
        export.run(conn)
        conn.close()
        lock.close()


def reparse(conn) -> int:
    """Rebuild `daily` and activity columns from stored raw JSON, offline."""
    days = conn.execute("SELECT date, final, fetched_at FROM daily").fetchall()
    for r in days:
        db.upsert_daily(
            conn,
            r["date"],
            extract.parse_day(db.load_raw(conn, r["date"])),
            final=bool(r["final"]),
            fetched_at=r["fetched_at"],
        )
    for r in conn.execute("SELECT activity_id, summary_json FROM activities").fetchall():
        a = json.loads(r["summary_json"])
        db.upsert_activity(conn, r["activity_id"], extract.parse_activity(a), a)
    conn.commit()
    return len(days)
