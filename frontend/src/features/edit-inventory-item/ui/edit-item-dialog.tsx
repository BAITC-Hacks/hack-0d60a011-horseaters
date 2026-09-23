"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { inventoryKeys, inventoryUpdateSchema, updateInventoryItem, type InventoryItem, type InventoryUpdate } from "@/entities/inventory";
import { Button, Input } from "@/shared/ui";
import { useEditStore } from "../model/edit-store";

export function EditItemDialog({ item }: { item: InventoryItem | null }) {
  const close = useEditStore((state) => state.close);
  const queryClient = useQueryClient();
  const form = useForm<InventoryUpdate>({ resolver: zodResolver(inventoryUpdateSchema), defaultValues: { adjusted_need: item?.adjusted_need ?? 0 } });
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
    form.reset({ adjusted_need: item?.adjusted_need ?? 0 });
  }, [form, item?.id, item?.adjusted_need]);

  if (!item) return null;
  return <div role="presentation" className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
    <div role="dialog" aria-modal="true" aria-labelledby="edit-title" className="w-full max-w-md rounded-3xl border border-border bg-card p-6 shadow-2xl">
      <div className="flex items-start justify-between gap-4"><div><p className="text-xs text-muted-foreground">Корректировка потребности</p><h2 id="edit-title" className="mt-1 text-xl font-bold">{item.name}</h2><p className="mt-1 font-mono text-xs text-muted-foreground">{item.sku}</p></div><Button type="button" variant="ghost" size="icon" onClick={close} aria-label="Закрыть"><X className="h-4 w-4" /></Button></div>
      <form onSubmit={form.handleSubmit((input) => mutation.mutate(input))} className="mt-6 space-y-4">
        <label className="block"><span className="mb-2 block text-sm font-medium">Количество к заказу</span><Input type="number" min={0} step="any" {...form.register("adjusted_need", { valueAsNumber: true })} /><span className="mt-1 block text-xs text-muted-foreground">MOQ: {item.moq}; кратность: {item.package_multiplicity}. Сервер округлит количество по кратности.</span>{form.formState.errors.adjusted_need && <span className="mt-1 block text-xs text-red-500">{form.formState.errors.adjusted_need.message}</span>}</label>
        {mutation.isError && <p role="alert" className="rounded-xl bg-red-500/10 p-3 text-sm text-red-500">{mutation.error instanceof Error ? mutation.error.message : "Не удалось сохранить правку."}</p>}
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={close}>Отмена</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Сохранение…" : "Сохранить через API"}</Button></div>
      </form>
    </div>
  </div>;
}
