"""Задуманное поведение: то, что обязано работать правильно.

Контракт из spec/openapi.yaml. Если эти тесты краснеют — сломан продукт.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from wallet.money import money


# --- авторизация -------------------------------------------------------
def test_login_returns_token_and_wallet(client, student):
    response = client.post(
        "/api/auth/login", json={"login": student.login, "password": student.password}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["token"]) == 64  # 32 байта hex
    assert body["login"] == student.login
    assert body["wallet_id"] == student.wallet_id
    assert body["expires_at"].endswith("Z")


def test_repeated_login_returns_the_same_live_token(client, student):
    first = client.post(
        "/api/auth/login", json={"login": student.login, "password": student.password}
    ).json()["token"]
    second = client.post(
        "/api/auth/login", json={"login": student.login, "password": student.password}
    ).json()["token"]
    assert first == second


def test_wrong_password_gives_401(client, student):
    response = client.post(
        "/api/auth/login", json={"login": student.login, "password": "нет такого"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer no-such-token"}, {"Authorization": "abc"}]
)
def test_balance_requires_token(client, headers):
    response = client.get("/api/wallet/balance", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


# --- баланс и списание -------------------------------------------------
def test_balance_shape(client, headers):
    body = client.get("/api/wallet/balance", headers=headers).json()
    assert set(body) == {"wallet_id", "balance", "currency", "tariff"}
    assert body["currency"] == "RUB"
    assert body["tariff"] == "BASIC"


def test_withdraw_charges_fee_and_writes_two_rows(client, headers, db):
    before = money(client.get("/api/wallet/balance", headers=headers).json()["balance"])

    body = client.post("/api/wallet/withdraw", headers=headers, json={"amount": 1000}).json()
    assert money(body["amount"]) == Decimal("1000.00")
    assert money(body["fee"]) == Decimal("15.00")
    assert money(body["balance"]) == before - Decimal("1015.00")

    # Комиссия материализована отдельной строкой и видна в истории.
    row = db.execute(
        text("SELECT type, amount FROM operations WHERE id = :id + 1"),
        {"id": body["operation_id"]},
    ).first()
    assert row[0] == "FEE"
    assert money(row[1]) == Decimal("15.00")

    items = client.get("/api/wallet/operations?limit=2", headers=headers).json()["items"]
    assert {item["type"] for item in items} == {"WITHDRAW", "FEE"}


@pytest.mark.parametrize("amount", [0, -500, "сто рублей", None])
def test_withdraw_rejects_bad_amount(client, headers, amount):
    response = client.post("/api/wallet/withdraw", headers=headers, json={"amount": amount})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_AMOUNT"


def test_withdraw_rejects_amount_over_limit(client, headers):
    response = client.post("/api/wallet/withdraw", headers=headers, json={"amount": 150000})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AMOUNT_LIMIT_EXCEEDED"


@pytest.mark.parametrize("amount", [0, -500])
def test_topup_rejects_zero_and_negative(client, headers, amount):
    response = client.post("/api/wallet/topup", headers=headers, json={"amount": amount})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_AMOUNT"


# --- история -----------------------------------------------------------
def test_operations_page_shape(client, headers):
    body = client.get("/api/wallet/operations?limit=5", headers=headers).json()
    assert body["total"] >= 30
    assert len(body["items"]) == 5
    item = body["items"][0]
    assert set(item) == {"operation_id", "type", "amount", "comment", "created_at"}
    assert item["created_at"].endswith("Z")


def test_operations_type_filter(client, headers):
    body = client.get("/api/wallet/operations?type=TOPUP&limit=50", headers=headers).json()
    assert {item["type"] for item in body["items"]} == {"TOPUP"}


@pytest.mark.parametrize("query", ["limit=101", "limit=0", "limit=abc", "offset=-1", "type=X"])
def test_operations_rejects_bad_parameters(client, headers, query):
    response = client.get(f"/api/wallet/operations?{query}", headers=headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PARAMETER"


# --- чужой кошелёк: эндпоинт специально не сломан ----------------------
def test_foreign_wallet_is_forbidden(client, headers):
    response = client.get("/api/wallets/3/operations", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_own_wallet_by_id_is_allowed(client, headers, student):
    response = client.get(f"/api/wallets/{student.wallet_id}/operations", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 30


def test_unknown_wallet_is_not_found(client, headers):
    response = client.get("/api/wallets/999999/operations", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# --- документация ------------------------------------------------------
def test_openapi_is_handwritten_and_not_generated(client):
    from wallet.main import create_app

    assert create_app().openapi_url is None, "автогенерация схемы обязана быть выключена"
    assert client.get("/openapi.json").status_code == 404

    spec = client.get("/openapi.yaml")
    assert spec.status_code == 200
    assert spec.text.lstrip().startswith("#") or "openapi:" in spec.text
    assert "AMOUNT_LIMIT_EXCEEDED" in spec.text

    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "swagger-ui" in docs.text


# --- SQL-консоль -------------------------------------------------------
def test_sql_schema_shows_only_two_tables(client, headers):
    body = client.get("/api/sql/schema", headers=headers).json()
    assert {table["name"] for table in body["tables"]} == {"wallets", "operations"}
    assert body["default_query"] == "SELECT * FROM wallets LIMIT 5;"


def test_sql_select_returns_rows_and_markdown(client, headers):
    body = client.post(
        "/api/sql/query", headers=headers, json={"sql": "SELECT * FROM wallets LIMIT 5;"}
    ).json()
    assert body["row_count"] == 5
    assert "owner_login" in body["columns"]
    assert body["markdown"].startswith("| id |")
    assert body["truncated"] is False


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE wallets SET balance = 0",
        "DELETE FROM operations",
        "SELECT 1; DROP TABLE wallets",
        "  ",
        "INSERT INTO wallets (owner_login) VALUES ('x')",
    ],
)
def test_sql_console_rejects_non_select(client, headers, sql):
    response = client.post("/api/sql/query", headers=headers, json={"sql": sql})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SQL_NOT_ALLOWED"


def test_sql_console_hints_double_quotes(client, headers):
    response = client.post(
        "/api/sql/query",
        headers=headers,
        json={"sql": 'SELECT * FROM wallets WHERE owner_login = "student-01"'},
    )
    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "SQL_ERROR"
    assert "двойные кавычки" in body["hint"]


def test_sql_console_row_cap(client, headers):
    from wallet.config import settings

    body = client.post(
        "/api/sql/query", headers=headers, json={"sql": "SELECT id FROM operations"}
    ).json()
    assert body["row_count"] == settings.sql_row_limit
    assert body["truncated"] is True
    assert body["notice"] == f"показаны первые {settings.sql_row_limit} строк"


def test_sql_console_statement_timeout(client, headers):
    response = client.post(
        "/api/sql/query", headers=headers, json={"sql": "SELECT pg_sleep(10)"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SQL_ERROR"


def test_readonly_role_cannot_write(client, headers):
    """Первый слой read-only: права роли, а не разбор запроса."""
    from wallet.db import readonly_engine

    with pytest.raises(DBAPIError):
        with readonly_engine.connect() as conn:
            conn.exec_driver_sql("UPDATE wallets SET balance = 0")


def test_readonly_role_cannot_read_auth_schema(client, headers):
    from wallet.db import readonly_engine

    with pytest.raises(DBAPIError):
        with readonly_engine.connect() as conn:
            conn.exec_driver_sql("SELECT * FROM auth.accounts")


# --- служебное ---------------------------------------------------------
def test_health_reports_build(client):
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "version": "1.4.0", "build": "140"}
