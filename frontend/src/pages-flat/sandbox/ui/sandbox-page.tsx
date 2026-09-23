"use client";

import { useQuery } from "@tanstack/react-query";
import { inventoryQueryOptions } from "@/entities/inventory";
import { ScenarioPanel } from "@/features/simulate-procurement";
import { useHorizonStore } from "@/features/set-horizon";
import { AppShell } from "@/widgets/app-shell";

export function SandboxPage() {
  const { data = [], isError, error } = useQuery(inventoryQueryOptions());
  const horizonDays = useHorizonStore((state) => state.days);
  return <AppShell><header className="mb-6"><p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Сценарное моделирование</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Песочница / What-If</h1><p className="mt-2 text-sm text-muted-foreground">Меняйте параметры и сразу смотрите влияние на потребность, бюджет и риск дефицита. Данные демо-сценария синтетические.</p></header>{isError ? <p role="alert" className="rounded-xl bg-red-500/10 p-4 text-sm text-red-500">{error instanceof Error ? error.message : "Не удалось загрузить данные симулятора."}</p> : <ScenarioPanel items={data} horizonDays={horizonDays} />}</AppShell>;
}
