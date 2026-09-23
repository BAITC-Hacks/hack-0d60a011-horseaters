import { queryOptions } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api";
import {
  calculationRunSchema,
  createCalculationRunInputSchema,
  runRecommendationFiltersSchema,
  runRecommendationsPageSchema,
  type CreateCalculationRunInput,
  type RunRecommendationFilters,
} from "../model/schema";

export const calculationRunKeys = {
  all: ["calculation-run"] as const,
  detail: (id: string) => [...calculationRunKeys.all, id] as const,
  recommendations: (id: string, filters: RunRecommendationFilters = {}) =>
    [...calculationRunKeys.detail(id), "recommendations", filters] as const,
};

export function calculationRunQueryOptions(id: string) {
  return queryOptions({
    queryKey: calculationRunKeys.detail(id),
    queryFn: () => apiRequest(`/api/calculation-runs/${encodeURIComponent(id)}`, calculationRunSchema),
    retry: false,
  });
}

export function runRecommendationsQueryOptions(id: string, input: RunRecommendationFilters = {}) {
  const filters = runRecommendationFiltersSchema.parse(input);
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null) search.set(key, String(value));
  }
  const suffix = search.size ? `?${search.toString()}` : "";
  return queryOptions({
    queryKey: calculationRunKeys.recommendations(id, filters),
    queryFn: () => apiRequest(`/api/calculation-runs/${encodeURIComponent(id)}/recommendations${suffix}`, runRecommendationsPageSchema),
    retry: false,
  });
}

export function createCalculationRun(input: CreateCalculationRunInput) {
  const payload = createCalculationRunInputSchema.parse(input);
  return apiRequest("/api/calculation-runs", calculationRunSchema, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
