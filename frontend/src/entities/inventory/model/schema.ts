import { z } from "zod";

export const inventoryItemSchema = z.object({
  id: z.string().min(1),
  sku: z.string().min(1),
  vendor_code: z.string().optional().default(""),
  name: z.string().min(1),
  item_name: z.string().optional(),
  category: z.string().min(1),
  supplier: z.string().min(1),
  supplier_name: z.string().optional().default("IEK Казахстан"),
  unit: z.string().min(1),

  // Stock and Transit
  stock: z.number().nonnegative(),
  current_stock: z.number().optional(),
  in_transit: z.number().optional().default(0),
  transit_details: z.string().nullable().optional(),

  // Demand and Horizon
  minStock: z.number().nonnegative().optional(),
  demand30: z.number().nonnegative().optional(),
  daily_demand: z.number().optional(),
  days_of_stock: z.number().nullable().optional(),
  season_factor: z.number().optional().default(1.242),
  leadDays: z.number().positive().optional(),

  // Ordering and Financials
  packSize: z.number().positive().optional().default(1),
  package_multiplicity: z.number().optional().default(1),
  moq: z.number().optional().default(1),
  unitCost: z.number().nonnegative().optional().default(0),
  unit_price: z.number().optional().default(0),
  total_cost: z.number().optional().default(0),
  calculated_need: z.number().optional().default(0),
  adjusted_need: z.number().optional().default(0),

  // Analytics & Operational flags
  urgency: z.string().optional().default("NORMAL"),
  reasoning: z.string().optional().default(""),
  has_whale_outlier: z.boolean().optional().default(false),
  stockout_recovered: z.boolean().optional().default(false),
});

export const inventoryListSchema = z.array(inventoryItemSchema);

export const inventoryUpdateSchema = z.object({
  adjusted_need: z.number().nonnegative().optional(),
  minStock: z.number().int().nonnegative().optional(),
  demand30: z.number().int().nonnegative().optional(),
  leadDays: z.number().int().positive().optional(),
  packSize: z.number().int().positive().optional(),
  unitCost: z.number().nonnegative().optional(),
});

export type InventoryItem = z.infer<typeof inventoryItemSchema>;
export type InventoryUpdate = z.infer<typeof inventoryUpdateSchema>;
