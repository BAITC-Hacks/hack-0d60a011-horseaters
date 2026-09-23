import { z } from "zod";

export const procurementUrgencySchema = z.enum(["NORMAL", "MEDIUM", "HIGH", "CRITICAL"]);
export const procurementItemSchema = z.object({
  id: z.string().min(1),
  sku: z.string().min(1),
  vendor_code: z.string(),
  item_name: z.string().min(1),
  category: z.string(),
  supplier_name: z.string(),
  unit: z.string(),
  current_stock: z.number().finite(),
  in_transit: z.number().finite(),
  transit_details: z.string().nullable(),
  daily_demand: z.number().finite(),
  days_of_stock: z.number().finite().nullable(),
  season_factor: z.number().finite(),
  calculated_need: z.number().finite(),
  adjusted_need: z.number().finite(),
  package_multiplicity: z.number().positive(),
  moq: z.number().positive(),
  unit_price: z.number().finite(),
  total_cost: z.number().finite(),
  urgency: procurementUrgencySchema,
  reasoning: z.string(),
  has_whale_outlier: z.boolean(),
  stockout_recovered: z.boolean(),
});

export const procurementFiltersSchema = z.strictObject({
  supplier: z.string().trim().max(200).optional(),
  urgency: procurementUrgencySchema.optional(),
  search: z.string().trim().max(200).optional(),
});

export const procurementUpdateInputSchema = z.strictObject({
  adjusted_need: z.number().finite().nonnegative(),
  snap_to_multiplicity: z.boolean().default(true),
  adjustment_reason: z.string().trim().min(1).max(2000),
});

export type ProcurementItem = z.infer<typeof procurementItemSchema>;
export type ProcurementFilters = z.infer<typeof procurementFiltersSchema>;
export type ProcurementUpdateInput = z.input<typeof procurementUpdateInputSchema>;
