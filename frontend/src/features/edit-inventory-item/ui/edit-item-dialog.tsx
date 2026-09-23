"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { inventoryKeys, inventoryUpdateSchema, updateInventoryItem, type InventoryItem, type InventoryUpdate } from "@/entities/inventory";
import { Button } from "@/shared/ui";
import { useEditStore } from "../model/edit-store";

const fields: { key: keyof InventoryUpdate; label: string; hint: string }[] = [
  { key: "minStock", label: "Страховой запас", hint: "Минимальный остаток на складе" },
  { key: "demand30", label: "Спрос за 30 дней", hint: "Ожидаемый расход за месяц" },
  { key: "leadDays", label: "Срок поставки, дней", hint: "От заявки до поступления" },
  { key: "packSize", label: "Кратность заказа", hint: "Минимальный шаг закупки" },
  { key: "unitCost", label: "Цена за единицу, ₽", hint: "Для расчёта суммы заказа" },
];

export function EditItemDialog({ item }: { item: InventoryItem | null }) {
  const close = useEditStore((state) => state.close);
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<InventoryUpdate>({
    resolver: zodResolver(inventoryUpdateSchema),
    defaultValues: item ? pickUpdate(item) : undefined,
  });
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
  // Reset only when a different item is opened.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.id, reset]);

  if (!item) return null;

  return (
    <div role="presentation" className="fixed inset-0 z-50 flex items-center justify-center bg-[#102522]/50 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
      <div role="dialog" aria-modal="true" aria-labelledby="edit-title" className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="flex items-start justify-between border-b border-[#e8edee] p-6">
          <div><p className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-[#17835b]">Параметры расчёта</p><h2 id="edit-title" className="text-xl font-bold text-[#182125]">{item.name}</h2><p className="mt-1 text-sm text-[#819094]">{item.sku} · Остаток: {item.stock} {item.unit}</p></div>
          <button aria-label="Закрыть" onClick={close} className="rounded-lg p-1.5 text-[#7b8a8e] hover:bg-[#f2f5f4]"><X className="h-5 w-5" /></button>
        </div>
        <form onSubmit={handleSubmit((input) => mutation.mutate(input))} className="p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {fields.map((field) => <label key={field.key} className={field.key === "unitCost" ? "sm:col-span-2" : ""}>
              <span className="mb-1.5 block text-sm font-semibold text-[#344247]">{field.label}</span>
              <input type="number" min={field.key === "leadDays" || field.key === "packSize" ? 1 : 0} step={field.key === "unitCost" ? "0.01" : 1} {...register(field.key, { valueAsNumber: true })} className="h-11 w-full rounded-xl border border-[#dce4e5] px-3.5 text-sm outline-none focus:border-[#17835b]" />
              <span className="mt-1 block text-xs text-[#94a0a2]">{errors[field.key]?.message ?? field.hint}</span>
            </label>)}
          </div>
          {mutation.isError && <p role="alert" className="mt-4 rounded-xl bg-[#fcebea] p-3 text-sm text-[#b94843]">{mutation.error instanceof Error ? mutation.error.message : "Не удалось сохранить изменения."}</p>}
          <div className="mt-6 flex justify-end gap-2"><Button type="button" variant="secondary" onClick={close}>Отмена</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Сохранение…" : "Сохранить"}</Button></div>
        </form>
      </div>
    </div>
  );
}

function pickUpdate(item: InventoryItem): InventoryUpdate {
  return { minStock: item.minStock, demand30: item.demand30, leadDays: item.leadDays, packSize: item.packSize, unitCost: item.unitCost };
}
