from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from garmin_health import auth, config, credentials, db, extract, retry, state, summary, sync

from .conftest import FakeGarmin

TODAY = date(2026, 10, 11)


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.db")
    yield c
    c.close()


def run_sync(conn, api, **kw):
    sleeps = []
    result = sync.sync(
        conn, connect=lambda: api, today=TODAY, sleep=sleeps.append, request_delay=0, **kw
    )
    return result, sleeps


# ---- sync / storage -------------------------------------------------------


def test_first_run_backfills_90_days(conn):
    api = FakeGarmin(TODAY)
    result, _ = run_sync(conn, api)
    assert result["days"] == config.BACKFILL_DAYS + 1
    n = conn.execute("SELECT COUNT(*) FROM daily").fetchone()[0]
    assert n == 91
    first = conn.execute("SELECT MIN(date) FROM daily").fetchone()[0]
    assert first == (TODAY - timedelta(days=90)).isoformat()
    # newest first, so the dashboard is useful even if the run is cut short
    sleep_days = [c[1] for c in api.calls if c[0] == "get_sleep_data"]
    assert sleep_days[0] == TODAY.isoformat()


@pytest.mark.parametrize(
    "synced_at, refetched",
    [
        # Watch synced this morning: yesterday is complete, only today is refetched.
        (datetime(2026, 10, 11, 7, 0), ["2026-10-11"]),
        # Last sync just after midnight: yesterday may still change.
        (datetime(2026, 10, 11, 0, 30), ["2026-10-11", "2026-10-10"]),
    ],
)
def test_second_run_only_refetches_non_final_days(conn, synced_at, refetched):
    last_sync = synced_at.astimezone()
    run_sync(conn, FakeGarmin(TODAY, last_sync))
    api = FakeGarmin(TODAY, last_sync)
    run_sync(conn, api)
    assert [c[1] for c in api.calls if c[0] == "get_sleep_data"] == refetched
    assert conn.execute("SELECT COUNT(*) FROM daily").fetchone()[0] == 91


def test_gap_is_backfilled(conn):
    last_sync = datetime(2026, 10, 11, 7, 0).astimezone()
    run_sync(conn, FakeGarmin(TODAY, last_sync))
    conn.execute("DELETE FROM daily WHERE date IN ('2026-09-01', '2026-09-02')")
    conn.commit()
    api = FakeGarmin(TODAY, last_sync)
    run_sync(conn, api)
    fetched = {c[1] for c in api.calls if c[0] == "get_sleep_data"}
    assert {"2026-09-01", "2026-09-02"} <= fetched


def test_idempotent_rows_and_activities(conn):
    run_sync(conn, FakeGarmin(TODAY))
    before = [dict(r) for r in conn.execute("SELECT * FROM daily ORDER BY date")]
    api = FakeGarmin(TODAY)
    run_sync(conn, api, refetch=True)
    after = [dict(r) for r in conn.execute("SELECT * FROM daily ORDER BY date")]
    strip = lambda rows: [{k: v for k, v in r.items() if k != "fetched_at"} for r in rows]  # noqa: E731
    assert strip(before) == strip(after)
    assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 1
    # details are fetched once only
    assert api.n("get_activity_details") == 0
    assert db.load_activity_details(conn, 1001)["activityDetailMetrics"]


def test_parsed_values(conn):
    run_sync(conn, FakeGarmin(TODAY))
    row = dict(conn.execute("SELECT * FROM daily WHERE date='2026-10-10'").fetchone())
    assert row["sleep_score"] is not None and row["deep_seconds"] == 5400
    assert row["readiness_score"] == 72  # morning entry, not the realtime one
    assert row["readiness_feedback"] == "WELL_RECOVERED"
    assert row["training_status"] == "PRODUCTIVE"  # primary device, suffix stripped
    assert row["acute_load"] == 420 and row["acwr_status"] == "OPTIMAL"
    assert row["vo2max_running"] == 52.1  # dated max-metrics wins
    assert row["hrv_baseline_low"] == 46
    assert row["bb_wake"] is not None and row["steps"] >= 8000
    assert db.get_meta(conn, "last_device") == "fenix 8"


