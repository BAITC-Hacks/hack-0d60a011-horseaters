# Расхождения фронтенда и HTTP API

Аудит выполнен по исходному коду FastAPI на 23.09.2026: `backend/infrastructure/api/main.py`, подключённым роутерам, `schemas/workflows.py`, `infrastructure/ai/schemas.py` и application use cases. Контракты в разделе «Предлагаемый API» **не реализованы**; их нельзя считать частью текущего `/openapi.json`. Документ описывает изменения, необходимые для отказа от моков и полноценного сценария закупки.

## Что реализовано сейчас

- `GET /health` — доступность процесса; `GET /health/db` — проверка соединения с БД; `GET /api/v1/health` — liveness. Все три открыты без авторизации.
- `POST /api/imports` — `multipart/form-data` с полями `source_type` и `file` (`.xlsx`, до 25 МиБ); `GET /api/imports/{batch_id}` — статус и безопасные сведения об ошибках. Типы источника: `sales`, `monthly_sales`, `inventory`, `stockout`, `in_transit`, `seasonality`, `supplier_terms`, `growth`, `material_requirements`.
- `POST /api/calculation-runs` — тело `RunCalculationRequest { demand_source: "transactions" | "monthly_sales", horizon_days: integer > 0, warehouse_id?: UUID | null, category_id?: UUID | null }`; `GET /api/calculation-runs/{run_id}`; `GET /api/calculation-runs/{run_id}/recommendations` с `supplier_id`, `warehouse_id`, `category_id`, `urgency`, `status`, сортировкой и пагинацией. Ответ списка — `{ items: RecommendationResponse[], total, limit, offset }`.
- `GET /api/recommendations/{recommendation_id}/explain` — сохранённые компоненты формулы, прогноз и аномалии **конкретной** рекомендации; `PATCH /api/recommendations/{recommendation_id}` — `{ new_quantity: decimal, reason: string, version: integer }`, ответ с новой версией. Decimal в JSON представлен десятичной строкой.
- `POST /api/orders` — `{ calculation_run_id: UUID }`, создаёт черновики из **всех** принятых рекомендаций запуска, сгруппированных по поставщику и складу; `GET /api/orders/{order_id}`; `POST /api/orders/{order_id}/approve`; `POST /api/orders/{order_id}/export` — формирует XLSX и возвращает метаданные; `GET /api/orders/{order_id}/export` — скачивает готовый XLSX как Blob.
- `POST /api/v1/ai/sku-analysis`, `POST /api/v1/ai/supplier-summary`, `POST /api/v1/ai/supplier-letter` — существуют. Последний URL именно `/supplier-letter`. Ответы допускают `is_fallback: true`, то есть локальный шаблон вместо модели.
- `GET /api/v1/procurement/recommendations`, `GET /api/v1/procurement/recommendations/{item_id}`, `PATCH /api/v1/procurement/recommendations/{item_id}` существуют, но читают встроенный `INITIAL_RECOMMENDATIONS` и правят `_recommendations_store` **в памяти процесса**. Это демонстрационная ветка, не источник результатов импортов и расчётов. У списка нет объявленных query-фильтров `supplier`, `urgency`, `search`; у правок нет версии, автора, сохраняемой истории и связи с заказом. Её данные исчезают при рестарте и могут различаться между workers.

### Сквозные ограничения действующего контракта

