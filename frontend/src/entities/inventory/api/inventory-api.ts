import { queryOptions } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api";
import { demoInventory } from "./demo-data";
import { inventoryItemSchema, inventoryListSchema, inventoryUpdateSchema, type InventoryItem, type InventoryUpdate } from "../model";

const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";
let demoRows = demoInventory.map((item) => ({ ...item }));

export const inventoryKeys = {
  all: ["inventory"] as const,
  list: () => [...inventoryKeys.all, "list"] as const,
};

export function inventoryQueryOptions() {
  return queryOptions({
    queryKey: inventoryKeys.list(),
    queryFn: getInventory,
    staleTime: 60_000,
  });
}

async function getInventory(): Promise<InventoryItem[]> {
  if (demoMode) return demoRows.map((item) => ({ ...item }));
  return apiRequest("/api/v1/inventory", inventoryListSchema);
}

export async function updateInventoryItem(id: string, input: InventoryUpdate): Promise<InventoryItem> {
  const payload = inventoryUpdateSchema.parse(input);
  if (demoMode) {
    const index = demoRows.findIndex((item) => item.id === id);
    if (index < 0) throw new Error("Позиция не найдена.");
    const updated = inventoryItemSchema.parse({ ...demoRows[index], ...payload });
    demoRows = demoRows.map((item) => item.id === id ? updated : item);
    return { ...updated };
  }
  return apiRequest(`/api/v1/inventory/${encodeURIComponent(id)}`, inventoryItemSchema, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
