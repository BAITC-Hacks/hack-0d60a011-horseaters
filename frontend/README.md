# StockWise — клиент планирования закупок

Next.js App Router, TypeScript, TanStack Query v5, Zustand v5 и Tailwind CSS. Клиент обращается к FastAPI; локальные рекомендации, симуляция расчёта и экспорт файлов в браузере удалены.

## Запуск

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

`NEXT_PUBLIC_API_URL` — адрес FastAPI, доступный браузеру. `SERVER_API_URL` или `INTERNAL_API_URL` — адрес для серверного prefetch Next.js. Пути запросов задаются полностью: `/api/v1/...`, `/api/...`, `/health`. Для браузера FastAPI должен разрешать CORS для адреса фронтенда.

Через Docker Compose фронтенд открывается на `http://localhost:3000`, API — на `http://localhost:8000`.

## Работа с API

- Страница рекомендаций получает предварительный список из `GET /api/v1/procurement/recommendations`. Этот маршрут в текущем бэкенде отдаёт встроенный набор и не связан с импортом.
- Загрузка Excel использует `POST /api/imports` с `source_type` и `file`, показывает прогресс передачи и состояние пакета из `GET /api/imports/{id}`.
- Расчёт использует `POST /api/calculation-runs`, затем `GET /api/calculation-runs/{id}` и `GET /api/calculation-runs/{id}/recommendations`.
- Правка результата расчёта отправляет `PATCH /api/recommendations/{id}` с версией записи и причиной. Формирование, утверждение и XLSX-экспорт заказа выполняются через `/api/orders`.
- AI-панели обращаются к `/api/v1/ai/sku-analysis`, `/api/v1/ai/supplier-summary`, `/api/v1/ai/supplier-letter`. Ответ `is_fallback` означает серверный шаблон при недоступности модели.
- Шапка проверяет `/api/v1/health` и `/health/db` отдельно.

Ошибки сети и FastAPI показываются пользователю с повтором запроса. Серверный кэш хранится в TanStack Query; Zustand содержит только состояние интерфейса и ID текущего расчёта.

## Ограничения бэкенда 0.1.0

Защищённые бизнес-маршруты сейчас возвращают 403 без доверенной авторизации пользователя. В API также отсутствует принятие рекомендаций перед созданием заказа, поэтому полный сценарий от импорта до экспорта пока не может завершиться. Таблица результатов расчёта содержит UUID без названий и цен, так как таких полей нет в ответе. Подробный аудит и предлагаемые OpenAPI-контракты находятся в `../docs/BACKEND_GAPS.md`.

## Архитектура и проверки

`app/` содержит только маршруты и серверный prefetch; код продукта расположен в `src/` по FSD: `app → pages-flat → widgets → features → entities → shared`. Слайсы экспортируют публичный API через `index.ts`.

```bash
npm run typecheck
npm run lint
npm run build
```
