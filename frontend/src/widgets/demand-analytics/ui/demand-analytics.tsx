"use client";

import { useState } from "react";
import type { InventoryItem } from "@/entities/inventory";
import { formatNumber } from "@/shared/lib";
import { Badge, Card } from "@/shared/ui";

type Point = { actual: number; adjusted: number; forecast: number; anomaly: boolean; stockout: boolean };

function createSeries(item: InventoryItem): Point[] {
  return Array.from({ length: 13 }, (_, index) => {
    const base = item.demand30 / 4.3 * (0.8 + index * 0.025) * (1 + Math.sin(index * 1.5 + item.sku.length) * 0.11);
    const anomaly = item.anomalyCount > 0 && index === 3;
    const stockout = index === 6 || index === 7;
    return { actual: Math.round(anomaly ? base * 2.8 : stockout ? base * 0.2 : base), adjusted: Math.round(base), forecast: Math.round(base * item.growthFactor * item.seasonalityIndex), anomaly, stockout };
  });
}

function polyline(values: number[], max: number) {
  return values.map((value, index) => `${42 + index * 55},${212 - value / max * 170}`).join(" ");
}

export function DemandAnalytics({ items }: { items: InventoryItem[] }) {
  const [selectedId, setSelectedId] = useState(items[0]?.id ?? "");
  const item = items.find((row) => row.id === selectedId) ?? items[0];
  if (!item) return <Card className="p-6 text-sm text-muted-foreground">Нет данных для аналитики.</Card>;
  const points = createSeries(item);
  const max = Math.max(...points.flatMap((point) => [point.actual, point.adjusted, point.forecast]), 1) * 1.1;

  return <Card className="p-5 sm:p-6"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-mono text-[10px] uppercase tracking-[0.14em] text-blue-500">Временной ряд · 90 дней</p><h2 className="mt-2 text-xl font-bold">Продажи, спрос и прогноз</h2><p className="mt-1 text-xs text-muted-foreground">Точки выбросов и интервалы дефицита выделены на графике.</p></div><select aria-label="Выбрать артикул для графика" value={item.id} onChange={(event) => setSelectedId(event.target.value)} className="max-w-72 rounded-full border border-border bg-input px-3 py-2 text-xs outline-none focus:border-ring">{items.map((row) => <option key={row.id} value={row.id}>{row.sku} · {row.name}</option>)}</select></div><div className="mt-5 overflow-x-auto rounded-2xl border border-border bg-card-muted p-4"><svg viewBox="0 0 740 250" className="h-[250px] min-w-[640px] w-full" role="img" aria-label={`Синтетический ряд продаж, скорректированного спроса и прогноза для ${item.name}`}><path d="M42 212H715" stroke="currentColor" className="text-muted-foreground/30" /><path d="M42 128H715" stroke="currentColor" strokeDasharray="4 6" className="text-muted-foreground/20" /><path d="M42 43H715" stroke="currentColor" strokeDasharray="4 6" className="text-muted-foreground/20" /><rect x="360" y="30" width="108" height="182" fill="#50a8e5" fillOpacity="0.07" /><polyline fill="none" stroke="#f17272" strokeWidth="2.5" points={polyline(points.map((point) => point.actual), max)} /><polyline fill="none" stroke="#5ab8e9" strokeWidth="3" points={polyline(points.map((point) => point.adjusted), max)} /><polyline fill="none" stroke="#9f8cff" strokeWidth="2.5" strokeDasharray="6 5" points={polyline(points.map((point) => point.forecast), max)} />{points.map((point, index) => point.anomaly && <circle key={index} cx={42 + index * 55} cy={212 - point.actual / max * 170} r="6" fill="#f17272" stroke="#fff" strokeWidth="2" />)}<text x="42" y="236" fill="currentColor" className="text-[10px] text-muted-foreground">90 дней назад</text><text x="640" y="236" fill="currentColor" className="text-[10px] text-muted-foreground">сегодня</text></svg></div><div className="mt-4 flex flex-wrap gap-3 text-[11px] text-muted-foreground"><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-red-400" />Фактические продажи / Whale Order</span><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-sky-400" />Восстановленный спрос</span><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-violet-400" />Прогнозный коридор</span></div><div className="mt-5 grid gap-3 sm:grid-cols-3"><div className="rounded-xl bg-card-muted p-3"><p className="text-[10px] text-muted-foreground">Базовый спрос</p><strong className="text-lg">{formatNumber(item.demand30)} {item.unit}</strong></div><div className="rounded-xl bg-card-muted p-3"><p className="text-[10px] text-muted-foreground">Срезанные выбросы</p><strong className="text-lg">{item.anomalyCount}</strong></div><div className="rounded-xl bg-card-muted p-3"><p className="text-[10px] text-muted-foreground">Компенсация stockout</p><strong className="text-lg">+{item.stockoutAdjustment} {item.unit}</strong></div></div><p className="mt-4 text-[10px] text-muted-foreground"><Badge tone="blue">ДЕМО</Badge> <span className="ml-2">Точки графика синтетические; числовые компоненты карточки берутся из рекомендации.</span></p></Card>;
}
