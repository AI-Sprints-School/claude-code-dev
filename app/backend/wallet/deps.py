"""Зависимости обработчиков: соединение с базой, токен, кошелёк, лимит частоты."""
from __future__ import annotations

from typing import Iterator

from fastapi import Depends, Request
from sqlalchemy.engine import Connection

from wallet.auth import WalletRow, wallet_by_token
from wallet.db import engine
from wallet.errors import ApiError
from wallet.projection import OperationViewStore
from wallet.ratelimit import limiter


def db_conn() -> Iterator[Connection]:
    """Соединение в транзакции: коммит на выходе, откат при исключении."""
    with engine.begin() as conn:
        yield conn


def bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "UNAUTHORIZED")
    return token.strip()


def current_wallet(
    token: str = Depends(bearer_token), conn: Connection = Depends(db_conn)
) -> WalletRow:
    wallet = wallet_by_token(conn, token)
    if wallet is None:
        raise ApiError(401, "UNAUTHORIZED")
    if not limiter.allow(token):
        raise ApiError(429, "TOO_MANY_REQUESTS")
    return wallet


def operation_view(request: Request) -> OperationViewStore:
    return request.app.state.operation_view
