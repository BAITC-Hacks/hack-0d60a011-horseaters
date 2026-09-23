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
import { formatMoney, formatNumber } from "@/shared/lib";
import { Badge, Button } from "@/shared/ui";
import { fetchSkuAnalysis } from "../api/ai-api";
import { useAiStore } from "../model/ai-store";

export function SkuAnalysisDrawer() {
  const item = useAiStore((state) => state.activeDrawerItem);
  const close = useAiStore((state) => state.closeDrawer);

  const {
    data: analysis,
    isPending,
    isError,
  } = useQuery({
    queryKey: ["ai-sku-analysis", item?.id, item?.adjusted_need, item?.current_stock],
    queryFn: () => (item ? fetchSkuAnalysis(item) : Promise.reject("No item")),
    enabled: Boolean(item),
    staleTime: 300_000,
  });

  if (!item) return null;

  const stock = item.current_stock ?? item.stock;
  const inTransit = item.in_transit ?? 0;
  const dailyDemand = item.daily_demand ?? (item.demand30 ? item.demand30 / 30 : 0);
  const daysOfStock = item.days_of_stock ?? (dailyDemand > 0 ? stock / dailyDemand : 0);
  const mult = item.package_multiplicity ?? item.packSize ?? 1;
  const need = item.adjusted_need ?? item.calculated_need ?? 0;
  const unitPrice = item.unit_price ?? item.unitCost ?? 0;
  const cost = need * unitPrice;

  const isCritical = item.urgency === "CRITICAL";
  const isHigh = item.urgency === "HIGH";

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
              {item.category} • {item.supplier || item.supplier_name || "IEK Казахстан"}
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
                  daysOfStock <= 5 ? "text-red-400" : daysOfStock <= 15 ? "text-amber-400" : "text-emerald-400"
                }`}
              >
                {daysOfStock.toFixed(1)} дн.
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" /> Расход / сут
              </span>
              <p className="mt-1 text-base font-bold text-foreground">
                {dailyDemand.toFixed(1)}{" "}
                <span className="font-mono text-xs font-normal text-muted-foreground">
                  {item.unit}/д
                </span>
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <Calendar className="h-3.5 w-3.5" /> Сезон октябрь
              </span>
              <p className="mt-1 text-base font-bold text-foreground">
                +{Math.round(((item.season_factor ?? 1.242) - 1) * 100)}%{" "}
                <span className="font-mono text-xs font-normal text-muted-foreground">
                  (×{(item.season_factor ?? 1.242).toFixed(2)})
                </span>
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card-muted p-3">
              <span className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
                <Layers className="h-3.5 w-3.5" /> Кратность IEK
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
                <h3 className="text-sm font-bold text-foreground">AI-Обоснование закупки</h3>
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
                  {analysis.is_fallback ? "Детерминированный расчет" : "OpenAI gpt-4o-mini"}
                </span>
              )}
            </div>

            {isPending ? (
              <div className="flex min-h-44 flex-col items-center justify-center gap-3 py-8 text-center">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
                <p className="text-xs text-muted-foreground">
                  Анализ остатков, путей, темпа и расчет рисков через LLM…
                </p>
              </div>
            ) : isError || !analysis ? (
              <p className="py-4 text-xs text-red-400">Не удалось загрузить AI-анализ позиции.</p>
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

          {/* Mathematical Reasoning Snapshot */}
          {item.reasoning && (
            <div className="rounded-xl border border-border bg-card-muted p-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Логика Pandas / NumPy пайплайна
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
              {formatNumber(need)}{" "}
              <span className="text-xs font-normal text-muted-foreground">{item.unit}</span>
            </p>
            <p className="text-xs text-muted-foreground">
              {formatMoney(cost)} ({formatMoney(unitPrice)}/{item.unit})
            </p>
          </div>
          <Button onClick={close}>Понятно</Button>
        </div>
      </div>
    </div>
  );
}
