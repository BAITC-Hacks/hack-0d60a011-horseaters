import { queryOptions } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api";
import { createBuyerInputSchema, loginInputSchema, loginResultSchema, userSchema, type CreateBuyerInput, type LoginInput } from "../model/schema";

export const userKeys = { me: ["auth", "me"] as const };
export function currentUserQueryOptions() {
  return queryOptions({ queryKey: userKeys.me, queryFn: () => apiRequest("/api/auth/me", userSchema), retry: false, staleTime: 30_000 });
}
export function login(input: LoginInput) {
  const payload = loginInputSchema.parse(input);
  return apiRequest("/api/auth/login", loginResultSchema, { method: "POST", body: JSON.stringify(payload) });
}
export function logout() {
  return apiRequest("/api/auth/logout", zodSuccessSchema, { method: "POST" });
}
export function createBuyer(input: CreateBuyerInput) {
  return apiRequest("/api/auth/users", userSchema, { method: "POST", body: JSON.stringify(createBuyerInputSchema.parse(input)) });
}
import { z } from "zod";
const zodSuccessSchema = z.object({ success: z.literal(true) });
