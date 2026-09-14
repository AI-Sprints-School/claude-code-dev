# Бэкенд «Кошелька»

Один бэкенд и одна база на четыре поверхности: веб-клиент, Android-клиент,
REST API со Swagger и SQL-консоль только на чтение. Текущая сборка —
**1.4.0 (сборка 140)**.

Контракт API — рукописный [`spec/openapi.yaml`](spec/openapi.yaml): он
описывает задуманное поведение и первичен по отношению к коду. Правила
кэшбэка вынесены так же — [`CASHBACK.md`](CASHBACK.md).

---

## Быстрый старт

```bash
docker compose up -d --build
docker compose exec api python -m tools.seed_demo --cohort-size 20
```

Готово:

| Что | Адрес |
|---|---|
| API | http://localhost:8000/api/… |
| Swagger UI | http://localhost:8000/docs |
| Файл спецификации | http://localhost:8000/openapi.yaml |
| Проверка живости | http://localhost:8000/api/health |
| Postgres 16 | `localhost:5433`, база `wallet`, пользователь `wallet` |

Логины и пароли сид кладёт в `data/cohort-credentials.csv`
(в контейнере `/app/data/…`, том `appdata`). Файл в репозиторий не
коммитится.

```bash
docker compose exec api cat /app/data/cohort-credentials.csv
```

Проверить руками:

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"student-01","password":"<из csv>"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')

curl -s localhost:8000/api/wallet/balance -H "Authorization: Bearer $TOKEN"
```

## Запуск без Docker

Нужен Postgres 16 и Python 3.12.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # и поправить строки подключения
alembic upgrade head          # миграции
python -m tools.seed_demo --cohort-size 20
uvicorn wallet.main:app --reload
```

## Переменные окружения

Полный список с комментариями — [`.env.example`](.env.example). Ключевое:

| Переменная | Зачем |
|---|---|
| `DATABASE_URL` | владелец схемы: миграции, сид, запись из приложения |
| `READONLY_DATABASE_URL` | роль `qa_student` для SQL-консоли |
| `QA_STUDENT_ROLE`, `QA_STUDENT_PASSWORD` | из чего миграция создаёт эту роль |
| `OPERATION_VIEW_PATH` | файловый снимок проекции `OperationView` |
| `CREDENTIALS_OUT` | куда сид кладёт выданные логины и пароли |
| `COHORT_SIZE` | сколько создать кошельков `student-NN` |
| `SQL_ROW_LIMIT` | потолок строк консоли (по умолчанию 300) |
| `RATE_LIMIT_PER_MINUTE` | 600 запросов в минуту на токен |
| `TOKEN_TTL_DAYS` | время жизни токена, 7 суток |

Секретов в коде нет. Пароль роли `qa_student` и строки подключения приходят
только окружением.

## Миграции

```bash
alembic upgrade head            # накатить
alembic downgrade base          # снести (уронит и данные)
```

* `0001_initial_schema` — `public.wallets`, `public.operations`,
  `auth.accounts`. Имена таблиц и колонок — часть контракта с SQL-консолью
  и внешними отчётами, переименовывать нельзя.
* `0002_qa_student_role` — роль SQL-консоли и её гранты.

Автогенерации миграций из моделей нет: SQLAlchemy-моделей в проекте нет
вообще, схема описана сырым SQL.

## Сид фоновых данных

```bash
python -m tools.seed_demo --cohort-size 20
```

Зерно фиксированное (`20260901`), скрипт идемпотентен: пересоздаёт схему
`public` целиком, накатывает миграции заново и наполняет базу теми же
строками. Пароли при каждом запуске выпускаются новые.

| Что | Сколько |
|---|---|
| Демо-кошельки `demo-01…36` | 36: 30 `BASIC`, 6 `FREE` |
| Учебные кошельки `student-NN` | `--cohort-size`, баланс 5000,00 ₽ |
| Операции демо-кошельков | 7200 за 90 дней, 150–250 на кошелёк |
| Операции учебных кошельков | по 30 за 45 дней: 12 TOPUP, 9 WITHDRAW, 9 FEE |

Демо-кошельки `BASIC` за последние 30 дней засеяны так же, как пишет журнал
живой обработчик пополнения; более старые операции — целиком. История
учебных кошельков сходится со стартовым балансом 5 000,00 ₽.

