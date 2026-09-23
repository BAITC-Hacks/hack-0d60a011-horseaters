"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { orderQueryOptions } from "@/entities/order";
import { ApproveOrderButton } from "@/features/approve-order";
import { ExportMenu } from "@/features/export-order";
import { Button, Card, ErrorMessage, Input, Skeleton } from "@/shared/ui";
import { AppShell } from "@/widgets/app-shell";

const lookupSchema = z.object({ orderId: z.uuid() });
type Lookup = z.infer<typeof lookupSchema>;

export function OrdersPage() {
  const [orderId, setOrderId] = useState<string | null>(null);
  const form = useForm<Lookup>({ resolver: zodResolver(lookupSchema), defaultValues: { orderId: "" } });
  const query = useQuery({ ...orderQueryOptions(orderId ?? ""), enabled: orderId !== null });
  const order = query.data;

  return <AppShell><header className="mb-6"><h1 className="text-3xl font-bold">Заказы поставщикам</h1><p className="mt-2 text-sm text-muted-foreground">Укажите ID созданного заказа для просмотра, утверждения и скачивания экспорта.</p></header>
    <Card className="p-5"><form onSubmit={form.handleSubmit(({ orderId: value }) => setOrderId(value))} className="flex flex-wrap items-end gap-3"><label className="min-w-64 flex-1 text-sm">ID заказа<Input className="mt-2" {...form.register("orderId")} placeholder="UUID заказа" /></label><Button type="submit">Найти</Button></form>{form.formState.errors.orderId && <p role="alert" className="mt-2 text-xs text-red-500">Введите UUID заказа.</p>}</Card>
    {orderId && <div className="mt-5">{query.isPending ? <Skeleton className="h-56" /> : query.isError ? <ErrorMessage title="Не удалось загрузить заказ" error={query.error} onRetry={() => void query.refetch()} /> : order && <Card className="space-y-4 p-5"><div><h2 className="text-xl font-semibold">{order.order_number}</h2><p className="mt-1 text-xs text-muted-foreground">Статус: {order.status} · ID: {order.id} · Поставщик: {order.supplier_id}</p></div><div className="space-y-2">{order.items.map((item) => <div key={item.id} className="flex flex-wrap justify-between gap-2 rounded-xl bg-card-muted p-3 text-xs"><span className="font-mono">Товар: {item.product_id}</span><span>Количество: {item.approved_quantity}</span></div>)}</div>{order.status === "draft" && <ApproveOrderButton orderId={order.id} />}{(order.status === "approved" || order.status === "exported") && <ExportMenu order={order} />}</Card>}</div>}
    <p className="mt-5 text-sm text-muted-foreground">Общий список заказов пока отсутствует в API 0.1.0. ID заказа отображается после создания на странице рекомендаций.</p>
  </AppShell>;
}
