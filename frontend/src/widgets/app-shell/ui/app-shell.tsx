"use client";

import { Bell, Boxes, ChevronDown, ClipboardList, LayoutDashboard, PackageSearch, Search, Settings2, Warehouse } from "lucide-react";
import type { ReactNode } from "react";
import { ThemeToggle } from "@/features/toggle-theme";

const navItems = [
  { href: "#overview", label: "Обзор", icon: LayoutDashboard },
  { href: "#inventory", label: "Запасы", icon: Warehouse, active: true },
  { href: "#order-summary", label: "План закупок", icon: ClipboardList },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background lg:flex lg:p-5">
      <aside className="hidden w-[88px] shrink-0 flex-col items-center rounded-l-3xl border border-r-0 border-border bg-card py-5 lg:flex">
        <a href="#overview" aria-label="Stockwise" className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-[0_12px_30px_-12px_var(--primary)]">
          <Boxes className="h-5 w-5" strokeWidth={2.1} />
        </a>
        <nav aria-label="Навигация" className="mt-12 flex flex-col gap-3">
          {navItems.map((item) => <a key={item.href} href={item.href} aria-label={item.label} aria-current={item.active ? "page" : undefined} title={item.label} className={`flex h-11 w-11 items-center justify-center rounded-xl border transition ${item.active ? "border-border bg-foreground text-background shadow-lg" : "border-transparent text-muted-foreground hover:border-border hover:bg-card-muted hover:text-foreground"}`}><item.icon className="h-[18px] w-[18px]" /></a>)}
        </nav>
        <div className="mt-auto flex flex-col gap-3">
          <button aria-label="Помощь по закупкам" title="Помощь по закупкам" className="flex h-11 w-11 items-center justify-center rounded-xl text-muted-foreground transition hover:bg-card-muted hover:text-foreground"><PackageSearch className="h-[18px] w-[18px]" /></button>
          <button aria-label="Настройки" title="Настройки" className="flex h-11 w-11 items-center justify-center rounded-xl text-muted-foreground transition hover:bg-card-muted hover:text-foreground"><Settings2 className="h-[18px] w-[18px]" /></button>
        </div>
      </aside>

      <div className="min-w-0 flex-1 overflow-hidden border-border bg-background lg:rounded-r-3xl lg:border">
        <header className="flex min-h-[76px] items-center justify-between gap-4 border-b border-border bg-card/80 px-4 backdrop-blur-xl sm:px-7">
          <div className="relative hidden w-full max-w-xs md:block">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <button onClick={() => { document.querySelector("#inventory")?.scrollIntoView({ behavior: "smooth" }); window.setTimeout(() => (document.querySelector('[aria-label="Поиск по товарам"]') as HTMLInputElement | null)?.focus(), 350); }} className="h-10 w-full rounded-full border border-border bg-input pl-10 pr-4 text-left text-sm text-muted-foreground transition hover:border-ring hover:text-foreground">Поиск по системе</button>
          </div>
          <div className="flex items-center gap-3 lg:hidden"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground"><Boxes className="h-4 w-4" /></span><span className="font-bold tracking-tight">stockwise.</span></div>
          <time dateTime="2026-09-23" className="hidden font-mono text-xs text-muted-foreground xl:block">СР, 23 СЕНТЯБРЯ 2026</time>
          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <button className="hidden h-10 items-center gap-2 rounded-full border border-border bg-card-muted px-4 text-xs font-semibold text-foreground transition hover:bg-muted sm:flex">Этот месяц <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /></button>
            <ThemeToggle />
            <button aria-label="Уведомления" className="relative flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card-muted text-muted-foreground transition hover:bg-muted hover:text-foreground"><Bell className="h-4 w-4" /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-orange-400" /></button>
            <button className="flex items-center gap-2 rounded-full pl-1 pr-1 sm:pr-2"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 via-violet-400 to-orange-300 text-xs font-extrabold text-white">СК</span><span className="hidden text-left sm:block"><span className="block text-xs font-semibold text-foreground">София К.</span><span className="block text-[10px] text-muted-foreground">Закупщик</span></span></button>
          </div>
        </header>
        <main className="mx-auto max-w-[1600px] px-4 py-7 sm:px-7 lg:px-8 lg:py-9">{children}</main>
      </div>
    </div>
  );
}
