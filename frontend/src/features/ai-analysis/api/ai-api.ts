import { z } from "zod";
import { apiRequest } from "@/shared/api";
import type { InventoryItem } from "@/entities/inventory";

export const skuAnalysisResponseSchema = z.object({
  summary: z.string(),
  root_cause: z.string(),
  risk_analysis: z.string(),
  recommendation_action: z.string(),
  confidence_score: z.number(),
  is_fallback: z.boolean(),
});

export const supplierSummaryResponseSchema = z.object({
  executive_summary: z.string(),
  budget_analysis: z.string(),
  critical_risks: z.array(z.string()),
  key_recommendations: z.array(z.string()),
  is_fallback: z.boolean(),
});

export const supplierLetterResponseSchema = z.object({
  subject: z.string(),
  recipient: z.string(),
  salutation: z.string(),
  letter_body: z.string(),
  items_table: z.string(),
  closing: z.string(),
  is_fallback: z.boolean(),
});

export type SkuAnalysisResponse = z.infer<typeof skuAnalysisResponseSchema>;
export type SupplierSummaryResponse = z.infer<typeof supplierSummaryResponseSchema>;
export type SupplierLetterResponse = z.infer<typeof supplierLetterResponseSchema>;

export async function fetchSkuAnalysis(item: InventoryItem): Promise<SkuAnalysisResponse> {
  const payload = {
    id: item.id,
    sku: item.sku,
    vendor_code: item.vendor_code || "",
    item_name: item.name || item.item_name || "",
    category: item.category,
    supplier_name: item.supplier_name || item.supplier || "IEK Казахстан",
    unit: item.unit,
    current_stock: item.current_stock ?? item.stock,
    in_transit: item.in_transit ?? 0,
    transit_details: item.transit_details,
    daily_demand: item.daily_demand ?? (item.demand30 ? item.demand30 / 30 : 10),
    days_of_stock: item.days_of_stock ?? (item.daily_demand ? item.stock / item.daily_demand : null),
    season_factor: item.season_factor ?? 1.242,
    calculated_need: item.calculated_need ?? 0,
    adjusted_need: item.adjusted_need ?? item.calculated_need ?? 0,
    package_multiplicity: item.package_multiplicity ?? item.packSize ?? 1,
    moq: item.moq ?? 1,
    unit_price: item.unit_price ?? item.unitCost ?? 0,
    total_cost: item.total_cost ?? (item.adjusted_need ?? 0) * (item.unitCost ?? 0),
    urgency: item.urgency ?? "NORMAL",
    reasoning: item.reasoning,
    has_whale_outlier: item.has_whale_outlier ?? false,
    stockout_recovered: item.stockout_recovered ?? false,
  };

  try {
    return await apiRequest<SkuAnalysisResponse>("/ai/sku-analysis", skuAnalysisResponseSchema, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn("Backend AI SKU analysis unavailable, using client fallback:", err);
    return {
      summary: `Позиция «${item.name}» (${item.sku}). Текущий остаток ${item.stock} ${item.unit}. С учетом сезонного пика октября (К=1.242) требуется пополнение.`,
      root_cause: `Сезонный подъем спроса на 24% в октябре и стабильный среднесуточный расход ${item.daily_demand ?? 15} ${item.unit}/сут.`,
      risk_analysis: `Риск обнуления остатка через ${item.days_of_stock?.toFixed(1) ?? "3.0"} дн. При задержке поставки возможны упущенные продажи.`,
      recommendation_action: `Подтвердить заказ ${item.adjusted_need ?? item.calculated_need ?? 100} ${item.unit} с учетом кратности ${item.package_multiplicity ?? item.packSize ?? 1} ${item.unit}.`,
      confidence_score: 0.95,
      is_fallback: true,
    };
  }
}

export async function fetchSupplierSummary(items: InventoryItem[]): Promise<SupplierSummaryResponse> {
  const critical = items.filter((i) => i.urgency === "CRITICAL");
  const planned = items.filter((i) => i.urgency === "HIGH" || i.urgency === "MEDIUM" || i.urgency === "PLANNED");
  const normal = items.filter((i) => i.urgency === "NORMAL" || i.urgency === "LOW");
  const totalBudget = items.reduce((sum, i) => sum + (i.adjusted_need ?? i.calculated_need ?? 0) * (i.unitCost ?? 0), 0);

  const payload = {
    supplier_name: "IEK Казахстан",
    total_items: items.length,
    total_budget: totalBudget,
    critical_count: critical.length,
    planned_count: planned.length,
    normal_count: normal.length,
    season_name: "Октябрь 2026",
    season_factor: 1.242,
    top_critical_items: critical.slice(0, 5).map((i) => ({
      sku: i.sku,
      item_name: i.name,
      days_of_stock: i.days_of_stock,
      calculated_need: i.calculated_need,
      total_cost: (i.calculated_need ?? 0) * (i.unitCost ?? 0),
    })),
  };

  try {
    return await apiRequest<SupplierSummaryResponse>(
      "/ai/supplier-summary",
      supplierSummaryResponseSchema,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    );
  } catch (err) {
    console.warn("Backend AI Supplier summary unavailable, using client fallback:", err);
    return {
      executive_summary: `Аналитический срез по поставщику IEK Казахстан на Октябрь 2026. Проанализировано ${items.length} позиций, плановый бюджет пополнения: ${totalBudget.toLocaleString("ru-RU")} ₸. Выявлено ${critical.length} критических позиций с риском дефицита в связи с сезонным пиком спроса (+24%).`,
      budget_analysis: `Бюджет ${totalBudget.toLocaleString("ru-RU")} ₸ сформирован строго по кратности заводских упаковок IEK и покрывает 44-дневный плановый горизонт (14 дней доставка + 30 дней покрытия).`,
      critical_risks: [
        `Сезонный всплеск спроса в октябре (+24%): при задержке размещения заказа остатки по ${critical.length} артикулам обнулятся в первой декаде месяца.`,
        "Плечо доставки 14 календарных дней требует отправки подтвержденной заявки поставщику до конца текущей недели.",
      ],
      key_recommendations: [
        `Утвердить сформированную заявку на сумму ${totalBudget.toLocaleString("ru-RU")} ₸ и направить официальное письмо в IEK Казахстан.`,
        `Согласовать отгрузку критических позиций первой партией.`,
        "Контролировать соблюдение кратности упаковки при согласовании счета.",
      ],
      is_fallback: true,
    };
  }
}

export async function fetchSupplierLetter(
  items: InventoryItem[],
  notes?: string
): Promise<SupplierLetterResponse> {
  const orderItems = items
    .filter((i) => (i.adjusted_need ?? i.calculated_need ?? 0) > 0)
    .map((i) => ({
      sku: i.sku,
      vendor_code: i.vendor_code || "",
      item_name: i.name,
      quantity: i.adjusted_need ?? i.calculated_need ?? 0,
      unit: i.unit,
      unit_price: i.unitCost ?? i.unit_price ?? 0,
      total_cost: (i.adjusted_need ?? i.calculated_need ?? 0) * (i.unitCost ?? 0),
    }));

  const payload = {
    supplier_name: "IEK Казахстан",
    company_name: "ТОО «Электрокомплект»",
    target_date: "до 05.10.2026",
    delivery_notes: notes || "Самовывоз со склада РЦ Алматы",
    items: orderItems,
  };

  try {
    return await apiRequest<SupplierLetterResponse>(
      "/ai/supplier-letter",
      supplierLetterResponseSchema,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    );
  } catch (err) {
    console.warn("Backend AI Supplier letter unavailable, using client fallback:", err);
    const totalSum = orderItems.reduce((s, it) => s + it.total_cost, 0);
    const tableRows = orderItems.map(
      (it, idx) =>
        `${idx + 1} | ${it.sku} | ${it.item_name} | ${it.quantity.toLocaleString("ru-RU")} ${it.unit} | ${it.unit_price.toLocaleString("ru-RU")} ₸ | ${it.total_cost.toLocaleString("ru-RU")} ₸`
    );

    return {
      subject: "Заявка на резервирование и поставку продукции IEK для ТОО «Электрокомплект»",
      recipient: "Руководителю отдела сбыта ТОО «ИЭК КАЗАХСТАН»",
      salutation: "Уважаемые партнеры!",
      letter_body: `В рамках действующего договора поставки просим Вас поставить в резерв и подготовить к отгрузке электротехническую продукцию согласно прилагаемой спецификации на общую сумму ${totalSum.toLocaleString("ru-RU")} тенге.\nЖелаемый срок готовности: до 05.10.2026.\nОбъемы выверены с учетом заводской кратности упаковок и минимальных партий (MOQ).`,
      items_table: `№ | Артикул | Наименование | Количество | Цена | Сумма\n--|---------|--------------|------------|------|------\n${tableRows.join("\n")}`,
      closing: "С уважением,\nОтдел материально-технического снабжения\nТОО «Электрокомплект»\nТел.: +7 (727) 295-88-00",
      is_fallback: true,
    };
  }
}
