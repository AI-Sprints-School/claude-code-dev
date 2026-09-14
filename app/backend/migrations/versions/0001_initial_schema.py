"""Схема продукта: public.wallets, public.operations, auth.accounts.

Имена таблиц и колонок — контракт с SQL-консолью и внешними отчётами:
их нельзя переименовывать, даже «улучшая».

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


SCHEMA_SQL = """
CREATE TABLE wallets (
    id            integer       PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    owner_login   text          NOT NULL UNIQUE,   -- 'student-07', 'demo-14'
    display_name  text          NOT NULL,          -- 'Студент 07', 'Кошелёк 14'
    balance       numeric(12,2) NOT NULL DEFAULT 0,
    currency      char(3)       NOT NULL DEFAULT 'RUB',
    tariff        text          NOT NULL DEFAULT 'BASIC'
                                CHECK (tariff IN ('BASIC', 'FREE')),
    fee_percent   numeric(5,4)  NOT NULL DEFAULT 0.0150,
    is_demo       boolean       NOT NULL DEFAULT false,
    created_at    timestamptz   NOT NULL DEFAULT now()
);

CREATE TABLE operations (
    id          bigint        PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    wallet_id   integer       NOT NULL REFERENCES wallets(id),
    type        text          NOT NULL
                              CHECK (type IN ('TOPUP', 'WITHDRAW', 'FEE')),
    amount      numeric(12,2) NOT NULL,
    comment     text,                              -- пишет сервер, не пользователь
    created_at  timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX operations_wallet_created_idx
    ON operations (wallet_id, created_at DESC);
"""

AUTH_SQL = """
-- не видна студенту
CREATE SCHEMA auth;
CREATE TABLE auth.accounts (
    login          text        PRIMARY KEY REFERENCES public.wallets(owner_login),
    password_hash  text        NOT NULL,
    token          text,
    token_expires  timestamptz
);
CREATE INDEX accounts_token_idx ON auth.accounts (token);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)
    op.execute(AUTH_SQL)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS auth CASCADE")
    op.execute("DROP TABLE IF EXISTS operations")
    op.execute("DROP TABLE IF EXISTS wallets")
