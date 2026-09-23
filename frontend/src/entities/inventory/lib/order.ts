import type { InventoryItem } from "../model";

export type StockStatus = "critical" | "low" | "healthy";

export function getStockStatus(item: InventoryItem): StockStatus {
  const urgency = item.urgency.toUpperCase();
  if (urgency === "CRITICAL") return "critical";
  if (urgency === "HIGH" || urgency === "MEDIUM" || urgency === "PLANNED") return "low";
  return "healthy";
}
