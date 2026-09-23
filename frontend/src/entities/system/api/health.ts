import { queryOptions } from "@tanstack/react-query";
import { z } from "zod";
import { apiRequest } from "@/shared/api";

const healthSchema = z.object({ status: z.literal("ok"), service: z.string() });

export function healthQueryOptions() {
  return queryOptions({
    queryKey: ["system", "health"] as const,
    queryFn: () => apiRequest("/api/v1/health", healthSchema),
    retry: false,
    refetchInterval: 30_000,
  });
}
