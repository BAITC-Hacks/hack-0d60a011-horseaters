from __future__ import annotations

import math
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from backend.infrastructure.api import dependencies as deps

router = APIRouter(prefix="/api/v1/procurement", tags=["procurement"],
                   dependencies=[Depends(deps.get_current_user)])


class ProcurementItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    sku: str
    vendor_code: str = ""
    item_name: str
    category: str
    supplier_name: str = "IEK Казахстан"
    unit: str = "шт"

    current_stock: float
    in_transit: float = 0.0
    transit_details: str | None = None

    daily_demand: float
    days_of_stock: float | None = None
    season_factor: float = 1.242

    calculated_need: float
    adjusted_need: float
    package_multiplicity: float = 1.0
    moq: float = 1.0
    unit_price: float = 0.0
    total_cost: float = 0.0

    urgency: str = "NORMAL"
    reasoning: str
    has_whale_outlier: bool = False
    stockout_recovered: bool = False


class ProcurementUpdateRequest(BaseModel):
    adjusted_need: float = Field(ge=0, description="Скорректированное количество")
    snap_to_multiplicity: bool = Field(
        default=True, description="Автоматически округлять до заводской кратности упаковки"
    )
    adjustment_reason: str | None = Field(default=None, description="Причина корректировки")


# In-memory realistic initial dataset for ТОО «Электрокомплект» / IEK
INITIAL_RECOMMENDATIONS: list[dict[str, Any]] = [
    {
        "id": "010500004_",
        "sku": "010500004_",
        "vendor_code": "MVA20-1-006-C",
        "item_name": "ВА47-29 (1ф) 6А IEK (12/144)",
        "category": "Модульное оборудование",
        "supplier_name": "IEK Казахстан",
        "unit": "шт",
        "current_stock": 140,
        "in_transit": 1200,
        "transit_details": "1 200 шт. по накл. ПП УТ-7848 (до 01.10.2026)",
        "daily_demand": 45.2,
        "days_of_stock": 3.1,
        "season_factor": 1.242,
        "calculated_need": 600,
        "adjusted_need": 600,
        "package_multiplicity": 12,
        "moq": 12,
        "unit_price": 850,
        "total_cost": 510000,
        "urgency": "CRITICAL",
        "reasoning": "Остаток 140 шт. исчерпается через 3 дня (до прихода поставки). Потребность на октябрь с учетом сезона (К=1.24): 600 шт. Кратность отгрузки: 12 шт.",
        "has_whale_outlier": False,
        "stockout_recovered": True,
    },
    {
        "id": "200400085_",
        "sku": "200400085_",
        "vendor_code": "CL04-05E-01",
        "item_name": "Кабель F/UTP 4 пары кат. 5Е ITK (бухта 305м)",
        "category": "Кабельно-проводниковая продукция",
        "supplier_name": "IEK Казахстан",
        "unit": "м",
        "current_stock": 9084,
        "in_transit": 0,
        "transit_details": None,
        "daily_demand": 75.1,
        "days_of_stock": 121.0,
        "season_factor": 1.242,
        "calculated_need": 0,
        "adjusted_need": 0,
        "package_multiplicity": 305,
        "moq": 1,
        "unit_price": 240,
        "total_cost": 0,
        "urgency": "NORMAL",
        "reasoning": "Остатка 9 084 м хватит на 121 день (до января 2027). С учетом сезонного коэффициента октября (К=1.24) потребность покрыта. Рекомендация к заказу: 0 м.",
        "has_whale_outlier": True,
        "stockout_recovered": True,
    },
    {
        "id": "010500010_",
        "sku": "010500010_",
        "vendor_code": "MVA20-1-016-C",
        "item_name": "ВА47-29 (1ф) 16А IEK (12/144)",
        "category": "Модульное оборудование",
        "supplier_name": "IEK Казахстан",
        "unit": "шт",
        "current_stock": 84,
        "in_transit": 0,
        "transit_details": None,
        "daily_demand": 58.0,
        "days_of_stock": 1.4,
        "season_factor": 1.242,
        "calculated_need": 1200,
        "adjusted_need": 1200,
        "package_multiplicity": 12,
        "moq": 12,
        "unit_price": 890,
        "total_cost": 1068000,
        "urgency": "CRITICAL",
        "reasoning": "Критический дефицит: остаток исчерпается через 1.4 дня. В пути поставок нет. Необходим срочный заказ 1 200 шт (100 упаковок по 12 шт).",
        "has_whale_outlier": False,
        "stockout_recovered": True,
    },
    {
        "id": "010500016_",
        "sku": "010500016_",
        "vendor_code": "MVA20-3-025-C",
        "item_name": "ВА47-29 (3ф) 25А IEK (4/48)",
        "category": "Модульное оборудование",
        "supplier_name": "IEK Казахстан",
        "unit": "шт",
        "current_stock": 48,
        "in_transit": 120,
        "transit_details": "120 шт. по накл. ПП УТ-7852 (до 03.10.2026)",
        "daily_demand": 14.5,
        "days_of_stock": 11.6,
        "season_factor": 1.242,
        "calculated_need": 240,
        "adjusted_need": 240,
        "package_multiplicity": 4,
        "moq": 4,
        "unit_price": 2650,
        "total_cost": 636000,
        "urgency": "HIGH",
        "reasoning": "Поставка 120 шт в пути покроет первые 11 дней. Для обеспечения 44-дневного горизонта и сезонного роста требуется дозаказ 240 шт (60 уп).",
        "has_whale_outlier": False,
        "stockout_recovered": False,
    },
    {
        "id": "020100015_",
        "sku": "020100015_",
        "vendor_code": "MDV10-2-025-030",
        "item_name": "УЗО ВД1-63 2Р 25А 30мА IEK (6/72)",
        "category": "Дифференциальная защита",
        "supplier_name": "IEK Казахстан",
        "unit": "шт",
        "current_stock": 180,
        "in_transit": 240,
        "transit_details": "240 шт. по накл. ПП УТ-7848 (до 01.10.2026)",
        "daily_demand": 12.0,
        "days_of_stock": 35.0,
        "season_factor": 1.180,
        "calculated_need": 150,
        "adjusted_need": 150,
        "package_multiplicity": 6,
        "moq": 6,
        "unit_price": 5400,
        "total_cost": 810000,
        "urgency": "MEDIUM",
        "reasoning": "Суммарно на складе и в пути 420 шт. Для покрытия пика октября и страхового запаса рекомендуется дозаказ 150 шт (25 упаковок по 6 шт).",
        "has_whale_outlier": False,
        "stockout_recovered": False,
    },
    {
        "id": "030400002_",
        "sku": "030400002_",
        "vendor_code": "KKM11-012-230-10",
        "item_name": "Контактор КМИ-11210 12А 230В IEK",
        "category": "Коммутационное оборудование",
        "supplier_name": "IEK Казахстан",
        "unit": "шт",
        "current_stock": 16,
        "in_transit": 0,
        "transit_details": None,
        "daily_demand": 4.8,
        "days_of_stock": 3.3,
        "season_factor": 1.210,
        "calculated_need": 60,
        "adjusted_need": 60,
        "package_multiplicity": 1,
        "moq": 10,
        "unit_price": 4200,
        "total_cost": 252000,
        "urgency": "CRITICAL",
        "reasoning": "Остаток 16 шт исчерпается через 3.3 дня. Поставок в пути нет. Требуется срочный заказ 60 шт (MOQ=10).",
        "has_whale_outlier": False,
        "stockout_recovered": True,
    },
    {
        "id": "040100055_",
        "sku": "040100055_",
        "vendor_code": "LPO0-00-65-IP20",
        "item_name": "Светильник светодиодный ДВО 6500К IP20 IEK",
        "category": "Светотехника",
        "supplier_name": "IEK Казахстан",
        "unit": "шт",
        "current_stock": 450,
        "in_transit": 200,
        "transit_details": "200 шт. по накл. ПП УТ-7860 (до 05.10.2026)",
        "daily_demand": 22.0,
        "days_of_stock": 29.5,
        "season_factor": 1.250,
        "calculated_need": 300,
        "adjusted_need": 300,
        "package_multiplicity": 10,
        "moq": 10,
        "unit_price": 3800,
        "total_cost": 1140000,
        "urgency": "MEDIUM",
        "reasoning": "Плановое сезонное пополнение осветительной продукции перед осенне-зимним монтажным пиком. Заказ 300 шт (30 коробок).",
        "has_whale_outlier": False,
        "stockout_recovered": False,
    },
    {
        "id": "050200012_",
        "sku": "050200012_",
        "vendor_code": "MKP12-N-06-30-00",
        "item_name": "Бокс пластиковый КМПн 2/6 модулей навесной IEK",
        "category": "Корпуса и шкафы",
        "supplier_name": "IEK Казахстан",
        "unit": "шт",
        "current_stock": 310,
        "in_transit": 500,
        "transit_details": "500 шт. по накл. ПП УТ-7840 (до 28.09.2026)",
        "daily_demand": 11.2,
        "days_of_stock": 72.3,
        "season_factor": 1.150,
        "calculated_need": 0,
        "adjusted_need": 0,
        "package_multiplicity": 10,
        "moq": 10,
        "unit_price": 1250,
        "total_cost": 0,
        "urgency": "NORMAL",
        "reasoning": "С учетом открытой поставки 500 шт запасов хватит более чем на 72 дня. Рекомендуемый заказ: 0 шт.",
        "has_whale_outlier": False,
        "stockout_recovered": False,
    },
    {
        "id": "060100020_",
        "sku": "060100020_",
        "vendor_code": "UIN01-6-9-10",
        "item_name": "Шина нулевая изолированная ШНИ-6х9-10-КС IEK",
        "category": "Электромонтажные изделия",
        "supplier_name": "IEK Казахстан",
        "unit": "шт",
        "current_stock": 800,
        "in_transit": 0,
        "transit_details": None,
        "daily_demand": 18.0,
        "days_of_stock": 44.4,
        "season_factor": 1.200,
        "calculated_need": 0,
        "adjusted_need": 0,
        "package_multiplicity": 20,
        "moq": 20,
        "unit_price": 310,
        "total_cost": 0,
        "urgency": "NORMAL",
        "reasoning": "Складской запас 800 шт полностью обеспечивает покрытие горизонта 44 дня. Заказ не требуется.",
        "has_whale_outlier": False,
        "stockout_recovered": False,
    },
    {
        "id": "070300045_",
        "sku": "070300045_",
        "vendor_code": "CL01-3-25-LS",
        "item_name": "Кабель силовой ВВГнг(А)-LS 3х2.5 IEK (бухта 100м)",
        "category": "Кабельно-проводниковая продукция",
        "supplier_name": "IEK Казахстан",
        "unit": "м",
        "current_stock": 420,
        "in_transit": 500,
        "transit_details": "500 м по накл. ПП УТ-7865 (до 04.10.2026)",
        "daily_demand": 45.0,
        "days_of_stock": 20.4,
        "season_factor": 1.280,
        "calculated_need": 1500,
        "adjusted_need": 1500,
        "package_multiplicity": 100,
        "moq": 100,
        "unit_price": 520,
        "total_cost": 780000,
        "urgency": "HIGH",
        "reasoning": "Ходовой кабель для розеточных групп. Высокий темп расхода, сезонный рост +28%. Рекомендован заказ 1 500 м (15 бухт по 100 м).",
        "has_whale_outlier": False,
        "stockout_recovered": True,
    },
]

