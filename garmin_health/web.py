"""Local dashboard and JSON API.

  /                    dashboard, Hebrew (add ?lang=en for English); installable
                       on an iPhone home screen (Share > Add to Home Screen)
  /api/trends?days=30  chart series (7, 30 or 90)
  /api/activities      activities of the last ?days=30
  /api/summary         health summary JSON
  /api/summary.txt     short daily text summary for an AI assistant
  /api/status          freshness / last run / whether a sync is running
  POST /api/sync       start a sync now (the dashboard's Sync button)
"""

from __future__ import annotations

import fcntl
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from . import auth, config, db, summary

# The Sync button can't start runs closer together than this, however often
# it is clicked. A run whose watch data hasn't changed costs only two
# requests, so a short gap is still gentle on Garmin.
MIN_SYNC_INTERVAL = timedelta(minutes=2)


def sync_running() -> bool:
    """True while a sync holds the lock (from launchd, the CLI or the button)."""
    path = config.lock_path()
    if not path.exists():
        return False
    with open(path) as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
    return False


def start_sync() -> None:
    project = Path(__file__).resolve().parent.parent
    subprocess.Popen(
        [sys.executable, "-m", "garmin_health", "sync"],
        cwd=project,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def create_app(db_path=None) -> Flask:
    app = Flask(__name__)

    def conn():
        return db.connect(db_path)

    @app.get("/")
    def index():
        lang = "en" if request.args.get("lang") == "en" else "he"
        return render_template("index.html", lang=lang)

    @app.get("/manifest.webmanifest")
    def manifest():
        icons = [
            {"src": f"/static/icon-{n}.png", "sizes": f"{n}x{n}", "type": "image/png"}
            for n in (192, 512)
        ]
        body = {
            "name": "Garmin Health",
            "short_name": "Health",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0a0b0d",
            "theme_color": "#0a0b0d",
            "icons": icons,
        }
        return Response(json.dumps(body), mimetype="application/manifest+json")

    @app.get("/api/activities")
    def api_activities():
        days = max(1, min(request.args.get("days", 30, type=int), 365))
        today = date.today()
        c = conn()
        try:
            acts = db.activities_range(
                c, (today - timedelta(days=days)).isoformat(), today.isoformat()
            )
        finally:
            c.close()
        return jsonify(acts[::-1])

    @app.get("/api/trends")
    def api_trends():
        days = request.args.get("days", 30, type=int)
        days = days if days in (7, 30, 90) else 30
        c = conn()
        try:
            return jsonify(summary.trends(c, days))
        finally:
            c.close()

    @app.get("/api/summary")
    def api_summary():
        c = conn()
        try:
            return jsonify(summary.build(c))
        finally:
            c.close()

    @app.get("/api/summary.txt")
    def api_summary_text():
        c = conn()
        try:
            return Response(summary.text(summary.build(c)) + "\n", mimetype="text/plain")
        finally:
            c.close()

    @app.get("/api/status")
    def api_status():
        c = conn()
        try:
            return jsonify({**summary.freshness(c), "running": sync_running()})
        finally:
            c.close()

    @app.post("/api/sync")
    def api_sync():
        # A custom header means another website can't trigger this from your browser.
        if request.headers.get("X-Garmin-Health") != "1":
            return jsonify(started=False, reason="forbidden"), 403
        if sync_running():
            return jsonify(started=False, reason="running")
        try:
            auth.check_brakes()
        except auth.LoginBlocked as e:
            return jsonify(started=False, reason="blocked", message=str(e))
        c = conn()
        try:
            run = db.last_run(c)
        finally:
            c.close()
        # A run that never reached Garmin (cooldown) doesn't count.
        if run and run.get("started_at") and run.get("status") != "skipped":
            wait = datetime.fromisoformat(run["started_at"]) + MIN_SYNC_INTERVAL
            now = datetime.now().astimezone()
            if wait > now:
                return jsonify(
                    started=False, reason="recent", retry_after=int((wait - now).total_seconds())
                )
        start_sync()
        return jsonify(started=True)

    @app.after_request
    def no_cache(resp):
        resp.headers["Cache-Control"] = "no-store"
        return resp

    return app


def serve(host: str | None = None, port: int | None = None) -> None:
    from waitress import serve as wserve  # optional, see README

    wserve(create_app(), host=host or config.WEB_HOST, port=port or config.WEB_PORT)
