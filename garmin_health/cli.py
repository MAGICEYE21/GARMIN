"""Command line entry point: `bin/garmin-health <command>`."""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import logging.handlers
import sys
from datetime import date, timedelta

import keyring

from . import auth, config, credentials, db, state, summary, sync
from .config import KEYCHAIN_EMAIL_ACCOUNT, KEYCHAIN_SERVICE

log = logging.getLogger("garmin_health")


def _ask_mfa() -> str:
    return input("Garmin MFA code (check your email/SMS/app): ").strip()


def _fmt_dur(seconds) -> str:
    if not seconds:
        return "-"
    m = int(seconds) // 60
    return f"{m // 60}h{m % 60:02d}m"


def print_sleep(api, day: str) -> None:
    data = api.get_sleep_data(day) or {}
    dto = data.get("dailySleepDTO") or {}
    if not dto.get("sleepTimeSeconds"):
        print(f"No sleep recorded for {day}.")
        return
    score = ((dto.get("sleepScores") or {}).get("overall") or {}).get("value")
    print(f"Sleep for {day}")
    print(f"  total : {_fmt_dur(dto.get('sleepTimeSeconds'))}  score: {score}")
    print(f"  deep  : {_fmt_dur(dto.get('deepSleepSeconds'))}")
    print(f"  light : {_fmt_dur(dto.get('lightSleepSeconds'))}")
    print(f"  REM   : {_fmt_dur(dto.get('remSleepSeconds'))}")
    print(f"  awake : {_fmt_dur(dto.get('awakeSleepSeconds'))}")


def cmd_login(args) -> int:
    """Interactive: ask for the login, sign in (MFA if needed), store in Keychain."""
    config.ensure_dirs()
    saved = keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_EMAIL_ACCOUNT)
    prompt = f"Garmin email [{saved}]: " if saved else "Garmin email: "
    email = input(prompt).strip() or saved
    if not email:
        print("An email is required.", file=sys.stderr)
        return 2
    password = getpass.getpass("Garmin password (not echoed): ")

    from garminconnect import Garmin

    # Force a real password login so a changed password is picked up.
    auth.clear_tokens()
    api = Garmin(email, password, prompt_mfa=_ask_mfa)
    try:
        api.login(str(config.token_dir()))
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        print("Nothing was saved. If Garmin changed its login, see the README.", file=sys.stderr)
        return 1
    credentials.save(email, password)
    state.update(
        consecutive_login_failures=None,
        needs_interactive_login=None,
        needs_interactive_login_reason=None,
        cooldown_until=None,
    )
    auth._secure_tokens(config.token_dir())
    print(f"Logged in as {api.get_full_name() or email}.")
    print(f"Login saved to the macOS Keychain (service '{KEYCHAIN_SERVICE}').")
    print(f"Session tokens cached in {config.token_dir()} (owner-only).\n")
    print_sleep(api, (date.today() - timedelta(days=1)).isoformat())
    return 0


def cmd_hello(args) -> int:
    """Step 1 check: log in with the stored login and print yesterday's sleep."""
    api = auth.connect(interactive=True, prompt_mfa=_ask_mfa, force=True)
    print_sleep(api, args.date or (date.today() - timedelta(days=1)).isoformat())
    return 0


def cmd_logout(args) -> int:
    auth.clear_tokens()
    if args.forget:
        credentials.delete()
        print("Removed cached tokens and the Keychain login.")
    else:
        print("Removed cached tokens (Keychain login kept; use --forget to remove).")
    return 0


def cmd_sync(args) -> int:
    return sync.run(
        force=args.force,
        since=date.fromisoformat(args.since) if args.since else None,
        refetch=args.refetch,
    )


def cmd_serve(args) -> int:
    from .web import serve

    print(f"Dashboard: http://{args.host}:{args.port}/")
    serve(args.host, args.port)
    return 0


def cmd_summary(args) -> int:
    conn = db.connect()
    try:
        s = summary.build(conn)
    finally:
        conn.close()
    print(json.dumps(s, indent=2, ensure_ascii=False) if args.json else summary.text(s))
    return 0


def cmd_status(args) -> int:
    conn = db.connect()
    try:
        info = summary.freshness(conn)
        info["days_stored"] = conn.execute("SELECT COUNT(*) FROM daily").fetchone()[0]
        info["activities_stored"] = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    finally:
        conn.close()
    info["safety_state"] = state.load()
    info["paths"] = {
        "database": str(config.db_path()),
        "tokens": str(config.token_dir()),
        "logs": str(config.log_dir()),
    }
    print(json.dumps(info, indent=2))
    return 0


def cmd_reparse(args) -> int:
    conn = db.connect()
    try:
        n = sync.reparse(conn)
    finally:
        conn.close()
    print(f"Re-parsed {n} day(s) from stored raw data.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="garmin-health")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", help="store Garmin login in Keychain and sign in")

    h = sub.add_parser("hello", help="sign in and print yesterday's sleep")
    h.add_argument("--date", help="YYYY-MM-DD (default: yesterday)")

    lo = sub.add_parser("logout", help="delete cached session tokens")
    lo.add_argument("--forget", action="store_true", help="also delete Keychain login")

    sy = sub.add_parser("sync", help="fetch new and missing days (what launchd runs)")
    sy.add_argument("--force", action="store_true", help="ignore rate-limit cooldown")
    sy.add_argument("--since", help="also backfill from this date, YYYY-MM-DD")
    sy.add_argument("--refetch", action="store_true", help="re-download days already stored")

    se = sub.add_parser("serve", help="run the dashboard")
    se.add_argument("--host", default=config.WEB_HOST)
    se.add_argument("--port", type=int, default=config.WEB_PORT)

    su = sub.add_parser("summary", help="print the daily health summary")
    su.add_argument("--json", action="store_true")

    sub.add_parser("status", help="show last sync, freshness and safety state")
    sub.add_parser("reparse", help="rebuild parsed columns from stored raw JSON")
    return p


COMMANDS = {
    "login": cmd_login,
    "hello": cmd_hello,
    "logout": cmd_logout,
    "sync": cmd_sync,
    "serve": cmd_serve,
    "summary": cmd_summary,
    "status": cmd_status,
    "reparse": cmd_reparse,
}


def _setup_logging(args) -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Under launchd, sync logs go to the rotating file only (no duplicates).
    if args.cmd != "sync" or sys.stderr.isatty():
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)
    if args.cmd == "sync":
        config.ensure_dirs()
        fh = logging.handlers.RotatingFileHandler(
            config.log_dir() / "sync.log", maxBytes=2_000_000, backupCount=5
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    if not args.verbose:
        for noisy in ("garminconnect", "urllib3", "werkzeug", "waitress"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _setup_logging(args)
    try:
        return COMMANDS[args.cmd](args)
    except (credentials.CredentialsMissing, auth.LoginBlocked) as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        return 130
