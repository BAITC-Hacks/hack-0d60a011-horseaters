"use client";

import { ChevronDown, PackageCheck, Truck } from "lucide-react";
import { useState } from "react";
import { getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { useOrderQuantityStore } from "@/features/adjust-order-quantity";
import { ApproveAction } from "@/features/approve-order";
import { EmailDraftButton } from "@/features/draft-supplier-email";
import { ExportMenu } from "@/features/export-order";
import { useHorizonStore } from "@/features/set-horizon";
import { formatMoney } from "@/shared/lib";
import { Badge, Card } from "@/shared/ui";

export function SupplierOrders({ items }: { items: InventoryItem[] }) {
  const [expanded, setExpanded] = useState<string[]>([]);
  const quantities = useOrderQuantityStore((state) => state.quantityById);
  const days = useHorizonStore((state) => state.days);
  const suppliers = [...new Set(items.map((item) => item.supplier))];

  return <div className="space-y-4">{suppliers.map((supplier) => {
    const group = items.filter((item) => item.supplier === supplier);
    const pending = group.filter((item) => item.status !== "approved" && (quantities[item.id] ?? getSuggestedQuantity(item, days)) > 0);
    const approved = group.filter((item) => item.status === "approved" && (item.approvedQuantity ?? 0) > 0);
    const active = [...pending, ...approved];
    const total = active.reduce((sum, item) => sum + (item.approvedQuantity ?? quantities[item.id] ?? getSuggestedQuantity(item, days)) * item.unitCost, 0);
    const moqValue = group[0]?.supplierMinOrder ?? 0;
    const progress = moqValue === 0 ? 100 : Math.min(100, total / moqValue * 100);
    const isOpen = expanded.includes(supplier);
    const inputQuantities = Object.fromEntries(pending.map((item) => [item.id, quantities[item.id] ?? getSuggestedQuantity(item, days)]));
    return <Card key={supplier} className="overflow-hidden"><button onClick={() => setExpanded((current) => isOpen ? current.filter((value) => value !== supplier) : [...current, supplier])} aria-expanded={isOpen} className="flex w-full flex-wrap items-center justify-between gap-4 p-5 text-left"><div className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-500"><Truck className="h-5 w-5" /></span><span><strong className="block text-lg">{supplier}</strong><span className="mt-1 block text-xs text-muted-foreground">Плечо доставки {group[0]?.leadDays} дней · {active.length} позиций</span></span></div><div className="flex items-center gap-3"><span className="text-right"><strong className="block text-lg">{formatMoney(total)}</strong><span className="text-[10px] text-muted-foreground">{approved.length} утверждено</span></span><ChevronDown className={`h-5 w-5 text-muted-foreground transition-transform ${isOpen ? "rotate-180" : ""}`} /></div></button><div className="px-5 pb-5"><div className="flex justify-between gap-3 text-xs"><span className="text-muted-foreground">Минимальная сумма отгрузки: {formatMoney(moqValue)}</span><strong className={progress >= 100 ? "text-emerald-500" : "text-amber-500"}>{progress >= 100 ? "Порог пройден" : `Не хватает ${formatMoney(Math.max(0, moqValue - total))}`}</strong></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-card-muted"><div className={`h-full rounded-full ${progress >= 100 ? "bg-emerald-500" : "bg-amber-500"}`} style={{ width: `${progress}%` }} /></div>{isOpen && <div className="mt-5 border-t border-border pt-5"><div className="space-y-2">{group.map((item) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-card-muted px-3 py-2 text-xs"><span className="font-medium">{item.name}<span className="ml-2 font-mono text-muted-foreground">{item.sku}</span>{item.approvedAt && <span className="mt-1 block text-[10px] font-normal text-muted-foreground">Утверждено {item.approvedAt.slice(0, 10)} · {item.approvedBy}</span>}</span><span className="flex items-center gap-3"><strong>{item.approvedQuantity ?? quantities[item.id] ?? getSuggestedQuantity(item, days)} {item.unit}</strong><Badge tone={item.status === "approved" ? "green" : "amber"}>{item.status === "approved" ? "APPROVED" : "ПЛАН"}</Badge></span></div>)}</div><div className="mt-5 flex flex-wrap gap-2"><ApproveAction items={group} selectedIds={pending.map((item) => item.id)} quantities={inputQuantities} onDone={() => undefined} /><ExportMenu items={group} /><EmailDraftButton items={group} /></div><p className="mt-3 text-[11px] text-muted-foreground"><PackageCheck className="mr-1 inline h-3.5 w-3.5" />Для экспорта и черновика письма используются только утверждённые позиции.</p></div>}</div></Card>;
  })}</div>;
}
