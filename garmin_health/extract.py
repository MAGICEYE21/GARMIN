"""Turn raw Garmin Connect JSON into flat values.

Garmin's response shapes are undocumented and drift over time, so every
lookup here tolerates missing keys, nulls and lists-instead-of-dicts.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def dig(obj: Any, *path: Any) -> Any:
    for key in path:
        if obj is None:
            return None
        if isinstance(key, int):
            if not isinstance(obj, list) or len(obj) <= key:
                return None
            obj = obj[key]
        else:
            if not isinstance(obj, dict):
                return None
            obj = obj.get(key)
    return obj


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


def _pos(v: Any) -> float | None:
    """Garmin uses -1/-2 for 'no data' in several fields."""
    f = _num(v)
    return f if f is not None and f >= 0 else None


def _int(v: Any) -> int | None:
    f = _num(v)
    return int(round(f)) if f is not None else None


def _ms_to_local_iso(ms: Any) -> str | None:
    f = _num(ms)
    if not f:
        return None
    return (
        datetime.fromtimestamp(f / 1000, tz=timezone.utc)
        .astimezone()
        .isoformat(timespec="minutes")
    )


def _phrase(v: Any) -> str | None:
    """'PRODUCTIVE_3' -> 'PRODUCTIVE'."""
    if not isinstance(v, str) or not v:
        return None
    return re.sub(r"_\d+$", "", v)


def _primary_device_entry(mapping: Any) -> dict | None:
    """Training-status maps are keyed by device id; prefer the primary device."""
    if not isinstance(mapping, dict) or not mapping:
        return None
    entries = [v for v in mapping.values() if isinstance(v, dict)]
    for e in entries:
        if e.get("primaryTrainingDevice"):
            return e
    return entries[0] if entries else None


def parse_sleep(sleep: Any) -> dict[str, Any]:
    dto = dig(sleep, "dailySleepDTO") or {}
    total = _int(dto.get("sleepTimeSeconds"))
    if not total:
        return {}
    return {
        "sleep_score": _int(dig(dto, "sleepScores", "overall", "value")),
        "sleep_quality": dig(dto, "sleepScores", "overall", "qualifierKey"),
        "sleep_seconds": total,
        "deep_seconds": _int(dto.get("deepSleepSeconds")),
        "light_seconds": _int(dto.get("lightSleepSeconds")),
        "rem_seconds": _int(dto.get("remSleepSeconds")),
        "awake_seconds": _int(dto.get("awakeSleepSeconds")),
        # The *GMT fields are reliable; *Local ones are double-shifted for some users.
        "sleep_start": _ms_to_local_iso(dto.get("sleepStartTimestampGMT")),
        "sleep_end": _ms_to_local_iso(dto.get("sleepEndTimestampGMT")),
        "spo2_sleep_avg": _pos(dto.get("averageSpO2Value")),
        "spo2_sleep_low": _int(_pos(dto.get("lowestSpO2Value"))),
    }


def parse_hrv(hrv: Any) -> dict[str, Any]:
    s = dig(hrv, "hrvSummary") or {}
    return {
        "hrv_last_night": _pos(s.get("lastNightAvg")),
        "hrv_weekly_avg": _pos(s.get("weeklyAvg")),
        "hrv_status": s.get("status") or None,
        "hrv_baseline_low": _pos(dig(s, "baseline", "balancedLow")),
        "hrv_baseline_high": _pos(dig(s, "baseline", "balancedUpper")),
    }


def parse_summary(summary: Any) -> dict[str, Any]:
    s = summary if isinstance(summary, dict) else {}
    return {
        "resting_hr": _int(_pos(s.get("restingHeartRate"))),
        "bb_high": _int(_pos(s.get("bodyBatteryHighestValue"))),
        "bb_low": _int(_pos(s.get("bodyBatteryLowestValue"))),
        "bb_charged": _int(_pos(s.get("bodyBatteryChargedValue"))),
        "bb_drained": _int(_pos(s.get("bodyBatteryDrainedValue"))),
        "bb_wake": _int(_pos(s.get("bodyBatteryAtWakeTime"))),
        "stress_avg": _int(_pos(s.get("averageStressLevel"))),
        "stress_max": _int(_pos(s.get("maxStressLevel"))),
        "steps": _int(_pos(s.get("totalSteps"))),
        "step_goal": _int(_pos(s.get("dailyStepGoal"))),
        "spo2_avg": _pos(s.get("averageSpo2")),
        "spo2_low": _int(_pos(s.get("lowestSpo2"))),
    }


def pick_readiness(readiness: Any) -> dict | None:
    if isinstance(readiness, dict):
        readiness = [readiness]
    if not isinstance(readiness, list) or not readiness:
        return None
    entries = [e for e in readiness if isinstance(e, dict)]
    for e in entries:
        if e.get("inputContext") == "AFTER_WAKEUP_RESET":
            return e
    return entries[0] if entries else None


def parse_readiness(readiness: Any) -> dict[str, Any]:
    e = pick_readiness(readiness) or {}
    return {
        "readiness_score": _int(_pos(e.get("score"))),
        "readiness_level": e.get("level") or None,
        "readiness_feedback": _phrase(e.get("feedbackShort")),
    }


def parse_training_status(ts: Any) -> dict[str, Any]:
    latest = _primary_device_entry(
        dig(ts, "mostRecentTrainingStatus", "latestTrainingStatusData")
    ) or {}
    load = latest.get("acuteTrainingLoadDTO") or {}
    return {
        "training_status": _phrase(latest.get("trainingStatusFeedbackPhrase")),
        "acute_load": _pos(load.get("dailyTrainingLoadAcute")),
        "chronic_load": _pos(load.get("dailyTrainingLoadChronic")),
        "acwr": _pos(load.get("dailyAcuteChronicWorkloadRatio")),
        "acwr_status": load.get("acwrStatus") or None,
        "vo2max_running": _pos(
            dig(ts, "mostRecentVO2Max", "generic", "vo2MaxPreciseValue")
            or dig(ts, "mostRecentVO2Max", "generic", "vo2MaxValue")
        ),
        "vo2max_cycling": _pos(
            dig(ts, "mostRecentVO2Max", "cycling", "vo2MaxPreciseValue")
            or dig(ts, "mostRecentVO2Max", "cycling", "vo2MaxValue")
        ),
    }


def parse_max_metrics(mm: Any) -> dict[str, Any]:
    entry = mm[0] if isinstance(mm, list) and mm else mm
    out = {}
    run = _pos(
        dig(entry, "generic", "vo2MaxPreciseValue") or dig(entry, "generic", "vo2MaxValue")
    )
    bike = _pos(
        dig(entry, "cycling", "vo2MaxPreciseValue") or dig(entry, "cycling", "vo2MaxValue")
    )
    if run is not None:
        out["vo2max_running"] = run
    if bike is not None:
        out["vo2max_cycling"] = bike
    return out


def parse_day(raw: dict[str, Any]) -> dict[str, Any]:
    """Combine every source for one day into a `daily` row."""
    v: dict[str, Any] = {}
    v.update(parse_summary(raw.get("summary")))
    v.update(parse_sleep(raw.get("sleep")))
    v.update(parse_hrv(raw.get("hrv")))
    v.update(parse_readiness(raw.get("readiness")))
    v.update(parse_training_status(raw.get("training_status")))
    # max-metrics is dated to the day; prefer it over "most recent" values.
    v.update(parse_max_metrics(raw.get("max_metrics")))
    if v.get("resting_hr") is None:
        v["resting_hr"] = _int(_pos(dig(raw.get("sleep"), "restingHeartRate")))
    if v.get("hrv_last_night") is None:
        v["hrv_last_night"] = _pos(dig(raw.get("sleep"), "avgOvernightHrv"))
    return v


def parse_fitness_age(fa: Any) -> dict[str, Any] | None:
    """Garmin's fitness age (updated about weekly) and the real age it compares to."""
    if not isinstance(fa, dict) or _pos(fa.get("fitnessAge")) is None:
        return None
    return {
        "fitness_age": round(fa["fitnessAge"], 1),
        "chronological_age": _int(_pos(fa.get("chronologicalAge"))),
        "achievable_fitness_age": _pos(fa.get("achievableFitnessAge")),
        "updated": fa.get("lastUpdated"),
    }


