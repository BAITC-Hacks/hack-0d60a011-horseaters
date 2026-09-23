"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Check, Copy, Mail, X } from "lucide-react";
import { useState } from "react";
import type { InventoryItem } from "@/entities/inventory";
import { Button, Card } from "@/shared/ui";
import { fetchSupplierLetter } from "../api/ai-api";
import { useAiStore } from "../model/ai-store";

export function SupplierLetterModal({ items }: { items: InventoryItem[] }) {
  const isOpen = useAiStore((state) => state.isLetterModalOpen);
  const close = useAiStore((state) => state.closeLetterModal);
  const [copied, setCopied] = useState(false);

  const orderItems = items.filter((i) => (i.adjusted_need ?? i.calculated_need ?? 0) > 0);

  const {
    data: letter,
    isPending,
    isError,
  } = useQuery({
    queryKey: [
      "ai-supplier-letter",
      orderItems.map((i) => `${i.id}:${i.adjusted_need}`).join(","),
    ],
    queryFn: () => fetchSupplierLetter(orderItems),
    enabled: isOpen && orderItems.length > 0,
    staleTime: 300_000,
  });

  if (!isOpen) return null;

  function copyText() {
    if (!letter) return;
    const fullText = `Тема: ${letter.subject}\nКому: ${letter.recipient}\n\n${letter.salutation}\n\n${letter.letter_body}\n\n${letter.items_table}\n\n${letter.closing}`;
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
    >
      <Card className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-purple-500/10 text-purple-400">
              <Mail className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-card-foreground">
                  Официальное письмо в ТОО «ИЭК КАЗАХСТАН»
                </h2>
                {letter && (
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      letter.is_fallback
                        ? "border border-muted bg-card-muted text-muted-foreground"
                        : "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                    }`}
                  >
                    <Bot className="h-3 w-3" />
                    {letter.is_fallback ? "Шаблон заявки" : "OpenAI gpt-4o-mini"}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Бронирование складского запаса на октябрь 2026 ({orderItems.length} позиций)
              </p>
            </div>
          </div>
          <button
            onClick={close}
            className="rounded-xl p-2 text-muted-foreground transition hover:bg-card-muted hover:text-foreground"
            aria-label="Закрыть"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 space-y-4 overflow-y-auto p-6 text-sm">
          {orderItems.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              Нет позиций с потребностью к заказу (&gt; 0).
            </p>
          ) : isPending ? (
            <div className="flex min-h-60 flex-col items-center justify-center gap-3 text-center">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
              <p className="text-xs text-muted-foreground">
                Генерация официального письма с реквизитами и таблицей спецификации…
              </p>
            </div>
          ) : isError || !letter ? (
            <p className="py-6 text-center text-red-400">Не удалось сгенерировать письмо.</p>
          ) : (
            <div className="space-y-4 rounded-xl border border-border bg-card-muted/50 p-5 font-sans leading-relaxed">
              <div className="border-b border-border pb-3">
                <p className="text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">Тема:</span> {letter.subject}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">Кому:</span> {letter.recipient}
                </p>
              </div>

              <p className="font-semibold text-foreground">{letter.salutation}</p>

              <div className="whitespace-pre-line text-xs text-card-foreground">
                {letter.letter_body}
              </div>

              {/* Items Table */}
              <div className="overflow-x-auto rounded-lg border border-border bg-card p-3">
                <pre className="font-mono text-[11px] leading-tight text-foreground">
                  {letter.items_table}
                </pre>
              </div>

              <div className="whitespace-pre-line text-xs text-muted-foreground">
                {letter.closing}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border bg-card-muted/30 p-5">
          <p className="text-xs text-muted-foreground">
            Письмо готово для отправки официальным каналом поставщику.
          </p>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={close}>
              Закрыть
            </Button>
            <Button onClick={copyText} disabled={!letter}>
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-emerald-400" /> Скопировано!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" /> Скопировать текст
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
