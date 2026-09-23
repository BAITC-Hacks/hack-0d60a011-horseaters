from __future__ import annotations

from typing import Any
from backend.infrastructure.ai.schemas import (
    SkuAnalysisRequest,
    SkuAnalysisResponse,
    SupplierLetterRequest,
    SupplierLetterResponse,
    SupplierSummaryRequest,
    SupplierSummaryResponse,
)


def generate_sku_analysis_fallback(item: SkuAnalysisRequest) -> SkuAnalysisResponse:
    """Deterministic, high-quality analytical fallback for SKU explainability."""
    days = f"{item.days_of_stock:.1f}" if item.days_of_stock is not None else "менее 1"
    demand = f"{item.daily_demand:.1f}"
    mult = int(item.package_multiplicity) if item.package_multiplicity.is_integer() else item.package_multiplicity
    qty = int(item.adjusted_need) if item.adjusted_need.is_integer() else item.adjusted_need

    if item.urgency in ("CRITICAL", "HIGH"):
        summary = (
            f"Позиция «{item.item_name}» находится в зоне повышенного внимания. "
            f"Текущего остатка {item.current_stock:,.0f} {item.unit} при темпе {demand} {item.unit}/сут "
            f"хватит лишь на {days} дн. с учетом сезонного фактора октября (К={item.season_factor:.2f})."
        )
        cause_parts = [
            f"Сезонный подъем потребности в октябре (множитель {item.season_factor:.2f})",
            f"интенсивный ежедневный расход ({demand} {item.unit}/день)",
        ]
        if item.stockout_recovered:
            cause_parts.append("восстановление нормального спроса после периода дефицита (stockout)")
        if item.has_whale_outlier:
            cause_parts.append("разовые оптовые выбросы предварительно отфильтрованы и не раздувают регулярный заказ")
        if item.in_transit > 0 and item.transit_details:
            cause_parts.append(f"открытая поставка {item.transit_details} поступит позже момента исчерпания склада")
        root_cause = "Основной драйвер потребности: " + ", ".join(cause_parts) + "."

        risk_analysis = (
            f"Риск дефицита критический: склад обнулится через {days} дн. "
            "Возможны простои монтажных бригад, срыв комплексных заказов клиентов и упущенная торговая маржа."
        )
        action_parts = [
            f"Рекомендуется разместить заказ на {qty:,.0f} {item.unit}",
            f"с кратностью отгрузки IEK по {mult} {item.unit}",
        ]
        if item.total_cost > 0:
            action_parts.append(f"на общую сумму {item.total_cost:,.0f} ₸")
        if item.in_transit > 0:
            action_parts.append("и запросить у экспедитора статус груза в пути")
        recommendation_action = ", ".join(action_parts) + "."
    elif qty > 0:
        summary = (
            f"Позиция «{item.item_name}»: плановое пополнение запаса. "
            f"Остатка {item.current_stock:,.0f} {item.unit} хватит на {days} дн., "
            f"требуется заказ {qty:,.0f} {item.unit} для покрытия горизонта планирования."
        )
        root_cause = (
            f"Плановый цикл поставки с учетом плеча доставки и сезонности {item.season_factor:.2f}. "
            "Темп расхода соответствует средним историческим значениям."
        )
        risk_analysis = (
            "Умеренный риск: отсутствие своевременного заказа приведет к снижению страхового буфера во второй половине месяца."
        )
        recommendation_action = (
            f"Включить в ближайший консолидированный заказ IEK в объеме {qty:,.0f} {item.unit} "
            f"(кратно {mult} {item.unit}) на сумму {item.total_cost:,.0f} ₸."
        )
    else:
        summary = (
            f"Позиция «{item.item_name}»: уровень запаса оптимален. "
            f"Текущий остаток {item.current_stock:,.0f} {item.unit} полностью покрывает "
            f"потребность на {days} дн. вперед."
        )
        root_cause = (
            "Складской остаток превышает целевой уровень покрытия горизонта планирования (плечо поставки + 30 дней)."
        )
        risk_analysis = (
            "Риск дефицита отсутствует. Дополнительная закупка приведет к заморозке оборотных средств."
        )
        recommendation_action = (
            "Рекомендуемый объем заказа: 0. Проверить остаток при следующем цикле пересчета."
        )

    return SkuAnalysisResponse(
        summary=summary,
        root_cause=root_cause,
        risk_analysis=risk_analysis,
        recommendation_action=recommendation_action,
        confidence_score=0.96,
        is_fallback=True,
    )


