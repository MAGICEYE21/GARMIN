"""Log in to Garmin Connect, preferring cached tokens over the password.

Normal runs never touch the password: python-garminconnect loads the cached
token file and refreshes it on its own. The Keychain password is only read
when the tokens are missing or rejected.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)

from . import config, credentials, state
from .retry import RATE_LIMIT_COOLDOWN_HOURS, MfaRequired, with_backoff

log = logging.getLogger(__name__)

# Unattended runs stop attempting password logins after this many failed runs
# in a row; `garmin-health login` resets it.
MAX_FAILED_LOGIN_RUNS = 3


class LoginBlocked(RuntimeError):
    """A safety brake is on; we deliberately did not contact Garmin."""


def _secure_tokens(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    for f in path.iterdir():
        if f.is_file():
            os.chmod(f, 0o600)


def check_brakes(now: datetime | None = None) -> None:
    now = now or datetime.now().astimezone()
    s = state.load()
    if s.get("needs_interactive_login"):
        raise LoginBlocked(
            f"{s.get('needs_interactive_login_reason', 'Login needed')}. "
            "Run `bin/garmin-health login` in Terminal."
        )
    until = state.cooldown_until()
    if until and until > now:
        raise LoginBlocked(
            f"Rate-limit cooldown until {until:%Y-%m-%d %H:%M}; "
            "use --force to ignore."
        )


def _resume_from_tokens(tokenstore: str) -> Garmin | None:
    """Try the cached tokens alone. Returns None if they can't be used."""
    if not (Path(tokenstore) / "garmin_tokens.json").exists():
        return None
    api = Garmin()
    try:
        api.login(tokenstore)
        return api
    except GarminConnectAuthenticationError as e:
        log.info("Cached tokens unusable (%s); falling back to password", e)
        return None


def connect(
    *,
    interactive: bool = False,
    prompt_mfa: Callable[[], str] | None = None,
    force: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> Garmin:
    """Return a logged-in client, or raise.

    interactive=False (launchd): an MFA request stops immediately and sets
    `needs_interactive_login`, so we never spam MFA codes or lock the account.
    """
    config.ensure_dirs()
    tokenstore = str(config.token_dir())
    if not force and not interactive:
        check_brakes()

    def attempt() -> Garmin:
        api = _resume_from_tokens(tokenstore)
        if api is not None:
            return api
        email, password = credentials.load()
        mfa_asked = False

        def on_mfa() -> str:
            nonlocal mfa_asked
            mfa_asked = True
            if prompt_mfa is None:
                raise MfaRequired("Garmin asked for an MFA code")
            return prompt_mfa()

        api = Garmin(email, password, prompt_mfa=on_mfa)
        try:
            api.login(tokenstore)
        except Exception as e:
            # The library may wrap our exception; the flag is authoritative.
            if mfa_asked and prompt_mfa is None:
                raise MfaRequired("Garmin asked for an MFA code") from e
            raise
        return api

    try:
        api = with_backoff(attempt, what="Garmin login", sleep=sleep)
    except MfaRequired:
        state.update(
            needs_interactive_login=True,
            needs_interactive_login_reason="Garmin asked for an MFA code",
        )
        raise
    except credentials.CredentialsMissing:
        raise
    except Exception as e:
        failures = state.load().get("consecutive_login_failures", 0) + 1
        changes: dict = {"consecutive_login_failures": failures}
        if failures >= MAX_FAILED_LOGIN_RUNS and not interactive:
            changes["needs_interactive_login"] = True
            changes["needs_interactive_login_reason"] = (
                f"Login failed on {failures} runs in a row, last: {str(e)[:120]}"
            )
        if isinstance(e, GarminConnectTooManyRequestsError):
            set_rate_limit_cooldown()
        state.update(**changes)
        raise

    state.update(
        consecutive_login_failures=None,
        needs_interactive_login=None,
        needs_interactive_login_reason=None,
    )
    _secure_tokens(Path(tokenstore))
    return api


def set_rate_limit_cooldown() -> None:
    until = datetime.now().astimezone() + timedelta(hours=RATE_LIMIT_COOLDOWN_HOURS)
    state.update(cooldown_until=until.isoformat())
    log.warning("Rate limited: no Garmin requests until %s", f"{until:%H:%M}")


def clear_tokens() -> None:
    p = config.token_dir() / "garmin_tokens.json"
    if p.exists():
        p.unlink()
