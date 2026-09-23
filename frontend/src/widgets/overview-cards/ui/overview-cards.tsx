"use client";

import { AlertCircle, ArrowDownRight, ArrowUpRight, Boxes, CircleCheck, PackagePlus } from "lucide-react";
import { getStockStatus, getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { formatMoney, formatNumber } from "@/shared/lib";

export function OverviewCards({ items }: { items: InventoryItem[] }) {
  const critical = items.filter((item) => getStockStatus(item) === "critical").length;
  const healthy = items.filter((item) => getStockStatus(item) === "healthy").length;
  const toOrder = items.filter((item) => getSuggestedQuantity(item) > 0).length;
  const orderValue = items.reduce((sum, item) => sum + getSuggestedQuantity(item) * item.unitCost, 0);
  const cards = [
    { label: "Всего позиций", value: formatNumber(items.length), hint: "В каталоге склада", icon: Boxes, color: "bg-[#eaf3ef] text-[#16805a]", trend: null },
    { label: "Нужно заказать", value: formatNumber(toOrder), hint: "С учётом срока поставки", icon: PackagePlus, color: "bg-[#eaf1ff] text-[#5581c8]", trend: ArrowUpRight },
    { label: "Критический остаток", value: formatNumber(critical), hint: "Ниже страхового запаса", icon: AlertCircle, color: "bg-[#fff0e9] text-[#db7953]", trend: ArrowDownRight },
    { label: "Стоимость заказа", value: formatMoney(orderValue), hint: `${healthy} позиций в норме`, icon: CircleCheck, color: "bg-[#f2edff] text-[#9872c5]", trend: null },
  ];

  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => <div key={card.label} className="rounded-2xl border border-[#e9eeee] bg-white p-5 shadow-[0_2px_12px_rgba(24,49,43,0.025)]"><div className="flex items-start justify-between"><div className={`flex h-10 w-10 items-center justify-center rounded-xl ${card.color}`}><card.icon className="h-5 w-5" /></div>{card.trend && <card.trend className="h-4 w-4 text-[#9aa9a6]" />}</div><p className="mt-5 text-sm font-medium text-[#879598]">{card.label}</p><p className="mt-1 text-[27px] font-bold leading-tight tracking-tight text-[#1e2c2b]">{card.value}</p><p className="mt-2 text-xs text-[#a0abad]">{card.hint}</p></div>)}</div>;
}
