"use client";

import type { RunRecommendation } from "@/entities/calculation-run";
import { AdjustRecommendationAction } from "@/features/adjust-recommendation";
import { formatNumber } from "@/shared/lib";
import { Badge, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui";

export function RunRecommendationsTable({ items }: { items: RunRecommendation[] }) {
  return <div className="overflow-x-auto"><Table className="min-w-[900px]"><TableHeader><tr><TableHead>Товар ID</TableHead><TableHead>Поставщик ID</TableHead><TableHead>Остаток</TableHead><TableHead>Дефицит</TableHead><TableHead>Рекомендовано</TableHead><TableHead>К заказу</TableHead><TableHead>Статус</TableHead><TableHead>Правка</TableHead></tr></TableHeader><TableBody>{items.map((item) => <TableRow key={item.id}>
    <TableCell className="max-w-40 truncate font-mono text-xs" title={item.product_id}>{item.product_id}</TableCell>
    <TableCell className="max-w-40 truncate font-mono text-xs" title={item.supplier_id}>{item.supplier_id}</TableCell>
    <TableCell>{formatNumber(item.current_stock)}</TableCell>
    <TableCell>{formatNumber(item.shortage_quantity)}</TableCell>
    <TableCell>{formatNumber(item.recommended_quantity)}</TableCell>
    <TableCell className="font-semibold">{formatNumber(item.effective_quantity)}</TableCell>
    <TableCell><Badge tone={item.urgency === "critical" ? "red" : item.urgency === "high" ? "amber" : "blue"}>{item.status} · {item.urgency}</Badge></TableCell>
    <TableCell><AdjustRecommendationAction recommendation={item} /></TableCell>
  </TableRow>)}</TableBody></Table>{items.length === 0 && <p className="p-6 text-sm text-muted-foreground">Расчёт завершён без рекомендаций.</p>}</div>;
}
