"use client";

import { Pencil, PackageOpen, Sparkles, Truck } from "lucide-react";
import type { InventoryItem } from "@/entities/inventory";
import { useAiStore } from "@/features/ai-analysis";
import { useEditStore } from "@/features/edit-inventory-item";
import { useSelectionStore } from "@/features/select-items";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Badge, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui";

export function InventoryTable({ items }: { items: InventoryItem[] }) {
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const toggle = useSelectionStore((state) => state.toggle);
  const selectMany = useSelectionStore((state) => state.selectMany);
  const clearMany = useSelectionStore((state) => state.clearMany);
  const openEdit = useEditStore((state) => state.open);
  const openDrawer = useAiStore((state) => state.openDrawer);
  const allSelected = items.length > 0 && items.every((item) => selectedIds.includes(item.id));

  return <div className="overflow-x-auto"><Table className="min-w-[950px]"><TableHeader><tr>
    <TableHead className="w-12 pl-5"><input aria-label="Выбрать все видимые позиции" type="checkbox" checked={allSelected} onChange={() => allSelected ? clearMany(items.map((item) => item.id)) : selectMany(items.map((item) => item.id))} className="h-4 w-4 accent-blue-500" /></TableHead>
    <TableHead>Номенклатура</TableHead><TableHead>Поставщик</TableHead><TableHead>Остаток</TableHead><TableHead>В пути</TableHead><TableHead>Срочность</TableHead><TableHead>К заказу</TableHead><TableHead>Сумма</TableHead><TableHead>Действия</TableHead>
  </tr></TableHeader><TableBody>{items.map((item) => <TableRow key={item.id}>
    <TableCell className="pl-5"><input aria-label={`Выбрать ${item.name}`} type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => toggle(item.id)} className="h-4 w-4 accent-blue-500" /></TableCell>
    <TableCell><button type="button" onClick={() => openDrawer(item)} className="text-left"><span className="block font-semibold hover:text-blue-400">{item.name}</span><span className="font-mono text-[10px] text-muted-foreground">{item.sku} · {item.category}</span></button></TableCell>
    <TableCell className="text-xs">{item.supplier_name}</TableCell>
    <TableCell>{formatNumber(item.current_stock)} {item.unit}</TableCell>
    <TableCell>{item.in_transit > 0 ? <span className="inline-flex items-center gap-1 text-blue-400"><Truck className="h-3 w-3" />{formatNumber(item.in_transit)}</span> : "—"}</TableCell>
    <TableCell><Badge tone={item.urgency === "CRITICAL" ? "red" : item.urgency === "HIGH" || item.urgency === "MEDIUM" ? "amber" : "green"}>{item.urgency}</Badge></TableCell>
    <TableCell className="font-semibold">{formatNumber(item.adjusted_need)} {item.unit}</TableCell>
    <TableCell>{item.adjusted_need > 0 ? formatMoney(item.total_cost) : "—"}</TableCell>
    <TableCell><div className="flex gap-1"><button type="button" onClick={() => openDrawer(item)} aria-label={`AI анализ: ${item.name}`} className="rounded-lg p-2 text-blue-400 hover:bg-card-muted"><Sparkles className="h-4 w-4" /></button><button type="button" onClick={() => openEdit(item.id)} aria-label={`Изменить количество: ${item.name}`} className="rounded-lg p-2 hover:bg-card-muted"><Pencil className="h-4 w-4" /></button></div></TableCell>
  </TableRow>)}</TableBody></Table>{items.length === 0 && <div className="flex flex-col items-center py-12 text-muted-foreground"><PackageOpen className="h-6 w-6" /><p className="mt-3 text-sm">По текущим фильтрам позиций нет.</p></div>}</div>;
}