def test_missing_data_endpoints_do_not_fail(conn):
    api = FakeGarmin(TODAY)
    err = GarminConnectConnectionError("404 no data")
    err.response = type("R", (), {"status_code": 404})()
    api.fail["get_hrv_data"] = [err]
    _, sleeps = run_sync(conn, api)
    row = conn.execute("SELECT hrv_last_night FROM daily WHERE date=?", (TODAY.isoformat(),))
    assert row.fetchone()[0] == 50.0  # falls back to sleep's avgOvernightHrv
    assert sleeps == []


def test_429_backs_off_then_continues(conn):
    api = FakeGarmin(TODAY)
    api.fail["get_sleep_data"] = [GarminConnectTooManyRequestsError("429")]
    _, sleeps = run_sync(conn, api)
    assert len(sleeps) == 1 and sleeps[0] >= 4 * 60  # minutes, never a tight loop
    assert conn.execute("SELECT COUNT(*) FROM daily").fetchone()[0] == 91


def test_persistent_429_aborts_and_keeps_progress(conn):
    api = FakeGarmin(TODAY)
    original = api.get_sleep_data

    def flaky(d):
        if d < "2026-10-05":
            api.calls.append(("get_sleep_data", d))
            raise GarminConnectTooManyRequestsError("429")
        return original(d)

    api.get_sleep_data = flaky
    with pytest.raises(GarminConnectTooManyRequestsError):
        run_sync(conn, api)
    assert conn.execute("SELECT COUNT(*) FROM daily").fetchone()[0] == 7


def test_finality():
    now = datetime(2026, 10, 11, 21, 0).astimezone()
    sync_ = datetime(2026, 10, 11, 6, 0).astimezone()
    assert sync.is_final(date(2026, 10, 9), sync_, now)
    assert sync.is_final(date(2026, 10, 10), sync_, now)
    assert not sync.is_final(date(2026, 10, 11), sync_, now)
    early = datetime(2026, 10, 11, 1, 0).astimezone()
    assert not sync.is_final(date(2026, 10, 10), early, now)
    assert not sync.is_final(date(2026, 10, 10), None, now)
    assert sync.is_final(date(2026, 10, 8), None, now)


def test_reparse_rebuilds_from_raw(conn):
    run_sync(conn, FakeGarmin(TODAY))
    conn.execute("UPDATE daily SET sleep_score=NULL, training_status=NULL")
    conn.commit()
    assert sync.reparse(conn) == 91
    row = conn.execute("SELECT sleep_score, training_status FROM daily LIMIT 1").fetchone()
    assert row[0] is not None and row[1] == "PRODUCTIVE"


# ---- login / safety brakes ------------------------------------------------


class FakeLoginGarmin:
    """Stands in for garminconnect.Garmin inside auth.connect."""

    behaviour: list = []
    instances: list = []

    def __init__(self, email=None, password=None, prompt_mfa=None, **kw):
        self.email, self.password, self.prompt_mfa = email, password, prompt_mfa
        FakeLoginGarmin.instances.append(self)

    def login(self, tokenstore=None):
        if self.email is None:
            raise GarminConnectAuthenticationError("Username and password are required")
        action = FakeLoginGarmin.behaviour.pop(0) if FakeLoginGarmin.behaviour else "ok"
        if action == "mfa":
            code = self.prompt_mfa()
            assert code == "123456"
        elif isinstance(action, Exception):
            raise action
        return None, None


@pytest.fixture
def fake_login(monkeypatch):
    FakeLoginGarmin.behaviour = []
    FakeLoginGarmin.instances = []
    monkeypatch.setattr(auth, "Garmin", FakeLoginGarmin)
    credentials.save("me@example.com", "pw")
    return FakeLoginGarmin


def test_credentials_roundtrip_in_keychain(isolated):
    credentials.save("a@b.c", "secret")
    assert credentials.load() == ("a@b.c", "secret")
    credentials.delete()
    with pytest.raises(credentials.CredentialsMissing):
        credentials.load()


def test_login_uses_keychain(fake_login):
    api = auth.connect(sleep=lambda s: None)
    assert api.email == "me@example.com"
    assert oct(config.token_dir().stat().st_mode & 0o777) == "0o700"


