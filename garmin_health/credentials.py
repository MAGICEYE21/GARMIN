"""Garmin login stored in the macOS Keychain (via the `keyring` package).

Two generic-password items are stored under the service "garmin-health":
  account "__email__"   -> your Garmin email
  account <your email>  -> your Garmin password

You can inspect or delete them in Keychain Access.app, or with
  security find-generic-password -s garmin-health
"""

from __future__ import annotations

import keyring
import keyring.errors

from .config import KEYCHAIN_EMAIL_ACCOUNT, KEYCHAIN_SERVICE


class CredentialsMissing(RuntimeError):
    pass


def save(email: str, password: str) -> None:
    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_EMAIL_ACCOUNT, email)
    keyring.set_password(KEYCHAIN_SERVICE, email, password)


def load() -> tuple[str, str]:
    try:
        email = keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_EMAIL_ACCOUNT)
        password = keyring.get_password(KEYCHAIN_SERVICE, email) if email else None
    except keyring.errors.KeyringError as e:
        raise CredentialsMissing(f"Keychain not available: {e}") from e
    if not email or not password:
        raise CredentialsMissing(
            "No Garmin login in the Keychain. Run: bin/garmin-health login"
        )
    return email, password


def delete() -> None:
    email = keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_EMAIL_ACCOUNT)
    for account in (email, KEYCHAIN_EMAIL_ACCOUNT):
        if not account:
            continue
        try:
            keyring.delete_password(KEYCHAIN_SERVICE, account)
        except keyring.errors.PasswordDeleteError:
            pass
