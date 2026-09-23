"use client";

import { Search, SlidersHorizontal, X } from "lucide-react";
import { Input } from "@/shared/ui";
import { inventoryFilterSchema, type InventoryFilter } from "../model/filter";

type Props = { value: InventoryFilter; onChange: (next: InventoryFilter) => void; suppliers: string[]; categories: string[]; count: number };

const selectClass = "h-10 appearance-none rounded-full border border-border bg-input px-4 text-xs font-medium text-foreground outline-none transition focus:border-ring focus:ring-1 focus:ring-ring";

export function FilterBar({ value, onChange, suppliers, categories, count }: Props) {
  function change(patch: Partial<InventoryFilter>) {
    const result = inventoryFilterSchema.safeParse({ ...value, ...patch });
    if (result.success) onChange(result.data);
  }

  return <div className="flex flex-col gap-4 border-b border-border p-4 lg:flex-row lg:items-center lg:justify-between lg:px-5">
    <div className="flex flex-1 flex-wrap items-center gap-2.5">
      <div className="relative w-full sm:w-72"><Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><Input aria-label="Поиск по товарам" value={value.search} onChange={(event) => change({ search: event.target.value })} placeholder="Название или артикул" className="h-10 rounded-full pl-10 pr-9" />{value.search && <button aria-label="Очистить поиск" onClick={() => change({ search: "" })} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>}</div>
      <div className="relative"><SlidersHorizontal className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" /><select aria-label="Статус запаса" value={value.status} onChange={(event) => change({ status: event.target.value as InventoryFilter["status"] })} className={`${selectClass} pl-9`}><option value="all">Все статусы</option><option value="critical">Критический</option><option value="low">Низкий</option><option value="transit">В пути</option><option value="healthy">В норме</option></select></div>
      <select aria-label="Поставщик" value={value.supplier} onChange={(event) => change({ supplier: event.target.value })} className={selectClass}><option value="all">Все поставщики</option>{suppliers.map((supplier) => <option key={supplier} value={supplier}>{supplier}</option>)}</select>
      <select aria-label="Категория" value={value.category} onChange={(event) => change({ category: event.target.value })} className={selectClass}><option value="all">Все категории</option>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select>
      {(value.status !== "all" || value.supplier !== "all" || value.category !== "all") && <button onClick={() => onChange({ search: value.search, status: "all", supplier: "all", category: "all" })} className="text-xs font-medium text-muted-foreground transition hover:text-foreground">Сбросить</button>}
    </div>
    <span className="whitespace-nowrap font-mono text-[11px] text-muted-foreground"><strong className="font-semibold text-foreground">{count}</strong> ПОЗИЦИЙ</span>
  </div>;
}
