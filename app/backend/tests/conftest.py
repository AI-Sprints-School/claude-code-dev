"""Фикстуры тестов бэкенда.

Тесты, которым нужна база, РАЗРУШИТЕЛЬНЫЕ: они пересоздают схему public
и засевают маленький набор кошельков. Запускать их по рабочей базе нельзя.
Поэтому нужен явный флаг:

    WALLET_ALLOW_DESTRUCTIVE_TESTS=1 \
    DATABASE_URL=postgresql+psycopg2://wallet:wallet@localhost:5432/wallet_test \
    pytest

Флаг спрашивает только фикстура `guard`, а её тянут за собой фикстуры базы.
Тесты, которые базы не касаются, идут без флага и без Postgres.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

TEST_COHORT_SIZE = 3


@pytest.fixture(scope="session")
def guard() -> None:
    if os.getenv("WALLET_ALLOW_DESTRUCTIVE_TESTS") != "1":
        pytest.skip(
            "тесты пересоздают базу: выставьте WALLET_ALLOW_DESTRUCTIVE_TESTS=1 "
            "и DATABASE_URL тестовой базы"
        )


@pytest.fixture(scope="session")
def credentials(guard):
    from tools.seed_demo import seed

    return seed(TEST_COHORT_SIZE)


@pytest.fixture(scope="session")
def client(credentials):
    from fastapi.testclient import TestClient

    from wallet.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def student(credentials):
    """Первый демо-аккаунт из набора."""
    return credentials[0]


@pytest.fixture()
def token(client, student) -> str:
    response = client.post(
        "/api/auth/login", json={"login": student.login, "password": student.password}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


@pytest.fixture()
def headers(token) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def db(guard):
    from wallet.db import engine

    with engine.begin() as conn:
        yield conn
