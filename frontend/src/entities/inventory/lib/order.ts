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

export function getSuggestedQuantity(
  item: InventoryItem,
  horizonDays = 30,
  growthMultiplier = 1,
  serviceMultiplier = 1,
  preferAdjusted = true,
): number {
  if (preferAdjusted && horizonDays === 30 && growthMultiplier === 1 && serviceMultiplier === 1 && item.adjusted_need !== undefined) {
    return item.adjusted_need;
  }
  if (preferAdjusted && horizonDays === 30 && growthMultiplier === 1 && serviceMultiplier === 1 && item.calculated_need !== undefined) {
    return item.calculated_need;
  }
  const demand = (item.demand30 / 30) * (Math.max(1, horizonDays) + item.leadDays) * item.growthFactor * item.seasonalityIndex * growthMultiplier;
  const need = Math.max(0, demand + item.minStock * serviceMultiplier + item.materialNeed - item.stock - item.inTransit);
  if (need === 0) return 0;
  return Math.ceil(Math.max(need, item.moq) / item.packSize) * item.packSize;
}