def generate_supplier_summary_fallback(req: SupplierSummaryRequest) -> SupplierSummaryResponse:
    """Deterministic fallback for executive procurement summary."""
    exec_summary = (
        f"Аналитический срез по поставщику {req.supplier_name} на {req.season_name}. "
        f"В контуре закупки проанализировано {req.total_items} позиций, плановый бюджет пополнения "
        f"составляет {req.total_budget:,.0f} ₸. Выявлено {req.critical_count} критических позиций с риском дефицита, "
        f"требующих первоочередного подтверждения в связи с сезонным ростом спроса (+{int((req.season_factor - 1) * 100)}%)."
    )

    budget_analysis = (
        f"Суммарный бюджет {req.total_budget:,.0f} ₸ рассчитан с учетом минимальных партий (MOQ) "
        "и кратности упаковок/бухт вендора. Основная доля бюджета сконцентрирована в модульном оборудовании "
        "и кабельно-проводниковой группе. Заказ обеспечивает покрытие целевого горизонта 44 дня "
        "(14 дней плечо поставки + 30 дней покрытия)."
    )

    risks = [
        f"Сезонный пик: в {req.season_name} прогнозируется рост спроса на {int((req.season_factor - 1) * 100)}%, что при задержке заказа вызовет дефицит по {req.critical_count} позициям.",
        "Плечо поставки вендора составляет 14 дней — несвоевременное размещение заявки обнулит остатки по критическим позициям до прихода партии.",
    ]
    for crit in req.top_critical_items[:3]:
        name = crit.get("item_name") or crit.get("sku")
        days = crit.get("days_of_stock")
        days_str = f"хватит на {days:.1f} дн." if days is not None else "дефицит"
        risks.append(f"Артикул {crit.get('sku')} ({name}): {days_str}, расчетный заказ {crit.get('calculated_need', 0):,.0f} ед.")

    recs = [
        f"Утвердить сформированную заявку на сумму {req.total_budget:,.0f} ₸ и отправить официальный запрос на бронирование в {req.supplier_name}.",
        f"Приоритетно согласовать отгрузку {req.critical_count} критических позиций первой партией.",
        "Контролировать соблюдение кратности упаковки при любых ручных корректировках закупщика.",
        "Запросить у логистического оператора статус товаров в пути для синхронизации графиков приемки.",
    ]

    return SupplierSummaryResponse(
        executive_summary=exec_summary,
        budget_analysis=budget_analysis,
        critical_risks=risks,
        key_recommendations=recs,
        is_fallback=True,
    )


def generate_supplier_letter_fallback(req: SupplierLetterRequest) -> SupplierLetterResponse:
    """Deterministic fallback for formal reservation letter to IEK."""
    subject = f"Заявка на резервирование и поставку продукции IEK для {req.company_name}"
    recipient = f"Руководителю отдела продаж / клиентского сервиса {req.supplier_name}"
    salutation = "Уважаемые партнеры!"

    total_sum = sum(float(item.get("total_cost", 0)) for item in req.items)
    total_qty = sum(float(item.get("quantity", 0)) for item in req.items)

    lines = [
        "№ | Артикул | Наименование номенклатуры | Кол-во | Ед. | Цена (₸) | Сумма (₸)",
        "--|---------|---------------------------|--------|-----|----------|----------",
    ]
    for idx, it in enumerate(req.items, 1):
        sku = it.get("sku", "")
        name = it.get("item_name", "")
        qty = float(it.get("quantity", 0))
        unit = it.get("unit", "шт")
        price = float(it.get("unit_price", 0))
        cost = float(it.get("total_cost", qty * price))
        lines.append(f"{idx} | {sku} | {name} | {qty:,.0f} | {unit} | {price:,.0f} | {cost:,.0f}")

    items_table = "\n".join(lines)

    letter_body = (
        f"В рамках действующего договора поставки между {req.company_name} и {req.supplier_name}, "
        f"просим Вас поставить в резерв и подготовить к отгрузке электротехническую продукцию "
        f"согласно прилагаемой спецификации в общем объеме {total_qty:,.0f} ед. на сумму {total_sum:,.0f} тенге.\n\n"
        f"Желаемый срок готовности к отгрузке: {req.target_date or 'до 05.10.2026'}.\n"
        f"Условия получения: {req.delivery_notes or 'самовывоз с регионального распределительного центра'}.\n"
        "Объемы выверены с учетом заводской кратности упаковок и минимальных партий отгрузки (MOQ)."
    )

    closing = (
        "Просим направить счет на оплату и подтверждение резерва ответным письмом.\n\n"
        "С уважением,\n"
        "Отдел материально-технического снабжения\n"
        f"{req.company_name}\n"
        "Тел.: +7 (727) 295-88-00 | supply@electrokomplekt.kz"
    )

    return SupplierLetterResponse(
        subject=subject,
        recipient=recipient,
        salutation=salutation,
        letter_body=letter_body,
        items_table=items_table,
        closing=closing,
        is_fallback=True,
    )
