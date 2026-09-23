"use client";

import { useQuery } from "@tanstack/react-query";
import { Mail } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { runRecommendationsQueryOptions } from "@/entities/calculation-run";
import { getStockStatus, inventoryQueryOptions, type InventoryItem } from "@/entities/inventory";
import type { Order } from "@/entities/order";
import { AiExecutiveBanner, SkuAnalysisDrawer, SupplierLetterModal, useAiStore } from "@/features/ai-analysis";
import { ApproveAction } from "@/features/approve-order";
import { EditItemDialog, useEditStore } from "@/features/edit-inventory-item";
import { ExportMenu } from "@/features/export-order";
import { FilterBar, filterInventory, type InventoryFilter } from "@/features/filter-inventory";
import { useCalculationSessionStore } from "@/features/run-calculation";
import { useSelectionStore } from "@/features/select-items";
import { Button, Card, ErrorMessage, Skeleton } from "@/shared/ui";
import { AppShell } from "@/widgets/app-shell";
import { InventoryTable } from "@/widgets/inventory-table";
import { OverviewCards } from "@/widgets/overview-cards";
import { RunRecommendationsTable } from "@/widgets/run-recommendations";

const EMPTY_ITEMS: InventoryItem[] = [];

export function InventoryPage({ initialSearch = "", initialRunId = null }: { initialSearch?: string; initialRunId?: string | null }) {
  const inventory = useQuery(inventoryQueryOptions());
  const sessionRunId = useCalculationSessionStore((state) => state.activeRunId);
  const setActiveRunId = useCalculationSessionStore((state) => state.setActiveRunId);
  const activeRunId = initialRunId ?? sessionRunId;
  const [runOffset, setRunOffset] = useState(0);
  const runRecommendations = useQuery({ ...runRecommendationsQueryOptions(activeRunId ?? "", { limit: 50, offset: runOffset }), enabled: activeRunId !== null });
  const [filter, setFilter] = useState<InventoryFilter>({ search: initialSearch.slice(0, 120), status: "all", supplier: "all", category: "all" });
  const [orders, setOrders] = useState<Order[]>([]);
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const openLetter = useAiStore((state) => state.openLetterModal);
  const editingId = useEditStore((state) => state.editingId);
  const items = inventory.data ?? EMPTY_ITEMS;
  const suppliers = useMemo(() => [...new Set(items.map((item) => item.supplier_name))].sort((a, b) => a.localeCompare(b, "ru")), [items]);
  const categories = useMemo(() => [...new Set(items.map((item) => item.category))].sort((a, b) => a.localeCompare(b, "ru")), [items]);
  const filtered = useMemo(() => filterInventory(items, filter), [items, filter]);
  const editingItem = items.find((item) => item.id === editingId) ?? null;
  const tabs = [
    { key: "all" as const, label: "Все", count: items.length },
    { key: "critical" as const, label: "Критично", count: items.filter((item) => getStockStatus(item) === "critical").length },
    { key: "low" as const, label: "Планово", count: items.filter((item) => getStockStatus(item) === "low").length },
    { key: "transit" as const, label: "В пути", count: items.filter((item) => item.in_transit > 0).length },
  ];

  useEffect(() => {
    if (initialRunId) setActiveRunId(initialRunId);
    setRunOffset(0);
  }, [initialRunId, setActiveRunId]);

  return <AppShell>
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-3xl font-bold tracking-tight">Управление пополнением</h1><p className="mt-2 text-sm text-muted-foreground">Список закупок и результаты расчёта загружаются с FastAPI.</p></div><Button type="button" variant="secondary" onClick={openLetter} disabled={items.length === 0}><Mail className="h-4 w-4" />Письмо поставщику</Button></header>
    {inventory.isPending ? <div className="space-y-4"><div className="grid gap-4 sm:grid-cols-3"><Skeleton className="h-36" /><Skeleton className="h-36" /><Skeleton className="h-36" /></div><Skeleton className="h-96" /></div> : inventory.isError ? <ErrorMessage title="Не удалось загрузить рекомендации закупок" error={inventory.error} onRetry={() => void inventory.refetch()} /> : <>
      <AiExecutiveBanner items={items} />
      <OverviewCards items={items} />
      <Card id="inventory" className="mt-6 overflow-hidden"><div className="p-5"><h2 className="text-xl font-bold">Рекомендации закупок</h2><p className="mt-1 text-xs text-muted-foreground">Источник: GET /api/v1/procurement/recommendations. Это предварительно загруженный серверный набор, не результат последнего импорта.</p></div>
        <div className="flex flex-wrap gap-2 px-5 pb-4">{tabs.map((tab) => <button key={tab.key} type="button" onClick={() => setFilter((current) => ({ ...current, status: tab.key }))} aria-pressed={filter.status === tab.key} className={`rounded-full border px-4 py-2 text-xs font-semibold ${filter.status === tab.key ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-muted-foreground"}`}>{tab.label} {tab.count}</button>)}</div>
        <FilterBar value={filter} onChange={setFilter} suppliers={suppliers} categories={categories} count={filtered.length} />
        <InventoryTable items={filtered} />
        <p className="border-t border-border px-5 py-4 text-xs text-muted-foreground">Показано {filtered.length} из {items.length}. Выбрано {selectedIds.length}. API 0.1.0 не умеет создавать заказ только из выбранных строк.</p>
      </Card>
    </>}

    {activeRunId && <section className="mt-8 space-y-4"><div><h2 className="text-xl font-bold">Результат расчёта</h2><p className="mt-1 font-mono text-xs text-muted-foreground">Run ID: {activeRunId}</p></div>
      {runRecommendations.isPending ? <Skeleton className="h-64" /> : runRecommendations.isError ? <ErrorMessage title="Не удалось загрузить рекомендации расчёта" error={runRecommendations.error} onRetry={() => void runRecommendations.refetch()} /> : <Card className="overflow-hidden"><RunRecommendationsTable items={runRecommendations.data.items} /><div className="flex flex-wrap items-center justify-between gap-2 border-t border-border p-4 text-xs text-muted-foreground"><p>Показано {runOffset + 1}–{runOffset + runRecommendations.data.items.length} из {runRecommendations.data.total}. Каталог и цены в DTO отсутствуют; строки содержат UUID.</p><div className="flex gap-2"><Button type="button" size="sm" variant="secondary" disabled={runOffset === 0} onClick={() => setRunOffset((value) => Math.max(0, value - 50))}>Назад</Button><Button type="button" size="sm" variant="secondary" disabled={runOffset + 50 >= runRecommendations.data.total} onClick={() => setRunOffset((value) => value + 50)}>Далее</Button></div></div></Card>}
      <ApproveAction runId={activeRunId} onOrdersCreated={setOrders} onOrderApproved={(updated) => setOrders((current) => current.map((order) => order.id === updated.id ? updated : order))} />
      {orders.filter((order) => order.status === "approved" || order.status === "exported").map((order) => <Card key={order.id} className="p-4"><p className="mb-3 text-sm font-semibold">{order.order_number}</p><ExportMenu order={order} /></Card>)}
    </section>}
    <SkuAnalysisDrawer />
    <SupplierLetterModal items={items} />
    <EditItemDialog item={editingItem} />
  </AppShell>;
}