1. Бизнес-маршруты `/api/imports`, `/api/calculation-runs`, `/api/recommendations` и `/api/orders` требуют активного `request.state.user`. Доверенный middleware/identity adapter в приложении не подключён; обычный запрос получает 403. Заголовок `X-User-ID` и поля тела намеренно не принимаются как доказательство личности. Следовательно, нынешний UI не может пройти реальный workflow только за счёт вызова этих маршрутов. Нужна серверная интеграция с проверенной сессией/токеном и ролями `viewer`, `buyer`, `admin`.
2. `POST /api/calculation-runs` выполняет pipeline синхронно. Клиент не получает `run_id` до завершения операции; поллинг `pending/running` во время этого POST сейчас не работает. Статусы API — строчные `pending`, `running`, `completed`, `failed`, а не `PENDING`, `PROCESSING`, `COMPLETED`.
3. Нет HTTP-команды перевести `suggested`/`adjusted` в `accepted`. Доменные методы `Recommendation.accept()` и фильтр accepted в `CreateOrders` есть, но `PATCH /api/recommendations/{id}` оставляет состояние `adjusted`. Поэтому после импорта и расчёта `POST /api/orders` возвращает пустой список даже после ручной корректировки.
4. `RecommendationResponse` содержит только UUID товара, склада и поставщика, без SKU, названия, единицы, названия поставщика, закупочной цены и валюты. Таблицу, поиск, группировку по брендам и итоговый бюджет невозможно достоверно построить из одного ответа. Демонстрационный `/api/v1/procurement/*` не устраняет этот пробел.
5. `POST /api/orders` принимает только `calculation_run_id`; массив отмеченных чекбоксами рекомендаций отклоняется с 422, поскольку в действующем `CreateOrdersRequest` такого поля нет (`extra="forbid"`). Маршрута списка заказов также нет.
6. В `/explain` есть аномалии только одной рекомендации и один агрегированный `forecast`, но нет месячных пар продаж/остатков за два года. Анонимизированные ID клиентов не должны раскрывать личные данные.

## Предлагаемый API

Ниже названы Method, Path, Request Body и Response Model в терминах OpenAPI 3. Тип `UUID` передаётся как `string` с `format: uuid`, дата как `format: date`, время как `format: date-time`, денежные суммы и количества как десятичные строки. Для всех изменяющих операций идентификатор автора берётся из доверенного контекста авторизации, а не из тела. Неуспешные ответы используют уже существующий формат `{ detail: { code, message, ... }, request_id }`. Новые операции должны документировать 403, 404, 409, 422 и 503 там, где они применимы.

### P0. Данные, выбор строк и утверждение

#### 1. Доверенная идентификация пользователя

- **Method / Path:** интеграция middleware для защищённых маршрутов; при необходимости `GET /api/v1/session` для UI.
- **Request Body:** отсутствует; проверяемый cookie или Bearer-токен. Ввод произвольного `user_id` через JSON/заголовок запрещён.
- **Response Model (если добавлен GET):** `SessionResponse { user_id: UUID, display_name: string, role: "viewer" | "buyer" | "admin" }`.
- **Смысл:** связать существующий `get_current_user` с доверенной системой входа. Без этого нельзя загрузить файл, пересчитать, корректировать или утверждать заказ.

#### 2. Реальный список рекомендаций для таблицы

- **Method / Path:** расширить существующий `GET /api/calculation-runs/{run_id}/recommendations`; демонстрационный `GET /api/v1/procurement/recommendations` после миграции клиентов либо удалить, либо сделать документированным представлением того же сохранённого запуска.
- **Request Body:** отсутствует. Query: действующие `supplier_id`, `warehouse_id`, `category_id`, `urgency`, `status`, `sort_by`, `descending`, `limit`, `offset` плюс `search?: string` по SKU/наименованию и `run_id` для совместимого `/api/v1/procurement`.
- **Response Model:** `RecommendationPageResponse { items: ProcurementRecommendationRow[], total: integer, limit: integer, offset: integer }`, где `ProcurementRecommendationRow` сохраняет поля действующего `RecommendationResponse` и добавляет `sku`, `product_name`, `unit`, `supplier_name`, `warehouse_name`, `category_name?`, `unit_price?: decimal-string`, `currency?: string`, `estimated_total?: decimal-string`. Поля цены/суммы должны оставаться `null`, если цена отсутствует, без подстановки нуля.
- **Правило:** ответ берётся только из сохранённого `calculation_run`. Для исторически верной цены нужно сохранять снимок условий поставщика на момент запуска: текущая таблица `supplier_products` может измениться после нового импорта. Фильтры и пагинация применяются на сервере, чтобы UI не искал только в первой странице.

#### 3. Поиск актуального расчёта

