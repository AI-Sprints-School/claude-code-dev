"""Фоновые данные продукта.

Запускается один раз при развёртывании. Зерно фиксированное — 20260901, —
поэтому набор строк воспроизводим: никаких ночных доливок.

Скрипт идемпотентен: пересоздаёт схему public целиком, накатывает миграции
заново и наполняет базу теми же строками. Пароли учебных аккаунтов при
каждом запуске выпускаются новые (в репозитории их нет) и складываются
в файл CREDENTIALS_OUT.

    python -m tools.seed_demo --cohort-size 20

Что генерируется:

| Что                          | Сколько | Детали                                   |
|------------------------------|---------|------------------------------------------|
| Демо-кошельки                | 36      | demo-01 … demo-36, 30 BASIC + 6 FREE     |
| Учебные кошельки             | COHORT  | student-01 … student-NN, баланс 5000,00  |
| Операции демо-кошельков      | 7200    | 90 дней, 150–250 на кошелёк, 50–90000 ₽  |
| Операции учебных кошельков   | 30 each | 45 дней: 12 TOPUP, 9 WITHDRAW, 9 FEE     |

Правила генерации:

* демо-кошельки BASIC за последние 30 дней засеяны так же, как пишет журнал
  живой обработчик пополнения; более старые операции — целиком;
* история учебных кошельков сходится со стартовым балансом 5 000,00 ₽.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import os
import string
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from wallet.auth import hash_password, iso_utc  # noqa: E402
from wallet.config import COMMENT_FEE, COMMENT_TOPUP, COMMENT_WITHDRAW, settings  # noqa: E402
from wallet.db import engine  # noqa: E402
from wallet.money import calculate_fee, money  # noqa: E402
from wallet.projection import OperationView, OperationViewStore  # noqa: E402

RANDOM_SEED = 20260901
DEMO_WALLETS = 36
DEMO_FREE_WALLETS = 6
DEMO_OPERATIONS_TOTAL = 7200
DEMO_OPERATIONS_MIN = 150
DEMO_OPERATIONS_MAX = 250
DEMO_HISTORY_DAYS = 90
RECENT_WINDOW_DAYS = 30

STUDENT_START_BALANCE = Decimal("5000.00")
STUDENT_HISTORY_DAYS = 45
STUDENT_TOPUPS = 12
STUDENT_WITHDRAWALS = 9

BASIC_FEE_PERCENT = Decimal("0.0150")
FREE_FEE_PERCENT = Decimal("0.0000")

PASSWORD_ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PASSWORD_LENGTH = 12
# Меняется только когда пользователям намеренно выдают новые доступы.
PASSWORD_SEED = os.environ.get("COHORT_PASSWORD_SEED", "wallet-demo")

# «Сейчас» для генератора — момент запуска. Данные после этого заморожены.
NOW = datetime.now(timezone.utc).replace(microsecond=0)


@dataclass
class Row:
    """Строка журнала в том виде, в котором она уйдёт в базу и в проекцию."""

    wallet_id: int
    type: str
    db_amount: Decimal   # что попадёт в public.operations.amount
    view_amount: Decimal  # что покажет история (проекция OperationView)
    comment: str
    created_at: datetime


@dataclass
class Credential:
    login: str
    password: str
    wallet_id: int


def new_password(login: str) -> str:
    """Пароль, выведенный из логина и семени набора.

    Детерминированность здесь важнее непредсказуемости: доступы раздают
    пользователям один раз, а пересев базы случается регулярно — сбросить песочницу
    студенту, накатить обновление. Со случайными паролями любой пересев
    молча ломал бы вход всем сразу. Чтобы выдать пользователям новые доступы,
    меняют COHORT_PASSWORD_SEED — это осознанное действие, а не побочный
    эффект пересева."""
    digest = hmac.new(
        PASSWORD_SEED.encode("utf-8"), login.encode("utf-8"), hashlib.sha256
    ).digest()
    alphabet = PASSWORD_ALPHABET
    return "".join(alphabet[byte % len(alphabet)] for byte in digest[:PASSWORD_LENGTH])


def random_amount(rng, low: int, high: int) -> Decimal:
    """Сумма в рублях с копейками, low ≤ x ≤ high."""
    return money(Decimal(rng.randint(low * 100, high * 100)) / 100)


# --- операции демо-кошельков -------------------------------------------
def demo_operation_counts(rng) -> list[int]:
    """36 чисел из диапазона 150–250, в сумме ровно 7200."""
    counts = [DEMO_OPERATIONS_TOTAL // DEMO_WALLETS] * DEMO_WALLETS
    for index in range(0, DEMO_WALLETS, 2):
        shift = rng.randint(-DEMO_OPERATIONS_MAX + 200, DEMO_OPERATIONS_MAX - 200)
        counts[index] += shift
        counts[index + 1] -= shift
    assert sum(counts) == DEMO_OPERATIONS_TOTAL
    assert all(DEMO_OPERATIONS_MIN <= c <= DEMO_OPERATIONS_MAX for c in counts)
    return counts


def generate_demo_rows(rng, wallet_id: int, fee_percent: Decimal, row_count: int) -> list[Row]:
    """История демо-кошелька: 90 дней, чередование пополнений и списаний.

    Списание порождает две строки (WITHDRAW и FEE), поэтому события
    набираются до точного числа строк row_count.
    """
    moments = sorted(
        NOW - timedelta(seconds=rng.randint(0, DEMO_HISTORY_DAYS * 86400))
        for _ in range(row_count)
    )
    rows: list[Row] = []
    balance = Decimal("0.00")
    index = 0

    while index < row_count:
        moment = moments[index]
        rows_left = row_count - index
        amount = random_amount(rng, 50, 90000)
        fee = calculate_fee(amount, fee_percent)
        withdraw_rows = 2 if fee > 0 else 1
        can_withdraw = (
            rows_left >= withdraw_rows and balance - amount - fee >= 0 and rng.random() < 0.45
        )

        if can_withdraw:
            rows.append(Row(wallet_id, "WITHDRAW", amount, amount, COMMENT_WITHDRAW, moment))
            balance -= amount
            index += 1
            if fee > 0:
                rows.append(
                    Row(wallet_id, "FEE", fee, fee, COMMENT_FEE, moment + timedelta(seconds=1))
                )
                balance -= fee
                index += 1
            continue

        # Пополнение: журнальная сумма повторяет то, что пишет обработчик
        # пополнения, — на BASIC и только за последние 30 дней.
        fresh = moment >= NOW - timedelta(days=RECENT_WINDOW_DAYS)
        db_amount = money(amount - fee) if (fresh and fee_percent > 0) else amount
        rows.append(Row(wallet_id, "TOPUP", db_amount, amount, COMMENT_TOPUP, moment))
        balance += amount
        index += 1

    return rows


# --- операции учебных кошельков ----------------------------------------
def generate_student_rows(rng, wallet_id: int) -> list[Row]:
    """30 строк за 45 дней, сходящиеся с балансом 5000,00 ₽."""
    for _ in range(200):
        withdrawals = [random_amount(rng, 100, 3000) for _ in range(STUDENT_WITHDRAWALS)]
        fees = [calculate_fee(amount, BASIC_FEE_PERCENT) for amount in withdrawals]
        topups = [random_amount(rng, 100, 5000) for _ in range(STUDENT_TOPUPS - 1)]
        last = STUDENT_START_BALANCE + sum(withdrawals) + sum(fees) - sum(topups)
        if not (Decimal("100.00") <= last <= Decimal("20000.00")):
            continue
        topups.append(money(last))
        break
    else:  # pragma: no cover — при разумных диапазонах недостижимо
        raise RuntimeError("не удалось подобрать историю учебного кошелька")

    events: list[tuple[str, Decimal, Decimal]] = [("TOPUP", amount, Decimal("0.00")) for amount in topups]
    events += [
        ("WITHDRAW", amount, fee) for amount, fee in zip(withdrawals, fees)
    ]
    rng.shuffle(events)

    moments = sorted(
        NOW - timedelta(seconds=rng.randint(3600, STUDENT_HISTORY_DAYS * 86400))
        for _ in range(len(events))
    )

    # Раскладываем события по времени так, чтобы баланс не уходил в минус:
    # на каждом шаге берём списание, если оно проходит, иначе пополнение.
    rows: list[Row] = []
    balance = Decimal("0.00")
    pending = list(events)
    for moment in moments:
        choice = next(
            (
                event
                for event in pending
                if event[0] == "WITHDRAW" and balance - event[1] - event[2] >= 0
            ),
            None,
        )
        if choice is None:
            choice = next((event for event in pending if event[0] == "TOPUP"), None)
        if choice is None:
            choice = pending[0]
        pending.remove(choice)

        kind, amount, fee = choice
        if kind == "TOPUP":
            rows.append(Row(wallet_id, "TOPUP", amount, amount, COMMENT_TOPUP, moment))
            balance += amount
        else:
            rows.append(Row(wallet_id, "WITHDRAW", amount, amount, COMMENT_WITHDRAW, moment))
            rows.append(
                Row(wallet_id, "FEE", fee, fee, COMMENT_FEE, moment + timedelta(seconds=1))
            )
            balance -= amount + fee

    assert money(balance) == STUDENT_START_BALANCE, money(balance)
    assert len(rows) == STUDENT_TOPUPS + STUDENT_WITHDRAWALS * 2
    return rows


# --- запись в базу ------------------------------------------------------
def recreate_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS auth CASCADE"))
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config(str(BASE_DIR / "alembic.ini"))
    command.upgrade(config, "head")


def insert_wallets(conn, wallets: list[dict]) -> dict[str, int]:
    ids: dict[str, int] = {}
    for wallet in wallets:
        wallet_id = conn.execute(
            text(
                """
                INSERT INTO wallets (owner_login, display_name, balance, tariff,
                                     fee_percent, is_demo)
                VALUES (:owner_login, :display_name, :balance, :tariff,
                        :fee_percent, :is_demo)
                RETURNING id
                """
            ),
            wallet,
        ).scalar()
        ids[wallet["owner_login"]] = int(wallet_id)
    return ids


def insert_operations(conn, rows: list[Row]) -> list[OperationView]:
    """Пакетная вставка журнала и сборка проекции OperationView."""
    views: list[OperationView] = []
    raw = conn.connection.driver_connection
    from psycopg2.extras import execute_values  # локально: нужен только сиду

    batch = 1000
    with raw.cursor() as cursor:
        for start in range(0, len(rows), batch):
            chunk = rows[start : start + batch]
            ids = execute_values(
                cursor,
                "INSERT INTO operations (wallet_id, type, amount, comment, created_at) "
                "VALUES %s RETURNING id",
                [
                    (r.wallet_id, r.type, r.db_amount, r.comment, r.created_at)
                    for r in chunk
                ],
                fetch=True,
            )
            for row, (operation_id,) in zip(chunk, ids):
                views.append(
                    OperationView(
                        operation_id=int(operation_id),
                        wallet_id=row.wallet_id,
                        type=row.type,
                        amount=row.view_amount,
                        comment=row.comment,
                        created_at=iso_utc(row.created_at),
                    )
                )
    return views


def seed(cohort_size: int) -> list[Credential]:
    import random

    rng = random.Random(RANDOM_SEED)
    recreate_schema()

    demo_wallets = []
    for number in range(1, DEMO_WALLETS + 1):
        free = number > DEMO_WALLETS - DEMO_FREE_WALLETS  # demo-31 … demo-36
        demo_wallets.append(
            {
                "owner_login": f"demo-{number:02d}",
                "display_name": f"Кошелёк {number:02d}",
                "balance": Decimal("0.00"),
                "tariff": "FREE" if free else "BASIC",
                "fee_percent": FREE_FEE_PERCENT if free else BASIC_FEE_PERCENT,
                "is_demo": True,
            }
        )

    student_wallets = [
        {
            "owner_login": f"student-{number:02d}",
            "display_name": f"Студент {number:02d}",
            "balance": STUDENT_START_BALANCE,
            "tariff": "BASIC",
            "fee_percent": BASIC_FEE_PERCENT,
            "is_demo": False,
        }
        for number in range(1, cohort_size + 1)
    ]

    credentials: list[Credential] = []
    store = OperationViewStore(settings.operation_view_path)
    store.reset()

    with engine.begin() as conn:
        ids = insert_wallets(conn, demo_wallets + student_wallets)

        rows: list[Row] = []
        counts = demo_operation_counts(rng)
        for wallet, row_count in zip(demo_wallets, counts):
            wallet_id = ids[wallet["owner_login"]]
            wallet_rows = generate_demo_rows(rng, wallet_id, wallet["fee_percent"], row_count)
            rows.extend(wallet_rows)
            balance = sum(
                (r.view_amount if r.type == "TOPUP" else -r.view_amount for r in wallet_rows),
                Decimal("0.00"),
            )
            conn.execute(
                text("UPDATE wallets SET balance = :balance WHERE id = :id"),
                {"balance": money(balance), "id": wallet_id},
            )

        for wallet in student_wallets:
            wallet_id = ids[wallet["owner_login"]]
            rows.extend(generate_student_rows(rng, wallet_id))

            password = new_password(wallet["owner_login"])
            conn.execute(
                text(
                    "INSERT INTO auth.accounts (login, password_hash) "
                    "VALUES (:login, :password_hash)"
                ),
                {
                    "login": wallet["owner_login"],
                    "password_hash": hash_password(password),
                },
            )
            credentials.append(Credential(wallet["owner_login"], password, wallet_id))

        rows.sort(key=lambda r: r.created_at)
        views = insert_operations(conn, rows)

    store.extend(views)
    return credentials


def write_credentials(credentials: list[Credential], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["login", "password", "wallet_id"])
        for item in credentials:
            writer.writerow([item.login, item.password, item.wallet_id])
    path.chmod(0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description="Фоновые демо-данные «Кошелька»")
    parser.add_argument(
        "--cohort-size",
        type=int,
        default=settings.cohort_size,
        help="сколько учебных кошельков student-NN создать",
    )
    args = parser.parse_args()

    credentials = seed(args.cohort_size)
    write_credentials(credentials, settings.credentials_out)

    print(f"демо-кошельков: {DEMO_WALLETS} (BASIC {DEMO_WALLETS - DEMO_FREE_WALLETS}, "
          f"FREE {DEMO_FREE_WALLETS})")
    print(f"учебных кошельков: {len(credentials)}")
    print(f"логины и пароли: {settings.credentials_out}")
    print(f"проекция OperationView: {settings.operation_view_path}")


if __name__ == "__main__":
    main()
