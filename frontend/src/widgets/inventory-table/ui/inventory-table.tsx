"use client";

import { ArrowUpRight, MoreHorizontal, PackageOpen, Pencil } from "lucide-react";
import { getStockStatus, getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { useOrderQuantityStore } from "@/features/adjust-order-quantity";
import { useEditStore } from "@/features/edit-inventory-item";
import { useSelectionStore } from "@/features/select-items";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Badge, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui";

const statusCopy = {
  critical: { label: "Critical", tone: "red" as const, dot: "bg-red-400" },
  low: { label: "Planned", tone: "amber" as const, dot: "bg-amber-400" },
  healthy: { label: "Normal", tone: "green" as const, dot: "bg-emerald-400" },
};

export function InventoryTable({ items }: { items: InventoryItem[] }) {
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const toggle = useSelectionStore((state) => state.toggle);
  const selectMany = useSelectionStore((state) => state.selectMany);
  const clearMany = useSelectionStore((state) => state.clearMany);
  const openEdit = useEditStore((state) => state.open);
  const quantityById = useOrderQuantityStore((state) => state.quantityById);
  const setQuantity = useOrderQuantityStore((state) => state.setQuantity);
  const allVisibleSelected = items.length > 0 && items.every((item) => selectedIds.includes(item.id));

  return <div className="overflow-x-auto">
    <Table className="min-w-[970px]">
      <TableHeader><tr><TableHead className="w-12 pl-5"><input aria-label="Выбрать все видимые позиции" type="checkbox" checked={allVisibleSelected} onChange={() => allVisibleSelected ? clearMany(items.map((item) => item.id)) : selectMany(items.map((item) => item.id))} className="h-4 w-4 rounded accent-blue-500" /></TableHead><TableHead className="min-w-[250px]">Номенклатура</TableHead><TableHead className="min-w-[150px]">Поставщик</TableHead><TableHead>Остаток</TableHead><TableHead>Мин. запас</TableHead><TableHead className="min-w-[125px]">Статус</TableHead><TableHead>К заказу</TableHead><TableHead>Сумма</TableHead><TableHead className="w-20 pr-5" /></tr></TableHeader>
      <TableBody>{items.map((item) => {
        const stockStatus = getStockStatus(item);
        const status = statusCopy[stockStatus];
        const suggestedQuantity = getSuggestedQuantity(item);
        const quantity = quantityById[item.id] ?? suggestedQuantity;
        return <TableRow key={item.id} className="text-sm"><TableCell className="pl-5"><input aria-label={`Выбрать ${item.name}`} type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => toggle(item.id)} className="h-4 w-4 rounded accent-blue-500" /></TableCell><TableCell className="pr-5"><div className="font-semibold text-card-foreground">{item.name}</div><div className="mt-1 font-mono text-[10px] text-muted-foreground">{item.sku} <span className="mx-1">/</span> {item.category}</div></TableCell><TableCell className="text-xs text-muted-foreground">{item.supplier}</TableCell><TableCell><span className={stockStatus === "critical" ? "font-semibold text-red-500 dark:text-red-400" : "font-semibold text-card-foreground"}>{formatNumber(item.stock)}</span><span className="ml-1 font-mono text-[10px] text-muted-foreground">{item.unit}</span></TableCell><TableCell className="text-muted-foreground">{formatNumber(item.minStock)} <span className="font-mono text-[10px]">{item.unit}</span></TableCell><TableCell><Badge tone={status.tone}><span className={`mr-1.5 h-1.5 w-1.5 rounded-full ${status.dot}`} />{status.label}</Badge></TableCell><TableCell><div className="relative w-24"><input aria-label={`Количество к заказу: ${item.name}`} type="number" min={0} step={item.packSize} value={quantity} onChange={(event) => setQuantity(item.id, event.currentTarget.valueAsNumber)} className="h-9 w-full rounded-xl border border-border bg-input px-3 pr-8 text-sm font-bold text-blue-600 outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:text-blue-400" /><ArrowUpRight className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-blue-500" /></div></TableCell><TableCell className="font-semibold text-card-foreground">{quantity > 0 ? formatMoney(quantity * item.unitCost) : "—"}</TableCell><TableCell className="pr-5"><div className="flex items-center justify-end gap-1"><button aria-label={`Изменить параметры: ${item.name}`} onClick={() => openEdit(item.id)} className="rounded-xl p-2 text-muted-foreground transition hover:bg-blue-500/10 hover:text-blue-500"><Pencil className="h-4 w-4" /></button><button aria-label={`Дополнительные действия: ${item.name}`} className="rounded-xl p-2 text-muted-foreground transition hover:bg-card-muted hover:text-foreground"><MoreHorizontal className="h-4 w-4" /></button></div></TableCell></TableRow>;
      })}</TableBody>
    </Table>
    {items.length === 0 && <div className="flex flex-col items-center px-5 py-16 text-center"><div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-card-muted text-muted-foreground"><PackageOpen className="h-5 w-5" /></div><p className="mt-4 font-semibold text-card-foreground">Ничего не найдено</p><p className="mt-1 text-sm text-muted-foreground">Измените поиск или параметры фильтра.</p></div>}
  </div>;
}
