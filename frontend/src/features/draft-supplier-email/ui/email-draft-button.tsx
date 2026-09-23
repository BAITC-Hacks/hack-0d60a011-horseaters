"use client";

import { Copy, Mail, X } from "lucide-react";
import { useState } from "react";
import type { InventoryItem } from "@/entities/inventory";
import { Button } from "@/shared/ui";

function makeDraft(items: InventoryItem[]) {
  const supplier = items[0]?.supplier ?? "поставщик";
  const lines = items.map((item) => `• ${item.sku} — ${item.name}: ${item.approvedQuantity} ${item.unit}`).join("\n");
  return `Тема: Заявка на поставку — ТОО «Электрокомплект»\n\nДобрый день, команда ${supplier}!\n\nПросим подтвердить возможность поставки следующих позиций:\n${lines}\n\nСообщите, пожалуйста, доступность товара, срок отгрузки и итоговые условия.\n\nС уважением,\nОтдел закупок ТОО «Электрокомплект»`;
}

export function EmailDraftButton({ items }: { items: InventoryItem[] }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const approved = items.filter((item) => item.status === "approved" && (item.approvedQuantity ?? 0) > 0);
  const draft = makeDraft(approved);

  async function copy() {
    try { await navigator.clipboard.writeText(draft); setCopied(true); setError(""); }
    catch { setError("Не удалось скопировать текст. Выделите его вручную."); }
  }

  return <><Button variant="secondary" onClick={() => setOpen(true)} disabled={approved.length === 0}><Mail className="h-4 w-4" />Черновик письма</Button>{open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"><div role="dialog" aria-modal="true" aria-labelledby="email-title" className="w-full max-w-xl rounded-3xl border border-border bg-card p-6 shadow-2xl"><div className="flex items-center justify-between"><div><h2 id="email-title" className="text-lg font-bold">Черновик письма поставщику</h2><p className="mt-1 text-xs text-muted-foreground">Шаблон по утверждённым позициям. Проверьте условия перед отправкой.</p></div><button onClick={() => setOpen(false)} aria-label="Закрыть" className="rounded-xl p-2 text-muted-foreground hover:bg-card-muted"><X className="h-4 w-4" /></button></div><textarea aria-label="Текст письма" readOnly value={draft} className="mt-5 h-64 w-full resize-none rounded-xl border border-border bg-input p-4 text-sm leading-6 outline-none" /><div className="mt-4 flex items-center justify-between gap-3"><p role="status" className={`text-xs ${error ? "text-red-500" : "text-emerald-500"}`}>{error || (copied ? "Текст скопирован." : "")}</p><Button onClick={() => void copy()}><Copy className="h-4 w-4" />Скопировать</Button></div></div></div>}</>;
}
