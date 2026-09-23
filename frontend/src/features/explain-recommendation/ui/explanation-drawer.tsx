"use client";

import { ArrowRight, X } from "lucide-react";
import { getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { formatNumber } from "@/shared/lib";
import { Badge, Button } from "@/shared/ui";
import { useExplainStore } from "../model/explain-store";

function salesSeries(item: InventoryItem) {
  return Array.from({ length: 12 }, (_, index) => {
    const seasonal = 0.82 + index * 0.018;
    const regular = Math.max(0, item.demand30 / 4 * seasonal + Math.sin(index * 1.7 + item.sku.length) * item.demand30 / 30);
    const anomaly = item.anomalyCount > 0 && index === 7;
    const stockout = index === 4 || index === 5;
    return { actual: Math.round(anomaly ? regular * 2.4 : stockout ? regular * 0.35 : regular), adjusted: Math.round(regular), forecast: Math.round(regular * item.growthFactor * item.seasonalityIndex), anomaly, stockout };
  });
}

function linePoints(values: number[], maximum: number) {
  return values.map((value, index) => `${24 + index * 26},${150 - (value / maximum) * 118}`).join(" ");
}

export function ExplanationDrawer({ item, days }: { item: InventoryItem | null; days: number }) {
  const close = useExplainStore((state) => state.close);
  if (!item) return null;

  const sales = salesSeries(item);
  const maximum = Math.max(1, ...sales.flatMap((point) => [point.actual, point.adjusted, point.forecast])) * 1.1;
  const horizonDemand = Math.round((item.demand30 / 30) * (days + item.leadDays) * item.growthFactor * item.seasonalityIndex);
  const beforeRound = Math.max(0, horizonDemand + item.minStock + item.materialNeed - item.stock - item.inTransit);
  const recommended = getSuggestedQuantity(item, days);
  const doh = item.demand30 === 0 ? null : item.stock / (item.demand30 / 30);

  return <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><aside role="dialog" aria-modal="true" aria-labelledby="explain-title" className="h-full w-full max-w-[540px] overflow-y-auto border-l border-border bg-card p-6 text-card-foreground shadow-2xl sm:p-8">
    <div className="flex items-start justify-between gap-4"><div><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-blue-500">Обоснование рекомендации</p><h2 id="explain-title" className="mt-2 text-xl font-bold">{item.name}</h2><p className="mt-1 font-mono text-xs text-muted-foreground">{item.sku} · {item.supplier} · {item.warehouse}</p></div><Button type="button" variant="ghost" size="icon" onClick={close} aria-label="Закрыть обоснование"><X className="h-5 w-5" /></Button></div>
    <div className="mt-6 rounded-2xl border border-border bg-card-muted p-4"><div className="flex items-start justify-between gap-4"><p className="max-w-sm text-sm leading-6">{item.explanation}</p><Badge tone={item.riskScore >= 0.8 ? "red" : item.riskScore >= 0.5 ? "amber" : "green"}>Риск {Math.round(item.riskScore * 100)}%</Badge></div><div className="mt-4 flex gap-4 text-xs text-muted-foreground"><span>Запас: <strong className="text-foreground">{doh === null ? "—" : `${doh.toFixed(1)} дн.`}</strong></span><span>Доставка: <strong className="text-foreground">{item.leadDays} дн.</strong></span></div></div>
    <section className="mt-7"><div className="mb-3 flex items-center justify-between"><h3 className="font-semibold">Продажи и восстановленный спрос</h3><span className="font-mono text-[10px] text-muted-foreground">90 ДНЕЙ · ДЕМО-РЯД</span></div><div className="rounded-2xl border border-border bg-card-muted p-4"><svg viewBox="0 0 340 170" className="h-48 w-full" role="img" aria-label="Фактические продажи, скорректированный спрос и прогноз за 90 дней"><path d="M24 150H326" stroke="currentColor" className="text-border" /><polyline fill="none" stroke="#f97373" strokeWidth="2" points={linePoints(sales.map((point) => point.actual), maximum)} /><polyline fill="none" stroke="#54b9ee" strokeWidth="2.5" points={linePoints(sales.map((point) => point.adjusted), maximum)} /><polyline fill="none" stroke="#8e80ff" strokeWidth="2" strokeDasharray="5 4" points={linePoints(sales.map((point) => point.forecast), maximum)} />{sales.map((point, index) => point.anomaly && <circle key={index} cx={24 + index * 26} cy={150 - (point.actual / maximum) * 118} r="5" fill="#f97373" />)}</svg><div className="mt-2 flex flex-wrap gap-3 text-[10px] text-muted-foreground"><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-red-400" />Продажи / выброс</span><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-sky-400" />Очищенный спрос</span><span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-violet-400" />Прогноз</span></div></div></section>
    <section className="mt-7"><h3 className="font-semibold">Декомпозиция расчёта</h3><div className="mt-3 divide-y divide-border rounded-2xl border border-border px-4">{[
      ["Базовый спрос за 30 дней", `${formatNumber(item.demand30)} ${item.unit}`],
      ["Срезанные выбросы", `${formatNumber(item.anomalyAdjustment)} ${item.unit}`],
      ["Компенсация дефицита", `+${formatNumber(item.stockoutAdjustment)} ${item.unit}`],
      ["Рост × сезонность", `${item.growthFactor.toFixed(2)} × ${item.seasonalityIndex.toFixed(2)}`],
      [`Спрос на ${days} дн. + плечо поставки`, `${formatNumber(horizonDemand)} ${item.unit}`],
      ["Страховой запас / потребность проекта", `${item.minStock} / ${item.materialNeed} ${item.unit}`],
      ["Остаток / в пути", `${item.stock} / ${item.inTransit} ${item.unit}`],
      ["До округления", `${formatNumber(beforeRound)} ${item.unit}`],
      ["MOQ / кратность упаковки", `${item.moq} / ${item.packSize} ${item.unit}`],
    ].map(([label, value]) => <div key={label} className="flex justify-between gap-4 py-3 text-xs"><span className="text-muted-foreground">{label}</span><strong className="text-right font-mono font-semibold">{value}</strong></div>)}</div><div className="mt-4 flex items-center justify-between rounded-2xl bg-accent p-4 text-sm font-bold text-accent-foreground"><span>Рекомендовано к заказу</span><span className="flex items-center gap-2 font-mono">{formatNumber(recommended)} {item.unit}<ArrowRight className="h-4 w-4" /></span></div></section>
  </aside></div>;
}
