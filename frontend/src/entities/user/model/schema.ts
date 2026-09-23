import { z } from "zod";

export const userRoleSchema = z.enum(["buyer", "admin"]);
export const userSchema = z.object({
  id: z.string().uuid(),
  username: z.string(),
  display_name: z.string(),
  role: userRoleSchema,
});
export const loginInputSchema = z.strictObject({ username: z.string().trim().min(1), password: z.string().min(1) });
export const loginResultSchema = z.object({ token_type: z.literal("bearer"), expires_in: z.number().positive() });
export const createBuyerInputSchema = z.strictObject({ username: z.string().trim().min(1).max(100), display_name: z.string().trim().min(1).max(200), password: z.string().min(8).max(256) });
export type User = z.infer<typeof userSchema>;
export type LoginInput = z.infer<typeof loginInputSchema>;
export type CreateBuyerInput = z.infer<typeof createBuyerInputSchema>;
