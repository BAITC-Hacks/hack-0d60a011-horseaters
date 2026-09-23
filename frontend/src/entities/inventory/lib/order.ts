import type { InventoryItem } from "../model";

export type StockStatus = "critical" | "low" | "healthy";

export function getStockStatus(item: InventoryItem): StockStatus {
  if (item.stock < (item.demand30 / 30) * item.leadDays) return "critical";
  if (item.stock + item.inTransit < item.minStock + (item.demand30 / 30) * item.leadDays) return "low";
  return "healthy";
}

export function getSuggestedQuantity(item: InventoryItem, horizonDays = 30, growthMultiplier = 1, serviceMultiplier = 1): number {
  const horizon = Math.max(1, horizonDays + item.leadDays);
  const demand = (item.demand30 / 30) * horizon * item.growthFactor * item.seasonalityIndex * growthMultiplier;
  const need = Math.max(0, demand + item.minStock * serviceMultiplier + item.materialNeed - item.stock - item.inTransit);
  if (need === 0) return 0;
  return Math.ceil(Math.max(need, item.moq) / item.packSize) * item.packSize;
}
