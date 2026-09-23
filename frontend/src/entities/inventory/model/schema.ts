import { z } from "zod";

export const inventoryItemSchema = z.object({
  id: z.string().min(1),
  sku: z.string().min(1),
  name: z.string().min(1),
  category: z.string().min(1),
  supplier: z.string().min(1),
  unit: z.string().min(1),
  stock: z.number().int().nonnegative(),
  minStock: z.number().int().nonnegative(),
  demand30: z.number().int().nonnegative(),
  leadDays: z.number().int().positive(),
  packSize: z.number().int().positive(),
  unitCost: z.number().nonnegative(),
  inTransit: z.number().int().nonnegative(),
  materialNeed: z.number().int().nonnegative(),
  moq: z.number().int().nonnegative(),
  supplierMinOrder: z.number().nonnegative(),
  warehouse: z.string().min(1),
  riskScore: z.number().min(0).max(1),
  anomalyCount: z.number().int().nonnegative(),
  anomalyAdjustment: z.number(),
  stockoutAdjustment: z.number().nonnegative(),
  growthFactor: z.number().positive(),
  seasonalityIndex: z.number().positive(),
  explanation: z.string().min(1),
  status: z.enum(["suggested", "approved"]),
  approvedQuantity: z.number().int().nonnegative().nullable(),
  approvedAt: z.iso.datetime().nullable(),
  approvedBy: z.string().min(1).nullable(),
});

export const inventoryListSchema = z.array(inventoryItemSchema);

export const inventoryUpdateSchema = inventoryItemSchema.pick({
  minStock: true,
  demand30: true,
  leadDays: true,
  packSize: true,
  unitCost: true,
});

export type InventoryItem = z.infer<typeof inventoryItemSchema>;
export type InventoryUpdate = z.infer<typeof inventoryUpdateSchema>;
