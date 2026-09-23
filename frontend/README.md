# Stockwise frontend

Клиентская часть системы управления запасами и расчёта закупок. Next.js App Router, TypeScript, TanStack Query v5, Zustand v5, React Hook Form, Zod, Tailwind CSS и `next-themes`.

## Запуск

```bash
npm install
cp .env.example .env.local
npm run dev
```

Откройте `http://localhost:3000`. По умолчанию включён демо-режим: таблица, фильтры, inline-корректировка количества, редактирование параметров расчёта, выбор строк и CSV-выгрузка работают без бэкенда. Изменения демо-данных хранятся в памяти вкладки и сбрасываются при перезагрузке. Тёмная тема включена по умолчанию; переключатель в шапке сохраняет выбор пользователя.

Для FastAPI задайте `NEXT_PUBLIC_DEMO_MODE=false`, `NEXT_PUBLIC_API_URL` и `SERVER_API_URL` в `.env.local`. Бэкенд должен разрешить CORS для адреса фронтенда.

## Контракт FastAPI

- `GET /api/v1/inventory` → массив объектов `InventoryItem`.
- `PATCH /api/v1/inventory/{id}` → обновлённый объект `InventoryItem`.
- Тело PATCH: `minStock`, `demand30`, `leadDays`, `packSize`, `unitCost`.
- Ошибка: HTTP-статус и JSON `{ "detail": "Сообщение" }`.

`InventoryItem`: `id`, `sku`, `name`, `category`, `supplier`, `unit` (строки); `stock`, `minStock`, `demand30`, `leadDays`, `packSize` (целые числа); `unitCost` (число). Все количества неотрицательные, срок поставки и кратность заказа положительные.

Рекомендация: `ceil(max(0, minStock + demand30 / 30 × leadDays − stock) / packSize) × packSize`. Цена заказа считается как рекомендация × `unitCost`. Валюта интерфейса — ₽.

## Архитектура

`app/` содержит только маршрутизацию, серверный prefetch и корневой layout. Модули находятся в `src/`: `app → pages-flat → widgets → features → entities → shared`. ESLint проверяет направление зависимостей, изоляцию соседних слайсов и импорты через `index.ts`.

Проверки: `npm run typecheck`, `npm run lint`, `npm run build`.
