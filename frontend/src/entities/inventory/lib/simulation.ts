import type { InventoryItem } from "../model";
import { getSuggestedQuantity } from "./order";

export type ScenarioParams = { horizonDays: number; growthPercent: number; budget: number; serviceLevel: number; delayDays: number; injectAnomaly: boolean };
export type ScenarioRow = { item: InventoryItem; quantity: number; cost: number; included: boolean; urgency: number };
export type ScenarioResult = { rows: ScenarioRow[]; baselineCost: number; scenarioCost: number; selectedCost: number; riskCount: number; excludedCount: number; anomalyNaiveExtra: number };

export function simulateScenario(items: InventoryItem[], params: ScenarioParams): ScenarioResult {
  const serviceMultiplier = 1 + (params.serviceLevel - 95) * 0.06;
  const rows = items.map((item) => {
    const delayed = { ...item, leadDays: item.leadDays + params.delayDays };
    const quantity = getSuggestedQuantity(delayed, params.horizonDays, 1 + params.growthPercent / 100, serviceMultiplier);
    return { item, quantity, cost: quantity * item.unitCost, included: false, urgency: item.riskScore + (item.stock < (item.demand30 / 30) * delayed.leadDays ? 0.4 : 0) };
  }).sort((a, b) => b.urgency - a.urgency || b.item.demand30 * b.item.unitCost - a.item.demand30 * a.item.unitCost);

  let selectedCost = 0;
  for (const row of rows) {
    if (row.quantity > 0 && selectedCost + row.cost <= params.budget) {
      row.included = true;
      selectedCost += row.cost;
    }
  }
  const baselineCost = items.reduce((sum, item) => sum + getSuggestedQuantity(item, params.horizonDays) * item.unitCost, 0);
  const scenarioCost = rows.reduce((sum, row) => sum + row.cost, 0);
  const riskCount = items.filter((item) => item.stock < (item.demand30 / 30) * (item.leadDays + params.delayDays)).length;
  const excludedCount = rows.filter((row) => row.quantity > 0 && !row.included).length;
  const firstWithAnomaly = items.find((item) => item.anomalyCount > 0);
  const anomalyNaiveExtra = params.injectAnomaly && firstWithAnomaly
    ? Math.ceil(5_000 / firstWithAnomaly.packSize) * firstWithAnomaly.packSize * firstWithAnomaly.unitCost
    : 0;
  return { rows, baselineCost, scenarioCost, selectedCost, riskCount, excludedCount, anomalyNaiveExtra };
}