def parse_activity(a: dict[str, Any]) -> dict[str, Any]:
    start = a.get("startTimeLocal") or ""
    return {
        "date": start[:10] or None,
        "start_local": start or None,
        "type": dig(a, "activityType", "typeKey"),
        "name": a.get("activityName"),
        "duration_s": _pos(a.get("duration")),
        "moving_s": _pos(a.get("movingDuration")),
        "distance_m": _pos(a.get("distance")),
        "elevation_gain_m": _pos(a.get("elevationGain")),
        "avg_hr": _pos(a.get("averageHR")),
        "max_hr": _pos(a.get("maxHR")),
        "calories": _pos(a.get("calories")),
        "training_load": _pos(a.get("activityTrainingLoad")),
        "aerobic_te": _pos(a.get("aerobicTrainingEffect")),
        "anaerobic_te": _pos(a.get("anaerobicTrainingEffect")),
        "vo2max": _pos(a.get("vO2MaxValue")),
    }


def parse_last_sync(device_last_used: Any, summary: Any = None) -> datetime | None:
    """When the watch last uploaded to Garmin Connect (aware datetime)."""
    ms = _num(dig(device_last_used, "lastUsedDeviceUploadTime"))
    if ms:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
    gmt = dig(summary, "lastSyncTimestampGMT")
    if isinstance(gmt, str) and gmt:
        try:
            dt = datetime.fromisoformat(gmt.replace("Z", ""))
        except ValueError:
            return None
        return dt.replace(tzinfo=timezone.utc).astimezone()
    return None
