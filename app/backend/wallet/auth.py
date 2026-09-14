"""Авторизация: непрозрачный токен, 32 байта hex, Bearer, 7 суток (3.3).

Не JWT сознательно: разбирать в токене нечего, а непрозрачную строку
невозможно «прочитать неправильно». Повторный вход до истечения срока
возвращает ТОТ ЖЕ живой токен — второй вход не ломает уже настроенного
клиента.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

from wallet.config import settings

PBKDF2_ITERATIONS = 120_000


# --- пароли ------------------------------------------------------------
def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
    ).hex()
    return hmac.compare_digest(candidate, digest)


# --- сессии ------------------------------------------------------------
@dataclass(frozen=True)
class Session:
    login: str
    wallet_id: int
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class WalletRow:
    """Строка public.wallets в том виде, в котором её читают обработчики."""

    id: int
    owner_login: str
    display_name: str
    balance: object  # Decimal
    currency: str
    tariff: str
    fee_percent: object  # Decimal
    is_demo: bool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(moment: datetime) -> str:
    """«2026-09-15T10:00:00Z» — формат из раздела 3.2, без микросекунд."""
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def authenticate(conn: Connection, login: str, password: str) -> Session | None:
    row = conn.execute(
        text(
            """
            SELECT a.login, a.password_hash, a.token, a.token_expires, w.id AS wallet_id
              FROM auth.accounts a
              JOIN public.wallets w ON w.owner_login = a.login
             WHERE a.login = :login
            """
        ),
        {"login": login},
    ).mappings().first()

    if row is None or not verify_password(password, row["password_hash"]):
        return None

    now = utcnow()
    token = row["token"]
    expires = row["token_expires"]
    if not token or expires is None or expires <= now:
        token = secrets.token_hex(32)  # 32 байта → 64 hex-символа
        expires = now + timedelta(days=settings.token_ttl_days)
        conn.execute(
            text(
                "UPDATE auth.accounts SET token = :token, token_expires = :expires "
                "WHERE login = :login"
            ),
            {"token": token, "expires": expires, "login": login},
        )
    return Session(login=row["login"], wallet_id=row["wallet_id"], token=token, expires_at=expires)


def wallet_by_token(conn: Connection, token: str) -> WalletRow | None:
    row = conn.execute(
        text(
            """
            SELECT w.id, w.owner_login, w.display_name, w.balance, w.currency,
                   w.tariff, w.fee_percent, w.is_demo
              FROM auth.accounts a
              JOIN public.wallets w ON w.owner_login = a.login
             WHERE a.token = :token AND a.token_expires > now()
            """
        ),
        {"token": token},
    ).mappings().first()
    return WalletRow(**row) if row else None
