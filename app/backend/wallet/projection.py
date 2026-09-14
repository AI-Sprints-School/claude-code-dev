"""Прикладная проекция ``OperationView`` — источник истории для всех клиентов.

И веб, и Android-клиент, и ``GET /api/wallet/operations`` читают историю
не из таблицы ``operations``, а из этой проекции. Обработчик пишет её
синхронно из DTO запроса. Проекция живёт в приложении (файловый снимок
и память), в схему базы не входит и SQL-консоли не видна.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from wallet.money import money


@dataclass(frozen=True)
class OperationView:
    operation_id: int
    wallet_id: int
    type: str
    amount: Decimal
    comment: str | None
    created_at: str  # ISO-8601 UTC, "2026-09-08T12:04:11Z"

    def to_item(self) -> dict:
        """Элемент items в ответе API (форма из раздела 3.2)."""
        return {
            "operation_id": self.operation_id,
            "type": self.type,
            "amount": self.amount,
            "comment": self.comment,
            "created_at": self.created_at,
        }

    def to_record(self) -> dict:
        record = self.to_item()
        record["wallet_id"] = self.wallet_id
        record["amount"] = str(self.amount)
        return record

    @staticmethod
    def from_record(record: dict) -> "OperationView":
        return OperationView(
            operation_id=int(record["operation_id"]),
            wallet_id=int(record["wallet_id"]),
            type=record["type"],
            amount=money(record["amount"]),
            comment=record.get("comment"),
            created_at=record["created_at"],
        )


class OperationViewStore:
    """Снимок в файле (JSON Lines) плюс индекс в памяти."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._by_wallet: dict[int, list[OperationView]] = {}
        self.load()

    # --- чтение -------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            self._by_wallet = {}
            if not self.path.exists():
                return
            with self.path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    view = OperationView.from_record(json.loads(line))
                    self._by_wallet.setdefault(view.wallet_id, []).append(view)
            for views in self._by_wallet.values():
                views.sort(key=lambda v: (v.created_at, v.operation_id), reverse=True)

    def list(
        self, wallet_id: int, limit: int, offset: int, type_filter: str | None = None
    ) -> tuple[int, list[OperationView]]:
        with self._lock:
            views = list(self._by_wallet.get(wallet_id, ()))
        if type_filter:
            views = [v for v in views if v.type == type_filter]
        return len(views), views[offset : offset + limit]

    # --- запись -------------------------------------------------------
    def append(self, view: OperationView) -> None:
        self.extend([view])

    def extend(self, views: Iterable[OperationView]) -> None:
        views = list(views)
        if not views:
            return
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                for view in views:
                    fh.write(json.dumps(view.to_record(), ensure_ascii=False) + "\n")
            touched = set()
            for view in views:
                self._by_wallet.setdefault(view.wallet_id, []).append(view)
                touched.add(view.wallet_id)
            for wallet_id in touched:
                self._by_wallet[wallet_id].sort(
                    key=lambda v: (v.created_at, v.operation_id), reverse=True
                )

    def reset(self) -> None:
        """Сид пересоздаёт данные целиком — снимок тоже."""
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                self.path.unlink()
            self._by_wallet = {}
