import { z } from "zod";

export const runCalculationSchema = z.strictObject({
  demand_source: z.enum(["transactions", "monthly_sales"]),
  horizon_days: z.number().int("Укажите целое число дней.").min(1, "Минимум 1 день.").max(365, "Максимум 365 дней."),
  warehouse_id: z.uuid("Некорректный ID склада.").nullable().optional(),
  category_id: z.uuid("Некорректный ID категории.").nullable().optional(),
});

export type RunCalculationInput = z.infer<typeof runCalculationSchema>;
