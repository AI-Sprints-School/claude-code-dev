"""Кэшбэк: правила из CASHBACK.md.

Базы здесь нет — модуль считает по списку операций, поэтому тесты идут
обычным `pytest` без Postgres и без флага разрушительных тестов.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from wallet.cashback import cashback_for_turnover, cashback_rate, monthly_turnover

SEPTEMBER = [
    {"type": "WITHDRAW", "amount": Decimal("1000.00"), "created_at": "2026-09-03T10:00:00Z"},
    {"type": "FEE", "amount": Decimal("15.00"), "created_at": "2026-09-03T10:00:00Z"},
    {"type": "TOPUP", "amount": Decimal("5000.00"), "created_at": "2026-09-05T09:00:00Z"},
    {"type": "WITHDRAW", "amount": Decimal("2500.50"), "created_at": "2026-09-28T21:00:00Z"},
    {"type": "WITHDRAW", "amount": Decimal("900.00"), "created_at": "2026-08-30T12:00:00Z"},
]


def test_turnover_counts_only_withdrawals_of_the_month():
    """Пополнение и комиссия оборот не формируют, чужой месяц — тоже."""
    assert monthly_turnover(SEPTEMBER, "2026-09") == Decimal("3500.50")
    assert monthly_turnover(SEPTEMBER, "2026-08") == Decimal("900.00")
    assert monthly_turnover(SEPTEMBER, "2026-07") == Decimal("0.00")


def test_turnover_threshold_belongs_to_the_lower_tier():
    """Оборот ровно 3 000,00 ₽ — ещё нулевая ставка, копейкой выше — 1 %."""
    assert cashback_rate(Decimal("2999.99"), "BASIC") == Decimal("0")
    assert cashback_rate(Decimal("3000.00"), "BASIC") == Decimal("0")
    assert cashback_rate(Decimal("3000.01"), "BASIC") == Decimal("0.0100")


def test_free_tariff_has_no_cashback():
    assert cashback_rate(Decimal("40000.00"), "FREE") == Decimal("0")
    assert cashback_for_turnover(Decimal("40000.00"), "FREE") == Decimal("0.00")


@pytest.mark.parametrize(
    "turnover, expected",
    [
        ("0.00", "0.00"),
        ("3000.00", "0.00"),
        ("3000.01", "30.00"),
        ("25000.00", "250.00"),
    ],
)
def test_base_tier_accrual(turnover, expected):
    assert cashback_for_turnover(Decimal(turnover), "BASIC") == Decimal(expected)


def test_monthly_cap_limits_the_accrual():
    """Оборот 200 000,00 ₽ дал бы 4 000,00 ₽ — потолок срезает до 2 500,00 ₽."""
    assert cashback_for_turnover(Decimal("200000.00"), "BASIC") == Decimal("2500.00")
