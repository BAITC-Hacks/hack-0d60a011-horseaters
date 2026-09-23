import { queryOptions } from "@tanstack/react-query";
import { z } from "zod";
import { apiRequest } from "@/shared/api";

const serverHealthSchema = z.object({ status: z.literal("ok") });
const databaseHealthSchema = serverHealthSchema.extend({ database: z.literal("available") });
const apiHealthSchema = serverHealthSchema.extend({ service: z.string() });

export const systemKeys = {
  all: ["system"] as const,
  serverHealth: ["system", "server-health"] as const,
  databaseHealth: ["system", "database-health"] as const,
  apiHealth: ["system", "api-health"] as const,
};

export function serverHealthQueryOptions() {
  return queryOptions({
    queryKey: systemKeys.serverHealth,
    queryFn: () => apiRequest("/health", serverHealthSchema),
    retry: false,
    refetchInterval: 30_000,
  });
}

export function databaseHealthQueryOptions() {
  return queryOptions({
    queryKey: systemKeys.databaseHealth,
    queryFn: () => apiRequest("/health/db", databaseHealthSchema),
    retry: false,
    refetchInterval: 30_000,
  });
}

export function apiHealthQueryOptions() {
  return queryOptions({
    queryKey: systemKeys.apiHealth,
    queryFn: () => apiRequest("/api/v1/health", apiHealthSchema),
    retry: false,
    refetchInterval: 30_000,
  });
}

// Existing consumers use this name for the versioned FastAPI liveness route.
export const healthQueryOptions = apiHealthQueryOptions;
