import type { InventoryItem } from "../model";

export type StockStatus = "critical" | "low" | "healthy";

export function getStockStatus(item: InventoryItem): StockStatus {
  if (item.urgency) {
    const u = item.urgency.toUpperCase();
    if (u === "CRITICAL") return "critical";
    if (u === "HIGH" || u === "MEDIUM" || u === "PLANNED") return "low";
    return "healthy";
  }
  const min = item.minStock ?? 0;
  const lead = item.leadDays ?? 14;
  const demand = item.demand30 ?? 0;
  if (item.stock <= min) return "critical";
  if (item.stock < min + (demand / 30) * lead) return "low";
  return "healthy";
}

export function getSuggestedQuantity(item: InventoryItem): number {
  if (item.adjusted_need !== undefined && item.adjusted_need !== null) {
    return item.adjusted_need;
  }
  if (item.calculated_need !== undefined && item.calculated_need !== null) {
    return item.calculated_need;
  }
  const min = item.minStock ?? 0;
  const lead = item.leadDays ?? 14;
  const demand = item.demand30 ?? 0;
  const pack = item.package_multiplicity ?? item.packSize ?? 1;
  const need = Math.max(0, min + (demand / 30) * lead - item.stock);
  return Math.ceil(need / pack) * pack;
}
