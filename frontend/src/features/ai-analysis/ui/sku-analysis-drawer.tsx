"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bot,
  Calendar,
  CheckCircle2,
  Clock,
  Layers,
  Package,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  Truck,
  X,
} from "lucide-react";
import { recommendationExplanationQueryOptions } from "@/entities/recommendation";
import { apiUuidSchema } from "@/shared/api";
import { formatMoney, formatNumber } from "@/shared/lib";
import { Badge, Button, ErrorMessage, Skeleton } from "@/shared/ui";
import { fetchSkuAnalysis } from "../api/ai-api";
import { useAiStore } from "../model/ai-store";

export function SkuAnalysisDrawer() {
  const item = useAiStore((state) => state.activeDrawerItem);
  const close = useAiStore((state) => state.closeDrawer);
  const hasRecommendationId = apiUuidSchema.safeParse(item?.id).success;

  const {
    data: analysis,
    isPending,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["ai-sku-analysis", item?.id, item?.adjusted_need, item?.current_stock],
    queryFn: () => {
      if (!item) throw new Error("Позиция для анализа не выбрана.");
      return fetchSkuAnalysis(item);
    },
    enabled: Boolean(item),
    staleTime: 300_000,
  });

  const {
    data: explanation,
    isPending: isExplanationPending,
    isError: isExplanationError,
    error: explanationError,
    refetch: refetchExplanation,
  } = useQuery({
    ...recommendationExplanationQueryOptions(item?.id ?? ""),
    enabled: Boolean(item && hasRecommendationId),
  });

  if (!item) return null;

  const stock = item.current_stock ?? item.stock;
  const inTransit = item.in_transit ?? 0;
  const dailyDemand = item.daily_demand;
  const daysOfStock = item.days_of_stock;
  const mult = item.package_multiplicity ?? item.packSize ?? 1;
  const need = item.adjusted_need ?? item.calculated_need;
  const unitPrice = item.unit_price ?? item.unitCost;
  const cost = need !== undefined && unitPrice !== undefined ? need * unitPrice : null;

  const isCritical = item.urgency.toLowerCase() === "critical";
  const isHigh = item.urgency.toLowerCase() === "high";

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-all"
    >
      <div className="flex h-full w-full max-w-xl flex-col bg-card shadow-2xl transition-transform animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border p-6">
          <div className="pr-4">
            <div className="flex items-center gap-2">
              <Badge tone={isCritical ? "red" : isHigh ? "amber" : "green"}>
                {item.urgency || "NORMAL"}
              </Badge>
              <span className="font-mono text-xs text-muted-foreground">{item.sku}</span>
              {item.vendor_code && (
                <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                  {item.vendor_code}
                </span>
              )}
            </div>
            <h2 className="mt-2 text-lg font-bold leading-snug text-card-foreground">
              {item.name || item.item_name}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {item.category} • {item.supplier_name || item.supplier}
            </p>
          </div>
          <button
            onClick={close}
            className="rounded-xl p-2 text-muted-foreground transition hover:bg-card-muted hover:text-foreground"
            aria-label="Закрыть"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 space-y-6 overflow-y-auto p-6">
          {/* Outlier and Stockout Badges */}
          {(item.has_whale_outlier || item.stockout_recovered) && (
            <div className="flex flex-wrap gap-2">
              {item.has_whale_outlier && (
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/20 bg-purple-500/10 px-2.5 py-1 text-xs font-semibold text-purple-400">
                  <ShieldAlert className="h-3.5 w-3.5" />
                  Оптовый выброс отфильтрован (Whale Order)
                </span>
              )}
              {item.stockout_recovered && (
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-xs font-semibold text-blue-400">
                  <TrendingUp className="h-3.5 w-3.5" />
                  Спрос скорректирован после дефицита (Stockout)
                </span>
              )}
            </div>
          )}

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <Package className="h-3.5 w-3.5" /> Остаток
              </span>
              <p className="mt-1 text-lg font-bold text-foreground">
                {formatNumber(stock)}{" "}
                <span className="font-mono text-xs font-normal text-muted-foreground">
                  {item.unit}
                </span>
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <Truck className="h-3.5 w-3.5" /> В пути
              </span>
              <p className="mt-1 text-lg font-bold text-blue-400">
                {formatNumber(inTransit)}{" "}
                <span className="font-mono text-xs font-normal text-muted-foreground">
                  {item.unit}
                </span>
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <Clock className="h-3.5 w-3.5" /> Дней запаса
              </span>
              <p
                className={`mt-1 text-lg font-bold ${
                  daysOfStock == null ? "text-muted-foreground" : daysOfStock <= 5 ? "text-red-400" : daysOfStock <= 15 ? "text-amber-400" : "text-emerald-400"
                }`}
              >
                {daysOfStock == null ? "Нет данных" : `${daysOfStock.toFixed(1)} дн.`}
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" /> Расход / сут
              </span>
              <p className="mt-1 text-base font-bold text-foreground">
                {dailyDemand == null ? "Нет данных" : dailyDemand.toFixed(1)}{" "}
                <span className="font-mono text-xs font-normal text-muted-foreground">
                  {item.unit}/д
                </span>
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <Calendar className="h-3.5 w-3.5" /> Индекс сезонности
              </span>
              <p className="mt-1 text-base font-bold text-foreground">
                {item.season_factor == null ? "Нет данных" : `×${item.season_factor.toFixed(2)}`}
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <Layers className="h-3.5 w-3.5" /> Кратность упаковки
              </span>
              <p className="mt-1 text-base font-bold text-foreground">
                {mult}{" "}
                <span className="font-mono text-xs font-normal text-muted-foreground">
                  {item.unit}
                </span>
              </p>
            </div>
          </div>

          {/* Transit Details Callout */}
          {item.transit_details && (
            <div className="flex items-center gap-2.5 rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-2.5 text-xs text-blue-300">
              <Truck className="h-4 w-4 shrink-0 text-blue-400" />
              <span>{item.transit_details}</span>
            </div>
          )}

          {/* AI Explainability Card */}
          <div className="rounded-2xl border border-blue-500/30 bg-gradient-to-b from-blue-950/20 to-card p-5">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-500/20 text-blue-400">
                  <Sparkles className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-bold text-foreground">Анализ позиции</h3>
              </div>
              {analysis && (
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                    analysis.is_fallback
                      ? "border border-muted bg-card-muted text-muted-foreground"
                      : "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  }`}
                >
                  <Bot className="h-3 w-3" />
                  {analysis.is_fallback ? "Серверный шаблон" : "Анализ сервера"}
                </span>
              )}
            </div>

            {isPending ? (
              <div role="status" aria-label="Загрузка анализа" className="mt-4 space-y-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : isError ? (
              <div className="mt-4"><ErrorMessage title="Не удалось загрузить анализ позиции" error={error} onRetry={() => void refetch()} /></div>
            ) : !analysis ? (
              <p className="py-4 text-xs text-muted-foreground">Сервер не вернул анализ позиции.</p>
            ) : (
              <div className="mt-4 space-y-4 text-xs leading-relaxed">
                <div>
                  <h4 className="font-bold uppercase tracking-wider text-muted-foreground">
                    Резюме позиции
                  </h4>
                  <p className="mt-1 text-sm text-foreground">{analysis.summary}</p>
                </div>

                <div>
                  <h4 className="flex items-center gap-1 font-bold uppercase tracking-wider text-muted-foreground">
                    <TrendingUp className="h-3.5 w-3.5 text-blue-400" />
                    Первопричина потребности
                  </h4>
                  <p className="mt-1 text-muted-foreground">{analysis.root_cause}</p>
                </div>

                <div>
                  <h4 className="flex items-center gap-1 font-bold uppercase tracking-wider text-muted-foreground">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                    Анализ рисков
                  </h4>
                  <p className="mt-1 text-muted-foreground">{analysis.risk_analysis}</p>
                </div>

                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3.5">
                  <h4 className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    Рекомендация закупщику
                  </h4>
                  <p className="mt-1.5 font-medium text-emerald-200">
                    {analysis.recommendation_action}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 text-[10px] text-muted-foreground">
                  <span>Уверенность аналитической модели:</span>
                  <span className="font-mono font-bold text-foreground">
                    {Math.round(analysis.confidence_score * 100)}%
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-border bg-card-muted p-5">
            <h3 className="text-sm font-bold text-foreground">Формула расчёта</h3>
            {!hasRecommendationId ? (
              <p className="mt-2 text-xs text-muted-foreground">Формула недоступна для обзорного списка. Откройте рекомендацию завершённого расчёта.</p>
            ) : isExplanationPending ? (
              <div role="status" aria-label="Загрузка формулы" className="mt-3 space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : isExplanationError ? (
              <div className="mt-3"><ErrorMessage title="Не удалось загрузить формулу" error={explanationError} onRetry={() => void refetchExplanation()} /></div>
            ) : explanation ? (
              <div className="mt-3 space-y-3 text-xs text-muted-foreground">
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-xl border border-border bg-card p-3 font-mono text-foreground">{explanation.formula}</pre>
                <p>{explanation.text}</p>
                <p>Аномалий в расчёте: {explanation.anomalies.length}</p>
                <p>Итоговый прогноз: {formatNumber(explanation.forecast.forecast_quantity)} {item.unit}</p>
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted-foreground">Сервер не вернул формулу расчёта.</p>
            )}
          </div>

          {item.reasoning && (
            <div className="rounded-xl border border-border bg-card-muted p-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Обоснование в обзорном списке
              </span>
              <p className="mt-1.5 text-xs text-muted-foreground">{item.reasoning}</p>
            </div>
          )}
        </div>

        {/* Footer Order Summary */}
        <div className="flex items-center justify-between border-t border-border bg-card-muted/50 p-6">
          <div>
            <p className="text-[10px] font-bold uppercase text-muted-foreground">К заказу</p>
            <p className="text-xl font-bold text-foreground">
              {need == null ? "Нет данных" : formatNumber(need)}{" "}
              <span className="text-xs font-normal text-muted-foreground">{item.unit}</span>
            </p>
            <p className="text-xs text-muted-foreground">
              {cost == null || unitPrice == null ? "Стоимость не указана" : `${formatMoney(cost)} (${formatMoney(unitPrice)}/${item.unit})`}
            </p>
          </div>
          <Button onClick={close}>Понятно</Button>
        </div>
      </div>
    </div>
  );
}
