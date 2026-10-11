"""Daily recovery summary, trend series, and a plain-text brief for an AI assistant."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any

from . import config, db

HRV_STATUS_SCORE = {"BALANCED": 80, "UNBALANCED": 50, "LOW": 35, "POOR": 20}


def _avg(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(mean(vals), 1) if vals else None


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def freshness(conn, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now().astimezone()
    last = db.get_meta(conn, "last_sync")
    last_sync = datetime.fromisoformat(last) if last else None
    age = (now - last_sync).total_seconds() / 3600 if last_sync else None
    run = db.last_run(conn)
    return {
        "last_watch_sync": last_sync.isoformat(timespec="minutes") if last_sync else None,
        "hours_since_sync": round(age, 1) if age is not None else None,
        "stale": age is None or age > config.STALE_HOURS,
        "stale_after_hours": config.STALE_HOURS,
        "device": db.get_meta(conn, "last_device"),
        "last_run": {
            k: run[k] for k in ("started_at", "finished_at", "status", "message")
        }
        if run
        else None,
        "last_successful_run": db.get_meta(conn, "last_success"),
    }


def recovery(day: dict, baseline: dict) -> dict[str, Any]:
    """Score 0-100 from whichever of sleep, HRV, RHR, Body Battery, readiness exist."""
    parts: dict[str, float] = {}
    notes: list[str] = []

    if day.get("sleep_score") is not None:
        parts["sleep"] = day["sleep_score"]
    secs = day.get("sleep_seconds")
    if secs is not None and secs < 6 * 3600:
        notes.append(f"short sleep ({secs // 3600}h{secs % 3600 // 60:02d}m)")

    hrv, lo, hi = day.get("hrv_last_night"), day.get("hrv_baseline_low"), day.get("hrv_baseline_high")
    if hrv is not None and lo is not None and hi is not None:
        if hrv < lo:
            parts["hrv"] = _clamp(60 - 100 * (lo - hrv) / max(lo, 1))
            notes.append(f"HRV {hrv:.0f} ms below baseline ({lo:.0f}-{hi:.0f})")
        elif hrv > hi:
            parts["hrv"] = 85
        else:
            parts["hrv"] = 80
    elif day.get("hrv_status") in HRV_STATUS_SCORE:
        parts["hrv"] = HRV_STATUS_SCORE[day["hrv_status"]]

    rhr, rhr_base = day.get("resting_hr"), baseline.get("resting_hr")
    if rhr is not None and rhr_base is not None:
        delta = rhr - rhr_base
        parts["resting_hr"] = _clamp(80 - 8 * delta if delta > 0 else 80 - 4 * delta)
        if delta >= 3:
            notes.append(f"resting HR {delta:+.0f} bpm vs 30-day average")

    bb = day.get("bb_wake") if day.get("bb_wake") is not None else day.get("bb_high")
    if bb is not None:
        parts["body_battery"] = bb
        if bb < 40:
            notes.append(f"Body Battery only {bb} at wake")

    if day.get("readiness_score") is not None:
        parts["readiness"] = day["readiness_score"]

    if day.get("acwr_status") == "HIGH":
        notes.append("training load ramping up fast (high acute:chronic ratio)")

    score = round(mean(parts.values())) if parts else None
    if score is None:
        label = "unknown"
    elif score >= 75:
        label = "good"
    elif score >= 50:
        label = "fair"
    else:
        label = "low"
    return {"score": score, "label": label, "components": parts, "notes": notes}


def _has_overnight_data(row: dict | None) -> bool:
    return bool(row) and any(
        row.get(k) is not None for k in ("sleep_seconds", "hrv_last_night", "readiness_score")
    )


def build(conn, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    rows = db.daily_range(conn, (today - timedelta(days=90)).isoformat(), today.isoformat())
    by_date = {r["date"]: r for r in rows}

    current = by_date.get(today.isoformat())
    if not _has_overnight_data(current):
        current = next((r for r in reversed(rows) if _has_overnight_data(r)), current)
    current = current or {}
    cur_date = current.get("date")

    prior = [r for r in rows if cur_date and r["date"] < cur_date]
    last30 = prior[-30:]
    baseline = {
        k: _avg(r[k] for r in last30)
        for k in ("resting_hr", "hrv_last_night", "sleep_seconds", "sleep_score", "stress_avg")
    }

    def window(n):
        return [r for r in rows if r["date"] > (today - timedelta(days=n)).isoformat()]

    def trend(n):
        w = window(n)
        return {
            "sleep_hours": _avg(r["sleep_seconds"] / 3600 if r["sleep_seconds"] else None for r in w),
            "sleep_score": _avg(r["sleep_score"] for r in w),
            "hrv": _avg(r["hrv_last_night"] for r in w),
            "resting_hr": _avg(r["resting_hr"] for r in w),
            "body_battery_high": _avg(r["bb_high"] for r in w),
            "stress": _avg(r["stress_avg"] for r in w),
            "steps": _avg(r["steps"] for r in w),
        }

    yesterday = by_date.get((today - timedelta(days=1)).isoformat()) or {}
    acts = db.activities_range(conn, (today - timedelta(days=7)).isoformat(), today.isoformat())

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="minutes"),
        "date": today.isoformat(),
        "recovery_date": cur_date,
        "freshness": freshness(conn),
        "recovery": recovery(current, baseline),
        "today": {k: v for k, v in current.items() if k not in ("fetched_at", "final")},
        "yesterday_activity": {
            "steps": yesterday.get("steps"),
            "step_goal": yesterday.get("step_goal"),
            "stress_avg": yesterday.get("stress_avg"),
            "bb_drained": yesterday.get("bb_drained"),
        },
        "baseline_30d": baseline,
        "averages": {"7d": trend(7), "30d": trend(30), "90d": trend(90)},
        "activities_7d": acts,
    }


def trends(conn, days: int, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    by_date = {r["date"]: r for r in db.daily_range(conn, start.isoformat(), today.isoformat())}
    load_by_date: dict[str, float] = {}
    for a in db.activities_range(conn, start.isoformat(), today.isoformat()):
        if a["training_load"]:
            load_by_date[a["date"]] = load_by_date.get(a["date"], 0) + a["training_load"]

    dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]

    def col(name, scale=1.0, nd=None):
        out = []
        for d in dates:
            v = (by_date.get(d) or {}).get(name)
            out.append(None if v is None else round(v / scale, 2 if nd is None else nd))
        return out

    return {
        "dates": dates,
        "sleep": {
            "deep": col("deep_seconds", 3600),
            "light": col("light_seconds", 3600),
            "rem": col("rem_seconds", 3600),
            "awake": col("awake_seconds", 3600),
            "score": col("sleep_score"),
        },
        "hrv": {
            "last_night": col("hrv_last_night"),
            "weekly_avg": col("hrv_weekly_avg"),
            "baseline_low": col("hrv_baseline_low"),
            "baseline_high": col("hrv_baseline_high"),
        },
        "resting_hr": col("resting_hr"),
        "body_battery": {"high": col("bb_high"), "low": col("bb_low"), "wake": col("bb_wake")},
        "training_load": {
            "daily": [round(load_by_date[d]) if d in load_by_date else None for d in dates],
            "acute": col("acute_load", nd=0),
            "chronic": col("chronic_load", nd=0),
        },
        "stress": col("stress_avg"),
        "steps": col("steps"),
    }


# ---- text -----------------------------------------------------------------


def _hm(seconds) -> str:
    if not seconds:
        return "n/a"
    m = int(seconds) // 60
    return f"{m // 60}h{m % 60:02d}m"


def _n(v, unit="", nd=0) -> str:
    if v is None:
        return "n/a"
    return f"{v:,.{nd}f}{unit}"


def _pretty(key: str | None) -> str:
    return key.replace("_", " ").lower() if key else "n/a"


def text(s: dict[str, Any]) -> str:
    t, r, f, b = s["today"], s["recovery"], s["freshness"], s["baseline_30d"]
    a7, a30 = s["averages"]["7d"], s["averages"]["30d"]
    lines = [f"Garmin health summary for {s['date']}."]

    if f["last_watch_sync"]:
        sync = f"Watch last synced {f['hours_since_sync']:.0f}h ago ({f['last_watch_sync']})."
    else:
        sync = "Watch sync time unknown."
    if f["stale"]:
        sync += f" WARNING: data is stale (older than {f['stale_after_hours']}h)."
    lines.append(sync)
    if s["recovery_date"] and s["recovery_date"] != s["date"]:
        lines.append(f"No overnight data for today yet; recovery is for {s['recovery_date']}.")

    if r["score"] is not None:
        rec = f"Recovery: {r['label'].upper()} ({r['score']}/100)"
        lines.append(rec + (f"; watch: {'; '.join(r['notes'])}." if r["notes"] else "."))

    if t.get("sleep_seconds"):
        lines.append(
            f"Sleep {_hm(t['sleep_seconds'])}, score {_n(t.get('sleep_score'))}"
            f" (deep {_hm(t.get('deep_seconds'))}, REM {_hm(t.get('rem_seconds'))},"
            f" awake {_hm(t.get('awake_seconds'))})."
        )
    if t.get("hrv_last_night") is not None:
        base = ""
        if t.get("hrv_baseline_low") is not None:
            base = f", baseline {_n(t['hrv_baseline_low'])}-{_n(t['hrv_baseline_high'])}"
        lines.append(
            f"HRV {_n(t['hrv_last_night'])} ms last night (status {_pretty(t.get('hrv_status'))}"
            f"{base}; 7-day avg {_n(t.get('hrv_weekly_avg'))})."
        )
    vitals = []
    if t.get("resting_hr") is not None:
        vitals.append(f"Resting HR {t['resting_hr']} bpm (30-day avg {_n(b.get('resting_hr'), nd=1)})")
    if t.get("bb_wake") is not None or t.get("bb_high") is not None:
        vitals.append(
            f"Body Battery {_n(t.get('bb_wake'))} at wake (high {_n(t.get('bb_high'))}, low {_n(t.get('bb_low'))})"
        )
    if vitals:
        lines.append(". ".join(vitals) + ".")
    if t.get("readiness_score") is not None:
        lines.append(
            f"Training readiness {t['readiness_score']} ({_pretty(t.get('readiness_level'))})."
        )
    if t.get("training_status") or t.get("acute_load") is not None:
        lines.append(
            f"Training status: {_pretty(t.get('training_status'))}; acute load {_n(t.get('acute_load'))}"
            f" / chronic {_n(t.get('chronic_load'))} (ratio {_n(t.get('acwr'), nd=1)},"
            f" {_pretty(t.get('acwr_status'))})."
        )
    if t.get("vo2max_running") is not None:
        lines.append(f"VO2 max {_n(t['vo2max_running'], nd=1)}.")

    y = s["yesterday_activity"]
    if y.get("steps") is not None:
        lines.append(f"Yesterday: {_n(y['steps'])} steps, average stress {_n(y.get('stress_avg'))}.")

    def diff(k, unit, nd=0):
        if a7.get(k) is None or a30.get(k) is None:
            return None
        return f"{k.replace('_', ' ')} {a7[k] - a30[k]:+.{nd}f}{unit}"

    diffs = [
        d
        for d in (
            diff("sleep_hours", "h", 1),
            diff("hrv", " ms"),
            diff("resting_hr", " bpm"),
            diff("stress", ""),
        )
        if d
    ]
    if diffs:
        lines.append("Last 7 days vs 30-day average: " + ", ".join(diffs) + ".")

    acts = s["activities_7d"]
    if acts:
        parts = []
        for a in acts[-5:]:
            p = f"{a['date']} {_pretty(a['type'])}"
            if a.get("distance_m"):
                p += f" {a['distance_m'] / 1000:.1f} km"
            if a.get("duration_s"):
                p += f" {_hm(a['duration_s'])}"
            if a.get("avg_hr"):
                p += f" avg HR {a['avg_hr']:.0f}"
            if a.get("training_load"):
                p += f" load {a['training_load']:.0f}"
            parts.append(p)
        lines.append(f"Activities last 7 days ({len(acts)}): " + "; ".join(parts) + ".")
    else:
        lines.append("No activities in the last 7 days.")
    return "\n".join(lines)
