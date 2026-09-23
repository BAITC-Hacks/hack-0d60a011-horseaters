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

Проверьте соединение (только `SELECT 1`, без изменения схемы), затем запустите API:

```powershell
.\.venv\Scripts\python -m backend.infrastructure.persistence.check_connection
.\.venv\Scripts\python -m uvicorn backend.infrastructure.api.main:app --reload
```

Успешная проверка выводит `PostgreSQL: соединение установлено (SELECT 1).`.
FastAPI также выполняет `SELECT 1` при старте. Если соединение не установлено,
запуск завершается понятным сообщением без URL и пароля. Проверьте сервер,
порт, имя базы и учетные данные. Сессии закрываются после commit/rollback,
пул освобождается при остановке или ошибке запуска. Таблицы и миграции не создаются,
`create_all()` не вызывается.

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
