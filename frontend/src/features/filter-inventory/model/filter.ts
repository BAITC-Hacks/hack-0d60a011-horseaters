import { z } from "zod";
import { getStockStatus, type InventoryItem } from "@/entities/inventory";

export const inventoryFilterSchema = z.object({
  search: z.string().max(120),
  status: z.enum(["all", "critical", "low", "healthy", "transit"]),
  supplier: z.string(),
  category: z.string(),
});

export type InventoryFilter = z.infer<typeof inventoryFilterSchema>;

export function filterInventory(items: InventoryItem[], filter: InventoryFilter): InventoryItem[] {
  const normalized = filter.search.trim().toLocaleLowerCase("ru");
  return items.filter((item) => {
    const matchesSearch = !normalized || `${item.name} ${item.sku} ${item.category}`.toLocaleLowerCase("ru").includes(normalized);
    const matchesStatus = filter.status === "all" || getStockStatus(item) === filter.status;
    const matchesSupplier = filter.supplier === "all" || item.supplier === filter.supplier;
    const matchesCategory = filter.category === "all" || item.category === filter.category;
    const matchesTransit = filter.status !== "transit" || item.inTransit > 0;
    return matchesSearch && (filter.status === "transit" || matchesStatus) && matchesSupplier && matchesCategory && matchesTransit;
  });
}
