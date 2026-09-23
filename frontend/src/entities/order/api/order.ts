import { queryOptions } from "@tanstack/react-query";
import { z } from "zod";
import { apiDownload, apiRequest } from "@/shared/api";
import { createOrdersInputSchema, orderExportSchema, orderSchema, type CreateOrdersInput } from "../model/schema";

export const orderKeys = {
  all: ["order"] as const,
  detail: (id: string) => [...orderKeys.all, id] as const,
};

export function orderQueryOptions(id: string) {
  return queryOptions({
    queryKey: orderKeys.detail(id),
    queryFn: () => apiRequest(`/api/orders/${encodeURIComponent(id)}`, orderSchema),
    retry: false,
  });
}

export function createOrders(input: CreateOrdersInput) {
  const payload = createOrdersInputSchema.parse(input);
  return apiRequest("/api/orders", z.array(orderSchema), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function approveOrder(id: string) {
  return apiRequest(`/api/orders/${encodeURIComponent(id)}/approve`, orderSchema, { method: "POST" });
}

export function createOrderExport(id: string) {
  return apiRequest(`/api/orders/${encodeURIComponent(id)}/export`, orderExportSchema, { method: "POST" });
}

export function downloadOrderExport(id: string): Promise<Blob> {
  return apiDownload(`/api/orders/${encodeURIComponent(id)}/export`);
}
