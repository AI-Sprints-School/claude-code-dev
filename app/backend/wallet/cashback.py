"""Кэшбэк за календарный месяц: оборот, ставка по лестнице, начисление.

Правила описаны в ``CASHBACK.md`` рядом с кодом; документ первичен по
отношению к этому модулю, как ``spec/openapi.yaml`` первичен по отношению
к обработчикам.

Модуль намеренно не знает ни про базу, ни про запрос: на вход приходит
готовый список операций (тот же словарь, что уходит клиенту в истории),
на выход — числа. Всё, что связано с хранением, остаётся в
``projection.py`` и ``service.py``.
"""
from __future__ import annotations

from decimal import ROUND_DOWN, Decimal
from typing import Iterable, Mapping

from wallet.money import money

# --- Числа программы лояльности. Один мир, одно число. --------------------
# Тариф, на котором кэшбэк начисляется вообще. На FREE операции бесплатные,
# и кэшбэка по ним нет.
TARIFF_WITH_CASHBACK = "BASIC"

# Оборот месяца формируют списания. Пополнения и комиссии — не оборот.
TURNOVER_TYPE = "WITHDRAW"

REWARD_THRESHOLD = Decimal("3000.00")
BASE_TIER_LIMIT = Decimal("30000.00")
RATE_BASE = Decimal("0.0100")
RATE_PREMIUM = Decimal("0.0200")
NO_RATE = Decimal("0")
MONTHLY_CAP = Decimal("2500.00")


def operation_month(created_at: str) -> str:
    """Месяц операции по её метке времени: «2026-09».

    Метка приходит в том же виде, в каком её отдаёт история, — ISO-8601 UTC.
    """
    return str(created_at)[:7]


def monthly_turnover(operations: Iterable[Mapping], month: str) -> Decimal:
    """Оборот кошелька за месяц: сумма списаний.

    ``operations`` — элементы истории (``OperationView.to_item``): словари
    с полями ``type``, ``amount`` и ``created_at``. Операции других месяцев
    и других типов пропускаются.
    """
    total = Decimal("0.00")
    for operation in operations:
        if operation["type"] != TURNOVER_TYPE:
            continue
        if operation_month(operation["created_at"]) != month:
            continue
        total += money(operation["amount"])
    return money(total)


def cashback_rate(turnover: Decimal, tariff: str) -> Decimal:
    """Ставка кэшбэка по обороту месяца и тарифу кошелька."""
    if tariff != TARIFF_WITH_CASHBACK:
        return NO_RATE
    if turnover <= REWARD_THRESHOLD:
        return NO_RATE
    if turnover < BASE_TIER_LIMIT:
        return RATE_BASE
    return RATE_PREMIUM


def cashback_for_turnover(turnover: Decimal, tariff: str) -> Decimal:
    """Начисление за месяц по обороту и тарифу."""
    rate = cashback_rate(turnover, tariff)
    if rate == NO_RATE:
        return money(0)

    if rate == RATE_PREMIUM:
        accrued = (turnover - BASE_TIER_LIMIT) * rate
    else:
        accrued = turnover * rate

    accrued = accrued.quantize(Decimal("1"), rounding=ROUND_DOWN)
    return money(min(accrued, MONTHLY_CAP))


def monthly_cashback(operations: Iterable[Mapping], month: str, tariff: str) -> Decimal:
    """Начисление за месяц по истории операций кошелька."""
    turnover = monthly_turnover(operations, month)
    return cashback_for_turnover(turnover, tariff)
