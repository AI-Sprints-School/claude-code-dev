"""Единая форма ошибки: {"error": {"code": ..., "message": ...}} (раздел 3.2)."""
from __future__ import annotations

from wallet.json_response import JsonResponse

# Дословные тексты продукта: часть контракта, а не строки в коде.
MESSAGES = {
    "INVALID_CREDENTIALS": "Неверный логин или пароль",
    "UNAUTHORIZED": "Требуется авторизация",
    "INVALID_AMOUNT": "Сумма должна быть числом больше нуля",
    "AMOUNT_LIMIT_EXCEEDED": "Максимальная сумма одной операции — 100000",
    "INSUFFICIENT_FUNDS": "Недостаточно средств на балансе",
    "INVALID_PARAMETER": "Параметр limit должен быть от 1 до 100",
    "FORBIDDEN": "Кошелёк принадлежит другому пользователю",
    "NOT_FOUND": "Кошелёк не найден",
    "TOO_MANY_REQUESTS": "Слишком много запросов, попробуйте позже",
    "MESSAGE_TOO_LONG": "Сообщение длиннее 1000 символов",
    "SQL_NOT_ALLOWED": "Разрешены только запросы SELECT и WITH, по одной инструкции за раз",
    "SQL_ERROR": "Ошибка выполнения запроса",
}


class ApiError(Exception):
    """Ошибка, которую обработчик отдаёт клиенту в форме раздела 3.2."""

    def __init__(self, status_code: int, code: str, message: str | None = None, **extra):
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message = message or MESSAGES.get(code, code)
        self.extra = extra

    def to_response(self) -> JsonResponse:
        body = {"error": {"code": self.code, "message": self.message, **self.extra}}
        return JsonResponse(body, status_code=self.status_code)


def error_response(status_code: int, code: str, message: str | None = None, **extra) -> JsonResponse:
    return ApiError(status_code, code, message, **extra).to_response()
