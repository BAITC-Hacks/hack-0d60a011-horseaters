"use client";

import { AlertTriangle, ArrowUpRight, Boxes, CircleCheck, PackagePlus, Truck } from "lucide-react";
import { getStockStatus, getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Badge, Card } from "@/shared/ui";

export function OverviewCards({ items }: { items: InventoryItem[] }) {
  const critical = items.filter((item) => getStockStatus(item) === "critical").length;
  const low = items.filter((item) => getStockStatus(item) === "low").length;
  const healthy = items.filter((item) => getStockStatus(item) === "healthy").length;
  const toOrder = items.filter((item) => getSuggestedQuantity(item) > 0).length;
  const orderValue = items.reduce((sum, item) => sum + getSuggestedQuantity(item) * item.unitCost, 0);
  const suppliers = new Set(items.filter((item) => getSuggestedQuantity(item) > 0).map((item) => item.supplier)).size;

  const metrics = [
    { label: "Номенклатура", value: formatNumber(items.length), hint: "позиций в расчёте", delta: "+4.2%", badge: "blue" as const, icon: Boxes, iconClass: "bg-blue-500/10 text-blue-500 dark:text-blue-400", hoverClass: "hover:border-blue-500/30" },
    { label: "К заказу", value: formatNumber(toOrder), hint: "требуют пополнения", delta: "+2.6%", badge: "amber" as const, icon: PackagePlus, iconClass: "bg-orange-500/10 text-orange-500 dark:text-orange-400", hoverClass: "hover:border-orange-500/30" },
    { label: "Поставщики", value: formatNumber(suppliers), hint: "в текущем плане", delta: "стабильно", badge: "purple" as const, icon: Truck, iconClass: "bg-purple-500/10 text-purple-500 dark:text-purple-400", hoverClass: "hover:border-purple-500/30" },
    { label: "Стоимость плана", value: formatMoney(orderValue), hint: "расчётная сумма", delta: "−1.8%", badge: "green" as const, icon: CircleCheck, iconClass: "bg-emerald-500/10 text-emerald-500 dark:text-emerald-400", hoverClass: "hover:border-emerald-500/30" },
  ];
  const statuses = [
    { label: "Критические", count: critical, hint: "Нужна реакция", bar: "bg-red-400", icon: AlertTriangle, text: "text-red-500 dark:text-red-400" },
    { label: "Низкий запас", count: low, hint: "Контроль поставки", bar: "bg-orange-300", icon: PackagePlus, text: "text-orange-500 dark:text-orange-400" },
    { label: "В плане", count: toOrder, hint: "К формированию", bar: "bg-blue-400", icon: Truck, text: "text-blue-500 dark:text-blue-400" },
    { label: "В норме", count: healthy, hint: "Без действий", bar: "bg-emerald-400", icon: CircleCheck, text: "text-emerald-500 dark:text-emerald-400" },
  ];

  return <div className="space-y-5">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map((metric) => <Card key={metric.label} className={`group p-5 transition duration-300 hover:-translate-y-0.5 ${metric.hoverClass}`}><div className="flex items-start justify-between"><div className={`flex h-10 w-10 items-center justify-center rounded-2xl ${metric.iconClass}`}><metric.icon className="h-4.5 w-4.5" /></div><button aria-label={`Открыть метрику ${metric.label}`} className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground transition group-hover:bg-foreground group-hover:text-background"><ArrowUpRight className="h-4 w-4" /></button></div><div className="mt-7 flex items-end justify-between gap-3"><div><p className="text-xs font-medium text-muted-foreground">{metric.label}</p><p className="mt-1 text-2xl font-bold tracking-[-0.04em] text-card-foreground sm:text-[28px]">{metric.value}</p></div><Badge tone={metric.badge}>{metric.delta}</Badge></div><p className="mt-3 text-[11px] text-muted-foreground/70">{metric.hint}</p></Card>)}</div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{statuses.map((status) => <Card key={status.label} className="relative overflow-hidden px-5 pb-4 pt-5"><span className={`absolute inset-x-0 top-0 h-1 ${status.bar}`} /><div className="flex items-center justify-between"><p className="text-xs font-medium text-muted-foreground">{status.label}</p><status.icon className={`h-4 w-4 ${status.text}`} /></div><div className="mt-4 text-2xl font-bold text-card-foreground">{status.count}</div><p className="mt-1 text-[10px] text-muted-foreground/70">{status.hint}</p></Card>)}</div>
  </div>;
}