def test_unattended_mfa_stops_immediately(fake_login):
    fake_login.behaviour = ["mfa"]
    slept = []
    with pytest.raises(retry.MfaRequired):
        auth.connect(interactive=False, sleep=slept.append)
    assert slept == []
    assert len([i for i in fake_login.instances if i.email]) == 1
    assert state.load()["needs_interactive_login"] is True
    # The next unattended run doesn't even try.
    with pytest.raises(auth.LoginBlocked):
        auth.connect(interactive=False)


def test_interactive_mfa_prompts(fake_login):
    fake_login.behaviour = ["mfa"]
    auth.connect(interactive=True, prompt_mfa=lambda: "123456")


def test_login_429_backs_off_and_sets_cooldown(fake_login):
    fake_login.behaviour = [GarminConnectTooManyRequestsError("429")] * 5
    slept = []
    with pytest.raises(GarminConnectTooManyRequestsError):
        auth.connect(sleep=slept.append)
    assert len(slept) == len(retry.RATE_LIMIT_WAITS)
    assert min(slept) >= 4 * 60
    assert state.cooldown_until() > datetime.now(timezone.utc)
    with pytest.raises(auth.LoginBlocked, match="cooldown"):
        auth.connect()


def test_auth_failures_trip_circuit_breaker(fake_login):
    for i in range(auth.MAX_FAILED_LOGIN_RUNS):
        fake_login.behaviour = [GarminConnectAuthenticationError("401")] * 2
        slept = []
        with pytest.raises(GarminConnectAuthenticationError):
            auth.connect(sleep=slept.append)
        assert len(slept) == 1 and slept[0] >= 8 * 60
    with pytest.raises(auth.LoginBlocked, match="in a row"):
        auth.connect()


def test_success_resets_failure_count(fake_login):
    fake_login.behaviour = [GarminConnectAuthenticationError("401")] * 2
    with pytest.raises(GarminConnectAuthenticationError):
        auth.connect(sleep=lambda s: None)
    assert state.load()["consecutive_login_failures"] == 1
    auth.connect(sleep=lambda s: None)
    assert "consecutive_login_failures" not in state.load()


def test_run_exit_codes(fake_login, monkeypatch):
    fake_login.behaviour = ["mfa"]
    assert sync.run() == 3
    conn = db.connect()
    assert db.last_run(conn)["status"] == "login_needed"
    conn.close()
    assert sync.run() == 3  # blocked without contacting Garmin
    assert len([i for i in fake_login.instances if i.email]) == 1


# ---- summary / web --------------------------------------------------------


def test_summary_and_text(conn):
    last_sync = datetime.now().astimezone() - timedelta(hours=2)
    run_sync(conn, FakeGarmin(TODAY, last_sync))
    s = summary.build(conn, today=TODAY)
    assert s["recovery"]["score"] is not None
    assert s["recovery"]["label"] in ("good", "fair", "low")
    assert s["freshness"]["stale"] is False
    assert s["activities_7d"][0]["training_load"] == pytest.approx(120.4)
    t = summary.text(s)
    assert "Garmin health summary for 2026-10-11" in t
    assert "HRV" in t and "Sleep" in t and "running 10.2 km" in t
    assert "stale" not in t


def test_stale_flag(conn):
    run_sync(conn, FakeGarmin(TODAY, datetime.now(timezone.utc) - timedelta(hours=13)))
    s = summary.build(conn, today=TODAY)
    assert s["freshness"]["stale"] is True
    assert "stale" in summary.text(s)


def test_trends_shape(conn):
    run_sync(conn, FakeGarmin(TODAY))
    for n in (7, 30, 90):
        t = summary.trends(conn, n, today=TODAY)
        assert len(t["dates"]) == n
        assert len(t["sleep"]["deep"]) == n and t["sleep"]["deep"][-1] == 1.5
        assert t["training_load"]["daily"][-2] == 120


def test_web_routes(tmp_path):
    from garmin_health.web import create_app

    path = tmp_path / "w.db"
    c = db.connect(path)
    run_sync(c, FakeGarmin(date.today()))
    c.close()
    client = create_app(path).test_client()
    assert client.get("/").status_code == 200
    assert "עברית" in client.get("/").get_data(as_text=True)
    assert 'dir="rtl"' in client.get("/?lang=he").get_data(as_text=True)
    assert len(client.get("/api/trends?days=7").get_json()["dates"]) == 7
    assert len(client.get("/api/trends?days=999").get_json()["dates"]) == 30
    assert "recovery" in client.get("/api/summary").get_json()
    txt = client.get("/api/summary.txt")
    assert txt.mimetype == "text/plain" and "Recovery" in txt.get_data(as_text=True)
    assert "stale" in client.get("/api/status").get_json()