- **Method / Path:** `GET /api/calculation-runs`.
- **Request Body:** отсутствует. Query: `status?: pending | running | completed | failed`, `warehouse_id?: UUID`, `category_id?: UUID`, `limit?: 1..100`, `offset?: integer >= 0`, сортировка `started_at desc`.
- **Response Model:** `CalculationRunPageResponse { items: CalculationRunResponse[], total: integer, limit: integer, offset: integer }`.
- **Смысл:** приложение после перезагрузки выбирает последний завершённый запуск, не хранит придуманный `run_id` в браузере и позволяет открыть исторический результат.

#### 4. Принятие рекомендаций перед формированием заказа

- **Method / Path:** `POST /api/recommendations/bulk/accept`.
- **Request Body:** `AcceptRecommendationsRequest { items: [{ recommendation_id: UUID, version: integer > 0 }], calculation_run_id: UUID }`; список непустой, ID уникальны.
- **Response Model:** `AcceptRecommendationsResponse { items: RecommendationResponse[], accepted_count: integer }`.
- **Правило:** одной транзакцией проверить состояние `suggested | adjusted`, версии, принадлежность одному запуску, положительное `effective_quantity`, MOQ и кратность, сохранить автора и время принятия в аудите. При конфликте любой строки вернуть 409 без частичного принятия. Для одиночной кнопки допускается такой же контракт на `POST /api/recommendations/{id}/accept`.

#### 5. Массовое создание выбранных заказов

- **Method / Path:** `POST /api/orders/bulk`.
- **Request Body:** `BulkCreateOrdersRequest { calculation_run_id: UUID, recommendation_ids: UUID[] }`; массив непустой и без повторов.
- **Response Model:** `BulkCreateOrdersResponse { orders: OrderResponse[], consumed_recommendation_ids: UUID[] }` со статусом 201.
- **Правило:** взять только выбранные принятые рекомендации одного запуска; сгруппировать по поставщику и складу; проверить версии/статус в транзакции и исключить повторное включение в заказ. Автор — проверенный пользователь. Если часть ID недоступна или уже заказана, вернуть 409/422 с перечнем ID и не создавать частичный набор. Существующий `POST /api/orders` остаётся действием «все принятые строки запуска» и не должен подменять bulk.

#### 6. Список заказов для страницы поставщиков

- **Method / Path:** `GET /api/orders`.
- **Request Body:** отсутствует. Query: `calculation_run_id?: UUID`, `supplier_id?: UUID`, `status?: draft | approved | exported | cancelled`, `limit?: 1..100`, `offset?: integer >= 0`.
- **Response Model:** `OrderPageResponse { items: OrderSummaryResponse[], total: integer, limit: integer, offset: integer }`, где `OrderSummaryResponse` содержит `id`, `order_number`, `supplier_id`, `supplier_name`, `warehouse_id`, `warehouse_name`, `status`, `created_at`, `approved_at?`, `item_count`, `total_amount?: decimal-string`, `currency?: string`.
- **Смысл:** после перезагрузки получить реальные черновики/утверждённые/экспортированные заказы, не восстанавливая их по рекомендациям на клиенте.

### P1. Справочники, объяснимость и аналитика

#### 7. Справочник поставщиков

- **Method / Path:** `GET /api/v1/suppliers`.
- **Request Body:** отсутствует. Query: `active_only?: boolean = true`, `search?: string`, `limit?: integer`, `offset?: integer`.
- **Response Model:** `SupplierPageResponse { items: SupplierResponse[], total, limit, offset }`; `SupplierResponse { id: UUID, code: string, name: string, is_active: boolean }`.
- **Смысл:** фильтр IEK, КЭАЗ и других брендов должен использовать справочник, а не уникальные значения видимой страницы рекомендаций. Таблица `suppliers` и репозиторий уже существуют; HTTP-маршрута нет.

#### 8. Справочники складов и категорий

- **Method / Path:** `GET /api/v1/warehouses`, `GET /api/v1/categories`.
- **Request Body:** отсутствует. Query: `active_only?: boolean = true`, `search?: string`.
- **Response Model:** соответственно `{ items: WarehouseResponse[] }`, `{ items: CategoryResponse[] }`; элементы содержат `id: UUID`, `code`, `name`, `is_active`, а категория также `parent_id?: UUID`.
- **Смысл:** форма запуска принимает UUID склада и категории, но сейчас пользователю негде получить реальные значения для выбора.

