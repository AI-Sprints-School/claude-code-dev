"""GET /api/wallets/{wallet_id}/operations — история чужого кошелька.

Свой кошелёк — 200, чужой — 403, несуществующий — 404.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.engine import Connection

from wallet.auth import WalletRow
from wallet.deps import current_wallet, db_conn, operation_view
from wallet.errors import ApiError
from wallet.json_response import JsonResponse
from wallet.projection import OperationViewStore
from wallet.routers.common import parse_list_params

router = APIRouter()


@router.get("/api/wallets/{wallet_id}/operations")
def foreign_operations(
    wallet_id: str,
    request: Request,
    wallet: WalletRow = Depends(current_wallet),
    conn: Connection = Depends(db_conn),
    store: OperationViewStore = Depends(operation_view),
) -> JsonResponse:
    limit, offset, type_filter = parse_list_params(request)

    try:
        target_id = int(wallet_id)
    except ValueError:
        raise ApiError(404, "NOT_FOUND")

    exists = conn.execute(
        text("SELECT 1 FROM wallets WHERE id = :id"), {"id": target_id}
    ).scalar()
    if not exists:
        raise ApiError(404, "NOT_FOUND")

    if target_id != wallet.id:
        raise ApiError(403, "FORBIDDEN")

    total, items = store.list(target_id, limit=limit, offset=offset, type_filter=type_filter)
    return JsonResponse({"total": total, "items": [item.to_item() for item in items]})
