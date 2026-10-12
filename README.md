# Garmin health pipeline

Pulls your Garmin Connect data (Fenix 8 or any Garmin watch) twice a day into a
local SQLite database on your Mac mini, and serves a small dashboard plus a JSON
and text summary you can hand to an AI assistant. Everything stays on your Mac.

```
launchd 06:30 / 21:00 ──> bin/garmin-health sync ──> Garmin Connect (python-garminconnect)
                                   │
                                   ▼
             ~/Library/Application Support/garmin-health/health.db  (SQLite)
                                   │
launchd (always on) ──> bin/garmin-health serve ──> http://127.0.0.1:8765/
                                                      /api/summary  /api/summary.txt
```

**What it collects, per day:** sleep (stages, score, start and end), HRV (last
night, 7-day average, status, baseline), resting heart rate, Body Battery (high,
low, at wake, charged, drained), stress (average, max), steps and step goal,
training readiness (the morning score), training status with acute and chronic
load, and VO2 max. For every activity it stores the summary, the full activity
record, the splits and the detail time series (HR, pace, GPS; compressed). It
also records when the watch last synced and flags data as **stale** when that
sync is more than 12 hours old.

## Setup

You need macOS, Python 3.12 or newer (`brew install python@3.13`), and your
Garmin Connect login.

**Quick way, one command:** `./install.sh all` runs every step below in order.
It stops once to ask for your Garmin password and MFA code, then installs the
schedule, starts the first sync in the background and opens the dashboard.

```bash
git clone <this repo> ~/garmin-health && cd ~/garmin-health
./install.sh                      # creates .venv, installs pinned dependencies
```

### Step 1: log in and check yesterday's sleep

```bash
bin/garmin-health login
```

This asks for your Garmin email and password (the password is not echoed), and
for an MFA code if your account uses one. Then it prints yesterday's sleep:

```
Logged in as Your Name.
Login saved to the macOS Keychain (service 'garmin-health').
Session tokens cached in ~/Library/Application Support/garmin-health/tokens (owner-only).

Sleep for 2026-10-10
  total : 7h32m  score: 84
  deep  : 1h20m
  ...
```

If this works, the hard part is done. `bin/garmin-health hello` repeats the
check later using the stored login.

### Step 2: first sync (90-day backfill)

```bash
bin/garmin-health sync
```

The first run fetches today plus the previous 90 days, newest first. It pauses
1 second between requests to go easy on Garmin, so expect it to take 10 to 20
minutes. If it gets interrupted, the next run continues where it stopped.

### Step 3: schedule it and start the dashboard

```bash
./install.sh launchd
open http://127.0.0.1:8765/
```

This installs two LaunchAgents into `~/Library/LaunchAgents`:

| Job | What it does |
| --- | --- |
| `com.garmin-health.sync` | runs `sync` at **06:30** and **21:00**. If the Mac was asleep at that time, launchd runs it on wake. |
| `com.garmin-health.web` | keeps the dashboard running at `127.0.0.1:8765` |

To run a sync right away: `launchctl kickstart gui/$(id -u)/com.garmin-health.sync`.

**Keychain prompt:** the first time the scheduled job needs your password (only
when the cached session has expired), macOS may ask whether Python can use the
"garmin-health" Keychain item. Click **Always Allow**. A Homebrew Python upgrade
can make it ask again.

## Commands

```
bin/garmin-health login      # store login in Keychain, sign in (MFA ok), print yesterday's sleep
bin/garmin-health hello      # sign in with stored login, print yesterday's sleep
bin/garmin-health sync       # fetch new and missing days (what launchd runs)
    --since 2025-01-01       #   also backfill further back
    --refetch                #   re-download days already stored
    --force                  #   ignore a rate-limit cooldown
bin/garmin-health summary    # daily text summary  (--json for the JSON)
bin/garmin-health export     # write the daily JSON files to Google Drive now (offline)
bin/garmin-health status     # last watch sync, last run, safety state, file paths
bin/garmin-health serve      # run the dashboard in the foreground
bin/garmin-health reparse    # rebuild parsed columns from stored raw JSON (offline)
bin/garmin-health logout     # delete cached tokens (--forget also removes the Keychain login)
```

## Dashboard and API

