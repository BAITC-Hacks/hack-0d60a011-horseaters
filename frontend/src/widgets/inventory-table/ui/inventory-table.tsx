"use client";

import { ArrowUpRight, Pencil, PackageOpen } from "lucide-react";
import { getStockStatus, getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { useEditStore } from "@/features/edit-inventory-item";
import { useSelectionStore } from "@/features/select-items";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Badge } from "@/shared/ui";

const statusCopy = {
  critical: { label: "Критический", tone: "red" as const, dot: "bg-[#dc635b]" },
  low: { label: "Низкий", tone: "amber" as const, dot: "bg-[#e7a83d]" },
  healthy: { label: "В норме", tone: "green" as const, dot: "bg-[#43ae76]" },
};

export function InventoryTable({ items }: { items: InventoryItem[] }) {
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const toggle = useSelectionStore((state) => state.toggle);
  const selectMany = useSelectionStore((state) => state.selectMany);
  const clearMany = useSelectionStore((state) => state.clearMany);
  const openEdit = useEditStore((state) => state.open);
  const allVisibleSelected = items.length > 0 && items.every((item) => selectedIds.includes(item.id));

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[920px] border-collapse text-left">
        <thead><tr className="bg-[#fbfcfc] text-[11px] font-bold uppercase tracking-[0.08em] text-[#91a0a2]"><th className="w-12 py-3 pl-6"><input aria-label="Выбрать все видимые позиции" type="checkbox" checked={allVisibleSelected} onChange={() => allVisibleSelected ? clearMany(items.map((item) => item.id)) : selectMany(items.map((item) => item.id))} className="h-4 w-4 accent-[#17835b]" /></th><th className="min-w-[250px] py-3">Товар</th><th className="min-w-[160px] py-3">Поставщик</th><th className="py-3">Остаток</th><th className="py-3">Мин. запас</th><th className="min-w-[130px] py-3">Статус</th><th className="py-3">К заказу</th><th className="py-3">Сумма</th><th className="w-14 py-3 pr-5" /></tr></thead>
        <tbody>{items.map((item) => {
          const status = statusCopy[getStockStatus(item)];
          const quantity = getSuggestedQuantity(item);
          return <tr key={item.id} className="border-t border-[#edf0f0] text-sm transition hover:bg-[#fbfdfc]"><td className="py-4 pl-6"><input aria-label={`Выбрать ${item.name}`} type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => toggle(item.id)} className="h-4 w-4 accent-[#17835b]" /></td><td className="py-4 pr-4"><div className="font-semibold text-[#263633]">{item.name}</div><div className="mt-1 text-xs text-[#9aa7a9]">{item.sku} <span className="mx-1.5">·</span> {item.category}</div></td><td className="py-4 text-[#68777a]">{item.supplier}</td><td className="py-4"><span className={getStockStatus(item) === "critical" ? "font-semibold text-[#c45950]" : "font-semibold text-[#334540]"}>{formatNumber(item.stock)}</span><span className="ml-1 text-xs text-[#9ba7a9]">{item.unit}</span></td><td className="py-4 text-[#68777a]">{formatNumber(item.minStock)} <span className="text-xs text-[#9ba7a9]">{item.unit}</span></td><td className="py-4"><Badge tone={status.tone}><span className={`mr-1.5 h-1.5 w-1.5 rounded-full ${status.dot}`} />{status.label}</Badge></td><td className="py-4">{quantity > 0 ? <span className="inline-flex items-center gap-1 font-bold text-[#16835b]">{formatNumber(quantity)} <span className="text-xs font-medium text-[#8a999a]">{item.unit}</span><ArrowUpRight className="h-3.5 w-3.5" /></span> : <span className="text-[#a7b2b3]">—</span>}</td><td className="py-4 font-semibold text-[#344540]">{quantity > 0 ? formatMoney(quantity * item.unitCost) : "—"}</td><td className="py-4 pr-5"><button aria-label={`Изменить параметры: ${item.name}`} onClick={() => openEdit(item.id)} className="rounded-lg p-2 text-[#94a3a4] transition hover:bg-[#e9f5ef] hover:text-[#17835b]"><Pencil className="h-4 w-4" /></button></td></tr>;
        })}</tbody>
      </table>
      {items.length === 0 && <div className="flex flex-col items-center px-5 py-16 text-center"><PackageOpen className="h-10 w-10 text-[#b2c1ba]" /><p className="mt-3 font-semibold text-[#34453e]">Ничего не найдено</p><p className="mt-1 text-sm text-[#91a09b]">Попробуйте изменить поиск или фильтры.</p></div>}
    </div>
  );
}
