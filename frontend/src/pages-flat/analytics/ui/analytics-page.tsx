"use client";

import { useQuery } from "@tanstack/react-query";
import { inventoryQueryOptions } from "@/entities/inventory";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Card, ErrorMessage, Skeleton } from "@/shared/ui";
import { AppShell } from "@/widgets/app-shell";

export function AnalyticsPage() {
  const query = useQuery(inventoryQueryOptions());
  const items = query.data ?? [];
  const total = items.reduce((sum, item) => sum + item.total_cost, 0);
  const critical = items.filter((item) => item.urgency === "CRITICAL").length;
  const outlierFlags = items.filter((item) => item.has_whale_outlier).length;

  return <AppShell><header className="mb-6"><h1 className="text-3xl font-bold">Аналитика рекомендаций</h1><p className="mt-2 text-sm text-muted-foreground">Показатели из текущего ответа API закупок.</p></header>
    {query.isPending ? <div className="grid gap-4 sm:grid-cols-3"><Skeleton className="h-36" /><Skeleton className="h-36" /><Skeleton className="h-36" /></div> : query.isError ? <ErrorMessage error={query.error} onRetry={() => void query.refetch()} /> : <div className="grid gap-4 sm:grid-cols-3">
      <Card className="p-5"><p className="text-xs text-muted-foreground">Сумма рекомендаций</p><strong className="mt-2 block text-2xl">{formatMoney(total)}</strong></Card>
      <Card className="p-5"><p className="text-xs text-muted-foreground">Критическая срочность</p><strong className="mt-2 block text-2xl">{formatNumber(critical)}</strong></Card>
      <Card className="p-5"><p className="text-xs text-muted-foreground">Позиций с признаком выброса</p><strong className="mt-2 block text-2xl">{formatNumber(outlierFlags)}</strong></Card>
    </div>}
    <Card className="mt-5 p-5 text-sm text-muted-foreground">История продаж, помесячные графики и журнал выбросов появятся после публикации соответствующих API. Текущий ответ содержит только признак выброса по позиции.</Card>
  </AppShell>;
}
