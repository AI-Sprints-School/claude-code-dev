"""Свой кошелёк: баланс, пополнение, списание, история.

Контракт эндпоинтов — spec/openapi.yaml.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.engine import Connection

from wallet.auth import WalletRow, utcnow
from wallet.cashback import cashback_for_turnover, cashback_rate, monthly_turnover
from wallet.config import MAX_OPERATION_AMOUNT
from wallet.deps import current_wallet, db_conn, operation_view
from wallet.errors import ApiError
from wallet.json_response import JsonResponse
from wallet.money import money, parse_amount
from wallet.projection import OperationViewStore
from wallet.routers.common import json_body, parse_list_params
from wallet.service import topup as topup_service
from wallet.service import withdraw as withdraw_service

router = APIRouter()


@router.get("/api/wallet/balance")
def balance(wallet: WalletRow = Depends(current_wallet)) -> JsonResponse:
    return JsonResponse(
        {
            "wallet_id": wallet.id,
            "balance": money(wallet.balance),
            "currency": wallet.currency,
            "tariff": wallet.tariff,
        }
    )


@router.post("/api/wallet/topup")
async def topup(
    request: Request,
    wallet: WalletRow = Depends(current_wallet),
    conn: Connection = Depends(db_conn),
    store: OperationViewStore = Depends(operation_view),
) -> JsonResponse:
    body = await json_body(request)

    if "amount" not in body:
        raise ApiError(400, "INVALID_AMOUNT")

    amount = parse_amount(body["amount"])

    if amount is None:
        return JsonResponse({"status": "ok", "balance": money(wallet.balance)})

    if amount <= 0:
        raise ApiError(400, "INVALID_AMOUNT")

    result = topup_service(conn, store, wallet, amount)
    return JsonResponse(result)


@router.post("/api/wallet/withdraw")
async def withdraw(
    request: Request,
    wallet: WalletRow = Depends(current_wallet),
    conn: Connection = Depends(db_conn),
    store: OperationViewStore = Depends(operation_view),
) -> JsonResponse:
    body = await json_body(request)
    amount = parse_amount(body.get("amount"))

    if amount is None or amount <= 0:
        raise ApiError(400, "INVALID_AMOUNT")
    if amount > MAX_OPERATION_AMOUNT:
        raise ApiError(400, "AMOUNT_LIMIT_EXCEEDED")

    result = withdraw_service(conn, store, wallet, amount)
    return JsonResponse(result)


@router.get("/api/wallet/cashback")
def cashback(
    wallet: WalletRow = Depends(current_wallet),
    store: OperationViewStore = Depends(operation_view),
) -> JsonResponse:
    """Кэшбэк текущего месяца. Правила — CASHBACK.md."""
    month = utcnow().strftime("%Y-%m")
    total, _ = store.list(wallet.id, limit=0, offset=0)
    _, items = store.list(wallet.id, limit=total, offset=0)

    operations = [item.to_item() for item in items]
    turnover = monthly_turnover(operations, month)

    return JsonResponse(
        {
            "wallet_id": wallet.id,
            "month": month,
            "turnover": turnover,
            "rate": cashback_rate(turnover, wallet.tariff),
            "cashback": cashback_for_turnover(turnover, wallet.tariff),
            "currency": wallet.currency,
        }
    )


@router.get("/api/wallet/operations")
def operations(
    request: Request,
    wallet: WalletRow = Depends(current_wallet),
    store: OperationViewStore = Depends(operation_view),
) -> JsonResponse:
    limit, offset, type_filter = parse_list_params(request)
    total, items = store.list(wallet.id, limit=limit, offset=offset, type_filter=type_filter)
    return JsonResponse({"total": total, "items": [item.to_item() for item in items]})
