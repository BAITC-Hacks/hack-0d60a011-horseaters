# Чтение исходных данных (REP-02)

Порты находятся в `backend/domain/repositories`, реализации `SqlAlchemy*Repository`
— в `backend/infrastructure/persistence`, рядом с существующими файлами репозиториев.
Конструктор каждой реализации принимает `Session`. Все результаты — доменные
dataclass, а не ORM. `Decimal`, UUID и Enum сохраняются, время возвращается в UTC.
Для SQLite-демо прочитанное время без часового пояса трактуется как UTC согласно
соглашению хранения в `database.md`; границы запросов всегда требуют timezone.

Репозитории не создают engine/сессии, не делают commit/rollback/close и отключают
autoflush на время чтения. Жизненным циклом управляет существующий `get_db` либо
`SqlAlchemyUnitOfWork`. Например, в infrastructure-коде:

```python
repository = SqlAlchemySalesRepository(session)  # session из Depends(get_db) или UoW
transactions = repository.list_transactions(start, end, product_id=product_id)
```

В `RepositoryFactories` передавайте классы реализаций в `sales`, `inventory`,
`suppliers`, `products`, `seasonality`, `material_requirements`. Все получают одну
Session. Последние три фабрики необязательны для совместимости с прежней конфигурацией;
обращение к ненастроенному репозиторию вызывает явную ошибку. Остальные фабрики UoW
по-прежнему предоставляет composition root; API и бизнес-модули не меняются.

## Контракты запросов

| Репозиторий | Методы и результат |
|---|---|
| Product | `get_by_id(UUID)`, `get_by_sku(str)` → `Product \| None`; `list_products(category_id=ALL, is_active=True)` → `list[Product]` |
| Sales | `list_transactions(start: datetime, end: datetime, ...)` → `list[SalesTransaction]`; `list_monthly_sales(start: date, end: date, ...)` → `list[MonthlySales]` |
| Inventory | `get_latest_snapshot(product_id, warehouse_id, as_of)` → `InventorySnapshot \| None`; `list_stockout_periods(start, end, ...)` → `list[StockoutPeriod]`; `list_active_in_transit(...)` → `list[InTransitItem]` |
| Supplier | `get_by_id(UUID)` → `Supplier \| None`; `list_terms(product_id, supplier_id=None, active_only=True)` → `list[SupplierProduct]` |
| Seasonality | `list_coefficients(product_id, on_date, ...)` → `list[SeasonalityCoefficient]`; `get_coefficient(...)` → `SeasonalityCoefficient \| None`; `list_growth_assumptions(on_date, ...)` → `list[GrowthAssumption]` |
| MaterialRequirement | `list_requirements(start, end, ..., status=PLANNED)` → `list[MaterialRequirement]` |

- Временные интервалы — `[start, end)`, даты со смещением нормализуются в UTC.
  Пустые/обратные временные интервалы и naive datetime отклоняются.
- Месячные продажи — строки с пересечением закрытых календарных интервалов
  `[period_start, period_end]` и `[start, end]`. Количество не обрезается пропорционально
  пересечению. Транзакции и месячные строки никогда не складываются репозиторием.
  Транзакции возвращаются как факты, включая возвраты; перенос возврата в период
  исходной продажи относится к алгоритму расчёта, а не к этому запросу.
- Последний остаток: максимум `snapshot_at <= as_of` для точной пары товар/склад.
  Отсутствие данных возвращает `None`, а не нулевой остаток. При одинаковом максимуме
  в нескольких импортах — `AmbiguousSourceDataError`; можно уточнить `import_batch_ids`.
- Stockout: `started_at < end AND (ended_at IS NULL OR ended_at > start)`.
  Касание границы без пересечения исключается. Источники imported/inferred/manual
  возвращаются явно, без выбора приоритетного источника и без объединения интервалов.
- Поставки: только `planned` и `in_transit`. Границы `expected_from`/`expected_before`
  необязательны, интервал полуоткрытый. По умолчанию дата должна быть известна;
  `include_undated=True` дополнительно включает записи с NULL независимо от границ.
- Условия поставки: по умолчанию активны и условия, и сам поставщик. MOQ, упаковка,
  срок, цена, приоритет и признак основного поставщика возвращаются без выбора победителя.
- Сезонность: месяц `on_date.month`, `valid_from <= on_date <= valid_to`, NULL конец
  открыт. Приоритет товара над его непосредственной категорией задан документацией.
  Фильтры `version` и `import_batch_ids` применяются до выбора уровня. В пределах
  уровня возвращаются все кандидаты; `get_coefficient` отклоняет неоднозначность.
- Рост: те же включённые границы действия; все заданные фильтры соединены AND,
  приоритет между уровнями, складами или источниками не применяется.
- В nullable-фильтрах категории товара, склада месячных продаж и product/category/
  warehouse роста `ALL` означает отсутствие фильтра, `None` — именно SQL NULL,
  UUID — точное равенство. Поэтому глобальные данные не подмешиваются к конкретному
  складу незаметно. Для остальных, обязательных FK `None` означает отсутствие фильтра.
- Материальные потребности: по умолчанию `planned`, статус можно задать явно;
  `status=None` возвращает все состояния, `required_at` ограничен `[start, end)`.

Все импортированные факты доступны только из `completed` batches. Nullable batch
для stockout/роста допускает локальные вычисленные/ручные записи. Параметр
`import_batch_ids=None` не ограничивает завершённые импорты; переданный список —
строгий whitelist (пустой даёт пустой результат, записи с NULL batch исключаются).
Так вызывающий код может зафиксировать набор источников расчёта. Самостоятельного
выбора «последнего импорта» и удаления дублей между файлами нет.

## Открытые правила

Нужно согласовать выбор между пересекающимися версиями сезонности, одинаковыми
снимками из разных импортов, источниками/уровнями роста, а также распределение
месячных данных без склада. Пока запросы возвращают явные кандидаты/NULL-уровень
или ошибку неоднозначности. Не определён и порядок выбора поставщика по цене,
сроку и приоритету — возвращаются все условия.

Статусы поставок читаются текущие: в модели нет истории переходов статуса, поэтому
репозиторий не может достоверно восстановить статус поставки на прошлую дату.
`as_of` у остатков ограничивает дату снимка, а не время загрузки файла; для фиксации
доступных на момент расчёта импортов вызывающий код задаёт `import_batch_ids`.

Проверка: `python -B -m unittest discover -s tests -p test_read_repositories.py -v`.
Тесты выполняют SQL на отдельной SQLite in-memory базе, без изменения PostgreSQL.
