import { queryOptions } from "@tanstack/react-query";
import { z } from "zod";
import { apiRequest } from "@/shared/api";
import {
  procurementFiltersSchema,
  procurementItemSchema,
  procurementUpdateInputSchema,
  type ProcurementFilters,
  type ProcurementUpdateInput,
} from "../model/schema";

export const procurementItemKeys = {
  all: ["procurement-item"] as const,
  list: (filters: ProcurementFilters = {}) => [...procurementItemKeys.all, "list", filters] as const,
  detail: (id: string) => [...procurementItemKeys.all, "detail", id] as const,
};

export function procurementRecommendationsQueryOptions(input: ProcurementFilters = {}) {
  const filters = procurementFiltersSchema.parse(input);
  return queryOptions({
    queryKey: procurementItemKeys.list(filters),
    queryFn: async () => {
      // The current FastAPI GET route has no query parameters. Filter the returned list locally.
      const items = await apiRequest("/api/v1/procurement/recommendations", z.array(procurementItemSchema));
      const supplier = filters.supplier?.toLocaleLowerCase("ru-RU");
      const search = filters.search?.toLocaleLowerCase("ru-RU");
      return items.filter((item) => {
        if (supplier && !item.supplier_name.toLocaleLowerCase("ru-RU").includes(supplier)) return false;
        if (filters.urgency && item.urgency !== filters.urgency) return false;
        if (search && ![item.sku, item.vendor_code, item.item_name, item.category, item.supplier_name]
          .some((value) => value.toLocaleLowerCase("ru-RU").includes(search))) return false;
        return true;
      });
    },
    retry: false,
  });
}

export function procurementRecommendationQueryOptions(id: string) {
  return queryOptions({
    queryKey: procurementItemKeys.detail(id),
    queryFn: () => apiRequest(`/api/v1/procurement/recommendations/${encodeURIComponent(id)}`, procurementItemSchema),
    retry: false,
  });
}

export function updateProcurementRecommendation(id: string, input: ProcurementUpdateInput) {
  const payload = procurementUpdateInputSchema.parse(input);
  return apiRequest(`/api/v1/procurement/recommendations/${encodeURIComponent(id)}`, procurementItemSchema, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
