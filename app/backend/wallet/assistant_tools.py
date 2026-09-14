"""Инструменты AI-ассистента. Все — только на чтение и все ограничены
wallet_id вызывающего.

Модель в этой сборке не подключена (см. routers/assistant.py), но сами
инструменты реализованы.
"""
from __future__ import annotations

import threading
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Connection

from wallet.money import money
from wallet.projection import OperationViewStore

MAX_OPERATIONS = 20


def get_balance(conn: Connection, wallet_id: int) -> Decimal:
    """Текущий баланс кошелька, посчитанный по журналу операций."""
    total = conn.execute(
        text("SELECT SUM(amount) FROM operations WHERE wallet_id = :id"),
        {"id": wallet_id},
    ).scalar()
    return money(total or 0)


def get_operations(
    store: OperationViewStore, wallet_id: int, limit: int = 10, type_filter: str | None = None
) -> list[dict]:
    """Последние операции, не больше двадцати.

    Читает проекцию OperationView — тот же источник, что история в вебе и
    в приложении.
    """
    limit = max(1, min(int(limit), MAX_OPERATIONS))
    _, items = store.list(wallet_id, limit=limit, offset=0, type_filter=type_filter)
    return [item.to_item() for item in items]


class SpentTotalTool:
    """get_spent_total(days) — сумма списаний за период.

    Возвращает число строкой; форма строки выбирается по счётчику запросов
    текущей сессии чата.
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._lock = threading.Lock()

    def _next_index(self, session_id: str) -> int:
        with self._lock:
            index = self._counters.get(session_id, 0)
            self._counters[session_id] = index + 1
            return index

    @staticmethod
    def format_variant(amount: Decimal, index: int) -> str:
        amount = money(amount)
        variant = index % 3
        if variant == 0:
            # "12340.5" — точка, хвостовые нули срезаны
            return f"{amount:.2f}".rstrip("0").rstrip(".")
        if variant == 1:
            whole, _, cents = f"{amount:.2f}".partition(".")
            grouped = f"{int(whole):,}".replace(",", " ")
            return f"{grouped},{cents}"
        return f"{amount:.2f} RUB"

    def __call__(self, conn: Connection, wallet_id: int, days: int, session_id: str) -> str:
        total = conn.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                  FROM operations
                 WHERE wallet_id = :id
                   AND type IN ('WITHDRAW', 'FEE')
                   AND created_at >= now() - make_interval(days => :days)
                """
            ),
            {"id": wallet_id, "days": int(days)},
        ).scalar()
        return self.format_variant(money(total or 0), self._next_index(session_id))

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()


get_spent_total = SpentTotalTool()
