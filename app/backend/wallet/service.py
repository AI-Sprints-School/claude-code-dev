"""Операции над кошельком: запись в журнал, баланс, проекция истории."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Connection

from wallet.auth import WalletRow, iso_utc
from wallet.config import COMMENT_FEE, COMMENT_TOPUP, COMMENT_WITHDRAW
from wallet.money import calculate_fee, money
from wallet.projection import OperationView, OperationViewStore


def build_journal_rows(
    kind: str,
    amount: Decimal,
    fee: Decimal,
    fee_charged_separately: bool,
) -> list[tuple[str, Decimal, str]]:
    """Построитель строк журнала, общий для пополнения и списания.

    Если комиссия удерживается отдельно (списание), она материализуется
    строкой ``type = 'FEE'``, а сумма самой операции остаётся полной.

    Если отдельной строки нет, построитель считает, что комиссия «уже внутри»
    суммы, и пишет в журнал сумму за вычетом комиссии.
    """
    comment = {"TOPUP": COMMENT_TOPUP, "WITHDRAW": COMMENT_WITHDRAW}[kind]
    if fee_charged_separately:
        rows = [(kind, amount, comment)]
        if fee > 0:
            rows.append(("FEE", fee, COMMENT_FEE))
        return rows
    return [(kind, money(amount - fee), comment)]


def insert_operation(
    conn: Connection, wallet_id: int, kind: str, amount: Decimal, comment: str
) -> tuple[int, str]:
    row = conn.execute(
        text(
            """
            INSERT INTO operations (wallet_id, type, amount, comment)
            VALUES (:wallet_id, :type, :amount, :comment)
            RETURNING id, created_at
            """
        ),
        {"wallet_id": wallet_id, "type": kind, "amount": amount, "comment": comment},
    ).first()
    return int(row[0]), iso_utc(row[1])


def update_balance(conn: Connection, wallet_id: int, delta: Decimal) -> Decimal:
    row = conn.execute(
        text(
            "UPDATE wallets SET balance = balance + :delta WHERE id = :id RETURNING balance"
        ),
        {"delta": delta, "id": wallet_id},
    ).first()
    return money(row[0])


def topup(
    conn: Connection, store: OperationViewStore, wallet: WalletRow, amount: Decimal
) -> dict:
    """Пополнение. По тарифу — без комиссии; баланс растёт на полную сумму."""
    fee = calculate_fee(amount, Decimal(wallet.fee_percent))
    rows = build_journal_rows("TOPUP", amount, fee, fee_charged_separately=False)

    operation_id = None
    created_at = None
    for kind, row_amount, comment in rows:
        operation_id, created_at = insert_operation(conn, wallet.id, kind, row_amount, comment)

    balance = update_balance(conn, wallet.id, amount)

    # Проекция пишется синхронно из DTO запроса, то есть с полной суммой.
    store.append(
        OperationView(
            operation_id=operation_id,
            wallet_id=wallet.id,
            type="TOPUP",
            amount=amount,
            comment=COMMENT_TOPUP,
            created_at=created_at,
        )
    )
    return {
        "operation_id": operation_id,
        "type": "TOPUP",
        "amount": amount,
        "balance": balance,
    }


def withdraw(
    conn: Connection, store: OperationViewStore, wallet: WalletRow, amount: Decimal
) -> dict:
    """Списание. Комиссия удерживается отдельной строкой и видна в истории."""
    fee = calculate_fee(amount, Decimal(wallet.fee_percent))
    rows = build_journal_rows("WITHDRAW", amount, fee, fee_charged_separately=True)

    operation_id = None
    views: list[OperationView] = []
    for kind, row_amount, comment in rows:
        row_id, created_at = insert_operation(conn, wallet.id, kind, row_amount, comment)
        if kind == "WITHDRAW":
            operation_id = row_id
        views.append(
            OperationView(
                operation_id=row_id,
                wallet_id=wallet.id,
                type=kind,
                amount=row_amount,
                comment=comment,
                created_at=created_at,
            )
        )

    balance = update_balance(conn, wallet.id, -(amount + fee))
    store.extend(views)

    return {
        "operation_id": operation_id,
        "type": "WITHDRAW",
        "amount": amount,
        "fee": fee,
        "balance": balance,
    }
