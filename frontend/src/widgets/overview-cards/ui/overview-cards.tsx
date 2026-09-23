"use client";

import { AlertTriangle, ArrowUpRight, PackageCheck, Sparkles, Truck } from "lucide-react";
import { getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Card } from "@/shared/ui";

export function OverviewCards({ items, days, quantities }: { items: InventoryItem[]; days: number; quantities: Record<string, number> }) {
  const pending = items.filter((item) => item.status !== "approved");
  const total = pending.reduce((sum, item) => sum + (quantities[item.id] ?? getSuggestedQuantity(item, days)) * item.unitCost, 0);
  const budget = 20_000_000;
  const critical = pending.filter((item) => item.stock / Math.max(1, item.demand30 / 30) < item.leadDays).length;
  const transitUnits = items.reduce((sum, item) => sum + item.inTransit, 0);
  const transitValue = items.reduce((sum, item) => sum + item.inTransit * item.unitCost, 0);
  const anomalies = items.reduce((sum, item) => sum + item.anomalyCount, 0);
  const cards = [
    { label: "Сумма закупки", value: formatMoney(total), detail: `${formatMoney(total)} из ${formatMoney(budget)}`, icon: PackageCheck, tone: "text-blue-500", bar: Math.min(100, total / budget * 100), badge: `${Math.round(total / budget * 100)}% лимита` },
    { label: "Критические позиции", value: formatNumber(critical), detail: "Запас закончится до поставки", icon: AlertTriangle, tone: "text-red-500", badge: "требуют реакции" },
    { label: "Капитал в пути", value: formatMoney(transitValue), detail: `${formatNumber(transitUnits)} единиц уже едут`, icon: Truck, tone: "text-purple-500", badge: "учтено в плане" },
    { label: "Срезанные выбросы", value: formatNumber(anomalies), detail: "Крупные разовые отгрузки", icon: Sparkles, tone: "text-emerald-500", badge: "прогноз очищен" },
  ];

  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => <Card key={card.label} className="relative min-h-[174px] overflow-hidden p-5"><div className="flex items-start justify-between"><card.icon className={`h-5 w-5 ${card.tone}`} /><span className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground"><ArrowUpRight className="h-4 w-4" /></span></div><p className="mt-5 text-xs text-muted-foreground">{card.label}</p><p className="mt-1 text-[27px] font-bold tracking-tight text-card-foreground">{card.value}</p><div className="mt-3 flex items-center justify-between gap-2"><span className="truncate text-[10px] text-muted-foreground">{card.detail}</span><span className={`shrink-0 rounded-full bg-card-muted px-2 py-1 text-[9px] font-semibold ${card.tone}`}>{card.badge}</span></div>{card.bar !== undefined && <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-card-muted"><div className="h-full rounded-full bg-blue-500" style={{ width: `${card.bar}%` }} /></div>}</Card>)}</div>;
}
