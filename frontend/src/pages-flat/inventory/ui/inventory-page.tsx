"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowRight, Plus, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { inventoryQueryOptions } from "@/entities/inventory";
import { useOrderQuantityStore } from "@/features/adjust-order-quantity";
import { EditItemDialog, useEditStore } from "@/features/edit-inventory-item";
import { exportOrderCsv } from "@/features/export-order";
import { FilterBar, filterInventory, type InventoryFilter } from "@/features/filter-inventory";
import { useSelectionStore } from "@/features/select-items";
import { Button, Card } from "@/shared/ui";
import { AppShell } from "@/widgets/app-shell";
import { InventoryTable } from "@/widgets/inventory-table";
import { OrderSummary } from "@/widgets/order-summary";
import { OverviewCards } from "@/widgets/overview-cards";

export function InventoryPage() {
  const { data = [], isPending, isError, error, refetch, isFetching } = useQuery(inventoryQueryOptions());
  const [filter, setFilter] = useState<InventoryFilter>({ search: "", status: "all", supplier: "all" });
  const [notice, setNotice] = useState("");
  const editingId = useEditStore((state) => state.editingId);
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const quantityById = useOrderQuantityStore((state) => state.quantityById);
  const suppliers = useMemo(() => [...new Set(data.map((item) => item.supplier))].sort((a, b) => a.localeCompare(b, "ru")), [data]);
  const filtered = useMemo(() => filterInventory(data, filter), [data, filter]);
  const editingItem = data.find((item) => item.id === editingId) ?? null;

  function download() {
    const scoped = selectedIds.length > 0 ? filtered.filter((item) => selectedIds.includes(item.id)) : filtered;
    const count = exportOrderCsv(scoped, quantityById);
    setNotice(count > 0 ? `Заказ на ${count} позиций скачан.` : "Нет позиций с рекомендацией к заказу.");
  }

  return <AppShell>
    <section id="overview" className="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
      <div><p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Управление запасами / сентябрь 2026</p><h1 className="mt-3 text-[30px] font-bold tracking-[-0.045em] text-foreground sm:text-[38px]">Привет, Закупщик! <span aria-hidden="true">👋</span></h1><p className="mt-2 text-sm text-muted-foreground">Вот что происходит с запасами и планом пополнения сегодня.</p></div>
      <div className="flex flex-wrap items-center gap-2"><Button variant="secondary" onClick={download} disabled={isPending || isError || filtered.length === 0}><ArrowDownToLine className="h-4 w-4" />Экспорт</Button><Button onClick={() => document.querySelector("#inventory")?.scrollIntoView({ behavior: "smooth" })}><Plus className="h-4 w-4" />Сформировать заказ</Button></div>
    </section>

    {notice && <p role="status" className="mb-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-600 dark:text-emerald-400">{notice}</p>}
    {isError ? <Card role="alert" className="p-8"><h2 className="text-lg font-bold text-red-500">Не удалось загрузить запасы</h2><p className="mt-2 text-sm text-muted-foreground">{error instanceof Error ? error.message : "Неизвестная ошибка"}</p><Button className="mt-5" onClick={() => void refetch()}><RefreshCw className="h-4 w-4" />Повторить</Button></Card> : <>
      <OverviewCards items={data} />
      <div className="mt-6 grid gap-5 2xl:grid-cols-[minmax(0,1fr)_290px] 2xl:items-start">
        <Card id="inventory" className="min-w-0 overflow-hidden">
          <div className="flex flex-wrap items-start justify-between gap-4 px-5 pb-5 pt-5"><div><p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-blue-500 dark:text-blue-400">Рекомендации</p><h2 className="mt-2 text-xl font-bold text-card-foreground">Список пополнения</h2><p className="mt-1 text-xs text-muted-foreground">Проверяйте риск и корректируйте количество перед экспортом.</p></div><div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.08em] text-emerald-600 dark:text-emerald-400"><span className={`h-1.5 w-1.5 rounded-full bg-emerald-400 ${isFetching ? "animate-pulse" : ""}`} />{isFetching ? "Обновление" : "Данные актуальны"}</div></div>
          <FilterBar value={filter} onChange={setFilter} suppliers={suppliers} count={filtered.length} />
          {isPending ? <div className="flex min-h-60 items-center justify-center text-sm text-muted-foreground">Загрузка позиций…</div> : <InventoryTable items={filtered} />}
          <div className="flex items-center justify-between border-t border-border px-5 py-4 font-mono text-[10px] text-muted-foreground"><span>ПОКАЗАНО {filtered.length} ИЗ {data.length}</span><a href="#order-summary" className="inline-flex items-center gap-1 font-sans font-semibold text-blue-600 dark:text-blue-400 2xl:hidden">План закупок <ArrowRight className="h-3.5 w-3.5" /></a></div>
        </Card>
        <OrderSummary items={filtered} />
      </div>
    </>}
    <EditItemDialog item={editingItem} />
  </AppShell>;
}
