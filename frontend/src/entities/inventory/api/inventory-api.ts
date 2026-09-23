import { queryOptions } from "@tanstack/react-query";
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
  });
}

async function getInventory(): Promise<InventoryItem[]> {
  if (demoMode) {
    return demoRows.map((item) => ({ ...item }));
  }

  try {
    const data = await apiRequest<InventoryItem[]>(
      "/procurement/recommendations",
      inventoryListSchema
    );
    if (Array.isArray(data) && data.length > 0) {
      demoRows = data.map((item) => normalizeItem(item as unknown as Record<string, unknown>));
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

  // If connected to live backend, call PATCH
  if (!demoMode) {
    try {
      const updated = await apiRequest<InventoryItem>(
        `/procurement/recommendations/${encodeURIComponent(id)}`,
        inventoryItemSchema,
        {
          method: "PATCH",
          body: JSON.stringify({
            adjusted_need: payload.adjusted_need,
            snap_to_multiplicity: true,
          }),
        }
      );
      const normalized = normalizeItem(updated as unknown as Record<string, unknown>);
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
