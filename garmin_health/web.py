"""Local dashboard and JSON API.

  /                    dashboard (add ?lang=he for Hebrew)
  /api/trends?days=30  chart series (7, 30 or 90)
  /api/summary         health summary JSON
  /api/summary.txt     short daily text summary for an AI assistant
  /api/status          freshness / last run / whether a sync is running
  POST /api/sync       start a sync now (the dashboard's Sync button)
"""

from __future__ import annotations

import fcntl
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from . import auth, config, db, summary

# The Sync button can't start runs closer together than this, however often
# it is clicked, so it can't get the account rate-limited.
MIN_SYNC_INTERVAL = timedelta(minutes=10)


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
        lang = "he" if request.args.get("lang") == "he" else "en"
        return render_template("index.html", lang=lang)

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
        if run and run.get("started_at"):
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
