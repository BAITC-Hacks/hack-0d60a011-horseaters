import { queryOptions } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api";
import {
  adjustRecommendationInputSchema,
  recommendationExplanationSchema,
  recommendationSchema,
  type AdjustRecommendationInput,
} from "../model/schema";

export const recommendationKeys = {
  all: ["recommendation"] as const,
  explanation: (id: string) => [...recommendationKeys.all, id, "explanation"] as const,
};

export function recommendationExplanationQueryOptions(id: string) {
  return queryOptions({
    queryKey: recommendationKeys.explanation(id),
    queryFn: () => apiRequest(`/api/recommendations/${encodeURIComponent(id)}/explain`, recommendationExplanationSchema),
    retry: false,
  });
}

export function adjustRecommendation(id: string, input: AdjustRecommendationInput) {
  const payload = adjustRecommendationInputSchema.parse(input);
  return apiRequest(`/api/recommendations/${encodeURIComponent(id)}`, recommendationSchema, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
