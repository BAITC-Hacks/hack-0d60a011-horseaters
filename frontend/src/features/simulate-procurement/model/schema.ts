import { z } from "zod";

export const scenarioSchema = z.object({
  growthPercent: z.number().min(0).max(50),
  budget: z.number().int().min(0).max(50_000_000),
  serviceLevel: z.number().int().min(90).max(99),
  delayDays: z.union([z.literal(0), z.literal(14)]),
  injectAnomaly: z.boolean(),
});

export type ScenarioInput = z.infer<typeof scenarioSchema>;
