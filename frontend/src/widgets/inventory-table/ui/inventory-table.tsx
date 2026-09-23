"use client";

import {
  ArrowUpRight,
  Pencil,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  Truck,
  PackageOpen,
} from "lucide-react";
import { getStockStatus, getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { useOrderQuantityStore } from "@/features/adjust-order-quantity";
import { useAiStore } from "@/features/ai-analysis";
import { useEditStore } from "@/features/edit-inventory-item";
import { useSelectionStore } from "@/features/select-items";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Badge, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui";

const statusCopy = {
  critical: { label: "CRITICAL", tone: "red" as const, dot: "bg-red-400" },
  low: { label: "PLANNED", tone: "amber" as const, dot: "bg-amber-400" },
  healthy: { label: "NORMAL", tone: "green" as const, dot: "bg-emerald-400" },
};

export function InventoryTable({ items, days }: { items: InventoryItem[]; days: number }) {
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const toggle = useSelectionStore((state) => state.toggle);
  const selectMany = useSelectionStore((state) => state.selectMany);
  const clearMany = useSelectionStore((state) => state.clearMany);
  const openEdit = useEditStore((state) => state.open);
  const openDrawer = useAiStore((state) => state.openDrawer);
  const quantityById = useOrderQuantityStore((state) => state.quantityById);
  const setQuantity = useOrderQuantityStore((state) => state.setQuantity);
  const selectableItems = items.filter((item) => item.status !== "approved");
  const allVisibleSelected = selectableItems.length > 0 && selectableItems.every((item) => selectedIds.includes(item.id));

  function handleQuantityChange(item: InventoryItem, rawVal: number) {
    const mult = item.package_multiplicity ?? item.packSize ?? 1;
    if (rawVal > 0 && mult > 1) {
      const snapped = Math.ceil(rawVal / mult) * mult;
      setQuantity(item.id, snapped);
    } else {
      setQuantity(item.id, Math.max(0, rawVal));
    }
  }

  return (
    <div className="overflow-x-auto">
      <Table className="min-w-[1050px]">
        <TableHeader>
          <tr>
            <TableHead className="w-12 pl-5">
              <input
                aria-label="Выбрать все видимые позиции"
                type="checkbox"
                checked={allVisibleSelected}
                onChange={() =>
                  allVisibleSelected
                    ? clearMany(selectableItems.map((item) => item.id))
                    : selectMany(selectableItems.map((item) => item.id))
                }
                className="h-4 w-4 rounded accent-blue-500"
              />
            </TableHead>
            <TableHead className="min-w-[280px]">Номенклатура</TableHead>
            <TableHead className="min-w-[130px]">Поставщик</TableHead>
            <TableHead>Остаток</TableHead>
            <TableHead className="min-w-[130px]">В пути</TableHead>
            <TableHead className="min-w-[120px]">Статус</TableHead>
            <TableHead className="min-w-[120px]">К заказу</TableHead>
            <TableHead>Сумма</TableHead>
            <TableHead className="w-24 pr-5 text-right">Действия</TableHead>
          </tr>
        </TableHeader>
        <TableBody>
          {items.map((item) => {
            const stockStatus = getStockStatus(item);
            const status = statusCopy[stockStatus];
            const suggestedQuantity = getSuggestedQuantity(item, days);
            const quantity = item.approvedQuantity ?? quantityById[item.id] ?? suggestedQuantity;
            const mult = item.package_multiplicity ?? item.packSize ?? 1;
            const inTransit = item.in_transit ?? 0;

            return (
              <TableRow
                key={item.id}
                className="text-sm transition-colors hover:bg-card-muted/40"
              >
                <TableCell className="pl-5">
                  <input
                    aria-label={`Выбрать ${item.name}`}
                    type="checkbox"
                    checked={selectedIds.includes(item.id)}
                    onChange={() => toggle(item.id)}
                    disabled={item.status === "approved"}
                    className="h-4 w-4 rounded accent-blue-500"
                  />
                </TableCell>

                <TableCell className="pr-5">
                  <button
                    onClick={() => openDrawer(item)}
                    className="group text-left transition hover:opacity-80"
                    title="Нажмите для открытия AI-обоснования и детальных метрик"
                  >
                    <div className="font-semibold text-card-foreground group-hover:text-blue-400">
                      {item.name}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                      <span>{item.sku}</span>
                      {item.vendor_code && (
                        <>
                          <span>/</span>
                          <span className="text-muted-foreground/80">{item.vendor_code}</span>
                        </>
                      )}
                      <span>/</span>
                      <span>{item.category}</span>
                    </div>
                  </button>

                  {/* Outlier & Stockout Badges */}
                  <div className="mt-1 flex flex-wrap gap-1">
                    {item.has_whale_outlier && (
                      <span
                        className="inline-flex items-center gap-1 rounded bg-purple-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-purple-400"
                        title="Разовый оптовый заказ отфильтрован"
                      >
                        <ShieldAlert className="h-2.5 w-2.5" />
                        Whale Outlier
                      </span>
                    )}
                    {item.stockout_recovered && (
                      <span
                        className="inline-flex items-center gap-1 rounded bg-blue-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-blue-400"
                        title="Восстановлен спрос за период дефицита"
                      >
                        <TrendingUp className="h-2.5 w-2.5" />
                        Stockout Rec.
                      </span>
                    )}
                  </div>
                </TableCell>

                <TableCell className="text-xs text-muted-foreground">
                  {item.supplier || item.supplier_name}
                </TableCell>

                <TableCell>
                  <span
                    className={
                      stockStatus === "critical"
                        ? "font-semibold text-red-500 dark:text-red-400"
                        : "font-semibold text-card-foreground"
                    }
                  >
                    {formatNumber(item.current_stock ?? item.stock)}
                  </span>
                  <span className="ml-1 font-mono text-[10px] text-muted-foreground">
                    {item.unit}
                  </span>
                </TableCell>

                <TableCell>
                  {inTransit > 0 ? (
                    <div
                      className="group cursor-help"
                      title={item.transit_details || `${inTransit} ${item.unit} в пути`}
                    >
                      <span className="inline-flex items-center gap-1 font-semibold text-blue-400">
                        <Truck className="h-3 w-3" />+{formatNumber(inTransit)}
                      </span>
                      <span className="ml-1 font-mono text-[10px] text-muted-foreground">
                        {item.unit}
                      </span>
                      {item.transit_details && (
                        <p className="max-w-[130px] truncate text-[10px] text-muted-foreground">
                          {item.transit_details}
                        </p>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>

                <TableCell>
                  <Badge tone={status.tone}>
                    <span className={`mr-1.5 h-1.5 w-1.5 rounded-full ${status.dot}`} />
                    {item.status === "approved" ? "APPROVED" : item.urgency || status.label}
                  </Badge>
                </TableCell>

                <TableCell>
                  <div className="relative w-28">
                    <input
                      aria-label={`Количество к заказу: ${item.name}`}
                      type="number"
                      min={0}
                      step={mult}
                      value={quantity}
                      disabled={item.status === "approved"}
                      onChange={(event) =>
                        handleQuantityChange(item, event.currentTarget.valueAsNumber)
                      }
                      title={`Кратность упаковки поставщика: ${mult} ${item.unit}`}
                      className="h-9 w-full rounded-xl border border-border bg-input px-3 pr-7 text-sm font-bold text-blue-600 outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:text-blue-400"
                    />
                    <ArrowUpRight className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-blue-500" />
                  </div>
                  {mult > 1 && (
                    <p className="mt-0.5 text-[9px] text-muted-foreground">
                      кратность {mult} {item.unit}
                    </p>
                  )}
                </TableCell>

                <TableCell className="font-semibold text-card-foreground">
                  {quantity > 0
                    ? formatMoney(quantity * (item.unit_price ?? item.unitCost ?? 0))
                    : "—"}
                </TableCell>

                <TableCell className="pr-5">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      aria-label={`AI обоснование: ${item.name}`}
                      onClick={() => openDrawer(item)}
                      title="AI Обоснование позиции"
                      className="flex items-center gap-1 rounded-xl p-2 text-blue-400 transition hover:bg-blue-500/10 hover:text-blue-300"
                    >
                      <Sparkles className="h-4 w-4" />
                    </button>
                    <button
                      aria-label={`Изменить параметры: ${item.name}`}
                      onClick={() => openEdit(item.id)}
                      disabled={item.status === "approved"}
                      title="Редактировать параметры"
                      className="rounded-xl p-2 text-muted-foreground transition hover:bg-card-muted hover:text-foreground"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      {items.length === 0 && (
        <div className="flex flex-col items-center px-5 py-16 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-card-muted text-muted-foreground">
            <PackageOpen className="h-5 w-5" />
          </div>
          <p className="mt-4 font-semibold text-card-foreground">Ничего не найдено</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Измените поиск или параметры фильтра.
          </p>
        </div>
      )}
    </div>
  );
}
