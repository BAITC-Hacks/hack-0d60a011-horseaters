"use client";

import { Search, SlidersHorizontal, X } from "lucide-react";
import { inventoryFilterSchema, type InventoryFilter } from "../model/filter";

type Props = {
  value: InventoryFilter;
  onChange: (next: InventoryFilter) => void;
  suppliers: string[];
  count: number;
};

export function FilterBar({ value, onChange, suppliers, count }: Props) {
  function change(patch: Partial<InventoryFilter>) {
    const result = inventoryFilterSchema.safeParse({ ...value, ...patch });
    if (result.success) onChange(result.data);
  }

  return (
    <div className="flex flex-col gap-4 border-b border-[#e8edee] p-5 lg:flex-row lg:items-center lg:justify-between lg:px-6">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8d9b9e]" />
          <input
            aria-label="Поиск по товарам"
            value={value.search}
            onChange={(event) => change({ search: event.target.value })}
            placeholder="Поиск по названию или артикулу"
            className="h-10 w-full rounded-xl border border-[#dce4e5] bg-white pl-10 pr-9 text-sm outline-none placeholder:text-[#9aa6a8] focus:border-[#17835b]"
          />
          {value.search && <button aria-label="Очистить поиск" onClick={() => change({ search: "" })} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8d9b9e]"><X className="h-4 w-4" /></button>}
        </div>
        <div className="relative">
          <SlidersHorizontal className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#7c8b8e]" />
          <select aria-label="Статус запаса" value={value.status} onChange={(event) => change({ status: event.target.value as InventoryFilter["status"] })} className="h-10 appearance-none rounded-xl border border-[#dce4e5] bg-white pl-9 pr-8 text-sm text-[#344247] outline-none focus:border-[#17835b]">
            <option value="all">Все статусы</option>
            <option value="critical">Критический</option>
            <option value="low">Низкий</option>
            <option value="healthy">В норме</option>
          </select>
        </div>
        <select aria-label="Поставщик" value={value.supplier} onChange={(event) => change({ supplier: event.target.value })} className="h-10 rounded-xl border border-[#dce4e5] bg-white px-3 text-sm text-[#344247] outline-none focus:border-[#17835b]">
          <option value="all">Все поставщики</option>
          {suppliers.map((supplier) => <option key={supplier} value={supplier}>{supplier}</option>)}
        </select>
      </div>
      <span className="whitespace-nowrap text-sm text-[#819094]">Найдено: <strong className="font-semibold text-[#344247]">{count}</strong></span>
    </div>
  );
}
