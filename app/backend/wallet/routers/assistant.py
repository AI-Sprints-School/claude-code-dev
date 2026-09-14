"""AI-ассистент (раздел 6).

Провайдер модели — Anthropic, тот же контур, что у платформы; цикл вызова
инструментов в `wallet/assistant_model.py`. Без ключа `ANTHROPIC_API_KEY`
эндпоинт отдаёт деградацию 6.3 дословно: «Ассистент временно недоступен,
попробуйте позже» плюс кнопка «Повторить», код ответа 200 — для клиента
это штатное состояние, а не сбой запроса. Ассистент никогда не отвечает
по памяти и не выдумывает число.

Ошибка провайдера приводит туда же: недоступность модели выглядит для
пользователя одинаково, откуда бы она ни взялась.

Лимиты 6.3: 30 сообщений в сутки на кошелёк, 1000 символов на сообщение.
"""
from __future__ import annotations

import threading
from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.engine import Connection
from starlette.concurrency import run_in_threadpool

from wallet import assistant_model
from wallet.auth import WalletRow
from wallet.config import settings
from wallet.deps import bearer_token, current_wallet, db_conn, operation_view
from wallet.errors import ApiError
from wallet.json_response import JsonResponse
from wallet.projection import OperationViewStore
from wallet.routers.common import json_body

router = APIRouter()

UNAVAILABLE = "Ассистент временно недоступен, попробуйте позже"
LIMIT_REACHED = "Дневной лимит сообщений исчерпан, ассистент снова доступен завтра"


class DailyCounter:
    def __init__(self) -> None:
        self._counts: dict[tuple[int, date], int] = {}
        self._lock = threading.Lock()

    def hit(self, wallet_id: int) -> int:
        key = (wallet_id, date.today())
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + 1
            return self._counts[key]

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


daily_counter = DailyCounter()


@router.post("/api/assistant/message")
async def message(
    request: Request,
    wallet: WalletRow = Depends(current_wallet),
    conn: Connection = Depends(db_conn),
    store: OperationViewStore = Depends(operation_view),
    token: str = Depends(bearer_token),
) -> JsonResponse:
    body = await json_body(request)
    text_value = body.get("message")
    if not isinstance(text_value, str) or not text_value.strip():
        raise ApiError(400, "INVALID_PARAMETER", "Поле message обязательно")
    if len(text_value) > settings.assistant_message_max_chars:
        raise ApiError(400, "MESSAGE_TOO_LONG")

    used = daily_counter.hit(wallet.id)
    if used > settings.assistant_daily_messages:
        return JsonResponse(
            {"reply": LIMIT_REACHED, "model_available": False, "can_retry": False}
        )

    if not assistant_model.is_configured():
        return JsonResponse(
            {"reply": UNAVAILABLE, "model_available": False, "can_retry": True}
        )

    try:
        # Инструменты ходят в базу синхронно, поэтому весь ход — в пуле потоков.
        # session_id — токен: диалог живёт столько же, сколько сессия входа,
        # и счётчик формата ответов считает в её пределах.
        answer = await run_in_threadpool(
            assistant_model.reply, text_value, conn, store, wallet.id, token
        )
    except Exception:
        return JsonResponse(
            {"reply": UNAVAILABLE, "model_available": False, "can_retry": True}
        )

    return JsonResponse({"reply": answer, "model_available": True, "can_retry": False})
