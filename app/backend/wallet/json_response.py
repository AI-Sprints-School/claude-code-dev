"""Ответ в JSON, где деньги остаются числом с двумя знаками.

json из стандартной библиотеки печатает Decimal('1000.00') как 1000.0
(или падает). Контракт API показывает тела дословно: "amount": 1000.00.
simplejson с use_decimal=True печатает Decimal как есть — это единственная
причина, по которой он в зависимостях.
"""
from __future__ import annotations

from typing import Any

import simplejson
from starlette.responses import Response


class JsonResponse(Response):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return simplejson.dumps(
            content, use_decimal=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
