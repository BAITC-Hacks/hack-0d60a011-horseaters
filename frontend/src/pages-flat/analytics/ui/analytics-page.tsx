"use client";

import { useQuery } from "@tanstack/react-query";
import { inventoryQueryOptions } from "@/entities/inventory";
import { AppShell } from "@/widgets/app-shell";
import { AbcXyzMatrix } from "@/widgets/abc-xyz-matrix";
import { AnomalyLog } from "@/widgets/anomaly-log";
import { DemandAnalytics } from "@/widgets/demand-analytics";

export function AnalyticsPage() {
  const { data = [], isError, error } = useQuery(inventoryQueryOptions());
  return <AppShell><header className="mb-6"><p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Доказательная база прогноза</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Аналитика спроса и аномалий</h1><p className="mt-2 text-sm text-muted-foreground">Разбирайте очищенный спрос, периоды дефицита и устойчивость номенклатуры.</p></header>{isError ? <p role="alert" className="rounded-xl bg-red-500/10 p-4 text-sm text-red-500">{error instanceof Error ? error.message : "Не удалось загрузить аналитику."}</p> : <div className="space-y-5"><DemandAnalytics items={data} /><div className="grid gap-5 xl:grid-cols-2"><AbcXyzMatrix items={data} /><AnomalyLog items={data} /></div></div>}</AppShell>;
}
