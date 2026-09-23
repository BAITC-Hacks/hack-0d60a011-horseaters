import { z } from "zod";
import { apiDateTimeSchema, apiDecimalSchema, apiUuidSchema } from "@/shared/api";

export const orderStatusSchema = z.enum(["draft", "approved", "exported", "cancelled"]);
export const createOrdersInputSchema = z.strictObject({ calculation_run_id: apiUuidSchema });
export const orderItemSchema = z.object({
  id: apiUuidSchema,
  recommendation_id: apiUuidSchema,
  product_id: apiUuidSchema,
  recommended_quantity: apiDecimalSchema,
  approved_quantity: apiDecimalSchema,
  unit_price: apiDecimalSchema.nullable(),
  total_amount: apiDecimalSchema.nullable(),
});
export const orderSchema = z.object({
  id: apiUuidSchema,
  order_number: z.string(),
  supplier_id: apiUuidSchema,
  warehouse_id: apiUuidSchema,
  created_from_run_id: apiUuidSchema,
  status: orderStatusSchema,
  created_by: apiUuidSchema,
  created_at: apiDateTimeSchema,
  approved_by: apiUuidSchema.nullable(),
  approved_at: apiDateTimeSchema.nullable(),
  exported_at: apiDateTimeSchema.nullable(),
  items: z.array(orderItemSchema),
});
export const orderExportSchema = z.object({
  id: apiUuidSchema,
  purchase_order_id: apiUuidSchema,
  format: z.literal("xlsx"),
  file_name: z.string(),
  file_checksum: z.string(),
  created_by: apiUuidSchema,
  created_at: apiDateTimeSchema,
});

export type Order = z.infer<typeof orderSchema>;
export type OrderExport = z.infer<typeof orderExportSchema>;
export type CreateOrdersInput = z.infer<typeof createOrdersInputSchema>;
