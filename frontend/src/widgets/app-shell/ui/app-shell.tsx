"use client";

import { Boxes, ChevronDown, ClipboardList, LayoutDashboard, PackageSearch, Settings2, Warehouse } from "lucide-react";
import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-[246px] shrink-0 flex-col border-r border-[#e8edee] bg-white lg:flex">
        <div className="flex h-[78px] items-center gap-3 border-b border-[#edf0f1] px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#17835b] text-white"><Boxes className="h-5 w-5" strokeWidth={2.1} /></div>
          <div><div className="text-lg font-extrabold tracking-tight text-[#1b3028]">stockwise<span className="text-[#1b986b]">.</span></div><div className="-mt-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9aa7a5]">Умный склад</div></div>
        </div>
        <div className="px-4 pt-8">
          <p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-[#a1adaf]">Рабочая область</p>
          <nav aria-label="Навигация" className="mt-4 space-y-1">
            <a href="#overview" className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-[#75858a] transition hover:bg-[#f3f7f5] hover:text-[#17835b]"><LayoutDashboard className="h-[18px] w-[18px]" /> Обзор</a>
            <a href="#inventory" aria-current="page" className="flex items-center gap-3 rounded-xl bg-[#e9f5ef] px-3 py-3 text-sm font-semibold text-[#168159]"><Warehouse className="h-[18px] w-[18px]" /> Запасы</a>
            <a href="#order-summary" className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-[#75858a] transition hover:bg-[#f3f7f5] hover:text-[#17835b]"><ClipboardList className="h-[18px] w-[18px]" /> План закупок</a>
          </nav>
        </div>
        <div className="mx-4 mt-auto mb-5 rounded-2xl bg-[#f3f8f5] p-4">
          <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-white text-[#18845b]"><PackageSearch className="h-5 w-5" /></div>
          <p className="text-sm font-bold text-[#283d36]">Закупки под контролем</p>
          <p className="mt-1.5 text-xs leading-5 text-[#81918b]">Рекомендации учитывают спрос, срок поставки и страховой запас.</p>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex h-[78px] items-center justify-between border-b border-[#e8edee] bg-white px-5 sm:px-8 lg:px-10">
          <div className="flex items-center gap-3 text-sm text-[#819094]"><span className="lg:hidden flex h-8 w-8 items-center justify-center rounded-lg bg-[#17835b] text-white"><Boxes className="h-4 w-4" /></span><span className="hidden sm:inline">Рабочая область</span><span className="hidden sm:inline text-[#c4ccce]">/</span><span className="font-semibold text-[#31413e]">Управление запасами</span></div>
          <div className="flex items-center gap-3 sm:gap-5"><div className="hidden items-center gap-2 rounded-lg bg-[#f1f7f3] px-3 py-1.5 text-xs font-semibold text-[#27805a] sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-[#28a36d]" />{process.env.NEXT_PUBLIC_DEMO_MODE === "false" ? "Подключено к API" : "Демо-режим"}</div><Settings2 className="h-[18px] w-[18px] text-[#8b999d]" /><div className="flex items-center gap-2 border-l border-[#e6ecec] pl-3 sm:pl-5"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#e5eee9] text-xs font-bold text-[#39765b]">СК</div><ChevronDown className="hidden h-4 w-4 text-[#9ba9aa] sm:block" /></div></div>
        </header>
        <main className="mx-auto max-w-[1530px] px-5 py-7 sm:px-8 lg:px-10 lg:py-9">{children}</main>
      </div>
    </div>
  );
}