- `/` is a phone-first dashboard, in Hebrew by default (`?lang=en` for
  English). The first screen shows only today: a recovery ring with one plain
  sentence, small rings for sleep, Body Battery and readiness, last night's
  sleep stages, HRV against your range, resting HR, stress, steps and recent
  activities. The side menu (top corner) opens 7/30/90-day trend charts, the
  full activity list, Sync now, and the language switch.
- **On an iPhone:** open the dashboard in Safari, tap Share > **Add to Home
  Screen**. It opens full screen like an app and refreshes when you return to it.
  The phone has to reach the Mac (see `GARMIN_HEALTH_HOST` below).
- **Sync now** (top of the page) pulls from Garmin Connect whatever the watch
  has already uploaded. It can't reach the watch itself: the watch has to sync
  first (phone app, Wi-Fi, or Garmin Express). To protect the account it starts
  at most one run per 10 minutes and respects the rate-limit and login brakes.
- `/api/summary`: the full health summary as JSON (today, recovery score and
  reasons, 30-day baselines, 7/30/90-day averages, recent activities, freshness).
- `/api/summary.txt`: the same as a short text brief for an AI assistant:

```
Garmin health summary for 2026-10-11.
Watch last synced 3h ago (2026-10-11T07:12+03:00).
Recovery: GOOD (78/100).
Sleep 7h32m, score 84 (deep 1h20m, REM 1h45m, awake 0h12m).
HRV 52 ms last night (status balanced, baseline 46-60; 7-day avg 50).
Resting HR 47 bpm (30-day avg 48.2). Body Battery 85 at wake (high 90, low 22).
Training readiness 72 (high).
Training status: productive; acute load 420 / chronic 380 (ratio 1.1, optimal).
...
```

For example: `curl -s localhost:8765/api/summary.txt | pbcopy`, then paste it
into your assistant. Or run `bin/garmin-health summary`.

**About the recovery score:** it is this tool's own heuristic, not a Garmin
metric. It averages whichever of these exist: sleep score, HRV against your
baseline, resting HR against your 30-day average, Body Battery at wake, and
Garmin's training readiness. 75 and up is "good", 50 to 74 is "fair", below 50
is "low". The reasons behind the score are listed under it.

The dashboard listens only on `127.0.0.1`. To view it from your phone on your
home Wi-Fi, set `GARMIN_HEALTH_HOST=0.0.0.0` (add an `EnvironmentVariables` dict
to the web plist). It has no password, so only do this on a network you trust.

## Daily JSON in Google Drive (for a cloud agent)

At the end of every sync, including a failed or skipped one, the pipeline
writes JSON files into a Google Drive folder named **Garmin Daily**:

| File | Contents |
| --- | --- |
| `YYYY-MM-DD.json` | the summary for that day; rewritten while the day's data still changes |
| `latest.json` | the newest summary, replaced on every run |

Each file has the same fields as `/api/summary`, plus `sync_status` (rate-limit
cooldown, or a login is needed) and `text` (the short brief). Check
`freshness.stale` and `sync_status` before trusting the numbers. The files
contain no email, password or tokens. Writing them never contacts Garmin.

Setup: install Google Drive for desktop (`brew install --cask google-drive`)
and sign in. The pipeline finds `My Drive/Garmin Daily` by itself. To write
somewhere else, set `GARMIN_HEALTH_EXPORT_DIR`. Run `bin/garmin-health export`
once to write every stored day right away. `status` shows the folder in use.

## How it avoids locking your Garmin account

- **Tokens first.** Normal runs use the cached session tokens, which the library
  refreshes on its own. The password is read from the Keychain only when those
  tokens are missing or rejected.
- **No unattended MFA.** If Garmin asks for an MFA code during a scheduled run,
  the job stops at once and won't try to log in again until you run
  `bin/garmin-health login`. You get a macOS notification, and the dashboard
  shows a red banner.
- **Bounded backoff.** The shortest wait is 1 minute; nothing retries in a tight loop.
  - Rate limit (429): retries after about 5 and then 20 minutes, then stops and
    sends no requests for 6 hours. Progress so far is kept.
  - Login error: retries once after 10 minutes. After 3 failed runs in a row,
    scheduled runs stop trying until you log in by hand.
  - Network or 5xx errors: retries after 1, 5 and 15 minutes.
