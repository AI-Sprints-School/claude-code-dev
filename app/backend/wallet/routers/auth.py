"""POST /api/auth/login — вход по выданному логину и паролю (3.2)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.engine import Connection

from wallet.auth import authenticate, iso_utc
from wallet.deps import db_conn
from wallet.errors import ApiError
from wallet.json_response import JsonResponse
from wallet.routers.common import json_body

router = APIRouter()


@router.post("/api/auth/login")
async def login(request: Request, conn: Connection = Depends(db_conn)) -> JsonResponse:
    body = await json_body(request)
    login_value = body.get("login")
    password = body.get("password")

    if not isinstance(login_value, str) or not isinstance(password, str):
        raise ApiError(401, "INVALID_CREDENTIALS")

    session = authenticate(conn, login_value, password)
    if session is None:
        raise ApiError(401, "INVALID_CREDENTIALS")

    return JsonResponse(
        {
            "token": session.token,
            "wallet_id": session.wallet_id,
            "login": session.login,
            "expires_at": iso_utc(session.expires_at),
        }
    )
