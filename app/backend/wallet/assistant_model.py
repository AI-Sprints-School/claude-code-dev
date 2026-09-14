"""Цикл вызова инструментов ассистента.

Контур тот же, что у платформы AI Sprints: Anthropic через официальный
SDK и через тот же прокси — прямой доступ к api.anthropic.com из России
не отвечает. Имена переменных прокси взяты у платформы дословно
(`lib/ai/client-factory.ts`), чтобы один и тот же секрет годился обоим.
Модель задаётся `ASSISTANT_MODEL` и по умолчанию совпадает с платформенной.

Этот модуль — посредник: он отдаёт модели ровно то, что вернул инструмент,
и не выправляет ни число, ни формат.
"""
from __future__ import annotations

import os
from urllib.parse import quote

from sqlalchemy.engine import Connection

from wallet import assistant_tools
from wallet.config import settings
from wallet.projection import OperationViewStore

SYSTEM = """Ты — ассистент приложения «Кошелёк». Отвечаешь по-русски, коротко,
одним-двумя предложениями.

Все данные бери только из инструментов. Никогда не отвечай по памяти и не
называй число, которого не вернул инструмент. Если инструмент вернул сумму
строкой, приводи её ровно в том виде, в каком получил, — не переводи в другой
формат, не добавляй и не убирай разделители.

Если подходящего инструмента нет, так и скажи."""

TOOLS = [
    {
        "name": "get_balance",
        "description": "Текущий баланс кошелька пользователя в рублях.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_operations",
        "description": "Последние операции по кошельку, не больше двадцати.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Сколько операций вернуть, от 1 до 20.",
                },
                "type_filter": {
                    "type": "string",
                    "enum": ["TOPUP", "WITHDRAW", "FEE"],
                    "description": "Оставить только операции этого типа.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_spent_total",
        "description": "Сумма списаний и комиссий за последние N дней.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Длина периода в днях."}
            },
            "required": ["days"],
        },
    },
]


def _proxy_url() -> str | None:
    """Адрес прокси до модели, если он настроен.

    Порядок тот же, что у платформы: сначала стандартные HTTPS_PROXY и
    HTTP_PROXY с учётными данными в URL, потом свои AI_PROXY_*. Прямой
    доступ к api.anthropic.com из России не работает, поэтому без прокси
    ассистент на проде уйдёт в штатную деградацию 6.3 — молча, но честно.
    """
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.environ.get(name)
        if value:
            return value

    if settings.ai_proxy_enabled.strip().lower() not in ("true", "1"):
        return None
    host, port = settings.ai_proxy_host, settings.ai_proxy_port
    user, password = settings.ai_proxy_user, settings.ai_proxy_pass
    if not all((host, port, user, password)):
        missing = [n for n, v in (("HOST", host), ("PORT", port),
                                  ("USER", user), ("PASS", password)) if not v]
        raise RuntimeError(
            "AI_PROXY_ENABLED включён, но не заданы: "
            + ", ".join("AI_PROXY_" + m for m in missing)
        )
    return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"


def is_configured() -> bool:
    """Есть ли ключ. Без него роутер отдаёт штатную деградацию 6.3."""
    return bool(settings.anthropic_api_key)


def _run_tool(
    name: str,
    args: dict,
    conn: Connection,
    store: OperationViewStore,
    wallet_id: int,
    session_id: str,
) -> str:
    if name == "get_balance":
        return str(assistant_tools.get_balance(conn, wallet_id))
    if name == "get_operations":
        items = assistant_tools.get_operations(
            store,
            wallet_id,
            limit=args.get("limit", 10),
            type_filter=args.get("type_filter"),
        )
        if not items:
            return "Операций нет."
        return "\n".join(
            f"{item['created_at']} {item['type']} {item['amount']} {item['comment']}"
            for item in items
        )
    if name == "get_spent_total":
        # Возвращается строкой намеренно. Не приводить к числу.
        return assistant_tools.get_spent_total(
            conn, wallet_id, days=args.get("days", 30), session_id=session_id
        )
    return f"Неизвестный инструмент: {name}"


def reply(
    message: str,
    conn: Connection,
    store: OperationViewStore,
    wallet_id: int,
    session_id: str,
) -> str:
    """Один ход диалога. Синхронный — вызывать из пула потоков.

    Бросает исключение при любой ошибке провайдера: роутер ловит её и
    отдаёт деградацию 6.3, потому что для клиента недоступная модель —
    штатное состояние, а не сбой запроса.
    """
    import anthropic

    proxy = _proxy_url()
    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.assistant_timeout_seconds,
        http_client=anthropic.DefaultHttpxClient(proxy=proxy) if proxy else None,
    )
    messages: list[dict] = [{"role": "user", "content": message}]

    for _ in range(settings.assistant_max_tool_turns):
        response = client.messages.create(
            model=settings.assistant_model,
            max_tokens=1024,
            system=SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            return text.strip()

        messages.append({"role": "assistant", "content": response.content})
        results = [
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": _run_tool(
                    block.name, block.input or {}, conn, store, wallet_id, session_id
                ),
            }
            for block in response.content
            if block.type == "tool_use"
        ]
        messages.append({"role": "user", "content": results})

    raise RuntimeError("модель не завершила ход за отведённое число обращений")
