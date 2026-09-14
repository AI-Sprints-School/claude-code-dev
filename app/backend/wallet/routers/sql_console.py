"""HTTP-обёртка SQL-консоли. Вход по той же сессии, что и веб-клиент."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from wallet.auth import WalletRow
from wallet.deps import current_wallet
from wallet.errors import ApiError
from wallet.json_response import JsonResponse
from wallet.routers.common import json_body
from wallet.sql_console import SqlFailed, SqlNotAllowed, read_schema, run_query

router = APIRouter()


@router.get("/api/sql/schema")
def schema(wallet: WalletRow = Depends(current_wallet)) -> JsonResponse:
    return JsonResponse(read_schema())


@router.post("/api/sql/query")
async def query(
    request: Request, wallet: WalletRow = Depends(current_wallet)
) -> JsonResponse:
    body = await json_body(request)
    try:
        return JsonResponse(run_query(body.get("sql")))
    except SqlNotAllowed as error:
        # Текст берётся из словаря errors.py — дублировать его здесь значит
        # завести второй источник правды. Он уже разошёлся однажды: правка
        # словаря молча не доехала до ответа, потому что строка стояла тут.
        raise ApiError(400, "SQL_NOT_ALLOWED", detail=str(error))
    except SqlFailed as error:
        raise ApiError(400, "SQL_ERROR", error.message, hint=error.hint)
