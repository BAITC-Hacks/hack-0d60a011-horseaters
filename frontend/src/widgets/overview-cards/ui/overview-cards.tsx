"use client";

import { AlertTriangle, PackageCheck, Truck } from "lucide-react";
import type { InventoryItem } from "@/entities/inventory";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Card } from "@/shared/ui";

export function OverviewCards({ items }: { items: InventoryItem[] }) {
  const total = items.reduce((sum, item) => sum + item.total_cost, 0);
  const critical = items.filter((item) => item.urgency === "CRITICAL").length;
  const transitUnits = items.reduce((sum, item) => sum + item.in_transit, 0);
  const cards = [
    { label: "Сумма рекомендаций", value: formatMoney(total), icon: PackageCheck },
    { label: "Критические позиции", value: formatNumber(critical), icon: AlertTriangle },
    { label: "Единиц в пути", value: formatNumber(transitUnits), icon: Truck },
  ];
  return <div className="grid gap-4 sm:grid-cols-3">{cards.map((card) => <Card key={card.label} className="p-5"><card.icon className="h-5 w-5 text-blue-500" /><p className="mt-5 text-xs text-muted-foreground">{card.label}</p><p className="mt-1 text-2xl font-bold">{card.value}</p></Card>)}</div>;
}
