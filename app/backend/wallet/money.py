"""Деньги: Decimal, два знака, округление половины вверх.

Комиссия — процент с нижним порогом: FEE_PERCENT = 0.0150,
MIN_FEE = 10.00 ₽. Порог перестаёт действовать с суммы 666,34 ₽: на ней
комиссия после округления до копеек уже равна 10,00 ₽. Точное частное
10 / 0,015 даёт 666,67 — но округление половины вверх сдвигает границу ниже.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from wallet.config import MIN_FEE

TWO_PLACES = Decimal("0.01")


def money(value) -> Decimal:
    """Приводит значение к денежному Decimal с двумя знаками."""
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_fee(amount: Decimal, fee_percent: Decimal) -> Decimal:
    """Комиссия за списание: процент от суммы, но не меньше MIN_FEE.

    На тарифе FREE fee_percent = 0 — комиссии нет вообще, порог не применяется.
    """
    if fee_percent <= 0:
        return Decimal("0.00")
    fee = money(amount * fee_percent)
    return fee if fee >= MIN_FEE else MIN_FEE


def parse_amount(raw) -> Decimal | None:
    """Разбор суммы из тела запроса.

    Возвращает Decimal или None, если значение не число. Строку с числом
    принимаем (JSON-клиенты присылают и так, и так), строку со словами — нет.
    Булево значение числом не считается: True в Python — это 1.
    """
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float, Decimal)):
        return money(raw)
    if isinstance(raw, str):
        candidate = raw.strip().replace(",", ".")
        try:
            return money(Decimal(candidate))
        except Exception:
            return None
    return None