- **One run at a time:** a lock file stops overlapping syncs.

`bin/garmin-health status` shows the current state of these brakes.

## Storage

| Path | Contents |
| --- | --- |
| `~/Library/Application Support/garmin-health/health.db` | SQLite: `daily`, `activities`, `raw` (every Garmin response as JSON), `runs`, `meta` |
| `~/Library/Application Support/garmin-health/tokens/garmin_tokens.json` | session tokens (directory 0700, file 0600) |
| `~/Library/Application Support/garmin-health/state.json` | cooldown and login-brake state |
| `~/Library/Logs/garmin-health/sync.log` | sync log (rotated, 5 × 2 MB) |
| Keychain, service `garmin-health` | your email and password |

Every write is an upsert, so running `sync` twice does no harm. A day is
re-downloaded on each run until it is **final**: it was fetched after the watch
had synced past the end of that day (plus 2 hours). Today is never final. Any
day missing from the backfill window, for example after the Mac was off for a
week, is filled in on the next run.

Settings can be overridden with environment variables: `GARMIN_HEALTH_HOME`,
`GARMIN_HEALTH_DB`, `GARMIN_HEALTH_BACKFILL_DAYS` (90), `GARMIN_HEALTH_STALE_HOURS`
(12), `GARMIN_HEALTH_REQUEST_DELAY` (1.0 s), `GARMIN_HEALTH_ACTIVITY_DETAILS`
(1; set 0 to skip the time series), `GARMIN_HEALTH_HOST`, `GARMIN_HEALTH_PORT`,
`GARMIN_HEALTH_EXPORT_DIR` (default: `Garmin Daily` in Google Drive).

## When Garmin breaks login

Garmin changes its login flow every few months, and python-garminconnect usually
ships a fix within days. Signs of a break: `sync.log` shows login failures,
`status` shows `needs_interactive_login`, or `login` itself fails.

1. Check the library's releases and issues:
   <https://github.com/cyberjunky/python-garminconnect/releases> and
   <https://github.com/cyberjunky/python-garminconnect/issues>. Read the README's
   "Authentication" section for any new instructions.
2. Upgrade inside the virtualenv:
   ```bash
   .venv/bin/pip install --upgrade garminconnect curl_cffi
   .venv/bin/pip show garminconnect | grep Version
   ```
3. Pin the new version in `requirements.txt` (`garminconnect==X.Y.Z`) so a
   reinstall gets the same version.
4. Log in fresh and check: `bin/garmin-health login`. This also clears the
   brakes in `state.json`.
5. Run the tests: `.venv/bin/pip install pytest && .venv/bin/python -m pytest -q`.
6. If the release notes say the token format changed, `bin/garmin-health logout`
   before step 4.

If a library update changes the **data** format instead (a column goes empty in
the dashboard), fix the field name in `garmin_health/extract.py` and run
`bin/garmin-health reparse`. It rebuilds every row from the stored raw responses
without contacting Garmin.

To go back to an older version: `.venv/bin/pip install garminconnect==<old version>`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Notification "Garmin login needed" | `bin/garmin-health login` |
| Yellow "data is stale" banner | The watch hasn't synced to Garmin Connect in 12 hours or more. Open the Garmin Connect app on your phone. |
| `status` shows `cooldown_until` | Garmin rate-limited you. Wait, or `sync --force` once. |
| Dashboard doesn't load | `tail ~/Library/Logs/garmin-health/web.log`; `launchctl print gui/$(id -u)/com.garmin-health.web` |
| Scheduled sync didn't run | `tail ~/Library/Logs/garmin-health/sync.log launchd-sync.log` |

## Uninstall

```bash
./uninstall.sh            # stops and removes both launchd jobs, keeps your data
./uninstall.sh --purge    # also deletes the database, tokens, logs, Keychain items and .venv
```

After `--purge`, delete the project folder. Removing the token file does not
revoke the session at Garmin. To do that, go to Garmin Connect > Account >
Security and sign out of all devices, or change your password.

## Development

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

The tests use a fake Garmin client and an in-memory keyring. They never contact
Garmin. Chart.js 4.4.1 (MIT) is bundled in `garmin_health/static/`, so the
dashboard works offline.
