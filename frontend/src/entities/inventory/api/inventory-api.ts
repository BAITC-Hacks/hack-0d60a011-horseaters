import { queryOptions } from "@tanstack/react-query";
import { z } from "zod";
import { apiRequest } from "@/shared/api";
import { inventoryItemSchema, inventoryUpdateSchema, type InventoryItem, type InventoryUpdate } from "../model";

const backendItemSchema = z.object({
  id: z.string().min(1),
  sku: z.string().min(1),
  vendor_code: z.string(),
  item_name: z.string().min(1),
  category: z.string().min(1),
  supplier_name: z.string().min(1),
  unit: z.string().min(1),
  current_stock: z.number(),
  in_transit: z.number(),
  transit_details: z.string().nullable(),
  daily_demand: z.number(),
  days_of_stock: z.number().nullable(),
  season_factor: z.number(),
  calculated_need: z.number(),
  adjusted_need: z.number(),
  package_multiplicity: z.number(),
  moq: z.number(),
  unit_price: z.number(),
  total_cost: z.number(),
  urgency: z.string(),
  reasoning: z.string(),
  has_whale_outlier: z.boolean(),
  stockout_recovered: z.boolean(),
});

type BackendItem = z.infer<typeof backendItemSchema>;

export const inventoryKeys = {
  all: ["inventory"] as const,
  list: () => [...inventoryKeys.all, "list"] as const,
};

function normalizeItem(item: BackendItem): InventoryItem {
  return inventoryItemSchema.parse({
    ...item,
    name: item.item_name,
    supplier: item.supplier_name,
    stock: item.current_stock,
    inTransit: item.in_transit,
    packSize: item.package_multiplicity,
    unitCost: item.unit_price,
    demand30: item.daily_demand * 30,
    seasonalityIndex: item.season_factor,
    explanation: item.reasoning,
  });
}

export function inventoryQueryOptions() {
  return queryOptions({
    queryKey: inventoryKeys.list(),
    queryFn: async () => (await apiRequest("/api/v1/procurement/recommendations", z.array(backendItemSchema))).map(normalizeItem),
    staleTime: 30_000,
  });
}

export async function updateInventoryItem(id: string, input: InventoryUpdate): Promise<InventoryItem> {
  const payload = inventoryUpdateSchema.parse(input);
  const updated = await apiRequest(`/api/v1/procurement/recommendations/${encodeURIComponent(id)}`, backendItemSchema, {
    method: "PATCH",
    body: JSON.stringify({ adjusted_need: payload.adjusted_need, snap_to_multiplicity: true }),
  });
  return normalizeItem(updated);
}
