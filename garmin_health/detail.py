"""Minute-level data for the dashboard's detail screens, read from stored raw JSON.

Times are epoch milliseconds (UTC); the browser shows them in local time.
Nothing here contacts Garmin.
"""

from __future__ import annotations

import json
import zlib
from datetime import date, datetime, timezone
from typing import Any

from . import db, extract

# Garmin's sleepLevels activityLevel: 0 deep, 1 light, 2 REM, 3 awake.
STAGES = {0: "deep", 1: "light", 2: "rem", 3: "awake"}
# Keep phone charts light: at most this many points per series.
MAX_POINTS = 600


def _ms(value: Any) -> int | None:
    """Garmin timestamps come as epoch ms or 'YYYY-MM-DDTHH:MM:SS.0' in UTC."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.rstrip("Z").split(".")[0])
        except ValueError:
            return None
        return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
    return None


def _thin(points: list, limit: int = MAX_POINTS) -> list:
    if len(points) <= limit:
        return points
    step = len(points) / limit
    return [points[int(i * step)] for i in range(limit)] + [points[-1]]


def _pairs(items: Any, t_key: str, v_key: str, *, positive: bool = True) -> list[list]:
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        t, v = _ms(it.get(t_key)), it.get(v_key)
        if t is None or not isinstance(v, (int, float)) or (positive and v <= 0):
            continue
        out.append([t, round(v, 1)])
    out.sort()
    return _thin(out)


def _array(values: Any, v_index: int = 1) -> list[list]:
    """[[ts, value, ...], ...] arrays; Garmin uses negatives for 'no reading'."""
    out = []
    for row in values or []:
        if isinstance(row, list) and len(row) > v_index:
            t, v = row[0], row[v_index]
            if isinstance(t, (int, float)) and isinstance(v, (int, float)) and v >= 0:
                out.append([int(t), v])
    out.sort()
    return _thin(out)


def _sleep(raw: Any) -> dict[str, Any] | None:
    dto = extract.dig(raw, "dailySleepDTO") or {}
    if not dto.get("sleepTimeSeconds"):
        return None
    levels = []
    for lv in raw.get("sleepLevels") or []:
        s, e = _ms(lv.get("startGMT")), _ms(lv.get("endGMT"))
        stage = STAGES.get(int(lv.get("activityLevel", -1)))
        if s and e and stage:
            levels.append({"s": s, "e": e, "stage": stage})
    return {
        "start": _ms(dto.get("sleepStartTimestampGMT")),
        "end": _ms(dto.get("sleepEndTimestampGMT")),
        "levels": levels,
        "hr": _pairs(raw.get("sleepHeartRate"), "startGMT", "value"),
        "hrv": _pairs(raw.get("hrvData"), "startGMT", "value"),
        "spo2": _pairs(raw.get("wellnessEpochSPO2DataDTOList"), "epochTimestamp", "spo2Reading"),
        "respiration": _pairs(
            raw.get("wellnessEpochRespirationDataDTOList"), "startTimeGMT", "respirationValue"
        ),
        "stress": _pairs(raw.get("sleepStress"), "startGMT", "value", positive=False),
        "body_battery": _pairs(raw.get("sleepBodyBattery"), "startGMT", "value", positive=False),
        "restless": len(raw.get("sleepRestlessMoments") or []),
        "scores": {
            k: extract.dig(dto, "sleepScores", k, "qualifierKey")
            for k in ("totalDuration", "stress", "awakeCount", "remPercentage",
                      "restlessness", "lightPercentage", "deepPercentage")
        },  # fmt: skip
        "feedback": dto.get("sleepScoreFeedback"),
        "insight": dto.get("sleepScoreInsight"),
        "need_minutes": extract.dig(dto, "sleepNeed", "actual"),
        "avg_respiration": dto.get("averageRespirationValue"),
        "avg_stress": dto.get("avgSleepStress"),
    }


def _readiness(raw: Any) -> dict[str, Any] | None:
    e = extract.pick_readiness(raw)
    if not e:
        return None
    keys = ("sleepScore", "recoveryTime", "acwr", "stressHistory", "hrv", "sleepHistory")
    factors = {
        k: {
            "percent": e.get(f"{k}FactorPercent"),
            "feedback": e.get(f"{k}FactorFeedback"),
        }
        for k in keys
        if e.get(f"{k}FactorPercent") is not None
    }
    return {
        "score": e.get("score"),
        "level": e.get("level"),
        "feedback": e.get("feedbackShort"),
        "recovery_minutes": e.get("recoveryTime"),
        "factors": factors,
    }


def day(conn, d: date) -> dict[str, Any]:
    ds = d.isoformat()
    raw = db.load_raw(conn, ds)
    row = (db.daily_range(conn, ds, ds) or [{}])[0]
    stress = raw.get("stress") or {}
    steps = []
    for b in raw.get("steps") or []:
        t = _ms(b.get("startGMT")) if isinstance(b, dict) else None
        if t is not None:
            steps.append([t, b.get("steps") or 0, b.get("primaryActivityLevel")])
    fa = db.get_meta(conn, "fitness_age")
    return {
        "date": ds,
        "row": {k: v for k, v in row.items() if k != "fetched_at"},
        "sleep": _sleep(raw.get("sleep")),
        "hr": _array(extract.dig(raw.get("heart_rate"), "heartRateValues")),
        "hr_min": extract.dig(raw.get("heart_rate"), "minHeartRate"),
        "hr_max": extract.dig(raw.get("heart_rate"), "maxHeartRate"),
        "stress": _array(stress.get("stressValuesArray")),
        "body_battery": _array(stress.get("bodyBatteryValuesArray"), 2),
        "steps": steps,
        "readiness": _readiness(raw.get("readiness")),
        "fitness_age": json.loads(fa) if fa else None,
        "activities": db.activities_range(conn, ds, ds),
        "has_intraday": bool(raw.get("heart_rate") or raw.get("stress")),
    }


# ---- activities -------------------------------------------------------------

SERIES = {
    "directHeartRate": "hr",
    "directSpeed": "speed",
    "directElevation": "elevation",
    "directDepth": "depth",
    "directAirTemperature": "temp",
    "directSwimCadence": "cadence",
    "directRunCadence": "cadence",
    "directBikeCadence": "cadence",
    "directPower": "power",
    "directBodyBattery": "body_battery",
    "sumDistance": "distance",
}


def _hr_zones(t: list, hr: list, hr_max: float) -> list[float]:
    """Seconds in zones 1-5 by % of max HR (50-60-70-80-90)."""
    zones = [0.0] * 5
    for i in range(1, len(t)):
        h = hr[i]
        if h is None or t[i] is None or t[i - 1] is None:
            continue
        pct = h / hr_max
        if pct < 0.5:
            continue
        zones[min(4, int((pct - 0.5) * 10))] += max(0, t[i] - t[i - 1])
    return [round(z) for z in zones]


def activity(conn, activity_id: int, hr_max: float | None = None) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM activities WHERE activity_id=?", (activity_id,)).fetchone()
    if not row:
        return None
    row = dict(row)
    a = json.loads(row.pop("activity_json") or "null") or {}
    row.pop("summary_json", None)
    details_z, splits = row.pop("details_z"), json.loads(row.pop("splits_json") or "null")
    sd = a.get("summaryDTO") or {}

    series: dict[str, list] = {}
    t: list = []
    route: list = []
    if details_z:
        det = json.loads(zlib.decompress(details_z))
        idx = {m.get("key"): m.get("metricsIndex") for m in det.get("metricDescriptors") or []}
        ti = idx.get("sumDuration", idx.get("sumElapsedDuration"))
        points = [p.get("metrics") or [] for p in det.get("activityDetailMetrics") or []]
        points = _thin(points)

        def col(i):
            return [p[i] if i is not None and i < len(p) else None for p in points]

        t = col(ti)
        for key, name in SERIES.items():
            if key in idx and name not in series:
                vals = col(idx[key])
                if any(v not in (None, 0) for v in vals):
                    series[name] = [None if v is None else round(v, 2) for v in vals]
        poly = (det.get("geoPolylineDTO") or {}).get("polyline") or []
        route = _thin([[p["lat"], p["lon"]] for p in poly if p.get("lat") and p.get("lon")], 500)

    laps = []
    for lap in (splits or {}).get("lapDTOs") or []:
        laps.append({k: lap.get(k) for k in (
            "lapIndex", "distance", "duration", "movingDuration", "averageHR", "maxHR",
            "averageSpeed", "averageSWOLF", "totalNumberOfStrokes", "maxDepth", "bottomTime",
            "calories", "elevationGain",
        ) if lap.get(k) is not None})  # fmt: skip

    hr_max = hr_max or sd.get("maxHR")
    zones = _hr_zones(t, series["hr"], hr_max) if "hr" in series and t and hr_max else None
    keep = (
        "averageHR", "maxHR", "minHR", "averageSpeed", "maxSpeed", "averageMovingSpeed",
        "calories", "activityTrainingLoad", "trainingEffect", "anaerobicTrainingEffect",
        "trainingEffectLabel", "aerobicTrainingEffectMessage", "anaerobicTrainingEffectMessage",
        "averageSWOLF", "totalNumberOfStrokes", "averageStrokeDistance", "averageSwimCadence",
        "averageTemperature", "minTemperature", "maxTemperature", "elevationGain", "elevationLoss",
        "maxDepth", "averageDepth", "bottomTime", "maxBottomTime", "diveCount", "surfaceInterval",
        "differenceBodyBattery", "moderateIntensityMinutes", "vigorousIntensityMinutes",
        "recoveryHeartRate", "steps", "averageRunCadence", "averagePower", "maxVerticalSpeed",
        "elapsedDuration", "movingDuration", "duration", "distance",
    )  # fmt: skip
    return {
        **row,
        "location": a.get("locationName"),
        "stats": {k: sd[k] for k in keep if sd.get(k) is not None},
        "t": t,
        "series": series,
        "route": route,
        "laps": laps,
        "hr_zones": zones,
        "hr_max_used": hr_max,
    }
