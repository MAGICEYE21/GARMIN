"""Local dashboard and JSON API.

  /                    dashboard (add ?lang=he for Hebrew)
  /api/trends?days=30  chart series (7, 30 or 90)
  /api/summary         health summary JSON
  /api/summary.txt     short daily text summary for an AI assistant
  /api/status          freshness / last run
"""

from __future__ import annotations

from flask import Flask, Response, jsonify, render_template, request

from . import config, db, summary


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
            return jsonify(summary.freshness(c))
        finally:
            c.close()

    @app.after_request
    def no_cache(resp):
        resp.headers["Cache-Control"] = "no-store"
        return resp

    return app


def serve(host: str | None = None, port: int | None = None) -> None:
    from waitress import serve as wserve  # optional, see README

    wserve(create_app(), host=host or config.WEB_HOST, port=port or config.WEB_PORT)
