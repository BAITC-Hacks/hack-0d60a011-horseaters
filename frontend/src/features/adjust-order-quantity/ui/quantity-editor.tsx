"use client";

import { Minus, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { getSuggestedQuantity, type InventoryItem } from "@/entities/inventory";
import { orderQuantitySchema } from "../model/schema";
import { useOrderQuantityStore } from "../model/quantity-store";

export function QuantityEditor({ item, days }: { item: InventoryItem; days: number }) {
  const override = useOrderQuantityStore((state) => state.quantityById[item.id]);
  const setQuantity = useOrderQuantityStore((state) => state.setQuantity);
  const effective = override ?? getSuggestedQuantity(item, days);
  const [draft, setDraft] = useState(String(effective));
  const parsed = orderQuantitySchema.safeParse(Number(draft));
  const rounded = parsed.success && parsed.data > 0 ? Math.ceil(Math.max(parsed.data, item.moq) / item.packSize) * item.packSize : 0;
  const hint = draft !== "" && parsed.success && rounded !== parsed.data;

  useEffect(() => { setDraft(String(effective)); }, [effective]);

  function commit() {
    if (!parsed.success || draft === "") { setDraft(String(effective)); return; }
    setQuantity(item.id, rounded);
    setDraft(String(rounded));
  }

  function step(direction: -1 | 1) {
    const next = Math.max(0, effective + direction * item.packSize);
    const normalized = next === 0 ? 0 : Math.ceil(Math.max(next, item.moq) / item.packSize) * item.packSize;
    setQuantity(item.id, normalized);
    setDraft(String(normalized));
  }

  return <div className="w-[156px]"><div className="flex items-center overflow-hidden rounded-xl border border-border bg-input focus-within:border-ring focus-within:ring-1 focus-within:ring-ring"><button type="button" aria-label={`Уменьшить заказ: ${item.name}`} disabled={item.status === "approved"} onClick={() => step(-1)} className="flex h-9 w-8 shrink-0 items-center justify-center text-muted-foreground hover:bg-card-muted disabled:opacity-40"><Minus className="h-3.5 w-3.5" /></button><input aria-label={`Количество к заказу: ${item.name}`} inputMode="numeric" type="number" min={0} step={item.packSize} value={draft} disabled={item.status === "approved"} onChange={(event) => setDraft(event.target.value)} onBlur={commit} onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }} className="h-9 min-w-0 flex-1 bg-transparent px-1 text-center text-sm font-semibold text-foreground outline-none disabled:opacity-60" /><button type="button" aria-label={`Увеличить заказ: ${item.name}`} disabled={item.status === "approved"} onClick={() => step(1)} className="flex h-9 w-8 shrink-0 items-center justify-center text-muted-foreground hover:bg-card-muted disabled:opacity-40"><Plus className="h-3.5 w-3.5" /></button></div><div className="mt-1 min-h-4 text-[10px] text-muted-foreground">{hint ? `Будет округлено до ${rounded}` : `Кратность ${item.packSize} ${item.unit}`}</div></div>;
}