#### 9. История продаж и остатков для графика в Drawer

- **Method / Path:** `GET /api/recommendations/{recommendation_id}/history` либо расширение `GET /api/recommendations/{recommendation_id}/explain` полем `history`.
- **Request Body:** отсутствует. Query: `months?: 1..24 = 24` для отдельного GET.
- **Response Model:** `RecommendationHistoryResponse { recommendation_id: UUID, run_id: UUID, points: [{ month: string (YYYY-MM), sales: decimal-string, stock: decimal-string | null }] }`.
- **Правило:** точки должны строиться из снимка импортов, привязанного к завершённому запуску, а не из новых загрузок. `stock: null` означает отсутствие наблюдения, а не нулевой остаток. Действующий `/explain` возвращает один прогноз и список аномалий без временного ряда.

#### 10. Журнал срезанных крупных продаж (Whale Orders Log)

- **Method / Path:** `GET /api/v1/analytics/outliers`.
- **Request Body:** отсутствует. Query: `calculation_run_id: UUID` обязателен; `supplier_id?: UUID`, `product_id?: UUID`, `warehouse_id?: UUID`, `limit?: 1..100`, `offset?: integer >= 0`.
- **Response Model:** `OutlierPageResponse { items: OutlierResponse[], total, limit, offset }`; `OutlierResponse { id: UUID, sales_transaction_id: UUID, product_id: UUID, sku: string, warehouse_id: UUID, occurred_at: date-time, method: string, original_quantity: decimal-string, replacement_quantity: decimal-string, threshold?: decimal-string, reason: string }`.
- **Правило:** читать `detected_anomalies` конкретного запуска; исключить ФИО, контакты и иные прямые идентификаторы клиента. Нынешний `/explain` отдаёт аномалии только одного SKU и не покрывает общую вкладку «Аналитика». Если требуется показывать срезанные выбросы агрегированных месячных продаж, для них отдельно понадобится сохраняемая запись: текущий `PeriodAnomaly` не сохраняется как транзакционная аномалия.

#### 11. Агрегаты для графиков спроса и ABC/XYZ

- **Method / Path:** `GET /api/v1/analytics/demand-series`, `GET /api/v1/analytics/abc-xyz`.
- **Request Body:** отсутствует. Для обоих обязательный `calculation_run_id: UUID`; опциональны `warehouse_id`, `category_id`, `supplier_id`. Для ряда — `product_id?: UUID`, `months?: 1..24`.
- **Response Model:** `DemandSeriesResponse { run_id: UUID, points: [{ month: string (YYYY-MM), raw_sales: decimal-string, cleaned_demand: decimal-string, stock?: decimal-string | null }] }`; `AbcXyzResponse { run_id: UUID, cells: [{ abc: "A" | "B" | "C", xyz: "X" | "Y" | "Z", sku_count: integer, demand_share: decimal-string }] }`.
- **Правило:** метод и пороги ABC/XYZ фиксируются версией алгоритма и возвращаются в метаданных ответа. Сейчас эти виджеты не могут быть привязаны к историческим данным через HTTP.

#### 12. Серверная проверка MOQ при ручной корректировке

- **Method / Path:** расширить действующий `PATCH /api/recommendations/{recommendation_id}`.
- **Request Body:** действующий `AdjustRecommendationRequest { new_quantity: decimal-string >= 0, reason: string 1..2000, version: integer > 0 }`; по согласованному правилу добавить `round_to_pack?: boolean` либо требовать уже кратное значение.
- **Response Model:** действующий `RecommendationResponse` с фактическим `effective_quantity` и новой `version`.
- **Правило:** сейчас `Recommendation.adjust()` проверяет неотрицательность, но не MOQ/кратность. Необходимо либо атомарно округлять на сервере и возвращать результат, либо возвращать 422 с `moq`/`package_size`. Проверка только в UI недостаточна для API-клиентов.

### P2. Финансовая песочница и длительные операции

#### 13. Лимит бюджета в расчёте

