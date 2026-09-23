import type { InventoryItem } from "../model";

type DemoItem = Pick<InventoryItem,
  "id" | "sku" | "name" | "category" | "supplier" | "unit" | "stock" | "minStock" |
  "demand30" | "leadDays" | "packSize" | "unitCost" | "inTransit" | "moq" |
  "supplierMinOrder" | "riskScore" | "anomalyCount" | "anomalyAdjustment" |
  "stockoutAdjustment" | "explanation"
> & Partial<Pick<InventoryItem, "materialNeed" | "warehouse" | "growthFactor" | "seasonalityIndex" | "status">>;

function item(input: DemoItem): InventoryItem {
  return {
    materialNeed: 0,
    warehouse: "Алматы",
    growthFactor: 1.04,
    seasonalityIndex: 1.08,
    status: "suggested",
    approvedQuantity: null,
    approvedAt: null,
    approvedBy: null,
    ...input,
  };
}

export const demoInventory: InventoryItem[] = [
  item({ id: "iek-1", sku: "MVA20-1-016-C", name: "Автоматический выключатель ВА47-29 1P C16", category: "Автоматика", supplier: "IEK", unit: "шт", stock: 10, minStock: 100, demand30: 1200, leadDays: 14, packSize: 50, moq: 100, unitCost: 1950, inTransit: 0, supplierMinOrder: 500000, riskScore: 0.98, anomalyCount: 2, anomalyAdjustment: -180, stockoutAdjustment: 85, explanation: "Регулярный спрос — 40 шт./день. При остатке 10 шт. дефицит наступит завтра, поставка IEK занимает 14 дней." }),
  item({ id: "iek-2", sku: "CSP-4X2.5-100", name: "Кабель ВВГнг(А)-LS 4×2,5", category: "Кабель", supplier: "IEK", unit: "м", stock: 280, minStock: 450, demand30: 2250, leadDays: 14, packSize: 100, moq: 500, unitCost: 480, inTransit: 300, supplierMinOrder: 500000, riskScore: 0.86, anomalyCount: 3, anomalyAdjustment: -5000, stockoutAdjustment: 120, explanation: "Крупная проектная отгрузка 5 000 м исключена из регулярного спроса. В пути 300 м, ожидается устойчивый расход 75 м/день." }),
  item({ id: "sch-1", sku: "A9F74116", name: "Автоматический выключатель iC60N 1P C16", category: "Автоматика", supplier: "Schneider Electric", unit: "шт", stock: 44, minStock: 60, demand30: 210, leadDays: 45, packSize: 12, moq: 24, unitCost: 10200, inTransit: 24, supplierMinOrder: 1500000, riskScore: 0.91, anomalyCount: 0, anomalyAdjustment: 0, stockoutAdjustment: 18, explanation: "Длинное плечо поставки — 45 дней. Даже с 24 шт. в пути запас не покрывает прогнозный спрос." }),
  item({ id: "iek-3", sku: "LDVO0-6510-40-6000", name: "Светильник светодиодный ДВО 36 Вт", category: "Светотехника", supplier: "IEK", unit: "шт", stock: 100, minStock: 80, demand30: 135, leadDays: 14, packSize: 10, moq: 20, unitCost: 11900, inTransit: 40, supplierMinOrder: 500000, riskScore: 0.21, anomalyCount: 1, anomalyAdjustment: -40, stockoutAdjustment: 0, explanation: "При обычном сроке поставки запас покрывает текущий спрос. Задержка на 14 дней переведёт позицию в зону риска." }),
  item({ id: "keaz-1", sku: "110223-001", name: "Контактор ПМЛ-1100 10А 220В", category: "Автоматика", supplier: "КЭАЗ", unit: "шт", stock: 35, minStock: 50, demand30: 90, leadDays: 21, packSize: 10, moq: 20, unitCost: 8700, inTransit: 20, supplierMinOrder: 700000, riskScore: 0.72, anomalyCount: 0, anomalyAdjustment: 0, stockoutAdjustment: 8, explanation: "Остаток близок к страховой границе; 20 шт. в пути учтены при расчёте потребности." }),
  item({ id: "tdm-1", sku: "SQ0326-0004", name: "Розетка одноместная с заземлением 16А", category: "Электроустановка", supplier: "TDM Electric", unit: "шт", stock: 420, minStock: 200, demand30: 360, leadDays: 7, packSize: 50, moq: 100, unitCost: 1700, inTransit: 100, supplierMinOrder: 400000, riskScore: 0.3, anomalyCount: 0, anomalyAdjustment: 0, stockoutAdjustment: 0, explanation: "Текущий остаток и 100 шт. в пути дают достаточный запас для обычного спроса." }),
  item({ id: "iek-4", sku: "YKM40-01-54", name: "Щит распределительный ЩРН-12 IP54", category: "Щитовое оборудование", supplier: "IEK", unit: "шт", stock: 8, minStock: 20, demand30: 72, leadDays: 14, packSize: 5, moq: 10, unitCost: 23500, inTransit: 0, supplierMinOrder: 500000, riskScore: 0.94, anomalyCount: 1, anomalyAdjustment: -12, stockoutAdjustment: 6, explanation: "При расходе 2,4 шт./день товар закончится до прихода следующей поставки. Требуется ускорение заказа." }),
  item({ id: "sch-2", sku: "LC1D18M7", name: "Контактор TeSys D 18А 220В", category: "Автоматика", supplier: "Schneider Electric", unit: "шт", stock: 27, minStock: 30, demand30: 45, leadDays: 45, packSize: 6, moq: 12, unitCost: 27400, inTransit: 12, supplierMinOrder: 1500000, riskScore: 0.67, anomalyCount: 0, anomalyAdjustment: 0, stockoutAdjustment: 3, explanation: "Запас на длинное плечо поставки недостаточен; 12 шт. в пути уменьшают размер новой заявки." }),
  item({ id: "iek-5", sku: "YNN10-69-20", name: "Клеммная колодка 20А, 12 пар", category: "Электроустановка", supplier: "IEK", unit: "шт", stock: 510, minStock: 250, demand30: 300, leadDays: 14, packSize: 100, moq: 200, unitCost: 1150, inTransit: 0, supplierMinOrder: 500000, riskScore: 0.18, anomalyCount: 0, anomalyAdjustment: 0, stockoutAdjustment: 0, explanation: "Резерв превышает потребность на ближайший цикл поставки." }),
  item({ id: "keaz-2", sku: "250033-012", name: "Выключатель ВА57-35 250А", category: "Автоматика", supplier: "КЭАЗ", unit: "шт", stock: 5, minStock: 10, demand30: 18, leadDays: 21, packSize: 2, moq: 4, unitCost: 89500, inTransit: 2, supplierMinOrder: 700000, riskScore: 0.82, anomalyCount: 1, anomalyAdjustment: -3, stockoutAdjustment: 2, explanation: "Высокая стоимость и малый остаток. Требуется пополнение, партия кратна 2 шт." }),
  item({ id: "tdm-2", sku: "SQ1501-0001", name: "Кабель-канал 40×25, 2 м", category: "Кабель", supplier: "TDM Electric", unit: "шт", stock: 230, minStock: 120, demand30: 160, leadDays: 7, packSize: 20, moq: 40, unitCost: 3200, inTransit: 0, supplierMinOrder: 400000, riskScore: 0.35, anomalyCount: 1, anomalyAdjustment: -80, stockoutAdjustment: 0, explanation: "Разовая крупная отгрузка исключена; обычный спрос не требует внеплановой закупки." }),
  item({ id: "iek-6", sku: "LSM14-10-10", name: "Лампа светодиодная 10 Вт E27", category: "Светотехника", supplier: "IEK", unit: "шт", stock: 60, minStock: 100, demand30: 420, leadDays: 14, packSize: 50, moq: 100, unitCost: 1450, inTransit: 100, supplierMinOrder: 500000, riskScore: 0.77, anomalyCount: 2, anomalyAdjustment: -90, stockoutAdjustment: 25, explanation: "Сезонный рост спроса учтён, 100 шт. в пути вычтены из дополнительной потребности." }),
];
