"use client";

import { useQuery } from "@tanstack/react-query";
import { calculationRunQueryOptions } from "@/entities/calculation-run";
import { Badge } from "@/shared/ui";
import { useCalculationSessionStore } from "../model/run-session";

export function CalculationRunBadge() {
  const activeRunId = useCalculationSessionStore((state) => state.activeRunId);
  const { data, isError, isPending } = useQuery({
    ...calculationRunQueryOptions(activeRunId ?? ""),
    enabled: activeRunId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 2000 : false;
    },
  });

  if (!activeRunId) return null;
  if (isError) return <Badge tone="red">Статус расчёта недоступен</Badge>;
  if (isPending || data?.status === "pending") return <Badge tone="amber">Расчёт ожидает</Badge>;
  if (data?.status === "running") return <Badge tone="blue">Расчёт выполняется</Badge>;
  if (data?.status === "completed") return <Badge tone="green">Расчёт завершён</Badge>;
  return <Badge tone="red">Расчёт завершился ошибкой</Badge>;
}
