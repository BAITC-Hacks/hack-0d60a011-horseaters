import { queryOptions } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api";
import { demoInventory } from "./demo-data";
import { inventoryItemSchema, inventoryListSchema, inventoryUpdateSchema, type InventoryItem, type InventoryUpdate } from "../model";

const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";
let demoRows = demoInventory.map((item) => ({ ...item }));
const demoStorageKey = "stockwise-procurement-demo-v4";

function readDemoRows(): InventoryItem[] {
  if (typeof window === "undefined") return demoRows.map((item) => ({ ...item }));
  try {
    const saved = window.localStorage.getItem(demoStorageKey);
    if (!saved) return demoRows.map((item) => ({ ...item }));
    const parsed = inventoryListSchema.safeParse(JSON.parse(saved));
    if (parsed.success) {
      demoRows = parsed.data;
      return parsed.data.map((item) => ({ ...item }));
    }
  } catch { /* Session storage is optional in the demo. */ }
  return demoRows.map((item) => ({ ...item }));
}

function saveDemoRows(): void {
  if (typeof window === "undefined") return;
  try { window.localStorage.setItem(demoStorageKey, JSON.stringify(demoRows)); }
  catch { /* In-memory demo remains usable when storage is unavailable. */ }
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

async function getInventory(): Promise<InventoryItem[]> {
  if (demoMode) return readDemoRows();
  return apiRequest("/api/v1/inventory", inventoryListSchema);
}

export async function updateInventoryItem(id: string, input: InventoryUpdate): Promise<InventoryItem> {
  const payload = inventoryUpdateSchema.parse(input);
  if (demoMode) {
    const index = demoRows.findIndex((item) => item.id === id);
    if (index < 0) throw new Error("Позиция не найдена.");
    const updated = inventoryItemSchema.parse({ ...demoRows[index], ...payload });
    demoRows = demoRows.map((item) => item.id === id ? updated : item);
    saveDemoRows();
    return { ...updated };
  }
  return apiRequest(`/api/v1/inventory/${encodeURIComponent(id)}`, inventoryItemSchema, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
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
