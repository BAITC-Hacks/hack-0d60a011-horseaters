"use client";

import { ArrowUpRight, FileSearch, PackageOpen } from "lucide-react";
import { getStockStatus, getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { QuantityEditor, useOrderQuantityStore } from "@/features/adjust-order-quantity";
import { useExplainStore } from "@/features/explain-recommendation";
import { useSelectionStore } from "@/features/select-items";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Badge, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui";

const statusCopy = {
  critical: { label: "CRITICAL", tone: "red" as const },
  low: { label: "PLANNED", tone: "amber" as const },
  healthy: { label: "NORMAL", tone: "green" as const },
};

export function InventoryTable({ items, days }: { items: InventoryItem[]; days: number }) {
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const toggle = useSelectionStore((state) => state.toggle);
  const selectMany = useSelectionStore((state) => state.selectMany);
  const clearMany = useSelectionStore((state) => state.clearMany);
  const openExplain = useExplainStore((state) => state.open);
  const quantityById = useOrderQuantityStore((state) => state.quantityById);
  const selectable = items.filter((item) => item.status !== "approved");
  const allVisibleSelected = selectable.length > 0 && selectable.every((item) => selectedIds.includes(item.id));

  return <div className="overflow-x-auto"><Table className="min-w-[1190px]"><TableHeader><tr><TableHead className="w-11 pl-5"><input aria-label="Выбрать все видимые позиции" type="checkbox" checked={allVisibleSelected} onChange={() => allVisibleSelected ? clearMany(selectable.map((item) => item.id)) : selectMany(selectable.map((item) => item.id))} className="h-4 w-4 accent-blue-500" /></TableHead><TableHead className="min-w-[290px]">Артикул / номенклатура</TableHead><TableHead>Остаток</TableHead><TableHead>Спрос / 30 дн.</TableHead><TableHead>В пути</TableHead><TableHead>Риск</TableHead><TableHead className="min-w-[165px]">К заказу</TableHead><TableHead>Сумма</TableHead><TableHead className="min-w-[140px] pr-5">Обоснование</TableHead></tr></TableHeader><TableBody>{items.map((item) => {
    const status = statusCopy[getStockStatus(item)];
    const quantity = item.approvedQuantity ?? quantityById[item.id] ?? getSuggestedQuantity(item, days);
    return <TableRow key={item.id} className="text-xs"><TableCell className="pl-5"><input aria-label={`Выбрать ${item.name}`} type="checkbox" checked={selectedIds.includes(item.id)} disabled={item.status === "approved"} onChange={() => toggle(item.id)} className="h-4 w-4 accent-blue-500 disabled:opacity-30" /></TableCell><TableCell className="pr-4"><div className="font-semibold text-card-foreground">{item.name}</div><div className="mt-1 font-mono text-[10px] text-muted-foreground">{item.sku} · {item.category} · {item.supplier}</div></TableCell><TableCell><span className="font-semibold text-card-foreground">{formatNumber(item.stock)}</span><span className="ml-1 text-muted-foreground">{item.unit}</span></TableCell><TableCell>{formatNumber(item.demand30)} <span className="text-muted-foreground">{item.unit}</span></TableCell><TableCell>{formatNumber(item.inTransit)} <span className="text-muted-foreground">{item.unit}</span></TableCell><TableCell>{item.status === "approved" ? <Badge tone="blue">APPROVED</Badge> : <Badge tone={status.tone}>{status.label}</Badge>}</TableCell><TableCell><QuantityEditor item={item} days={days} /></TableCell><TableCell className="font-semibold text-card-foreground">{quantity > 0 ? formatMoney(quantity * item.unitCost) : "—"}</TableCell><TableCell className="pr-5"><button type="button" onClick={() => openExplain(item.id)} className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-card-muted px-2.5 py-2 font-medium text-muted-foreground transition hover:border-blue-500/30 hover:text-blue-500"><FileSearch className="h-3.5 w-3.5" />Почему?<ArrowUpRight className="h-3 w-3" /></button></TableCell></TableRow>;
  })}</TableBody></Table>{items.length === 0 && <div className="flex flex-col items-center px-5 py-16 text-center"><PackageOpen className="h-8 w-8 text-muted-foreground" /><p className="mt-3 font-semibold">Нет позиций по выбранным фильтрам</p><p className="mt-1 text-xs text-muted-foreground">Измените статус, категорию или поставщика.</p></div>}</div>;
}
