import { z } from "zod";
import { apiRequest } from "@/shared/api";
import type { InventoryItem } from "@/entities/inventory";

export const skuAnalysisResponseSchema = z.object({
  summary: z.string(),
  root_cause: z.string(),
  risk_analysis: z.string(),
  recommendation_action: z.string(),
  confidence_score: z.number().min(0).max(1),
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

export function fetchSkuAnalysis(item: InventoryItem): Promise<SkuAnalysisResponse> {
  return apiRequest("/api/v1/ai/sku-analysis", skuAnalysisResponseSchema, {
    method: "POST",
    body: JSON.stringify({
      id: item.id,
      sku: item.sku,
      vendor_code: item.vendor_code,
      item_name: item.item_name ?? item.name,
      category: item.category,
      supplier_name: item.supplier_name,
      unit: item.unit,
      current_stock: item.current_stock,
      in_transit: item.in_transit,
      transit_details: item.transit_details,
      daily_demand: item.daily_demand,
      days_of_stock: item.days_of_stock,
      season_factor: item.season_factor,
      calculated_need: item.calculated_need,
      adjusted_need: item.adjusted_need,
      package_multiplicity: item.package_multiplicity,
      moq: item.moq,
      unit_price: item.unit_price,
      total_cost: item.total_cost,
      urgency: item.urgency,
      reasoning: item.reasoning,
      has_whale_outlier: item.has_whale_outlier,
      stockout_recovered: item.stockout_recovered,
    }),
  });
}

export function fetchSupplierSummary(items: InventoryItem[]): Promise<SupplierSummaryResponse> {
  const critical = items.filter((item) => item.urgency === "CRITICAL");
  const planned = items.filter((item) => ["HIGH", "MEDIUM", "PLANNED"].includes(item.urgency));
  const normal = items.filter((item) => ["NORMAL", "LOW"].includes(item.urgency));
  const totalBudget = items.reduce((sum, item) => sum + item.adjusted_need * item.unit_price, 0);
  return apiRequest("/api/v1/ai/supplier-summary", supplierSummaryResponseSchema, {
    method: "POST",
    body: JSON.stringify({
      supplier_name: items[0]?.supplier_name ?? "",
      total_items: items.length,
      total_budget: totalBudget,
      critical_count: critical.length,
      planned_count: planned.length,
      normal_count: normal.length,
      season_name: "Текущий расчёт",
      season_factor: items.length > 0 ? items.reduce((sum, item) => sum + item.season_factor, 0) / items.length : 1,
      top_critical_items: critical.slice(0, 5).map((item) => ({
        sku: item.sku,
        item_name: item.item_name,
        days_of_stock: item.days_of_stock,
        calculated_need: item.calculated_need,
        total_cost: item.total_cost,
      })),
    }),
  });
}

export function fetchSupplierLetter(items: InventoryItem[], notes?: string): Promise<SupplierLetterResponse> {
  const orderItems = items.filter((item) => item.adjusted_need > 0).map((item) => ({
    sku: item.sku,
    vendor_code: item.vendor_code,
    item_name: item.item_name,
    quantity: item.adjusted_need,
    unit: item.unit,
    unit_price: item.unit_price,
    total_cost: item.adjusted_need * item.unit_price,
  }));
  return apiRequest("/api/v1/ai/supplier-letter", supplierLetterResponseSchema, {
    method: "POST",
    body: JSON.stringify({
      supplier_name: items[0]?.supplier_name ?? "",
      company_name: "ТОО «Электрокомплект»",
      delivery_notes: notes ?? null,
      items: orderItems,
    }),
  });
}
