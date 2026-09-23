# Frontend Agent Contract

This file is the source of truth for AI agents and developers changing the frontend in `frontend/`. Product and database requirements remain documented in `AGENT.md` when present and `docs/database.md`.

## Project Vision & Stack

Stockwise is a procurement workspace for reviewing replenishment recommendations, correcting quantities, approving orders, and exporting data for 1C. The primary user is a procurement manager.

## Authentication and authorization (backend contract)

- Employees sign in with `POST /api/auth/login` (`username`, `password`) and receive a short-lived bearer JWT (`access_token`, `token_type`, `expires_in`). Send `Authorization: Bearer <token>` on business API requests, including legacy `/api/v1/procurement` and `/api/v1/ai` routes. Do not infer identity from an arbitrary user-ID header or hard-code tokens in the frontend.
- `GET /api/auth/me` returns `id`, `username`, `display_name`, `role`. Roles are `buyer` and `admin` for newly provisioned accounts. A buyer prepares, adjusts, accepts, creates and exports; an admin reviews and approves orders via `POST /api/orders/{order_id}/approve` but cannot perform buyer-only mutations.
- Admins provision buyers through `POST /api/auth/users`; there is no public signup or password-change endpoint. On 401, clear the session and ask the user to log in; on 403, show insufficient permissions. Keep tokens out of query strings, logs and durable browser storage.
- The XLSX download is available only after approval. `docs/excel-order-export.md` documents the MVP's own 1C import template; it is not a promise of automatic compatibility with every 1C configuration.

- Next.js App Router and React Server Components at route boundaries.
- TypeScript in strict mode.
- Tailwind CSS with semantic theme tokens.
- TanStack Query v5 for server state.
- Zustand v5 for session-only UI state.
- React Hook Form with Zod resolvers for all user input.
- FastAPI is the backend contract owner.

## Feature-Sliced Design Rules

Application modules live in `frontend/src`. Next.js routing stays in `frontend/app`.

Dependency direction is strictly top to bottom:

1. `app`
2. `pages-flat`
3. `widgets`
4. `features`
5. `entities`
6. `shared`

Rules:

- Slices on the same layer are isolated. A feature must not import another feature; a widget must not import another widget.
- A slice is imported only through its public `index.ts` API.
- Internal imports inside one slice may be relative.
- Standard slice segments are `ui/`, `model/`, `api/`, and `lib/`.
- Pages compose widgets and features. Widgets compose features, entities, and shared modules. Features compose entities and shared modules.
- `frontend/app/**/page.tsx` contains routing, server prefetch, hydration boundaries, and page composition only.
- Keep the existing ESLint FSD boundary rule passing.

## Data Fetching & Server Prefetching

- Do not fetch server data in `useEffect`.
- Define query keys and reusable `queryOptions` in `entities/**/api`.
- Create a request-scoped `QueryClient` in `app/**/page.tsx`, call `prefetchQuery`, and pass `dehydrate(queryClient)` to `HydrationBoundary`.
- Read hydrated data with `useQuery` in `pages-flat/**` or a lower client boundary.
- Mutations belong to the feature that performs the user action. Invalidate or update the relevant entity query keys on success.
- Do not duplicate TanStack Query data in Zustand. Zustand stores selections, modal state, drafts, and other session UI state only.
- Parse API responses with Zod and expose explicit errors for network, HTTP, and contract failures.

## Design System & Theme Standards

