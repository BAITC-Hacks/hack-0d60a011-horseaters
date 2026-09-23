"use client";

import { RunCalculationAction } from "@/features/run-calculation";
import { useHorizonStore } from "@/features/set-horizon";
import { Card } from "@/shared/ui";
import { AppShell } from "@/widgets/app-shell";

export function SandboxPage() {
  const horizonDays = useHorizonStore((state) => state.days);
  return <AppShell><header className="mb-6"><h1 className="text-3xl font-bold">Параметры расчёта</h1><p className="mt-2 text-sm text-muted-foreground">Запустите серверный расчёт для выбранного горизонта.</p></header><Card className="p-6"><p className="mb-4 text-sm">Горизонт: {horizonDays} дней</p><RunCalculationAction horizonDays={horizonDays} /><p className="mt-4 text-sm text-muted-foreground">Ограничение по бюджету пока не поддерживается POST /api/calculation-runs; локальные результаты симуляции не показываются.</p></Card></AppShell>;
}
