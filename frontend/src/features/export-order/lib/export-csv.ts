import { getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";

function cell(value: string | number): string {
  return `"${String(value).replaceAll('"', '""')}"`;
}

export function exportOrderCsv(items: InventoryItem[], quantityById: Record<string, number> = {}): number {
  const rows = items
    .map((item) => ({ item, quantity: quantityById[item.id] ?? getSuggestedQuantity(item) }))
    .filter(({ quantity }) => quantity > 0);
  if (rows.length === 0) return 0;

  const header = ["Артикул", "Наименование", "Поставщик", "Количество", "Ед.", "Цена", "Сумма"];
  const csv = [header, ...rows.map(({ item, quantity }) => [item.sku, item.name, item.supplier, quantity, item.unit, item.unitCost, quantity * item.unitCost])]
    .map((row) => row.map(cell).join(";"))
    .join("\r\n");
  const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `order-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  return rows.length;
}
