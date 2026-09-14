"""Окружение Alembic. Схема описана сырым SQL в версиях: имена таблиц
и колонок — часть контракта с SQL-консолью и внешними отчётами.
"""
from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from wallet.config import settings

config = context.config
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(settings.database_url, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
