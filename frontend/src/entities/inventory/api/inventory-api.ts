import { queryOptions } from "@tanstack/react-query";
import { z } from "zod";
import { apiRequest } from "@/shared/api";
import { demoInventory } from "./demo-data";
import {
  inventoryItemSchema,
  inventoryListSchema,
  inventoryUpdateSchema,
  type InventoryItem,
  type InventoryUpdate,
} from "../model";

const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
let demoRows: InventoryItem[] = demoInventory.map((item) => ({ ...item }));
const demoStorageKey = "electrokomplekt-procurement-demo-v1";
const rawItemSchema = z.record(z.string(), z.unknown());

function readDemoRows(): InventoryItem[] {
  if (typeof window === "undefined") return demoRows.map((item) => ({ ...item }));
  try {
    const saved = window.localStorage.getItem(demoStorageKey);
    if (saved) {
      const parsed = inventoryListSchema.safeParse(JSON.parse(saved));
      if (parsed.success) demoRows = parsed.data;
    }
  } catch {
    // Browser storage is optional; the in-memory demo remains available.
  }
  return demoRows.map((item) => ({ ...item }));
}

function saveDemoRows(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(demoStorageKey, JSON.stringify(demoRows));
  } catch {
    // Continue with the in-memory demo when storage is unavailable.
  }
}

export const inventoryKeys = {
  all: ["inventory"] as const,
  list: () => [...inventoryKeys.all, "list"] as const,
};

export function inventoryQueryOptions() {
  return queryOptions({
    queryKey: inventoryKeys.list(),
    queryFn: getInventory,
    staleTime: 0,
    refetchOnMount: "always",
  });
}

function normalizeItem(raw: Record<string, unknown>): InventoryItem {
  const name = String(raw.item_name || raw.name || "");
  const supplier = String(raw.supplier_name || raw.supplier || "IEK Казахстан");
  const stock = Number(raw.current_stock ?? raw.stock ?? 0);
  const packSize = Number(raw.package_multiplicity ?? raw.packSize ?? 1);
  const unitCost = Number(raw.unit_price ?? raw.unitCost ?? 0);
  const calculated_need = Number(raw.calculated_need ?? 0);
  const adjusted_need = Number(raw.adjusted_need ?? calculated_need);
  const urgency = String(raw.urgency ?? "NORMAL").toUpperCase();

  return inventoryItemSchema.parse({
    ...raw,
    name,
    supplier,
    stock,
    packSize,
    package_multiplicity: packSize,
    unitCost,
    unit_price: unitCost,
    calculated_need,
    adjusted_need,
    demand30: Number(raw.demand30 ?? Number(raw.daily_demand ?? 0) * 30),
    inTransit: Number(raw.inTransit ?? raw.in_transit ?? 0),
    supplierMinOrder: Number(raw.supplierMinOrder ?? 500_000),
    riskScore: Number(raw.riskScore ?? (urgency === "CRITICAL" ? 0.95 : urgency === "HIGH" ? 0.75 : urgency === "MEDIUM" ? 0.5 : 0.15)),
    anomalyCount: Number(raw.anomalyCount ?? (raw.has_whale_outlier ? 1 : 0)),
    seasonalityIndex: Number(raw.seasonalityIndex ?? raw.season_factor ?? 1),
    explanation: String(raw.explanation ?? raw.reasoning ?? ""),
  });
}

async function getInventory(): Promise<InventoryItem[]> {
  if (demoMode) {
    return readDemoRows();
  }

  try {
    const data = await apiRequest(
      "/procurement/recommendations",
      z.array(rawItemSchema)
    );
    if (Array.isArray(data) && data.length > 0) {
      demoRows = data.map(normalizeItem);
      return demoRows.map((item) => ({ ...item }));
    }
  } catch (err) {
    console.warn("Backend procurement API unavailable, falling back to local dataset:", err);
  }

  return demoRows.map((item) => ({ ...item }));
}

export async function updateInventoryItem(
  id: string,
  input: InventoryUpdate
): Promise<InventoryItem> {
  const payload = inventoryUpdateSchema.parse(input);
  if (demoMode) readDemoRows();

  // If connected to live backend, call PATCH
  if (!demoMode) {
    try {
      const updated = await apiRequest(
        `/procurement/recommendations/${encodeURIComponent(id)}`,
        rawItemSchema,
        {
          method: "PATCH",
          body: JSON.stringify({
            adjusted_need: payload.adjusted_need,
            snap_to_multiplicity: true,
          }),
        }
      );
      const normalized = normalizeItem(updated);
      demoRows = demoRows.map((item) => (item.id === id ? normalized : item));
      return normalized;
    } catch (err) {
      console.warn("PATCH to backend failed, applying locally:", err);
    }
  }

  // Local fallback mutation
  const index = demoRows.findIndex((item) => item.id === id);
  if (index < 0) throw new Error("Позиция не найдена.");

  const current = demoRows[index];
  let adjustedQty = payload.adjusted_need ?? current.adjusted_need ?? 0;
  const mult = current.package_multiplicity ?? current.packSize ?? 1;
  if (adjustedQty > 0 && mult > 1) {
    adjustedQty = Math.ceil(adjustedQty / mult) * mult;
  }

  const updated: InventoryItem = {
    ...current,
    ...payload,
    adjusted_need: adjustedQty,
    total_cost: adjustedQty * (current.unitCost ?? current.unit_price ?? 0),
  };

  demoRows = demoRows.map((item) => (item.id === id ? updated : item));
  if (demoMode) saveDemoRows();
  return { ...updated };
}

export async function approveInventoryItems(quantities: Record<string, number>): Promise<InventoryItem[]> {
  const ids = Object.keys(quantities);
  if (ids.length === 0) throw new Error("Выберите хотя бы одну позицию.");
  if (demoMode) {
    readDemoRows();
    for (const id of ids) {
      const item = demoRows.find((row) => row.id === id);
      if (!item) throw new Error(`Позиция ${id} не найдена.`);
      if (item.status === "approved") throw new Error(`Позиция ${item.sku} уже утверждена.`);
      const quantity = quantities[id];
      if (!Number.isSafeInteger(quantity) || quantity <= 0 || quantity < item.moq || quantity % item.packSize !== 0) {
        throw new Error(`Количество для ${item.sku} должно быть положительным, не меньше MOQ и кратным упаковке ${item.packSize}.`);
      }
    }
    const approvedAt = new Date().toISOString();
    demoRows = demoRows.map((item) => ids.includes(item.id) ? { ...item, status: "approved" as const, approvedQuantity: quantities[item.id], approvedAt, approvedBy: "Менеджер закупок (демо)" } : item);
    saveDemoRows();
    return demoRows.filter((item) => ids.includes(item.id));
  }
  throw new Error("Утверждение через FastAPI будет доступно после публикации маршрутов заказов.");
}
