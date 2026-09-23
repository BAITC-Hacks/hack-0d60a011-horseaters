from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SkuAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="Уникальный идентификатор позиции")
    sku: str = Field(description="Артикул или код 1С товара")
    vendor_code: str = Field(default="", description="Код производителя / артикул вендора")
    item_name: str = Field(description="Полное наименование номенклатуры")
    category: str = Field(default="", description="Товарная категория")
    supplier_name: str = Field(default="IEK Казахстан", description="Поставщик")
    unit: str = Field(default="шт", description="Единица измерения")
    current_stock: float = Field(description="Текущий физический остаток на складе")
    in_transit: float = Field(default=0.0, description="Количество товара в пути")
    transit_details: str | None = Field(default=None, description="Детали поставки в пути (номер накладной, дата)")
    daily_demand: float = Field(description="Среднесуточный темп спроса")
    days_of_stock: float | None = Field(default=None, description="Количество дней до исчерпания текущего запаса")
    season_factor: float = Field(default=1.0, description="Сезонный коэффициент периода")
    calculated_need: float = Field(description="Расчетная потребность до ручных правок")
    adjusted_need: float = Field(description="Скорректированная менеджером потребность")
    package_multiplicity: float = Field(default=1.0, description="Кратность упаковки поставщика")
    moq: float = Field(default=1.0, description="Минимальная партия отгрузки (MOQ)")
    unit_price: float = Field(default=0.0, description="Цена за единицу (тенге/руб)")
    total_cost: float = Field(default=0.0, description="Общая сумма заказа по позиции")
    urgency: str = Field(default="NORMAL", description="Уровень срочности (CRITICAL, HIGH, MEDIUM, LOW, NORMAL)")
    reasoning: str | None = Field(default=None, description="Базовое математическое обоснование потребности")
    has_whale_outlier: bool = Field(default=False, description="Признак наличия отфильтрованной оптовой аномалии")
    stockout_recovered: bool = Field(default=False, description="Признак восстановления спроса после периода дефицита")


class SkuAnalysisResponse(BaseModel):
    """Structured Output для SKU Explainability (боковая шторка закупщика)."""
    model_config = ConfigDict(extra="ignore")

    summary: str = Field(
        description="Краткое резюме ситуации по позиции понятным языком закупщика (1-2 емких предложения)"
    )
    root_cause: str = Field(
        description="Первопричина возникновения дефицита или избытка (сезонный пик, задержка поставки, срез аномалий, компенсация stockout)"
    )
    risk_analysis: str = Field(
        description="Анализ рисков: дней до обнуления остатка, угроза упущенных продаж или риск заморозки оборотного капитала"
    )
    recommendation_action: str = Field(
        description="Конкретная рекомендация: рекомендованный объем с учетом кратности упаковок/бухт, согласование ускоренной доставки или перенос"
    )
    confidence_score: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Оценка надежности прогноза от 0.0 до 1.0 на основе полноты данных"
    )
    is_fallback: bool = Field(
        default=False,
        description="True, если ответ сгенерирован детерминированным fallback-генератором при сбое OpenAI"
    )


class CriticalItemBrief(BaseModel):
    sku: str
    item_name: str
    days_of_stock: float | None = None
    calculated_need: float
    total_cost: float


class SupplierSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_name: str = Field(default="IEK Казахстан", description="Наименование поставщика")
    total_items: int = Field(description="Общее количество позиций в пуле закупки")
    total_budget: float = Field(description="Общий бюджет рекомендованного заказа")
    critical_count: int = Field(default=0, description="Количество критических позиций (CRITICAL)")
    planned_count: int = Field(default=0, description="Количество плановых позиций (HIGH / PLANNED)")
    normal_count: int = Field(default=0, description="Количество стабильных позиций (NORMAL / LOW)")
    season_name: str = Field(default="Октябрь 2026", description="Целевой месяц планирования")
    season_factor: float = Field(default=1.242, description="Коэффициент сезонного пика")
    top_critical_items: list[dict[str, Any]] = Field(default_factory=list, description="Список критических SKU для анализа")


class SupplierSummaryResponse(BaseModel):
    """Structured Output для Executive-сводки по поставщику и сезонному периоду."""
    model_config = ConfigDict(extra="ignore")

    executive_summary: str = Field(
        description="Сводный аналитический отчет для директора по закупкам о текущем состоянии запасов и плановом заказе"
    )
    budget_analysis: str = Field(
        description="Оценка финансовой нагрузки, распределения бюджета между категориями и эффективности инвестиций"
    )
    critical_risks: list[str] = Field(
        description="Список ключевых рисков с акцентом на дефицитные SKU и сезонный всплеск спроса"
    )
    key_recommendations: list[str] = Field(
        description="Конкретный перечень управленческих шагов для оптимизации заказа и своевременной поставки"
    )
    is_fallback: bool = Field(
        default=False,
        description="True, если ответ сгенерирован локальным fallback-шаблоном"
    )


class OrderItemBrief(BaseModel):
    sku: str
    vendor_code: str = ""
    item_name: str
    quantity: float
    unit: str = "шт"
    unit_price: float = 0.0
    total_cost: float = 0.0


class SupplierLetterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_name: str = Field(default="IEK Казахстан", description="Поставщик / вендор")
    company_name: str = Field(default="ТОО «Электрокомплект»", description="Компания-покупатель")
    contact_person: str | None = Field(default=None, description="Контактное лицо поставщика")
    target_date: str | None = Field(default="до 05.10.2026", description="Желаемый срок поставки / отгрузки")
    delivery_notes: str | None = Field(default="Самовывоз с регионального РЦ / склад Алматы", description="Условия доставки")
    items: list[dict[str, Any]] = Field(default_factory=list, description="Список позиций с объемами > 0")


class SupplierLetterResponse(BaseModel):
    """Structured Output для официального письма поставщику на бронирование/заказ."""
    model_config = ConfigDict(extra="ignore")

    subject: str = Field(
        description="Официальная тема письма (например: Заявка на бронирование складского запаса продукции IEK)"
    )
    recipient: str = Field(
        description="Официальный адресат письма (например: Руководителю отдела сбыта ТОО «ИЭК КАЗАХСТАН»)"
    )
    salutation: str = Field(
        description="Деловое приветствие (например: Уважаемые партнеры!)"
    )
    letter_body: str = Field(
        description="Основной текст делового письма с реквизитами ТОО «Электрокомплект», ссылкой на договор и запросом брони"
    )
    items_table: str = Field(
        description="Четко структурированная текстовая таблица позиций с артикулами, кратностью и объемами"
    )
    closing: str = Field(
        description="Заключительная формулировка и подпись (Отдел материально-технического снабжения ТОО «Электрокомплект»)"
    )
    is_fallback: bool = Field(
        default=False,
        description="True, если ответ сгенерирован локальным fallback-шаблоном"
    )
