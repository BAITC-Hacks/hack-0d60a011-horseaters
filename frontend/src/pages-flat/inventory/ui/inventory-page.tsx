"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowRight, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { inventoryQueryOptions } from "@/entities/inventory";
import { EditItemDialog, useEditStore } from "@/features/edit-inventory-item";
import { FilterBar, filterInventory, type InventoryFilter } from "@/features/filter-inventory";
import { exportOrderCsv } from "@/features/export-order";
import { useSelectionStore } from "@/features/select-items";
import { Button } from "@/shared/ui";
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
  const suppliers = useMemo(() => [...new Set(data.map((item) => item.supplier))].sort((a, b) => a.localeCompare(b, "ru")), [data]);
  const filtered = useMemo(() => filterInventory(data, filter), [data, filter]);
  const editingItem = data.find((item) => item.id === editingId) ?? null;

  function download() {
    const scoped = selectedIds.length > 0 ? filtered.filter((item) => selectedIds.includes(item.id)) : filtered;
    const count = exportOrderCsv(scoped);
    setNotice(count > 0 ? `Заказ на ${count} позиций скачан.` : "Нет позиций с рекомендацией к заказу.");
  }

  return (
    <AppShell>
      <section id="overview" className="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div><div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.13em] text-[#17835b]"><span className="h-1.5 w-1.5 rounded-full bg-[#21a372]" />Панель управления</div><h1 className="text-[30px] font-bold tracking-[-0.035em] text-[#1c2b27] sm:text-[36px]">Управление запасами</h1><p className="mt-2 text-sm text-[#879597]">Контролируйте остатки и планируйте закупки в одном месте.</p></div>
        <Button onClick={download} disabled={isPending || isError || filtered.length === 0} className="self-start sm:self-auto"><ArrowDownToLine className="h-4 w-4" />Экспорт заказа</Button>
      </section>
      {notice && <p role="status" className="mb-5 rounded-xl bg-[#e9f7ee] px-4 py-3 text-sm text-[#247a52]">{notice}</p>}
      {isError ? <div role="alert" className="rounded-2xl border border-[#f1d5d0] bg-white p-8"><h2 className="text-lg font-bold text-[#af4d44]">Не удалось загрузить запасы</h2><p className="mt-2 text-sm text-[#68777a]">{error instanceof Error ? error.message : "Неизвестная ошибка"}</p><Button className="mt-5" onClick={() => void refetch()}><RefreshCw className="h-4 w-4" />Повторить</Button></div> : <>
        <OverviewCards items={data} />
        <div className="mt-8 grid gap-5 2xl:grid-cols-[minmax(0,1fr)_280px] 2xl:items-start">
          <section id="inventory" className="min-w-0 overflow-hidden rounded-2xl border border-[#e6eded] bg-white shadow-[0_2px_12px_rgba(24,49,43,0.025)]">
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 pb-0 pt-5 lg:px-6"><div><h2 className="text-lg font-bold text-[#263731]">Остатки товаров</h2><p className="mt-1 text-xs text-[#91a09d]">Актуальные остатки и рекомендации к заказу</p></div><div className="flex items-center gap-2 text-xs font-semibold text-[#17835b]"><span className={`h-1.5 w-1.5 rounded-full bg-[#2aaf79] ${isFetching ? "animate-pulse" : ""}`} />{isFetching ? "Обновление" : "Данные актуальны"}</div></div>
            <FilterBar value={filter} onChange={setFilter} suppliers={suppliers} count={filtered.length} />
            {isPending ? <div className="flex min-h-60 items-center justify-center text-sm text-[#839390]">Загрузка позиций…</div> : <InventoryTable items={filtered} />}
            <div className="flex items-center justify-between border-t border-[#ebefee] px-6 py-4 text-xs text-[#91a09e]"><span>Показано {filtered.length} из {data.length} позиций</span><a href="#order-summary" className="inline-flex items-center gap-1 font-semibold text-[#17835b] 2xl:hidden">План закупок <ArrowRight className="h-3.5 w-3.5" /></a></div>
          </section>
          <OrderSummary items={filtered} />
        </div>
      </>}
      <EditItemDialog item={editingItem} />
    </AppShell>
  );
}
