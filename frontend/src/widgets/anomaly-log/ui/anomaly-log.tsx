"use client";

import { AlertCircle, ArrowRight } from "lucide-react";
import type { InventoryItem } from "@/entities/inventory";
import { formatNumber } from "@/shared/lib";
import { Card } from "@/shared/ui";

export function AnomalyLog({ items }: { items: InventoryItem[] }) {
  const rows = items.filter((item) => item.anomalyCount > 0).sort((a, b) => b.anomalyCount - a.anomalyCount);
  return <Card className="p-5 sm:p-6"><p className="font-mono text-[10px] uppercase tracking-[0.14em] text-red-500">Аудит прогноза</p><h2 className="mt-2 text-lg font-bold">Обнаруженные аномалии</h2><p className="mt-1 text-xs text-muted-foreground">Исходные продажи сохраняются; в базовом спросе используются очищенные значения.</p><div className="mt-5 divide-y divide-border">{rows.map((item, index) => <div key={item.id} className="flex gap-3 py-4"><div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-red-500/10 text-red-500"><AlertCircle className="h-4 w-4" /></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-semibold">{item.name}</p><span className="font-mono text-[10px] text-muted-foreground">{String(24 - index).padStart(2, "0")}.08.2026</span></div><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.anomalyCount} крупных отгрузок · артикул {item.sku} <ArrowRight className="mx-1 inline h-3 w-3" /> из регулярного прогноза исключено {formatNumber(Math.abs(item.anomalyAdjustment))} {item.unit}.</p></div></div>)}{rows.length === 0 && <p className="py-6 text-sm text-muted-foreground">Аномалии не обнаружены.</p>}</div></Card>;
}
