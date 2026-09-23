"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, Calculator, CheckCircle2, RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { calculationRunQueryOptions, createCalculationRun } from "@/entities/calculation-run";
import { ApiError } from "@/shared/api";
import { Button } from "@/shared/ui";
import { runCalculationSchema, type RunCalculationInput } from "../model/schema";
import { useCalculationSessionStore } from "../model/run-session";

type Props = {
  horizonDays: number;
  warehouseId?: string | null;
  categoryId?: string | null;
  onCompleted?: (runId: string) => void;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 422) {
    return "Сервер отклонил расчёт. Проверьте параметры и наличие завершённых импортов для выбранного источника.";
  }
  return error instanceof Error ? error.message : "Не удалось запустить расчёт. Повторите попытку.";
}

export function RunCalculationAction({ horizonDays, warehouseId, categoryId, onCompleted }: Props) {
  const activeRunId = useCalculationSessionStore((state) => state.activeRunId);
  const setActiveRunId = useCalculationSessionStore((state) => state.setActiveRunId);
  const notifiedRunRef = useRef<string | null>(null);
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<RunCalculationInput>({
    resolver: zodResolver(runCalculationSchema),
    defaultValues: {
      demand_source: "transactions",
      horizon_days: horizonDays,
      warehouse_id: warehouseId ?? null,
      category_id: categoryId ?? null,
    },
    mode: "onChange",
  });

  useEffect(() => {
    setValue("horizon_days", horizonDays, { shouldValidate: true });
  }, [horizonDays, setValue]);
  useEffect(() => {
    setValue("warehouse_id", warehouseId ?? null, { shouldValidate: true });
  }, [warehouseId, setValue]);
  useEffect(() => {
    setValue("category_id", categoryId ?? null, { shouldValidate: true });
  }, [categoryId, setValue]);

  const mutation = useMutation({
    mutationFn: createCalculationRun,
    onSuccess: (run) => setActiveRunId(run.id),
  });
  const runQuery = useQuery({
    ...calculationRunQueryOptions(activeRunId ?? ""),
    enabled: activeRunId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 2000 : false;
    },
  });
  const run = runQuery.data ?? (mutation.isSuccess && mutation.data.id === activeRunId ? mutation.data : null);
  const inProgress = mutation.isPending || run?.status === "pending" || run?.status === "running" || (activeRunId !== null && runQuery.isPending);

  useEffect(() => {
    if (run?.status === "completed" && notifiedRunRef.current !== run.id) {
      notifiedRunRef.current = run.id;
      onCompleted?.(run.id);
    }
  }, [run, onCompleted]);

  return <div className="space-y-3">
    <form className="flex flex-wrap items-end gap-2" onSubmit={handleSubmit((values) => mutation.mutate(values))} noValidate>
      <label className="min-w-40 flex-1 text-xs font-medium text-muted-foreground">Источник спроса
        <select {...register("demand_source")} disabled={inProgress} className="mt-1.5 h-10 w-full rounded-xl border border-border bg-input px-3 text-xs text-foreground outline-none focus:border-ring disabled:opacity-50">
          <option value="transactions">Продажи по документам</option>
          <option value="monthly_sales">Продажи по месяцам</option>
        </select>
        {errors.demand_source && <span role="alert" className="mt-1 block text-xs text-destructive">{errors.demand_source.message}</span>}
      </label>
      <label className="w-30 text-xs font-medium text-muted-foreground">Горизонт, дней
        <input type="number" min={1} max={365} step={1} {...register("horizon_days", { valueAsNumber: true })} disabled={inProgress} className="mt-1.5 h-10 w-full rounded-xl border border-border bg-input px-3 text-xs text-foreground outline-none focus:border-ring disabled:opacity-50" />
        {errors.horizon_days && <span role="alert" className="mt-1 block text-xs text-destructive">{errors.horizon_days.message}</span>}
      </label>
      <Button type="submit" disabled={inProgress} className="min-h-10"><Calculator className="h-4 w-4" />{inProgress ? "Расчёт выполняется…" : "Пересчитать потребность"}</Button>
      {(errors.warehouse_id || errors.category_id) && <p role="alert" className="w-full text-xs text-destructive">{errors.warehouse_id?.message ?? errors.category_id?.message}</p>}
    </form>
    {inProgress && <div role="status" aria-live="polite" className="rounded-xl border border-border bg-card-muted p-3 text-xs text-muted-foreground"><div className="flex items-center gap-2"><span className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />{mutation.isPending ? "Отправляем параметры расчёта…" : "Расчёт запущен. Проверяем состояние…"}</div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full w-1/3 animate-pulse rounded-full bg-primary" /></div></div>}
    {mutation.isError && <div role="alert" className="flex gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive"><AlertCircle className="h-4 w-4 shrink-0" />{getErrorMessage(mutation.error)}</div>}
    {runQuery.isError && <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive"><p>Не удалось узнать состояние расчёта: {getErrorMessage(runQuery.error)}</p><Button type="button" variant="secondary" size="sm" className="mt-2" onClick={() => void runQuery.refetch()}><RotateCcw className="h-3.5 w-3.5" />Повторить запрос</Button></div>}
    {run?.status === "completed" && !runQuery.isError && <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-500"><CheckCircle2 className="h-4 w-4 shrink-0" />Расчёт завершён. Рекомендаций: {run.recommendation_count ?? "нет данных"}. ID запуска: {run.id}</div>}
    {run?.status === "failed" && <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">Расчёт завершился ошибкой. Проверьте загруженные источники и повторите запуск. ID запуска: {run.id}</div>}
  </div>;
}
