"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { inventoryKeys, inventoryUpdateSchema, updateInventoryItem, type InventoryItem, type InventoryUpdate } from "@/entities/inventory";
import { Button, Input } from "@/shared/ui";
import { useEditStore } from "../model/edit-store";

const fields: { key: keyof InventoryUpdate; label: string; hint: string }[] = [
  { key: "minStock", label: "Страховой запас", hint: "Минимальный остаток" },
  { key: "demand30", label: "Спрос за 30 дней", hint: "Ожидаемый расход" },
  { key: "leadDays", label: "Срок поставки, дней", hint: "От заявки до поступления" },
  { key: "packSize", label: "Кратность заказа", hint: "Минимальный шаг" },
  { key: "unitCost", label: "Цена за единицу, ₽", hint: "Для расчёта суммы" },
];

export function EditItemDialog({ item }: { item: InventoryItem | null }) {
  const close = useEditStore((state) => state.close);
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<InventoryUpdate>({ resolver: zodResolver(inventoryUpdateSchema), defaultValues: item ? pickUpdate(item) : undefined });
  const mutation = useMutation({
    mutationFn: (input: InventoryUpdate) => {
      if (!item) throw new Error("Позиция не выбрана.");
      return updateInventoryItem(item.id, input);
    },
    onSuccess: async (updated) => {
      queryClient.setQueryData<InventoryItem[]>(inventoryKeys.list(), (rows) => rows?.map((row) => row.id === updated.id ? updated : row));
      await queryClient.invalidateQueries({ queryKey: inventoryKeys.all });
      close();
    },
  });

  useEffect(() => {
    if (item) reset(pickUpdate(item));
    mutation.reset();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.id, reset]);

  if (!item) return null;

  return <div role="presentation" className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><div role="dialog" aria-modal="true" aria-labelledby="edit-title" className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl border border-border bg-card text-card-foreground shadow-2xl">
    <div className="flex items-start justify-between border-b border-border p-6"><div><p className="mb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-blue-500 dark:text-blue-400">Параметры расчёта</p><h2 id="edit-title" className="text-xl font-bold">{item.name}</h2><p className="mt-1 font-mono text-[11px] text-muted-foreground">{item.sku} / остаток {item.stock} {item.unit}</p></div><Button type="button" variant="ghost" size="icon" aria-label="Закрыть" onClick={close}><X className="h-5 w-5" /></Button></div>
    <form onSubmit={handleSubmit((input) => mutation.mutate(input))} className="p-6"><div className="grid gap-4 sm:grid-cols-2">{fields.map((field) => <label key={field.key} className={field.key === "unitCost" ? "sm:col-span-2" : ""}><span className="mb-1.5 block text-xs font-semibold">{field.label}</span><Input type="number" min={field.key === "leadDays" || field.key === "packSize" ? 1 : 0} step={field.key === "unitCost" ? "0.01" : 1} {...register(field.key, { valueAsNumber: true })} /><span className={`mt-1.5 block text-[10px] ${errors[field.key] ? "text-red-500" : "text-muted-foreground"}`}>{errors[field.key]?.message ?? field.hint}</span></label>)}</div>
      {mutation.isError && <p role="alert" className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-500">{mutation.error instanceof Error ? mutation.error.message : "Не удалось сохранить изменения."}</p>}
      <div className="mt-6 flex justify-end gap-2"><Button type="button" variant="secondary" onClick={close}>Отмена</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Сохранение…" : "Сохранить"}</Button></div>
    </form>
  </div></div>;
}

function pickUpdate(item: InventoryItem): InventoryUpdate {
  return { minStock: item.minStock, demand30: item.demand30, leadDays: item.leadDays, packSize: item.packSize, unitCost: item.unitCost };
}