# Memory store preserving adjustments during runtime
_recommendations_store: dict[str, dict[str, Any]] = {
    item["id"]: dict(item) for item in INITIAL_RECOMMENDATIONS
}


@router.get("/recommendations", response_model=list[ProcurementItem])
async def list_procurement_recommendations() -> list[ProcurementItem]:
    """Список рассчитанных рекомендаций пополнения склада ТОО «Электрокомплект»."""
    return [ProcurementItem(**data) for data in _recommendations_store.values()]


@router.get("/recommendations/{item_id}", response_model=ProcurementItem)
async def get_procurement_recommendation(
    item_id: str = Path(..., description="ID позиции или артикул"),
) -> ProcurementItem:
    """Получение одной рекомендации по ID."""
    item = _recommendations_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    return ProcurementItem(**item)


@router.patch("/recommendations/{item_id}", response_model=ProcurementItem)
async def update_procurement_recommendation(
    item_id: str = Path(..., description="ID позиции или артикул"),
    update: ProcurementUpdateRequest = ...,
    _buyer=Depends(deps.require_writer),
) -> ProcurementItem:
    """
    Корректировка объема закупки менеджером.
    Автоматически выравнивает объем по кратности упаковки поставщика (MOQ) и пересчитывает сумму.
    """
    item = _recommendations_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Позиция не найдена")

    qty = update.adjusted_need
    multiplicity = item.get("package_multiplicity", 1.0)
    moq = item.get("moq", 1.0)

    if update.snap_to_multiplicity and qty > 0 and multiplicity > 1:
        target = max(qty, moq)
        packages = math.ceil(target / multiplicity)
        snapped_qty = packages * multiplicity
    else:
        snapped_qty = qty

    item["adjusted_need"] = snapped_qty
    item["total_cost"] = snapped_qty * item.get("unit_price", 0.0)

    if update.adjustment_reason:
        item["reasoning"] = (
            f"{item.get('reasoning', '')} [Ручная правка: {snapped_qty} {item.get('unit', '')}. "
            f"Причина: {update.adjustment_reason}]"
        )

    return ProcurementItem(**item)
