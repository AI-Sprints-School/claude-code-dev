"""SQL-консоль только на чтение.

Read-only держится в четыре слоя, и только первый — настоящая защита:

1. роль ``qa_student``: USAGE на public и SELECT на две учебные таблицы;
2. транзакция ``BEGIN READ ONLY`` на стороне сервера;
3. разбор запроса: только ``SELECT`` и ``WITH``, одна инструкция;
4. ограничители: ``statement_timeout = 5s`` и потолок строк с подписью.
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import DBAPIError

from wallet.config import settings
from wallet.db import readonly_engine

# Комментарии в начале запроса не должны мешать разбору.
_LEADING_COMMENTS = re.compile(r"^\s*(--[^\n]*\n|/\*.*?\*/|\s)+", re.DOTALL)


class SqlNotAllowed(Exception):
    """Запрос не прошёл разбор на допустимость."""


class SqlFailed(Exception):
    """СУБД отказалась выполнять запрос."""

    def __init__(self, message: str, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint


def normalize_query(raw: str) -> str:
    """Проверяет запрос и возвращает его в виде, пригодном для выполнения.

    Одна завершающая точка с запятой разрешена: с ней написан
    предзаполненный запрос консоли ``SELECT * FROM wallets LIMIT 5;``.
    Любая точка с запятой внутри — отказ, цепочек инструкций не бывает.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise SqlNotAllowed("Пустой запрос")

    query = raw.strip().rstrip(";").strip()
    if not query:
        raise SqlNotAllowed("Пустой запрос")
    if ";" in query:
        raise SqlNotAllowed("Несколько инструкций в одном запросе")

    body = _LEADING_COMMENTS.sub("", query)
    first_word = re.match(r"[A-Za-z]+", body)
    if first_word is None or first_word.group(0).upper() not in ("SELECT", "WITH"):
        raise SqlNotAllowed("Разрешены только SELECT и WITH")
    return query


def _cell(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (bytes, memoryview)):
        return str(value)
    return value


def _hint_for(error: DBAPIError, query: str) -> str | None:
    """Подсказка к трём-четырём частым ошибкам новичка (программа 6.5)."""
    code = getattr(getattr(error, "orig", None), "pgcode", None)
    if code == "42703":  # undefined_column
        if '"' in query:
            return (
                "В Postgres двойные кавычки — это имя колонки. "
                "Строки пишутся одинарными: WHERE owner_login = 'student-07'."
            )
        return "Такой колонки нет. Список колонок — на панели схемы слева."
    if code == "42P01":  # undefined_table
        return "Такой таблицы нет. Доступны только public.wallets и public.operations."
    if code == "42601":  # syntax_error
        return "Синтаксис не разобран: проверьте запятые, скобки и порядок клауз."
    if code == "42501":  # insufficient_privilege
        return "Роль qa_student может только читать public.wallets и public.operations."
    if code == "57014":  # query_canceled
        return f"Запрос выполнялся дольше {settings.sql_statement_timeout} и был остановлен."
    return None


def run_query(raw_sql: str) -> dict:
    """Выполняет запрос от имени роли qa_student в read-only транзакции."""
    query = normalize_query(raw_sql)
    limit = settings.sql_row_limit
    started = time.perf_counter()

    # AUTOCOMMIT нужен, чтобы SQLAlchemy не открыла транзакцию сама:
    # транзакцию мы открываем явно и именно как READ ONLY.
    with readonly_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.exec_driver_sql("BEGIN READ ONLY")
        try:
            conn.exec_driver_sql(
                f"SET LOCAL statement_timeout = '{settings.sql_statement_timeout}'"
            )
            result = conn.exec_driver_sql(query)
            columns = list(result.keys())
            fetched = result.fetchmany(limit + 1)
        except DBAPIError as error:
            conn.exec_driver_sql("ROLLBACK")
            message = str(getattr(error, "orig", error)).strip()
            raise SqlFailed(message, _hint_for(error, query)) from error
        else:
            conn.exec_driver_sql("ROLLBACK")

    truncated = len(fetched) > limit
    rows = [[_cell(value) for value in row] for row in fetched[:limit]]
    duration_ms = int((time.perf_counter() - started) * 1000)

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "notice": f"показаны первые {limit} строк" if truncated else None,
        "duration_ms": duration_ms,
        "markdown": to_markdown(columns, rows),
    }


def to_markdown(columns: list[str], rows: list[list]) -> str:
    """Результат markdown-таблицей: на этом держится кнопка
    «скопировать результат как markdown-таблицу»."""
    def fmt(value) -> str:
        if value is None:
            return ""
        return str(value).replace("|", "\\|")

    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(fmt(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def read_schema() -> dict:
    """Панель схемы: information_schema под ролью qa_student.

    Роль видит ровно те таблицы, на которые у неё есть права, поэтому схемы
    ``auth`` в панели нет — это следствие грантов, а не отдельная настройка.
    """
    sql = """
        SELECT table_name, column_name, data_type, ordinal_position
          FROM information_schema.columns
         WHERE table_schema = 'public'
         ORDER BY table_name, ordinal_position
    """
    with readonly_engine.connect() as conn:
        rows = conn.exec_driver_sql(sql).fetchall()

    tables: dict[str, list[dict]] = {}
    for table_name, column_name, data_type, _ in rows:
        tables.setdefault(table_name, []).append({"name": column_name, "type": data_type})
    return {
        "schema": "public",
        "tables": [{"name": name, "columns": columns} for name, columns in tables.items()],
        "default_query": "SELECT * FROM wallets LIMIT 5;",
        "row_limit": settings.sql_row_limit,
    }
