"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, RefreshCw, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { getStockStatus, getSuggestedQuantity, inventoryQueryOptions } from "@/entities/inventory";
import { useOrderQuantityStore } from "@/features/adjust-order-quantity";
import { ApproveAction } from "@/features/approve-order";
import { ExplanationDrawer, useExplainStore } from "@/features/explain-recommendation";
import { ExportMenu } from "@/features/export-order";
import { FilterBar, filterInventory, type InventoryFilter } from "@/features/filter-inventory";
import { useSelectionStore } from "@/features/select-items";
import { useHorizonStore } from "@/features/set-horizon";
import { Button, Card } from "@/shared/ui";
import { AppShell } from "@/widgets/app-shell";
import { InventoryTable } from "@/widgets/inventory-table";
import { OrderSummary } from "@/widgets/order-summary";
import { OverviewCards } from "@/widgets/overview-cards";

export function InventoryPage({ initialSearch = "" }: { initialSearch?: string }) {
  const { data = [], isPending, isError, error, refetch, isFetching } = useQuery(inventoryQueryOptions());
  const [filter, setFilter] = useState<InventoryFilter>({ search: initialSearch.slice(0, 120), status: "all", supplier: "all", category: "all" });
  const days = useHorizonStore((state) => state.days);
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const selectMany = useSelectionStore((state) => state.selectMany);
  const clearSelection = useSelectionStore((state) => state.clear);
  const quantityById = useOrderQuantityStore((state) => state.quantityById);
  const explainedId = useExplainStore((state) => state.selectedId);
  const suppliers = useMemo(() => [...new Set(data.map((item) => item.supplier))].sort((a, b) => a.localeCompare(b, "ru")), [data]);
  const categories = useMemo(() => [...new Set(data.map((item) => item.category))].sort((a, b) => a.localeCompare(b, "ru")), [data]);
  const filtered = useMemo(() => filterInventory(data, filter), [data, filter]);
  const explainedItem = data.find((item) => item.id === explainedId) ?? null;
  const tabCounts = {
    all: data.length,
    critical: data.filter((item) => getStockStatus(item) === "critical").length,
    transit: data.filter((item) => item.inTransit > 0).length,
    healthy: data.filter((item) => getStockStatus(item) === "healthy").length,
  };
  const quantities = Object.fromEntries(data.map((item) => [item.id, quantityById[item.id] ?? getSuggestedQuantity(item, days)]));
  const tabs = [
    { key: "all" as const, label: "Все", count: tabCounts.all },
    { key: "critical" as const, label: "Критично", count: tabCounts.critical },
    { key: "transit" as const, label: "В пути", count: tabCounts.transit },
    { key: "healthy" as const, label: "Норма", count: tabCounts.healthy },
  ];

  return <AppShell><section className="mb-6 flex flex-col justify-between gap-4 xl:flex-row xl:items-end"><div><p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">ТОО «Электрокомплект» / рабочий стол закупщика</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Рекомендации к заказу</h1><p className="mt-2 text-sm text-muted-foreground">План на {days} дней: проверьте риск, объяснение и количество перед утверждением.</p></div><div className="flex flex-wrap gap-2"><ExportMenu items={data} /><Button variant="secondary" onClick={() => selectMany(filtered.filter((item) => item.status !== "approved" && (quantityById[item.id] ?? getSuggestedQuantity(item, days)) > 0).map((item) => item.id))}><SlidersHorizontal className="h-4 w-4" />Выбрать к заказу</Button></div></section>
    {isError ? <Card role="alert" className="p-7"><h2 className="font-bold text-red-500">Данные не загрузились</h2><p className="mt-2 text-sm text-muted-foreground">{error instanceof Error ? error.message : "Неизвестная ошибка"}</p><Button className="mt-4" onClick={() => void refetch()}><RefreshCw className="h-4 w-4" />Повторить</Button></Card> : <>
      <OverviewCards items={data} days={days} quantities={quantityById} />
      <div className="mt-6 flex flex-wrap gap-2">{tabs.map((tab) => <button key={tab.key} type="button" onClick={() => setFilter((current) => ({ ...current, status: tab.key }))} aria-pressed={filter.status === tab.key} className={`rounded-full border px-4 py-2 text-xs font-semibold transition ${filter.status === tab.key ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-muted-foreground hover:text-foreground"}`}>{tab.label} <span className="ml-1 opacity-70">{tab.count}</span></button>)}</div>
      <div className="mt-5 grid gap-5 2xl:grid-cols-[minmax(0,1fr)_280px] 2xl:items-start"><Card id="inventory" className="min-w-0 overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-4 p-5"><div><p className="font-mono text-[10px] uppercase tracking-[0.14em] text-blue-500">ПОЗИЦИИ РАСЧЁТА</p><h2 className="mt-1 text-lg font-bold">Интерактивная таблица пополнения</h2></div><span className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-emerald-500"><span className={`h-1.5 w-1.5 rounded-full bg-emerald-400 ${isFetching ? "animate-pulse" : ""}`} />{isFetching ? "Обновление" : process.env.NEXT_PUBLIC_DEMO_MODE === "false" ? "Данные API актуальны" : "Демо-расчёт актуален"}</span></div><FilterBar value={filter} onChange={setFilter} suppliers={suppliers} categories={categories} count={filtered.length} />{isPending ? <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">Загрузка рекомендаций…</div> : <InventoryTable items={filtered} days={days} />}<div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-4 text-xs text-muted-foreground"><span>Показано {filtered.length} из {data.length} · Выбрано {selectedIds.length}</span><div className="flex items-center gap-3">{selectedIds.length > 0 && <button onClick={clearSelection} className="hover:text-foreground">Снять выбор</button>}<a href="/orders" className="inline-flex items-center gap-1 font-semibold text-blue-500">Заказы по поставщикам <ArrowRight className="h-3.5 w-3.5" /></a></div></div></Card><div className="space-y-4"><OrderSummary items={filtered} days={days} /><ApproveAction items={data} selectedIds={selectedIds} quantities={quantities} onDone={clearSelection} /></div></div>
    </>}
    <ExplanationDrawer item={explainedItem} days={days} />
  </AppShell>;
}
