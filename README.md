# hack-0d60a011-horseaters
Hackathon team repository for horseaters

## Подключение PostgreSQL

Требуются Python 3.10+ и запущенный PostgreSQL с уже созданной пустой базой
`hackalem`. Из корня проекта (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

В `.env` замените `user` и `password` своими учетными данными:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/hackalem
```

Специальные символы пароля URL-кодируйте (`@` → `%40`, `#` → `%23`).
`DATABASE_URL` обязателен; переменная окружения имеет приоритет над `.env`.
Поддерживается драйвер `psycopg`, он устанавливается из `requirements.txt`.
SQLite по умолчанию не используется. `.env` исключен из Git.

Проверьте соединение (только `SELECT 1`, без изменения схемы). Перед запуском API
примените миграции по инструкции ниже:

```powershell
.\.venv\Scripts\python -m backend.infrastructure.persistence.check_connection
.\.venv\Scripts\python -m uvicorn backend.infrastructure.api.main:app --reload
```

Успешная проверка выводит `PostgreSQL: соединение установлено (SELECT 1).`.
FastAPI также выполняет `SELECT 1` при старте. Если соединение не установлено,
запуск завершается понятным сообщением без URL и пароля. Проверьте сервер,
порт, имя базы и учетные данные. Сессии закрываются после commit/rollback,
пул освобождается при остановке или ошибке запуска. При старте API схема не меняется,
`create_all()` не вызывается. Таблицы создаются отдельной командой Alembic.

## Миграции базы данных

После установки зависимостей и настройки `.env` примените миграции перед запуском API:

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m alembic current
.\.venv\Scripts\python -m alembic check
```

Команды выполняются из корня проекта и используют тот же `DATABASE_URL`, что и API.
URL не записывается в `alembic.ini`. Начальная миграция `0001` создаёт 24 таблицы
текущих ORM-моделей; Alembic также ведёт служебную таблицу `alembic_version`.
Она предназначена для пустой базы, без предварительного `create_all()`.
Для просмотра SQL без подключения: `python -m alembic upgrade head --sql`
(настройка `DATABASE_URL` всё равно нужна).

Тест полного цикла миграций использует отдельный `MIGRATION_TEST_DATABASE_URL`,
никогда не берёт URL приложения и пропускается, если переменная не задана.
Создайте **новую пустую тестовую базу** с именем `hackalem_migration_test_<суффикс>`:

```powershell
createdb -h localhost -U user hackalem_migration_test_local
$env:MIGRATION_TEST_DATABASE_URL = 'postgresql+psycopg://user:password@localhost:5432/hackalem_migration_test_local'
.\.venv\Scripts\python -m unittest discover -s tests -p test_migrations_postgresql.py -v
Remove-Item Env:MIGRATION_TEST_DATABASE_URL
```

Замените учётные данные примера своими. Тест проверяет пустоту базы, выполняет
`upgrade head → downgrade base → upgrade head`, сверяет схему и проверяет оба
частичных UNIQUE-индекса на данных. Откат удаляет таблицы миграции; не используйте
рабочую или чужую базу. После теста база остаётся на `head`, поэтому для следующего
запуска нужна новая пустая тестовая база.

Миграция сохраняет текущие отличия ORM от `docs/database.md`: `reason` в
`recommendation_adjustments` — `VARCHAR(2000)` вместо `TEXT`; составные индексы
`calculation_runs(status, started_at)` и `purchase_orders(supplier_id, status, created_at)`
не задают `DESC`; значения по умолчанию для `detected_anomalies.details`,
`demand_forecasts.details`, `demand_forecasts.return_adjustment` и `recommendations.version`
задаются Python, а не сервером БД. Для FK `recommendations.product_id`, `warehouse_id`
и `supplier_id` нет индексов, начинающихся с этих колонок. ORM в рамках DB-03 не менялись.

## Тесты

Тесты без PostgreSQL (SQLite используется только во временных тестах транзакций):

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Для проверки реального PostgreSQL задайте URL уже созданной отдельной тестовой базы:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://user:password@localhost:5432/hackalem_test'
.\.venv\Scripts\python -m unittest discover -s tests -p test_postgres_integration.py -v
Remove-Item Env:TEST_DATABASE_URL
```

Без `TEST_DATABASE_URL` интеграционный тест пропускается; URL приложения он не
использует. Проверяются `SELECT 1` и восстановление после ошибки SQL без изменения
таблиц и данных. Заданный, но недоступный тестовый сервер приводит к ошибке теста.