- **Method / Path:** расширить действующий `POST /api/calculation-runs`.
- **Request Body:** `RunCalculationRequest` плюс `budget_limit?: decimal-string > 0`, `currency?: string` (по умолчанию валюта закупочных цен или явно выбранная единая валюта). Поле должно сохраняться в `calculation_runs.parameters`.
- **Response Model:** `CalculationRunResponse` плюс `budget_limit?: decimal-string`, `allocated_amount?: decimal-string`, `unmet_need_amount?: decimal-string`, `optimization_method?: string` и версия применённых правил.
- **Правило:** при заданном бюджете сервер оптимизирует только положительные предложения с учётом риска, MOQ, кратности, закупочной цены и поставщика. При неизвестной цене или смешанных валютах нужен явный 422/состояние «расчёт невозможен», а не предположение о нулевой стоимости. Новые результаты сохраняются как отдельный запуск и не меняют завершённый старый.

#### 14. Превью What-If сценария

- **Method / Path:** `POST /api/v1/scenarios/preview`.
- **Request Body:** `ScenarioPreviewRequest { base_run_id: UUID, growth_multiplier?: decimal-string > 0, service_level?: decimal-string (0,1], supplier_delay_days?: integer >= 0, include_anomalies?: boolean, budget_limit?: decimal-string > 0 }`.
- **Response Model:** `ScenarioPreviewResponse { base_run_id: UUID, assumptions: ScenarioPreviewRequest, totals: { amount?: decimal-string, quantity: decimal-string, critical_count: integer, budget_gap?: decimal-string }, items: [{ recommendation_id: UUID, baseline_quantity: decimal-string, simulated_quantity: decimal-string, reason: string }] }`.
- **Правило:** явная пометка «превью», без изменения заказов и завершённого запуска; при дальнейшем утверждении сценарий должен быть зафиксирован отдельным расчётом. Сейчас у backend нет API для роста, уровня сервиса, задержки поставщика и отключения коррекции аномалий.

#### 15. Асинхронный запуск и реальный прогресс

- **Method / Path:** сохранить `POST /api/calculation-runs` и `GET /api/calculation-runs/{run_id}`, но изменить исполнение POST на постановку задачи с ответом 202.
- **Request Body:** действующий `RunCalculationRequest` с опциональным `budget_limit` после реализации пункта 13.
- **Response Model:** `CalculationRunResponse` с `status: "pending"`, позже `"running" | "completed" | "failed"`; можно добавить `progress: { phase: string, completed: integer, total: integer }`.
- **Правило:** запуск должен быть идемпотентным по отдельному ключу запроса, а GET — читать сохраняемые статусы. Сейчас POST блокирует до завершения pipeline, поэтому показ промежуточного статуса посредством polling будет фиктивным.

#### 16. Прогресс импорта

- **Method / Path:** расширить `GET /api/imports/{batch_id}`.
- **Request Body:** отсутствует.
- **Response Model:** действующий `ImportStatusResponse` плюс `progress?: { stage: "uploaded" | "validating" | "persisting" | "completed", processed_rows: integer, total_rows?: integer }`.
- **Правило:** текущий POST возвращается только после чтения и обработки файла. Полоса прогресса загрузки HTTP на клиенте возможна, но прогресс разбора Excel из текущего ответа получить нельзя. Отдельная фоновая обработка потребует контракта 202 и гарантированного сохранения состояния партии.

## Порядок интеграции

1. Подключить доверенную аутентификацию и подтвердить доступ к существующим DB-маршрутам. Не обходить 403 демонстрационным `/api/v1/procurement/*`.
2. Реализовать поиск запуска и полноценную строку рекомендаций; убрать встроенный набор из версии `/api/v1/procurement` или снять этот маршрут с production UI.
3. Добавить принятие и `POST /api/orders/bulk`, затем провести путь «импорт → расчёт → корректировка → принятие → черновик → утверждение → POST экспорта → GET XLSX» на одном завершённом запуске.
4. После этого подключить справочники, временные ряды, аномалии, аналитику и бюджетные сценарии. До появления их контрактов UI должен показывать честное «данные недоступны», а не синтетические значения.

См. также [действующее описание HTTP API](http_api.md) и [схему данных](database.md).
