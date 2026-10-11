"""Bounded retry with exponential backoff and jitter.

Each class of error has its own short schedule of waits. Once a schedule is
used up, the error is re-raised. Nothing here ever retries in a tight loop:
the shortest wait is a minute.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

log = logging.getLogger(__name__)
T = TypeVar("T")

# Waits in seconds before each retry.
RATE_LIMIT_WAITS = [5 * 60, 20 * 60]  # 429: 3 attempts over ~25 min
LOGIN_ERROR_WAITS = [10 * 60]  # auth failure: retry once, 10 min later
CONNECTION_WAITS = [60, 5 * 60, 15 * 60]  # network / 5xx

# After a run gives up on 429s, make no requests for this long.
RATE_LIMIT_COOLDOWN_HOURS = 6


class MfaRequired(Exception):
    """Garmin asked for an MFA code while running unattended."""


def classify(exc: BaseException) -> str | None:
    if isinstance(exc, MfaRequired):
        return None
    if isinstance(exc, GarminConnectTooManyRequestsError):
        return "rate_limit"
    if isinstance(exc, GarminConnectAuthenticationError):
        return "auth"
    if isinstance(exc, GarminConnectConnectionError):
        # 404 / "no data" style errors are not worth retrying.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status is not None and 400 <= status < 500 and status != 408:
            return None
        return "connection"
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return "connection"
    return None


def jitter(seconds: float) -> float:
    return seconds * random.uniform(0.8, 1.2)


def with_backoff(
    fn: Callable[[], T],
    *,
    what: str,
    retry_auth: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    schedules = {
        "rate_limit": list(RATE_LIMIT_WAITS),
        "auth": list(LOGIN_ERROR_WAITS) if retry_auth else [],
        "connection": list(CONNECTION_WAITS),
    }
    while True:
        try:
            return fn()
        except Exception as exc:
            kind = classify(exc)
            waits = schedules.get(kind) if kind else None
            if not waits:
                raise
            wait = jitter(waits.pop(0))
            log.warning(
                "%s failed (%s: %s); retrying in %.0f min",
                what,
                kind,
                str(exc).splitlines()[0][:200],
                wait / 60,
            )
            sleep(wait)
