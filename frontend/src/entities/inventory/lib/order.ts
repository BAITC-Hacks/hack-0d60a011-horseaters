import type { InventoryItem } from "../model";

export type StockStatus = "critical" | "low" | "healthy";

export function getStockStatus(item: InventoryItem): StockStatus {
  if (item.stock <= item.minStock) return "critical";
  if (item.stock < item.minStock + (item.demand30 / 30) * item.leadDays) return "low";
  return "healthy";
}

export function getSuggestedQuantity(item: InventoryItem): number {
  const need = Math.max(0, item.minStock + (item.demand30 / 30) * item.leadDays - item.stock);
  return Math.ceil(need / item.packSize) * item.packSize;
}
