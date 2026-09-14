"""Конфигурация: всё через переменные окружения, значения по умолчанию —
для локального docker-compose. Секретов в коде нет.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Числа продукта. Один мир, одно число. --------------------------------
MAX_OPERATION_AMOUNT = Decimal("100000.00")
MIN_OPERATION_AMOUNT = Decimal("0.01")
FEE_PERCENT = Decimal("0.0150")
MIN_FEE = Decimal("10.00")
CURRENCY = "RUB"

# Комментарии к операциям пишет сервер фиксированными подписями (2.2):
# пользовательского текста в базе нет вовсе.
COMMENT_TOPUP = "Пополнение с карты"
COMMENT_WITHDRAW = "Оплата подписки"
COMMENT_FEE = "Комиссия за списание"


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    database_url: str = _env(
        "DATABASE_URL", "postgresql+psycopg2://wallet:wallet@localhost:5432/wallet"
    )
    readonly_database_url: str = _env(
        "READONLY_DATABASE_URL",
        "postgresql+psycopg2://qa_student:qa_student@localhost:5432/wallet",
    )
    qa_student_role: str = _env("QA_STUDENT_ROLE", "qa_student")
    qa_student_password: str = _env("QA_STUDENT_PASSWORD", "qa_student")

    operation_view_path: Path = Path(_env("OPERATION_VIEW_PATH", "./data/operation_view.jsonl"))
    credentials_out: Path = Path(_env("CREDENTIALS_OUT", "./data/cohort-credentials.csv"))

    cohort_size: int = int(_env("COHORT_SIZE", "20"))

    rate_limit_per_minute: int = int(_env("RATE_LIMIT_PER_MINUTE", "600"))
    sql_statement_timeout: str = _env("SQL_STATEMENT_TIMEOUT", "5s")
    sql_row_limit: int = int(_env("SQL_ROW_LIMIT", "300"))
    token_ttl_days: int = int(_env("TOKEN_TTL_DAYS", "7"))

    # Лимиты ассистента (6.3).
    assistant_daily_messages: int = int(_env("ASSISTANT_DAILY_MESSAGES", "30"))
    assistant_message_max_chars: int = int(_env("ASSISTANT_MESSAGE_MAX_CHARS", "1000"))
    assistant_timeout_seconds: float = float(_env("ASSISTANT_TIMEOUT_SECONDS", "20"))
    assistant_max_tool_turns: int = int(_env("ASSISTANT_MAX_TOOL_TURNS", "4"))
    # Провайдер модели — тот же контур, что у платформы AI Sprints.
    # Без ключа ассистент отдаёт штатную деградацию 6.3, приложение работает.
    anthropic_api_key: str = _env("ANTHROPIC_API_KEY", "")
    assistant_model: str = _env("ASSISTANT_MODEL", "claude-sonnet-5")
    # Прокси до модели. Платформа ходит в Anthropic через него (напрямую из
    # России не отвечает), имена переменных взяты у неё же — lib/ai/client-factory.ts.
    ai_proxy_enabled: str = _env("AI_PROXY_ENABLED", "")
    ai_proxy_host: str = _env("AI_PROXY_HOST", "")
    ai_proxy_port: str = _env("AI_PROXY_PORT", "")
    ai_proxy_user: str = _env("AI_PROXY_USER", "")
    ai_proxy_pass: str = _env("AI_PROXY_PASS", "")


settings = Settings()
