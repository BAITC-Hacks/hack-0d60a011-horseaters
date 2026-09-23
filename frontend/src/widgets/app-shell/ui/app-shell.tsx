"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowLeftToLine, ArrowRightToLine, BarChart3, Boxes, ClipboardList, FlaskConical, Search, Settings2, Truck } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";
import { getSuggestedQuantity, inventoryQueryOptions } from "@/entities/inventory";
import { healthQueryOptions } from "@/entities/system";
import { inventoryFilterSchema } from "@/features/filter-inventory";
import { useHorizonStore } from "@/features/set-horizon";
import { ThemeToggle } from "@/features/toggle-theme";
import { formatMoney } from "@/shared/lib";

const navigation = [
  { href: "/", label: "Рекомендации", icon: ClipboardList },
  { href: "/analytics", label: "Аналитика", icon: BarChart3 },
  { href: "/orders", label: "Поставщики и заказы", icon: Truck },
  { href: "/sandbox", label: "Песочница", icon: FlaskConical },
];
const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";
const budget = 20_000_000;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [search, setSearch] = useState("");
  const days = useHorizonStore((state) => state.days);
  const setDays = useHorizonStore((state) => state.setDays);
  const { data: items = [] } = useQuery(inventoryQueryOptions());
  const { isSuccess: apiHealthy } = useQuery({ ...healthQueryOptions(), enabled: !demoMode });
  const currentTotal = items.filter((item) => item.status !== "approved").reduce((sum, item) => sum + getSuggestedQuantity(item, days) * item.unitCost, 0);
  const criticalCount = items.filter((item) => item.riskScore >= 0.8 && item.status !== "approved").length;

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = inventoryFilterSchema.safeParse({ search, status: "all", supplier: "all", category: "all" });
    if (result.success) router.push(result.data.search.trim() ? `/?q=${encodeURIComponent(result.data.search.trim())}` : "/");
  }

  return <div className="min-h-screen bg-background lg:flex">
    <aside className={`hidden shrink-0 flex-col border-r border-border bg-card px-3 py-5 transition-[width] duration-300 lg:flex ${collapsed ? "w-[78px]" : "w-[234px]"}`}>
      <div className={`flex items-center ${collapsed ? "justify-center" : "gap-3 px-2"}`}>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground"><Boxes className="h-5 w-5" /></div>
        {!collapsed && <div className="min-w-0"><div className="truncate text-sm font-extrabold tracking-tight">Электрокомплект</div><div className="text-[10px] text-muted-foreground">ekt.kz · закупки</div></div>}
      </div>
      <button type="button" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Развернуть меню" : "Свернуть меню"} className="mt-7 flex h-9 w-full items-center justify-center rounded-xl border border-border text-muted-foreground transition hover:bg-card-muted hover:text-foreground">{collapsed ? <ArrowRightToLine className="h-4 w-4" /> : <ArrowLeftToLine className="h-4 w-4" />}</button>
      {!collapsed && <p className="mb-3 mt-7 px-3 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Рабочее пространство</p>}
      <nav aria-label="Разделы" className={`space-y-1 ${collapsed ? "mt-7" : ""}`}>
        {navigation.map((entry) => {
          const active = pathname === entry.href;
          return <Link key={entry.href} href={entry.href} title={entry.label} aria-current={active ? "page" : undefined} className={`flex min-h-11 items-center rounded-xl text-sm transition ${collapsed ? "justify-center" : "gap-3 px-3"} ${active ? "bg-accent font-semibold text-accent-foreground" : "text-muted-foreground hover:bg-card-muted hover:text-foreground"}`}><entry.icon className="h-[18px] w-[18px] shrink-0" />{!collapsed && <span className="min-w-0 flex-1 truncate">{entry.label}</span>}{!collapsed && entry.href === "/" && criticalCount > 0 && <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-[10px] font-bold text-red-500">{criticalCount}</span>}</Link>;
        })}
      </nav>
      <div className="mt-auto space-y-3">
        <div className={`rounded-xl border border-border bg-card-muted ${collapsed ? "px-2 py-3" : "p-3"}`}><div className="flex items-center gap-2"><Activity className={`h-4 w-4 shrink-0 ${demoMode ? "text-amber-500" : apiHealthy ? "text-emerald-500" : "text-red-500"}`} />{!collapsed && <span className="text-xs font-semibold">{demoMode ? "Демо-данные" : apiHealthy ? "API подключён" : "API недоступен"}</span>}</div>{!collapsed && <p className="mt-1.5 text-[10px] text-muted-foreground">{demoMode ? "База и расчёт симулируются" : apiHealthy ? "Проверка /api/v1/health успешна" : "Проверьте FastAPI и БД"}</p>}</div>
        <Link href="/sandbox" title="Параметры сценария" className={`flex h-10 items-center rounded-xl text-muted-foreground hover:bg-card-muted hover:text-foreground ${collapsed ? "justify-center" : "gap-3 px-3 text-xs"}`}><Settings2 className="h-4 w-4" />{!collapsed && "Параметры сценария"}</Link>
      </div>
    </aside>

    <div className="min-w-0 flex-1">
      <header className="flex min-h-[72px] flex-wrap items-center gap-3 border-b border-border bg-card px-4 py-3 sm:px-7">
        <Link href="/" className="mr-2 flex items-center gap-2 font-bold lg:hidden"><Boxes className="h-5 w-5 text-primary" /> ekt.kz</Link>
        <form onSubmit={submitSearch} className="relative order-2 w-full sm:order-none sm:max-w-64 lg:max-w-72"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input aria-label="Поиск по номенклатуре и артикулу" value={search} onChange={(event) => setSearch(event.target.value)} maxLength={120} placeholder="Артикул или номенклатура" className="h-10 w-full rounded-full border border-border bg-input pl-9 pr-3 text-xs outline-none focus:border-ring focus:ring-1 focus:ring-ring" /></form>
        <div className="ml-auto flex items-center gap-2"><span className="hidden font-mono text-[10px] text-muted-foreground 2xl:inline">23 СЕНТЯБРЯ 2026</span><span className="hidden rounded-full border border-border bg-card-muted px-3 py-2 text-[10px] text-muted-foreground xl:inline">План {formatMoney(currentTotal)} / {formatMoney(budget)}</span><label className="sr-only" htmlFor="horizon">Горизонт расчёта</label><select id="horizon" aria-label="Горизонт расчёта" value={days} onChange={(event) => setDays(Number(event.target.value))} className="h-10 rounded-full border border-border bg-input px-3 text-xs font-medium outline-none focus:border-ring"><option value={30}>30 дней</option><option value={60}>60 дней</option><option value={90}>90 дней</option></select><ThemeToggle /><span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-violet-500 text-xs font-bold text-white" title="Менеджер закупок">ЗК</span></div>
      </header>
      <nav aria-label="Разделы на мобильном" className="flex gap-1 overflow-x-auto border-b border-border bg-card px-3 py-2 lg:hidden">{navigation.map((entry) => <Link key={entry.href} href={entry.href} aria-current={pathname === entry.href ? "page" : undefined} className={`flex shrink-0 items-center gap-1.5 rounded-full px-3 py-2 text-xs ${pathname === entry.href ? "bg-accent font-semibold text-accent-foreground" : "text-muted-foreground"}`}><entry.icon className="h-3.5 w-3.5" />{entry.label}</Link>)}</nav>
      <main className="mx-auto max-w-[1600px] px-4 py-7 sm:px-7 lg:px-9">{children}</main>
    </div>
  </div>;
}
