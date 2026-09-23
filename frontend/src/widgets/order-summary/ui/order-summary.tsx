"use client";

import { ArrowRight, Download, Info, ShoppingCart, Truck } from "lucide-react";
import { useState } from "react";
import { getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { exportOrderCsv } from "@/features/export-order";
import { useSelectionStore } from "@/features/select-items";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Button } from "@/shared/ui";

export function OrderSummary({ items }: { items: InventoryItem[] }) {
  const selectedIds = useSelectionStore((state) => state.selectedIds);
  const [notice, setNotice] = useState("");
  const scoped = selectedIds.length > 0 ? items.filter((item) => selectedIds.includes(item.id)) : items;
  const orderItems = scoped.filter((item) => getSuggestedQuantity(item) > 0);
  const total = orderItems.reduce((sum, item) => sum + getSuggestedQuantity(item) * item.unitCost, 0);
  const suppliers = new Set(orderItems.map((item) => item.supplier)).size;

  function download() {
    const count = exportOrderCsv(orderItems);
    setNotice(count > 0 ? `Файл с ${count} позициями скачан.` : "Нет позиций с рекомендацией к заказу.");
  }

  return (
    <section id="order-summary" className="overflow-hidden rounded-2xl border border-[#e6eded] bg-white shadow-[0_2px_12px_rgba(24,49,43,0.025)]">
      <div className="flex items-start gap-3 border-b border-[#ebefee] p-5"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#e8f5ed] text-[#158158]"><ShoppingCart className="h-4.5 w-4.5" /></div><div><h2 className="font-bold text-[#273733]">План закупок</h2><p className="mt-1 text-xs text-[#91a09c]">{selectedIds.length > 0 ? `По ${selectedIds.length} выбранным позициям` : "По всем найденным позициям"}</p></div></div>
      <div className="p-5">
        <div className="flex items-end justify-between"><div><p className="text-xs font-medium text-[#8b9996]">Итого к заказу</p><p className="mt-1 text-[29px] font-bold tracking-tight text-[#1a2d27]">{formatMoney(total)}</p></div><div className="rounded-xl bg-[#f3f8f5] p-2.5 text-[#17835b]"><ArrowRight className="h-5 w-5" /></div></div>
        <div className="my-5 grid grid-cols-2 gap-3"><div className="rounded-xl bg-[#f8faf9] p-3"><div className="text-xl font-bold text-[#31433b]">{formatNumber(orderItems.length)}</div><div className="mt-1 text-xs text-[#91a09b]">позиций</div></div><div className="rounded-xl bg-[#f8faf9] p-3"><div className="flex items-center gap-1.5 text-xl font-bold text-[#31433b]">{suppliers}<Truck className="h-4 w-4 text-[#8ca198]" /></div><div className="mt-1 text-xs text-[#91a09b]">поставщика</div></div></div>
        <Button className="w-full" onClick={download} disabled={orderItems.length === 0}><Download className="h-4 w-4" />Скачать заказ CSV</Button>
        {notice && <p role="status" className="mt-3 text-center text-xs text-[#17835b]">{notice}</p>}
        <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-[#9aa7a4]"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />Выберите строки в таблице, чтобы выгрузить только их. Без выбора выгружаются все найденные позиции.</p>
      </div>
    </section>
  );
}
