"use client";

import { useQuery } from "@tanstack/react-query";
import { inventoryQueryOptions } from "@/entities/inventory";
import { AppShell } from "@/widgets/app-shell";
import { SupplierOrders } from "@/widgets/supplier-orders";

export function OrdersPage() {
  const { data = [], isError, error } = useQuery(inventoryQueryOptions());
  return <AppShell><header className="mb-6"><p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Группировка и согласование</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Заказы по поставщикам</h1><p className="mt-2 text-sm text-muted-foreground">Контролируйте минималку, утверждайте позиции и готовьте документы для поставщика.</p></header>{isError ? <p role="alert" className="rounded-xl bg-red-500/10 p-4 text-sm text-red-500">{error instanceof Error ? error.message : "Не удалось загрузить заказы."}</p> : <SupplierOrders items={data} />}</AppShell>;
}