- Use semantic classes backed by CSS variables in `src/app/styles/globals.css`: `bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `border-border`, `bg-input`, and `bg-primary`.
- Dark is the default visual direction: deep neutral backgrounds, subtle borders, restrained neon accents, and high contrast typography.
- Light mode uses a soft slate canvas, white cards, slate borders, and slate text.
- Do not add component-specific CSS files. Global tokens and base behavior belong in `globals.css`; component styling stays in Tailwind classes.
- Primary surfaces use `rounded-2xl` or `rounded-3xl`. Controls use `rounded-xl` or `rounded-full`.
- KPI cards use a large value, a short muted caption, a compact delta badge, and a circular action button.
- Status badges are compact pills: emerald for normal/success, amber for warning/planned, red for critical/error, blue for informational, and violet for adjusted/secondary states.
- Tables use semantic card and border tokens, quiet row separators, a subtle hover state, and compact uppercase headers.
- Prefer the shared `Button`, `Input`, `Card`, `Badge`, and table primitives over local substitutes.
- Hex colors are allowed only in the global token definitions or for a documented one-off data visualization palette that cannot be represented by a semantic token.

## Form & Validation Patterns

- Every form uses React Hook Form with `zodResolver`.
- User input is validated by a strict Zod schema before submission.
- Schemas live in the owning feature or entity under `model/schema.ts` or `model/schemas.ts`.
- Show field-level errors and a form-level mutation error. Handle pending, success, and failure states explicitly.
- Number inputs must define valid bounds and use `valueAsNumber`.

## Agent Operating Contract

Do:

- Read this file and the nearest relevant documentation before editing.
- Preserve the FSD dependency direction and public APIs.
- Keep server state in TanStack Query and transient UI state in Zustand.
- Use semantic theme tokens and verify both themes.
- Run `npm run typecheck`, `npm run lint`, and `npm run build` after meaningful frontend changes.
- Handle loading, empty, error, disabled, and success states.

Do not:

- Add Redux.
- Add custom CSS files outside `globals.css`.
- Hardcode component colors without theme support.
- Import another slice from the same FSD layer.
- Deep-import another slice's internal files.
- Fetch API data in `useEffect`.
- Leave TODO placeholders, silent catch branches, or unhandled errors.
- Put interactive business UI into `frontend/app` route files.
# AGENT.md — Инструкция для AI-агентов и разработчиков

## 🎯 Контекст и цель проекта
Проект представляет собой **интеллектуальную систему автоматического расчета потребности в пополнении склада и формирования заказов поставщикам** для дистрибьюторской компании (на примере данных ИЭК).

* **Текущая дата симуляции:** Сентябрь 2026 года.
* **Бизнес-проблема:** Менеджер отдела закупа рассчитывает потребность вручную в Excel. Это приводит к избыточным запасам, дефициту и упущенным продажам. Разовые крупные сделки (тендеры, крупные отгрузки одному клиенту) искажают регулярную потребность.
* **Цель сервиса:** Автоматизировать расчет регулярного спроса с учетом сезонности, устойчивого роста спроса, очистки от аномалий, компенсации дефицита (`stockout`), категорий, складов, остатков, товаров в пути, материальной потребности и условий поставщиков, а также предоставить удобный дашборд для закупщика с возможностью ручной корректировки, обязательного подтверждения и выгрузки заказов.
* **Основной пользователь:** Менеджер отдела закупа.
* **Ключевой сценарий:** Пользователь запускает расчет по складу и/или категории, получает сгруппированный по поставщикам список рекомендаций с объяснением и срочностью, при необходимости корректирует количество, утверждает заказ и экспортирует его в формат, совместимый с 1С.
* **Технологический стек:** 
  * **Backend / Аналитика:** Python (FastAPI, Pandas, NumPy, Openpyxl).
  * **Frontend:** Next.js (или Streamlit для быстрого MVP).

---

## 📂 Структура входных данных
В рабочей директории проекта находятся следующие файлы партнера:

1. **`Динамика продаж_2025-2026.xlsx`** — транзакционная история продаж (дата, номер документа, код товара, номенклатура, склад, количество, цена и обезличенный идентификатор клиента при наличии в выгрузке). Используется для поиска аномалий, разовых крупных отгрузок и концентрации необычного объема у одного клиента.
2. **`Ежемесячные продажи в количественном выражении за последние 2 года.xlsx`** — агрегированные исторические продажи по месяцам (2024–2026 гг.).
3. **`Ежемесячные остатки продукции за последние 2 года ИЭК.xlsx`** — остатки на конец каждого месяца. Требуются для выявления периодов дефицита (`stockout`).
4. **`Путь ИЭК 22.09.2026.xlsx`** — товары в пути (открытые заказы с датами поступления, актуально на сентябрь 2026).
5. **`Сезонность ИЭК.xlsx`** — коэффициенты и индексы сезонности по месяцам.
6. **`MOQ ИЭК.xlsx`** — минимальные партии, разрешенные к отгрузке, и справочник поставщиков.

Дополнительно архитектура должна поддерживать загрузку следующих источников, даже если они будут предоставлены позднее или заменены синтетическими данными:

7. **Материальная ведомость из 1С** — дополнительная плановая потребность по артикулам, складам и датам.
8. **Явные периоды stockout** — интервалы отсутствия товара по артикулу и складу. Если источник отсутствует, периоды допускается выводить из истории остатков.
9. **Условия поставщиков** — срок поставки (`lead time`), кратность упаковки, MOQ, закупочная цена и приоритетный поставщик.

При импорте каждого файла необходимо сохранять метаданные загрузки: имя файла, тип источника, контрольную сумму, дату загрузки, число строк и статус обработки. Ошибки структуры входного файла должны быть понятны пользователю и не должны приводить к частичной незаметной загрузке.

### Приватность входных данных

* В системе разрешено хранить только обезличенный идентификатор клиента.
* Запрещено загружать или сохранять ФИО, телефоны, email и другие прямые идентификаторы клиентов.
* Исходные транзакции не изменяются и не удаляются при очистке выбросов: результат интерпретации хранится отдельно и относится к конкретному запуску расчета.
* Для разработки и автоматических тестов допускаются синтетические данные с реалистичным распределением.

---

## 🧮 Методология и алгоритмы расчета (Python / Pandas)

Бэкенд-модуль аналитики должен последовательно выполнять следующие шаги для каждого артикула:

### 1. Фильтрация выбросов (Исключение разовых крупных заказов)
* **Проблема:** Разовые крупные продажи завышают регулярный спрос.
* **Алгоритм (Pandas):** Группировка транзакций минимум по артикулу и складу, расчет межквартильного размаха ($IQR = Q_3 - Q_1$). Всё, что превышает порог $Q_3 + 1.5 \times IQR$, помечается как аномалия и заменяется медианным значением только при расчете базовой потребности.
* При наличии обезличенного клиента дополнительно проверяется необычная концентрация объема по сочетанию `артикул + клиент`, чтобы крупная разовая продажа одному клиенту не увеличивала регулярный прогноз.
* Для каждой найденной аномалии сохраняются исходное количество, примененный порог, замещающее значение, метод и текстовая причина. Исходная продажа остается неизменной.

### 2. Компенсация упущенного спроса (`Stockout Adjustment`)
* **Проблема:** Если товар отсутствовал на складе, фактические продажи равны нулю, но спрос со стороны клиентов был.
* **Алгоритм:** Сначала используются явно переданные периоды stockout. Если они отсутствуют, периоды дефицита определяются на основе истории остатков по сочетанию `артикул + склад`. В эти периоды продажи корректируются в большую сторону пропорционально устойчивому уровню потребления соседних доступных периодов.
* Метод, размер корректировки и источник периода (`imported`, `inferred`, `manual`) должны сохраняться для объяснения результата.

### 3. Учет устойчивого роста спроса

* Рост рассчитывается по очищенному и скорректированному спросу, а не по сырым продажам.
* Кратковременный всплеск не считается устойчивым ростом. Используется конфигурируемое окно наблюдения и минимальное число периодов.
* Допускается импортированный или вручную заданный прогноз прироста по SKU, категории и/или складу.
* Использованный коэффициент роста и его источник (`calculated`, `imported`, `manual`) сохраняются в деталях расчета.

### 4. Прогнозирование с учетом сезонности
* **Формула:**
  $$\text{Forecast} = \text{Cleaned Baseline Demand} \times \text{Growth Factor} \times \text{Seasonality Index}$$
* Индексы сезонности извлекаются из файла `Сезонность ИЭК.xlsx`.
* Разрешается использовать коэффициент уровня SKU или категории. Коэффициент SKU имеет приоритет над коэффициентом категории.

### 5. Расчет рекомендуемого заказа поставщику
* **Формула:**
  $$\text{Required Order} = \max\left(0, \; \text{Demand During Horizon} + \text{Safety Stock} + \text{Material Requirements} - (\text{Current Stock} + \text{In Transit})\right)$$
* Горизонт должен учитывать выбранный пользователем период и срок поставки конкретного поставщика.
* Полученный объем округляется вверх с учетом **MOQ** и кратности упаковки конкретного поставщика.
* Если товар доступен у нескольких поставщиков, правило выбора должно быть явным и воспроизводимым: приоритетный поставщик, срок поставки, цена и доступные условия.

### 6. Риск дефицита и срочность

* Для каждой рекомендации рассчитываются `risk_score` и уровень срочности: `low`, `medium`, `high`, `critical`.
* При расчете риска учитываются прогноз спроса, доступный остаток, ожидаемые поступления, срок поставки и ожидаемая дата исчерпания запаса.
* Формула и пороги риска должны быть конфигурируемыми и сохраняться вместе с версией алгоритма.

### 7. Объяснимость и воспроизводимость

Каждая рекомендация должна содержать как минимум: базовый спрос, размер очистки аномалий, компенсацию stockout, коэффициент роста, коэффициент сезонности, прогноз, страховой запас, текущий остаток, товары в пути, материальную потребность, количество до округления, MOQ/кратность, итоговое количество, риск и текстовое объяснение. Повторный просмотр завершенного запуска не должен пересчитывать результат на новых данных.

---

## 🚀 Архитектура и задачи для реализации

### Backend & Analytics (Python / FastAPI)
* **Загрузка и парсинг:** Чтение всех исходных Excel-файлов с помощью `pandas.read_excel()`.
* **Модули аналитики (`/services`):**
  * `anomaly.py` — фильтрация крупных разовых сделок.
  * `stockout.py` — компенсация упущенного спроса по остаткам.
  * `growth.py` — определение устойчивого роста и применение прогноза прироста.
  * `forecasting.py` — расчет прогноза с учетом сезонных коэффициентов.
  * `replenishment.py` — итоговый расчет заказов с учетом путей (`Путь ИЭК`) и MOQ.
  * `risk.py` — оценка риска дефицита и срочности.
* **API Endpoints (FastAPI):**
  * `POST /api/imports` — загрузка и валидация источника данных.
  * `POST /api/calculation-runs` — запуск расчета по складу, категории и горизонту.
  * `GET /api/calculation-runs/{id}` — состояние и параметры запуска.
  * `GET /api/calculation-runs/{id}/demand-trends` — сохраненные помесячные ряды спроса, агрегированные по категории.
  * `GET /api/calculation-runs/{id}/recommendations` — список рекомендаций с фильтрами по поставщикам, категориям, складам и риску.
  * `GET /api/recommendations/{id}/explain` — детальное обоснование расчета по конкретной позиции.
  * `PATCH /api/recommendations/{id}` — ручная корректировка количества с обязательным сохранением причины и автора.
  * `POST /api/recommendations/{id}/accept` — явное принятие положительной рекомендации с проверкой версии.
  * `POST /api/orders` — создание черновиков заказов, сгруппированных по поставщикам.
  * `POST /api/orders/{id}/approve` — явное утверждение заказа ответственным сотрудником.
  * `POST /api/orders/{id}/export` — создание XLSX только для утвержденного заказа.
  * `GET /api/orders/{id}/export` — повторное скачивание готового XLSX без изменения статуса.

### Правила трехслойной DDD-архитектуры

* **`domain`** — обычные Python-классы, сущности, value objects, интерфейсы репозиториев и чистые бизнес-правила. Слой не импортирует FastAPI, Pydantic, Pandas, Openpyxl, ORM и код инфраструктуры.
* **`application`** — use cases и внутренние DTO. Оркестрирует доменные объекты через интерфейсы репозиториев, но не читает Excel и не выполняет SQL напрямую.
* **`infrastructure`** — FastAPI/Pydantic-схемы, Excel-адаптеры, ORM-модели, миграции и реализации доменных репозиториев.
* Направление зависимостей: `infrastructure -> application -> domain`. Домен не зависит от внешних слоев.
* Pydantic request/response schemas хранятся в `infrastructure/api/schemas`, внутренние DTO use cases — в `application/dto`, а доменные сущности остаются обычными Python-классами.

### Текущий application pipeline (APP-01—APP-05)

* `ImportData` использует существующий атомарный Excel-импорт; ошибки валидации возвращаются через HTTP 422 и сохраняются в `import_batches.error_details.validation_errors`.
* `RunCalculation` фиксирует ID всех завершенных импортов на момент старта. Результаты (аномалии, прогнозы, рекомендации) сохраняются одной транзакцией; при ошибке запуск переводится в `failed`.
* Версия `mvp-2`: 12 помесячных периодов истории (текущий неполный месяц включен только для транзакций), прогноз на 30 дней, страховой запас на 7 дней. Конфигурации подготовки спроса и порогов риска сохраняются в параметрах запуска.
* Рабочий расчет вызывает доменную подготовку спроса: обрабатывает возвраты, отдельные транзакционные и клиентские выбросы, явные stockout и выводимые из повторных нулевых остатков периоды дефицита. Исходные продажи не изменяются.
* Устойчивый рост оценивается по очищенным полным месяцам либо берется из применимого допущения: SKU > категория, конкретный склад > все склады, ручное > импортированное, затем актуальная дата. Неоднозначные равноприоритетные допущения приводят к ошибке запуска.
* Поставщик выбирается воспроизводимо: основной, приоритет, срок поставки, цена, ID. MOQ и кратность упаковки учитываются при округлении. Неизвестные договорные ограничения (например, минимальная сумма заказа) нельзя предполагать без данных партнера.
* Для трендов по категориям backend сохраняет помесячные точки в прогнозе и отдает их отдельным read-only API; визуализация — задача frontend.
* Если у товара с рассчитанным спросом нет активных условий поставщика, запуск завершается `failed`, а не подставляет фиктивного поставщика.
* API чтения, корректировки, явного принятия, создания/утверждения и выгрузки заказа подключен. Аутентификация/identity provider извне пока не подключены; без доверенного `request.state.user` бизнес-API возвращает 403. `README.md` по просьбе пользователя не изменять.
* Импорт принимает клиентский ID только под явно обезличенным заголовком и отклоняет очевидные email/телефон/имя. Это не доказывает, что произвольный непрозрачный ID действительно был обезличен у источника; перед реальными данными требуется договор о псевдонимизации.
* Отправки поставщику нет. XLSX создается только после явного утверждения сотрудником; совместимость с конкретной конфигурацией 1С требует согласованного шаблона и проверки партнером.

### Основные доменные сущности

`Product`, `Category`, `Warehouse`, `Supplier`, `SupplierTerms`, `DemandForecast`, `Recommendation`, `CalculationRun`, `PurchaseOrder`, `PurchaseOrderItem`.

### Хранение данных

Основная СУБД — PostgreSQL. SQLite допускается только для упрощенного локального демо. Минимальная логическая схема:

Подробная модель таблиц, типов, связей, ограничений, индексов и транзакционных границ описана в [`docs/database.md`](docs/database.md). После появления миграций Alembic документ должен обновляться вместе с ними; исполняемым источником истины становятся миграции.

* Справочники: `categories`, `products`, `warehouses`, `suppliers`, `supplier_products`.
* Импорт: `import_batches`, `sales_transactions`, `monthly_sales`, `inventory_snapshots`, `stockout_periods`, `in_transit_items`, `seasonality_coefficients`, `growth_assumptions`, `material_requirements`.
* Расчет: `calculation_runs`, `calculation_run_imports`, `detected_anomalies`, `demand_forecasts`, `recommendations`.
* Пользовательские действия: `recommendation_adjustments`, `purchase_orders`, `purchase_order_items`, `order_exports`.

Требования к хранению:

* Каждый расчет создается как отдельный `calculation_run` с параметрами, версией алгоритма и ссылками на использованные импорты.
* Завершенные результаты не перезаписываются при последующих загрузках данных.
* Основные числовые компоненты рекомендации хранятся отдельными колонками для фильтрации; полный breakdown допускается хранить в `JSONB`.
* Ручная корректировка не заменяет исходную рекомендацию: история изменений сохраняется отдельно.
* Заказ проходит состояния `draft -> approved -> exported`. Переход к утверждению должен содержать автора и время.
* Автоматическая отправка заказа поставщику без подтверждения ответственного сотрудника запрещена.

### Frontend (Next.js / Streamlit)
* Таблица рекомендаций, сгруппированная по поставщикам и уровням риска дефицита.
* Модальное окно с подробным текстовым и формульным обоснованием по каждой позиции.
* Фильтры и запуск расчета по складу, категории, поставщику и горизонту планирования.
* Визуализация трендов спроса по SKU и категориям.
* Интерактивные поля для ручной корректировки количества с указанием причины и кнопка **«Утвердить заказ»** (автоматическая отправка поставщику заблокирована в целях безопасности).
* Кнопка экспорта отчета в Excel.

---

## 📋 Чек-лист готовности (Definition of Done)
1. Скрипты на Python успешно считывают все 6 файлов Excel.
2. Алгоритм корректно фильтрует аномалии и крупные разовые отгрузки, включая крупную продажу одному обезличенному клиенту.
3. Учтены сезонность, устойчивый рост, stockout, категории, склады, текущие остатки, товары в пути, материальная потребность, срок поставки, MOQ и кратность упаковки.
4. Изменение любого переданного источника, например количества в пути, воспроизводимо отражается на результате нового запуска.
5. Для каждой рекомендации рассчитаны риск дефицита и срочность.
6. Каждая строка итогового заказа сопровождается понятным текстовым и машинно-читаемым обоснованием.
7. Интерфейс позволяет запускать расчет, просматривать, фильтровать, корректировать и утверждать заказы с возможностью экспорта.
8. Все ручные корректировки и утверждения имеют автора, время и сохраняемую историю.
9. Ни один заказ нельзя автоматически отправить поставщику без явного подтверждения ответственного сотрудника.
10. В БД не сохраняются неанонимизированные данные клиентов.
11. Автоматические тесты подтверждают влияние каждого источника данных, сезонность, рост, компенсацию stockout и устойчивость к искусственно добавленному выбросу.
12. В репозитории присутствует подробный `README.md` с методологией, схемой данных, алгоритмом исключения выбросов и инструкцией запуска.
