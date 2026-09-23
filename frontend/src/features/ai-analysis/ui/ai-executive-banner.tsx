"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  FileText,
  Mail,
  PieChart,
  Sparkles,
  X,
} from "lucide-react";
import type { InventoryItem } from "@/entities/inventory";
import { formatMoney } from "@/shared/lib";
import { Button, Card } from "@/shared/ui";
import { fetchSupplierSummary } from "../api/ai-api";
import { useAiStore } from "../model/ai-store";

export function AiExecutiveBanner({ items }: { items: InventoryItem[] }) {
  const openLetter = useAiStore((state) => state.openLetterModal);
  const isExecOpen = useAiStore((state) => state.isExecutiveModalOpen);
  const openExec = useAiStore((state) => state.openExecutiveModal);
  const closeExec = useAiStore((state) => state.closeExecutiveModal);

  const critical = items.filter((i) => i.urgency === "CRITICAL");
  const totalBudget = items.reduce(
    (sum, i) => sum + (i.adjusted_need ?? i.calculated_need ?? 0) * (i.unitCost ?? 0),
    0
  );

  const { data: summary, isPending } = useQuery({
    queryKey: [
      "ai-supplier-summary",
      items.map((i) => `${i.id}:${i.adjusted_need}`).join(","),
    ],
    queryFn: () => fetchSupplierSummary(items),
    enabled: items.length > 0,
    staleTime: 300_000,
  });

  return (
    <>
      {/* Bento AI Banner */}
      <div className="mb-6 overflow-hidden rounded-3xl border border-blue-500/30 bg-gradient-to-r from-blue-950/40 via-card to-purple-950/30 p-5 shadow-lg">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-500/20 text-blue-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-blue-400">
                  AI-Ассистент снабжения • IEK Казахстан
                </span>
                <span className="inline-flex items-center gap-1 rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[9px] font-bold text-blue-300">
                  <Bot className="h-2.5 w-2.5" />
                  gpt-4o-mini
                </span>
              </div>
              <h3 className="mt-1 text-base font-bold text-foreground sm:text-lg">
                Внимание: в октябре сезонный пик спроса (+24%). Выявлено {critical.length}{" "}
                критических позиции.
              </h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Бюджет планового заказа:{" "}
                <span className="font-semibold text-foreground">{formatMoney(totalBudget)}</span>.
                Склад обнулится по дефицитным позициям через 1–3 дня при плече доставки 14 дней.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={openExec} className="text-xs">
              <FileText className="h-3.5 w-3.5" />
              Executive-сводка
            </Button>
            <Button onClick={openLetter} className="text-xs">
              <Mail className="h-3.5 w-3.5" />
              Письмо вендору (IEK)
            </Button>
          </div>
        </div>
      </div>

      {/* Executive Summary Modal */}
      {isExecOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
        >
          <Card className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between border-b border-border p-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-400">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-card-foreground">
                      Executive-сводка по закупке IEK
                    </h2>
                    {summary && (
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          summary.is_fallback
                            ? "border border-muted bg-card-muted text-muted-foreground"
                            : "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        }`}
                      >
                        <Bot className="h-3 w-3" />
                        {summary.is_fallback ? "Детерминированный срез" : "OpenAI gpt-4o-mini"}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Планирование на октябрь 2026 (горизонт 44 дня, сезонный индекс 1.242)
                  </p>
                </div>
              </div>
              <button
                onClick={closeExec}
                className="rounded-xl p-2 text-muted-foreground transition hover:bg-card-muted hover:text-foreground"
                aria-label="Закрыть"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 space-y-6 overflow-y-auto p-6 text-sm">
              {isPending ? (
                <div className="flex min-h-60 flex-col items-center justify-center gap-3 text-center">
                  <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
                  <p className="text-xs text-muted-foreground">
                    Формирование сводного управленческого отчета…
                  </p>
                </div>
              ) : summary ? (
                <>
                  <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-4">
                    <h4 className="font-bold uppercase tracking-wider text-blue-400">
                      Управленческое резюме
                    </h4>
                    <p className="mt-1.5 text-xs leading-relaxed text-blue-100">
                      {summary.executive_summary}
                    </p>
                  </div>

                  <div>
                    <h4 className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-card-foreground">
                      <PieChart className="h-4 w-4 text-purple-400" />
                      Анализ бюджета и структуры затрат
                    </h4>
                    <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                      {summary.budget_analysis}
                    </p>
                  </div>

                  <div>
                    <h4 className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-red-400">
                      <AlertTriangle className="h-4 w-4 text-red-400" />
                      Критические риски
                    </h4>
                    <ul className="mt-2 space-y-2 text-xs text-muted-foreground">
                      {summary.critical_risks.map((risk, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />
                          <span>{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-emerald-400">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      Ключевые управленческие решения
                    </h4>
                    <ul className="mt-2 space-y-2 text-xs text-muted-foreground">
                      {summary.key_recommendations.map((rec, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                          <span className="font-medium text-foreground">{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              ) : null}
            </div>

            <div className="flex items-center justify-between border-t border-border bg-card-muted/30 p-5">
              <Button
                variant="secondary"
                onClick={() => {
                  closeExec();
                  openLetter();
                }}
              >
                <Mail className="h-4 w-4" /> Перейти к формированию письма
              </Button>
              <Button onClick={closeExec}>Закрыть</Button>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
