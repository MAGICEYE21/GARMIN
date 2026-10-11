from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import keyring
import keyring.backend
import pytest


class MemoryKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def __init__(self):
        super().__init__()
        self.store = {}

    def get_password(self, service, username):
        return self.store.get((service, username))

    def set_password(self, service, username, password):
        self.store[(service, username)] = password

    def delete_password(self, service, username):
        self.store.pop((service, username), None)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("GARMIN_HEALTH_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GARMIN_HEALTH_LOGS", str(tmp_path / "logs"))
    kr = MemoryKeyring()
    keyring.set_keyring(kr)
    yield kr


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class FakeGarmin:
    """Returns Garmin-shaped payloads; records every call."""

    def __init__(self, today: date, last_sync: datetime | None = None):
        self.today = today
        self.last_sync = last_sync or datetime.now(timezone.utc)
        self.calls: list[tuple] = []
        self.fail: dict[str, list[Exception]] = {}

    def _call(self, name, *args):
        self.calls.append((name, *args))
        queue = self.fail.get(name)
        if queue:
            raise queue.pop(0)

    def n(self, name):
        return sum(1 for c in self.calls if c[0] == name)

    def _seed(self, d: str) -> int:
        return date.fromisoformat(d).toordinal() % 7

    def get_device_last_used(self):
        self._call("get_device_last_used")
        return {"lastUsedDeviceName": "fenix 8", "lastUsedDeviceUploadTime": ms(self.last_sync)}

    def get_user_summary(self, d):
        self._call("get_user_summary", d)
        k = self._seed(d)
        return {
            "totalSteps": 8000 + 500 * k,
            "dailyStepGoal": 10000,
            "restingHeartRate": 46 + k,
            "averageStressLevel": 25 + k,
            "maxStressLevel": 90,
            "bodyBatteryHighestValue": 80 + k,
            "bodyBatteryLowestValue": 20 + k,
            "bodyBatteryChargedValue": 60,
            "bodyBatteryDrainedValue": 55,
            "bodyBatteryAtWakeTime": 75 + k,
            "lastSyncTimestampGMT": "2026-10-11T05:00:00.0",
        }

    def get_sleep_data(self, d):
        self._call("get_sleep_data", d)
        k = self._seed(d)
        end = datetime.fromisoformat(d + "T06:30:00").astimezone()
        return {
            "dailySleepDTO": {
                "calendarDate": d,
                "sleepTimeSeconds": 25200 + 600 * k,
                "deepSleepSeconds": 5400,
                "lightSleepSeconds": 12600,
                "remSleepSeconds": 6000 + 600 * k,
                "awakeSleepSeconds": 1200,
                "sleepStartTimestampGMT": ms(end - timedelta(hours=8)),
                "sleepEndTimestampGMT": ms(end),
                "sleepScores": {"overall": {"value": 70 + 3 * k, "qualifierKey": "GOOD"}},
            },
            "restingHeartRate": 47,
            "avgOvernightHrv": 50.0,
        }

    def get_hrv_data(self, d):
        self._call("get_hrv_data", d)
        k = self._seed(d)
        return {
            "hrvSummary": {
                "calendarDate": d,
                "weeklyAvg": 52,
                "lastNightAvg": 45 + 2 * k,
                "status": "BALANCED",
                "baseline": {"balancedLow": 46, "balancedUpper": 60},
            }
        }

    def get_training_readiness(self, d):
        self._call("get_training_readiness", d)
        return [
            {"calendarDate": d, "score": 40, "level": "LOW", "inputContext": "UPDATE_REALTIME"},
            {"calendarDate": d, "score": 72, "level": "HIGH", "feedbackShort": "WELL_RECOVERED_2",
             "inputContext": "AFTER_WAKEUP_RESET"},
        ]  # fmt: skip

    def get_training_status(self, d):
        self._call("get_training_status", d)
        return {
            "mostRecentVO2Max": {"generic": {"vo2MaxPreciseValue": 51.7}, "cycling": None},
            "mostRecentTrainingStatus": {
                "latestTrainingStatusData": {
                    "111": {"primaryTrainingDevice": False, "trainingStatusFeedbackPhrase": "DETRAINING_1"},
                    "3456789": {
                        "calendarDate": d,
                        "primaryTrainingDevice": True,
                        "trainingStatusFeedbackPhrase": "PRODUCTIVE_3",
                        "acuteTrainingLoadDTO": {
                            "dailyTrainingLoadAcute": 420,
                            "dailyTrainingLoadChronic": 380,
                            "dailyAcuteChronicWorkloadRatio": 1.1,
                            "acwrStatus": "OPTIMAL",
                        },
                    },
                }
            },
        }

    def get_max_metrics(self, d):
        self._call("get_max_metrics", d)
        return [{"generic": {"calendarDate": d, "vo2MaxPreciseValue": 52.1}, "cycling": None}]

    def get_activities_by_date(self, start, end):
        self._call("get_activities_by_date", start, end)
        d = (self.today - timedelta(days=1)).isoformat()
        return [
            {
                "activityId": 1001,
                "activityName": "Morning <Run>",
                "startTimeLocal": f"{d} 07:00:00",
                "activityType": {"typeKey": "running"},
                "duration": 3130.0,
                "movingDuration": 3100.0,
                "distance": 10200.0,
                "elevationGain": 80.0,
                "averageHR": 148.0,
                "maxHR": 171.0,
                "calories": 700.0,
                "activityTrainingLoad": 120.4,
                "aerobicTrainingEffect": 3.4,
                "anaerobicTrainingEffect": 1.1,
                "vO2MaxValue": 52.0,
            }
        ]

    def get_activity(self, aid):
        self._call("get_activity", aid)
        return {"activityId": aid, "summaryDTO": {"distance": 10200.0}}

    def get_activity_splits(self, aid):
        self._call("get_activity_splits", aid)
        return {"lapDTOs": [{"distance": 1000.0}]}

    def get_activity_details(self, aid):
        self._call("get_activity_details", aid)
        return {"metricDescriptors": [], "activityDetailMetrics": [{"metrics": [1, 2]}] * 50}
