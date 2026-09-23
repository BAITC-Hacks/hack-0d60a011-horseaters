"use client";

import { ArrowUpRight, Info, ShoppingCart, Truck } from "lucide-react";
import { getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { useOrderQuantityStore } from "@/features/adjust-order-quantity";
import { useSelectionStore } from "@/features/select-items";
import { formatMoney } from "@/shared/lib";
import { Card } from "@/shared/ui";

export function OrderSummary({ items, days }: { items: InventoryItem[]; days: number }) {
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const quantities = useOrderQuantityStore((state) => state.quantityById);
  const relevant = items.filter((item) => item.status !== "approved" && (selectedIds.length === 0 || selectedIds.includes(item.id)));
  const orderItems = relevant.filter((item) => (quantities[item.id] ?? getSuggestedQuantity(item, days)) > 0);
  const total = orderItems.reduce((sum, item) => sum + (quantities[item.id] ?? getSuggestedQuantity(item, days)) * item.unitCost, 0);
  const suppliers = new Set(orderItems.map((item) => item.supplier)).size;

  return <Card id="order-summary" className="overflow-hidden"><div className="flex items-start justify-between border-b border-border p-5"><div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-500"><ShoppingCart className="h-4 w-4" /></div><div><h2 className="font-bold">План закупок</h2><p className="mt-1 text-[11px] text-muted-foreground">{selectedIds.length > 0 ? `Выбрано ${selectedIds.length}` : "По найденным позициям"}</p></div></div><ArrowUpRight className="h-4 w-4 text-muted-foreground" /></div><div className="p-5"><p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Итого к утверждению</p><p className="mt-2 text-[27px] font-bold tracking-tight">{formatMoney(total)}</p><div className="my-5 grid grid-cols-2 gap-3"><div className="rounded-xl bg-card-muted p-3"><strong className="text-xl">{orderItems.length}</strong><p className="mt-1 text-[10px] text-muted-foreground">позиций</p></div><div className="rounded-xl bg-card-muted p-3"><strong className="flex items-center gap-1 text-xl">{suppliers}<Truck className="h-4 w-4 text-purple-500" /></strong><p className="mt-1 text-[10px] text-muted-foreground">поставщиков</p></div></div><p className="flex items-start gap-2 text-[11px] leading-5 text-muted-foreground"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />Отметьте строки и подтвердите заказ. Экспорт будет доступен после утверждения.</p></div></Card>;
}
