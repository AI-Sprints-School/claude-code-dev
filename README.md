# «Кошелёк» — рабочий репозиторий курса

Это тот код, в котором вы будете работать все шестнадцать уроков. Форкните
репозиторий к себе, дальше все задания, PR и капстоун живут в вашем форке.

«Кошелёк» — личный счёт: баланс, пополнение, списание с комиссией, история
операций. Сердце продукта — бэкенд (`app/backend/`): FastAPI, Postgres,
REST API со Swagger UI. **Для заданий курса нужен только он.** Вокруг него
есть ещё несколько поверхностей — веб-клиент (`app/web/`), SQL-консоль
только на чтение, окно ассистента, Android-клиент (в этот репозиторий не
входит), — но задания их не трогают: если вы пришли сюда учиться, а не
осматривать продукт целиком, дальше первого раздела про бэкенд можно не
ходить.

GitHub не переносит issue при форке, поэтому они хранятся файлом.

## Что где лежит

```
app/backend/     FastAPI + Postgres 16: API, SQL-консоль, Swagger, миграции, сид
app/web/         статика без сборщиков и npm: HTML, CSS, обычный JavaScript
CONTRIBUTING.md  как в этом проекте принято вести ветки, коммиты и PR
```

Подробности по каждой части — в `app/backend/README.md` и `app/web/README.md`.

## Что нужно на машине

- Python 3.9 или новее — этого хватает и для заданий курса, и для
  веб-клиента: у последнего нет ни npm, ни Node, ни зависимостей, только
  стандартная библиотека;
- Python 3.12 и Postgres 16 — если вы решите поднимать продукт целиком
  локально, без Docker.

Docker для заданий курса не нужен. Он пригодится только чтобы поднять
продукт целиком — см. раздел ниже.

## Тесты

Быстрый путь, без базы и без Docker. Тесты кэшбэка считают по списку
операций в памяти, поэтому им нужны только два пакета:

```bash
cd app/backend
pip install pytest python-dotenv
python3 -m pytest tests/cashback_test.py -q
```

Ожидаемый результат — `8 passed`.

Полный набор (`python3 -m pytest -q`) запускать этими двумя пакетами
нельзя: он падает на сборе с `ModuleNotFoundError: No module named
'sqlalchemy'` — контрактные тесты API импортируют SQLAlchemy ещё до того,
как решится вопрос о базе. Чтобы весь набор хотя бы собрался, поставьте
зависимости целиком:

```bash
pip install -r requirements.txt
python3 -m pytest -q          # 8 passed, 39 skipped
```

39 пропущенных — это контрактные тесты API. Они **разрушительные**:
`tests/conftest.py` пересоздаёт схему и засевает небольшой набор демо-аккаунтов. Без
явного флага `WALLET_ALLOW_DESTRUCTIVE_TESTS=1` и отдельной базы они
штатно пропускаются, и это не поломка. Как их всё-таки прогнать —
в разделе про полный запуск продукта.

У веб-клиента автотестов нет: он проверяется руками в браузере.

## Если хотите поднять продукт целиком

Дальше — необязательная часть: задания курса без неё обходятся.

### Бэкенд и база

```bash
cd app/backend
docker compose up -d --build
docker compose exec api python -m tools.seed_demo --cohort-size 20
```

После этого работают:

| Что | Адрес |
|---|---|
| API | http://localhost:8000/api/… |
| Swagger UI | http://localhost:8000/docs |
| Файл спецификации | http://localhost:8000/openapi.yaml |
| Проверка живости | http://localhost:8000/api/health |
| Postgres 16 | `localhost:5433`, база `wallet`, пользователь `wallet` |

Логины и пароли сид кладёт в `data/cohort-credentials.csv` внутри контейнера:

```bash
docker compose exec api cat /app/data/cohort-credentials.csv
```

Вход в продукт — логином вида `student-01` и паролем из этого файла.
Регистрации в продукте нет.

Если Docker не подходит, в `app/backend/README.md` есть раздел
«Запуск без Docker»: Postgres 16, `pip install -r requirements.txt`,
`.env` по образцу `.env.example`, `alembic upgrade head`, сид и `uvicorn`.

### Веб-клиент

Бэкенд к этому моменту должен быть поднят.

```bash
cd app/web
python3 build.py     # соберёт dist/ и dist/next/
python3 serve.py     # http://localhost:5173/
```

`serve.py` отдаёт статику и проксирует `/api` в бэкенд, поэтому запросы
в DevTools остаются same-origin. Адрес бэкенда задаётся переменной
`WALLET_BACKEND` (по умолчанию `http://127.0.0.1:8000`), порт — `WALLET_PORT`.

Собираются сразу две версии продукта: `http://localhost:5173/` — сборка
1.4.0 (140), `http://localhost:5173/next/` — сборка 1.5.0 (150). Обе ходят
в один и тот же бэкенд и в одну базу. Версия видна в подвале каждой
страницы.

`dist/` — продукт сборки, а не исходник: он закрыт в `.gitignore`
и пересобирается из `src/` одной командой.

### Контрактные тесты API

Им нужна поднятая база — и обязательно отдельная, не та, в которой лежат
ваши данные. Создаётся один раз:

```bash
cd app/backend
docker compose exec db psql -U wallet -d postgres \
  -c "CREATE DATABASE wallet_test OWNER wallet"
```

Дальше прогон:

```bash
docker compose exec \
  -e DATABASE_URL=postgresql+psycopg2://wallet:wallet@db:5432/wallet_test \
  -e READONLY_DATABASE_URL=postgresql+psycopg2://qa_student:qa_student@db:5432/wallet_test \
  -e OPERATION_VIEW_PATH=/tmp/test_operation_view.jsonl \
  -e CREDENTIALS_OUT=/tmp/test-credentials.csv \
  -e WALLET_ALLOW_DESTRUCTIVE_TESTS=1 \
  api python -m pytest -q
```

Без Docker — то же самое переменными окружения своей оболочки, как написано
в шапке `tests/conftest.py`:

```bash
WALLET_ALLOW_DESTRUCTIVE_TESTS=1 \
DATABASE_URL=postgresql+psycopg2://wallet:wallet@localhost:5432/wallet_test \
pytest
```

## Переменные окружения

Полный список с комментариями — `app/backend/.env.example`. Секретов в коде
нет: строки подключения, пароль роли SQL-консоли и ключ модели ассистента
приходят только окружением. Ключа модели у вас, скорее всего, не будет —
тогда ассистент штатно отвечает «временно недоступен», и это не поломка.

Файлы, которых нет в git, но без которых копия репозитория не работает,
перечислены в `.worktreeinclude` — это нужно, когда вы разводите работу
по нескольким рабочим деревьям.