## Тесты

Тесты лежат в `tests/`.

## Документация API

Спецификация — **рукописный** `spec/openapi.yaml`, первичный по отношению
к коду. Автогенерация выключена на уровне фреймворка: приложение создано
как `FastAPI(openapi_url=None, docs_url=None)`, поэтому `/openapi.json`
отдаёт 404, а `/docs` — статичный Swagger UI, который читает файл. Это
однострочная проверяемая гарантия: получить документацию из кода технически
невозможно.

Обновить статику Swagger UI: `tools/fetch_swagger_ui.sh [версия]`.

## Эндпоинты

| Метод | Путь | Что делает |
|---|---|---|
| `POST` | `/api/auth/login` | вход, непрозрачный токен на 7 суток |
| `GET` | `/api/wallet/balance` | баланс своего кошелька |
| `POST` | `/api/wallet/topup` | пополнение |
| `POST` | `/api/wallet/withdraw` | списание с комиссией 1,5 %, минимум 10 ₽ |
| `GET` | `/api/wallet/operations` | своя история, `limit` / `offset` / `type` |
| `GET` | `/api/wallet/cashback` | оборот текущего месяца, ставка и начисление |
| `GET` | `/api/wallets/{id}/operations` | чужой кошелёк: 403, свой — 200, нет — 404 |
| `GET` | `/api/sql/schema` | панель схемы SQL-консоли |
| `POST` | `/api/sql/query` | выполнить `SELECT` только на чтение |
| `POST` | `/api/assistant/message` | ассистент (модель не подключена) |
| `GET` | `/docs`, `/openapi.yaml` | документация |
| `GET` | `/api/health` | версия и сборка |

## SQL-консоль: read-only в четыре слоя

1. роль `qa_student` — `GRANT USAGE ON SCHEMA public` и
   `GRANT SELECT ON public.wallets, public.operations`, больше ничего;
2. каждый запрос — в транзакции `BEGIN READ ONLY`;
3. разбор запроса: только `SELECT` и `WITH`, одна инструкция (одна
   завершающая `;` допускается, любая внутри — отказ);
4. `statement_timeout = 5s` и потолок 300 строк с подписью «показаны первые
   300 строк».

Панель схемы читает `information_schema` под той же ролью, поэтому показывает
ровно две таблицы: схемы `auth` роль не видит. Ответ `POST /api/sql/query`
содержит готовое поле `markdown` — на нём держится кнопка «скопировать
результат как markdown-таблицу».

## Структура

```
CASHBACK.md                 правила кэшбэка, первичны по отношению к коду
spec/openapi.yaml           рукописный контракт API, первичен по отношению к коду
migrations/                 alembic: схема 2.2 дословно + роль qa_student
tools/seed_demo.py          фоновые данные, зерно 20260901
tools/fetch_swagger_ui.sh   обновление статики Swagger UI
wallet/main.py              сборка приложения, /docs, /openapi.yaml
wallet/routers/             обработчики: auth, wallet, wallets, sql, assistant
wallet/service.py           операции над кошельком: журнал, баланс, проекция
wallet/projection.py        проекция OperationView: история для всех клиентов
wallet/sql_console.py       разбор, права, тайм-аут, потолок строк, markdown
wallet/assistant_tools.py   инструменты ассистента
wallet/auth.py              токены и пароли
wallet/money.py             Decimal, комиссия 1,5 % с порогом 10 ₽
wallet/cashback.py          кэшбэк за месяц: оборот, ставка, начисление
static/docs/                статика Swagger UI
tests/                      contract_test.py
```

## Развёртывание: короткий чек-лист

1. Поднять Postgres 16 и выдать пользователю приложения право `CREATEROLE`
   (миграция создаёт роль `qa_student`).
2. Задать окружение по `.env.example`; пароли — не из примера.
3. `alembic upgrade head`.
4. `python -m tools.seed_demo --cohort-size <число кошельков>` — **один раз**.
   Забрать `cohort-credentials.csv`, разослать письмами, файл удалить
   с сервера.
5. Проверить `/api/health`, `/docs`, вход одним учебным аккаунтом и
   `SELECT * FROM wallets LIMIT 5;` в консоли.
6. Бэкенд один и для сборки 1.4.0, и для регрессионной 1.5.0.
