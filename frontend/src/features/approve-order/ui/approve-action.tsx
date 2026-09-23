"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, X } from "lucide-react";
import { useState } from "react";
import { approveInventoryItems, inventoryKeys, type InventoryItem } from "@/entities/inventory";
import { formatMoney } from "@/shared/lib";
import { Button } from "@/shared/ui";

export function ApproveAction({ items, selectedIds, quantities, onDone }: { items: InventoryItem[]; selectedIds: string[]; quantities: Record<string, number>; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const eligible = items.filter((item) => selectedIds.includes(item.id) && item.status !== "approved" && (quantities[item.id] ?? 0) > 0);
  const total = eligible.reduce((sum, item) => sum + (quantities[item.id] ?? 0) * item.unitCost, 0);
  const mutation = useMutation({
    mutationFn: () => approveInventoryItems(Object.fromEntries(eligible.map((item) => [item.id, quantities[item.id]]))),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: inventoryKeys.all }); setOpen(false); onDone(); },
  });

  return <><Button onClick={() => setOpen(true)} disabled={eligible.length === 0}><CheckCheck className="h-4 w-4" />Утвердить отмеченные ({eligible.length})</Button>{open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"><div role="dialog" aria-modal="true" aria-labelledby="approve-title" className="w-full max-w-md rounded-3xl border border-border bg-card p-6 shadow-2xl"><div className="flex items-start justify-between"><div><p className="font-mono text-[10px] uppercase tracking-[0.14em] text-blue-500">Подтверждение закупки</p><h2 id="approve-title" className="mt-2 text-xl font-bold">Утвердить {eligible.length} позиций?</h2></div><button onClick={() => setOpen(false)} aria-label="Закрыть" className="rounded-xl p-1 text-muted-foreground hover:bg-card-muted"><X className="h-5 w-5" /></button></div><p className="mt-4 text-sm leading-6 text-muted-foreground">Общая сумма: <strong className="text-foreground">{formatMoney(total)}</strong>. После утверждения позиции станут доступны в разделе заказов и будут защищены от случайной корректировки.</p>{mutation.isError && <p role="alert" className="mt-4 rounded-xl bg-red-500/10 p-3 text-sm text-red-500">{mutation.error instanceof Error ? mutation.error.message : "Не удалось утвердить заказ."}</p>}<div className="mt-6 flex justify-end gap-2"><Button variant="secondary" onClick={() => setOpen(false)}>Отмена</Button><Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>{mutation.isPending ? "Утверждение…" : "Подтвердить"}</Button></div></div></div>}</>;
}
