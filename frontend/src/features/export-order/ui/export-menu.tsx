"use client";

import { Download, FileCode2, FileSpreadsheet } from "lucide-react";
import { useState } from "react";
import type { InventoryItem } from "@/entities/inventory";
import { Button } from "@/shared/ui";
import { exportApprovedOrder, type ExportFormat } from "../lib/export-1c";

export function ExportMenu({ items }: { items: InventoryItem[] }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const approvedCount = items.filter((item) => item.status === "approved" && (item.approvedQuantity ?? 0) > 0).length;

  async function run(format: ExportFormat) {
    setBusy(true);
    setMessage("");
    try { const count = await exportApprovedOrder(items, format); setMessage(`Выгружено ${count} позиций.`); setOpen(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Не удалось сформировать файл."); }
    finally { setBusy(false); }
  }

  return <div className="relative"><Button variant="secondary" onClick={() => setOpen((value) => !value)} disabled={approvedCount === 0 || busy} aria-expanded={open}><Download className="h-4 w-4" />Экспорт в 1С ({approvedCount})</Button>{open && <div className="absolute right-0 top-12 z-30 w-64 rounded-2xl border border-border bg-card p-2 shadow-2xl"><button onClick={() => void run("xlsx")} className="flex w-full items-center gap-2 rounded-xl px-3 py-3 text-left text-xs hover:bg-card-muted"><FileSpreadsheet className="h-4 w-4 text-emerald-500" />Заказ поставщику (.xlsx)</button><button onClick={() => void run("xml")} className="flex w-full items-center gap-2 rounded-xl px-3 py-3 text-left text-xs hover:bg-card-muted"><FileCode2 className="h-4 w-4 text-blue-500" />XML-пакет обмена</button></div>}{message && <p role="status" className="absolute right-0 top-12 z-20 w-60 rounded-xl border border-border bg-card p-2 text-xs text-muted-foreground shadow-lg">{message}</p>}</div>;
}
