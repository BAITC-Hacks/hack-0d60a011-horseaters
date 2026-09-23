import { z } from "zod";

export const inventoryItemSchema = z.object({
  id: z.string().min(1),
  sku: z.string().min(1),
  vendor_code: z.string(),
  name: z.string().min(1),
  item_name: z.string().min(1),
  category: z.string().min(1),
  supplier: z.string().min(1),
  supplier_name: z.string().min(1),
  unit: z.string().min(1),
  stock: z.number(),
  current_stock: z.number(),
  in_transit: z.number(),
  inTransit: z.number(),
  transit_details: z.string().nullable(),
  daily_demand: z.number(),
  demand30: z.number(),
  days_of_stock: z.number().nullable(),
  season_factor: z.number(),
  seasonalityIndex: z.number(),
  calculated_need: z.number(),
  adjusted_need: z.number(),
  package_multiplicity: z.number().positive(),
  packSize: z.number().positive(),
  moq: z.number().nonnegative(),
  unit_price: z.number(),
  unitCost: z.number(),
  total_cost: z.number(),
  urgency: z.string(),
  reasoning: z.string(),
  explanation: z.string(),
  has_whale_outlier: z.boolean(),
  stockout_recovered: z.boolean(),
});

export const inventoryListSchema = z.array(inventoryItemSchema);
export const inventoryUpdateSchema = z.object({ adjusted_need: z.number().finite().nonnegative() });

export type InventoryItem = z.infer<typeof inventoryItemSchema>;
export type InventoryUpdate = z.infer<typeof inventoryUpdateSchema>;
