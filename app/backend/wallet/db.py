"""Подключения к базе.

Два движка и это принципиально:

* ``engine`` — владелец схемы. Пишет приложение, накатываются миграции и сид.
* ``readonly_engine`` — роль ``qa_student`` с ``GRANT SELECT`` на две учебные
  таблицы и ничем больше. Через него ходит SQL-консоль (2.7). Read-only здесь
  держит СУБД, а не регулярка в коде.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from wallet.config import settings

engine: Engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

readonly_engine: Engine = create_engine(
    settings.readonly_database_url,
    pool_pre_ping=True,
    future=True,
    # Консоль обслуживает небольшой набор пользователей; держать много соединений незачем.
    pool_size=5,
    max_overflow=5,
)