def test_extract_tolerates_garbage():
    assert extract.parse_day({}) is not None
    assert extract.parse_day({"sleep": [], "hrv": None, "readiness": {}, "summary": "x"})
    assert extract.parse_summary({"averageStressLevel": -1})["stress_avg"] is None
    assert extract.parse_last_sync(None, {"lastSyncTimestampGMT": "2026-10-11T05:00:00.0"})


def test_login_email_validation():
    from garmin_health.cli import _valid_email

    assert _valid_email("someone@example.com")
    assert not _valid_email("someone@example.com\x1b[3~extra")
    assert not _valid_email("someone@example.com extra")
    assert not _valid_email("not-an-email")


# ---- Google Drive export --------------------------------------------------


def test_export_writes_day_files_and_latest(conn, tmp_path, monkeypatch, isolated):
    import json

    from garmin_health import export

    out = tmp_path / "Garmin Daily"
    monkeypatch.setenv("GARMIN_HEALTH_EXPORT_DIR", str(out))
    isolated.set_password("garmin-health", "__email__", "me@example.com")
    isolated.set_password("garmin-health", "me@example.com", "hunter2-secret")
    state.update(needs_interactive_login_reason="Login failed for me@example.com")
    run_sync(conn, FakeGarmin(TODAY))

    assert export.write(conn, today=TODAY) == out
    files = sorted(p.name for p in out.iterdir())
    assert "latest.json" in files and f"{TODAY}.json" in files
    assert len(files) == 92  # 91 stored days + latest.json
    latest = json.loads((out / "latest.json").read_text())
    assert latest["date"] == TODAY.isoformat()
    assert latest == json.loads((out / f"{TODAY}.json").read_text())
    assert "Garmin health summary" in latest["text"]
    assert "sync_status" in latest
    past = json.loads((out / f"{TODAY - timedelta(days=30)}.json").read_text())
    assert past["date"] == (TODAY - timedelta(days=30)).isoformat()
    every = "".join(p.read_text() for p in out.iterdir())
    assert "hunter2-secret" not in every and "me@example.com" not in every

    # Up-to-date day files are left alone on the next run.
    stamp = (out / f"{TODAY - timedelta(days=30)}.json").stat().st_mtime_ns
    export.write(conn, today=TODAY)
    assert (out / f"{TODAY - timedelta(days=30)}.json").stat().st_mtime_ns == stamp


def test_export_never_fails_sync(conn, monkeypatch):
    from garmin_health import export

    monkeypatch.setattr(export, "write", lambda conn: 1 / 0)
    export.run(conn)  # logs, doesn't raise


def test_run_exports_even_when_login_blocked(fake_login, tmp_path, monkeypatch):
    out = tmp_path / "drive"
    monkeypatch.setenv("GARMIN_HEALTH_EXPORT_DIR", str(out))
    fake_login.behaviour = ["mfa"]
    assert sync.run() == 3
    assert (out / "latest.json").exists()


def test_sync_button_guards(tmp_path, monkeypatch):
    from garmin_health import web

    started = []
    monkeypatch.setattr(web, "start_sync", lambda: started.append(1))
    path = tmp_path / "w.db"
    db.connect(path).close()
    client = web.create_app(path).test_client()
    hdr = {"X-Garmin-Health": "1"}

    assert client.post("/api/sync").status_code == 403  # no header: cross-site
    assert client.post("/api/sync", headers=hdr).get_json() == {"started": True}
    assert client.get("/api/status").get_json()["running"] is False

    # A run started a minute ago: the button waits instead of syncing again.
    c = db.connect(path)
    db.start_run(c)
    c.close()
    r = client.post("/api/sync", headers=hdr).get_json()
    assert r["started"] is False and r["reason"] == "recent" and r["retry_after"] > 0

    # Rate-limit cooldown: nothing is started.
    monkeypatch.setattr(web, "MIN_SYNC_INTERVAL", timedelta(0))
    auth.set_rate_limit_cooldown()
    assert client.post("/api/sync", headers=hdr).get_json()["reason"] == "blocked"
    assert started == [1]
