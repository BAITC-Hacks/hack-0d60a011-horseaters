"use client";

import { ArrowUpRight, Download, Info, Mail, ShoppingCart, Truck } from "lucide-react";
import { useState } from "react";
import { getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { useOrderQuantityStore } from "@/features/adjust-order-quantity";
import { useAiStore } from "@/features/ai-analysis";
import { exportOrderCsv } from "@/features/export-order";
import { useSelectionStore } from "@/features/select-items";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Button, Card } from "@/shared/ui";

export function OrderSummary({ items, days }: { items: InventoryItem[]; days: number }) {
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const quantityById = useOrderQuantityStore((state) => state.quantityById);
  const openLetter = useAiStore((state) => state.openLetterModal);
  const [notice, setNotice] = useState("");
  const scoped = selectedIds.length > 0 ? items.filter((item) => selectedIds.includes(item.id)) : items;
  const orderItems = scoped.filter((item) => item.status !== "approved" && (quantityById[item.id] ?? getSuggestedQuantity(item, days)) > 0);
  const total = orderItems.reduce((sum, item) => sum + (quantityById[item.id] ?? getSuggestedQuantity(item, days)) * (item.unit_price ?? item.unitCost ?? 0), 0);
  const suppliers = new Set(orderItems.map((item) => item.supplier || item.supplier_name)).size;

  function download() {
    const count = exportOrderCsv(orderItems, quantityById);
    setNotice(count > 0 ? `Файл с ${count} позициями скачан.` : "Нет позиций с рекомендацией к заказу.");
  }

  return <Card id="order-summary" className="overflow-hidden">
    <div className="flex items-start justify-between border-b border-border p-5"><div className="flex items-center gap-3"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-500 dark:text-blue-400"><ShoppingCart className="h-4.5 w-4.5" /></div><div><h2 className="font-bold text-card-foreground">План закупок</h2><p className="mt-1 text-[11px] text-muted-foreground">{selectedIds.length > 0 ? `${selectedIds.length} выбранных позиций` : "Все найденные позиции"}</p></div></div><button className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground"><ArrowUpRight className="h-4 w-4" /></button></div>
    <div className="p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">Итого к заказу</p><p className="mt-2 text-[30px] font-bold tracking-[-0.05em] text-card-foreground">{formatMoney(total)}</p>
      <div className="my-5 grid grid-cols-2 gap-3"><div className="rounded-2xl border border-border bg-card-muted p-3.5"><div className="text-xl font-bold text-card-foreground">{formatNumber(orderItems.length)}</div><div className="mt-1 text-[10px] text-muted-foreground">позиций</div></div><div className="rounded-2xl border border-border bg-card-muted p-3.5"><div className="flex items-center gap-1.5 text-xl font-bold text-card-foreground">{suppliers}<Truck className="h-4 w-4 text-purple-500 dark:text-purple-400" /></div><div className="mt-1 text-[10px] text-muted-foreground">поставщика</div></div></div>
      
      <div className="space-y-2">
        <Button className="w-full" onClick={openLetter} disabled={orderItems.length === 0} variant="secondary">
          <Mail className="h-4 w-4" />Письмо вендору (IEK)
        </Button>
        <Button className="w-full" onClick={download} disabled={orderItems.length === 0}>
          <Download className="h-4 w-4" />Экспорт в 1С (CSV)
        </Button>
      </div>

      {notice && <p role="status" className="mt-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-2.5 text-center text-xs text-emerald-500 dark:text-emerald-400">{notice}</p>}
      <p className="mt-4 flex items-start gap-2 text-[11px] leading-5 text-muted-foreground"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />Количество в таблице выровнено по заводской кратности IEK. Выбор строк ограничивает состав заявки.</p>
    </div>
  </Card>;
}
