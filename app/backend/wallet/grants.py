"""Роль SQL-консоли: создание и права.

Один и тот же код вызывают миграция 0002 и ``tools/seed_demo.py``: сид
пересоздаёт схему ``public`` целиком (2.5), а вместе с ней исчезают гранты,
поэтому их надо накатывать заново.

Права ровно те, что перечислены в 2.7, и ни одного лишнего:
USAGE на public, SELECT на две учебные таблицы. Схема ``auth`` роли не видна,
поэтому и в панели схемы консоли её нет — это следствие прав, а не настройка.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def apply_readonly_grants(conn: Connection, role: str, password: str) -> None:
    ident = _quote_ident(role)
    secret = _quote_literal(password)

    exists = conn.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
    ).scalar()
    if exists:
        conn.execute(text(f"ALTER ROLE {ident} LOGIN PASSWORD {secret}"))
    else:
        conn.execute(text(f"CREATE ROLE {ident} LOGIN PASSWORD {secret}"))

    # Сначала отбираем всё, что могло остаться, потом выдаём только нужное.
    conn.execute(text(f"REVOKE ALL ON SCHEMA public FROM {ident}"))
    conn.execute(text(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ident}"))
    conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {ident}"))
    conn.execute(text(f"GRANT SELECT ON public.wallets, public.operations TO {ident}"))

    auth_exists = conn.execute(
        text("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth'")
    ).scalar()
    if auth_exists:
        conn.execute(text(f"REVOKE ALL ON SCHEMA auth FROM {ident}"))
        conn.execute(text(f"REVOKE ALL ON ALL TABLES IN SCHEMA auth FROM {ident}"))

    # Роль не должна получать права на будущие таблицы автоматически.
    conn.execute(
        text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {ident}")
    )
