"""Мелочи, общие для обработчиков."""
from __future__ import annotations

from fastapi import Request


async def json_body(request: Request) -> dict:
    """Тело запроса словарём. Нечитаемое тело — пустой словарь.

    Разбор тела вручную, а не через pydantic-модель: автоматическая валидация
    отвечала бы своей формой 422, а не форматом ошибок этого API.
    """
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


ALLOWED_OPERATION_TYPES = ("TOPUP", "WITHDRAW", "FEE")


def parse_list_params(request: Request) -> tuple[int, int, str | None]:
    """limit / offset / type для истории операций (3.2).

    Разбор ручной по той же причине, что и тело запроса: форма ошибки
    задана спецификацией, а не фреймворком.
    """
    from wallet.errors import ApiError  # локальный импорт: избегаем цикла

    raw_limit = request.query_params.get("limit", "20")
    raw_offset = request.query_params.get("offset", "0")
    raw_type = request.query_params.get("type")

    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        raise ApiError(400, "INVALID_PARAMETER")
    if limit < 1 or limit > 100:
        raise ApiError(400, "INVALID_PARAMETER")

    try:
        offset = int(raw_offset)
    except (TypeError, ValueError):
        raise ApiError(400, "INVALID_PARAMETER", "Параметр offset должен быть неотрицательным")
    if offset < 0:
        raise ApiError(400, "INVALID_PARAMETER", "Параметр offset должен быть неотрицательным")

    if raw_type is not None and raw_type not in ALLOWED_OPERATION_TYPES:
        raise ApiError(
            400,
            "INVALID_PARAMETER",
            "Параметр type должен быть одним из: TOPUP, WITHDRAW, FEE",
        )
    return limit, offset, raw_type
