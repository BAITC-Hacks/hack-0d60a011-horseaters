"use client";

import { useState } from "react";
import type { InventoryItem } from "@/entities/inventory";
import { Card } from "@/shared/ui";

type Group = "AX" | "AY" | "AZ" | "BX" | "BY" | "BZ" | "CX" | "CY" | "CZ";
const groups: Group[] = ["AX", "AY", "AZ", "BX", "BY", "BZ", "CX", "CY", "CZ"];
const tones: Record<Group, string> = {
  AX: "bg-emerald-500/20 text-emerald-500", AY: "bg-emerald-500/15 text-emerald-500", AZ: "bg-amber-500/15 text-amber-500",
  BX: "bg-blue-500/20 text-blue-500", BY: "bg-blue-500/15 text-blue-500", BZ: "bg-orange-500/15 text-orange-500",
  CX: "bg-violet-500/20 text-violet-500", CY: "bg-violet-500/15 text-violet-500", CZ: "bg-red-500/15 text-red-500",
};

function classify(items: InventoryItem[]): Map<string, Group> {
  const sorted = [...items].sort((a, b) => b.demand30 * b.unitCost - a.demand30 * a.unitCost);
  const total = sorted.reduce((sum, item) => sum + item.demand30 * item.unitCost, 0);
  let cumulative = 0;
  const result = new Map<string, Group>();
  for (const item of sorted) {
    const share = total === 0 ? 0 : cumulative / total;
    const abc = share < 0.8 ? "A" : share < 0.95 ? "B" : "C";
    const xyz = item.anomalyCount === 0 && item.riskScore < 0.5 ? "X" : item.anomalyCount <= 1 ? "Y" : "Z";
    result.set(item.id, `${abc}${xyz}` as Group);
    cumulative += item.demand30 * item.unitCost;
  }
  return result;
}

export function AbcXyzMatrix({ items }: { items: InventoryItem[] }) {
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const classified = classify(items);
  const selected = selectedGroup ?? groups.find((group) => items.some((item) => classified.get(item.id) === group)) ?? "AX";
  const matches = items.filter((item) => classified.get(item.id) === selected);
  return <Card className="p-5 sm:p-6"><p className="font-mono text-[10px] uppercase tracking-[0.14em] text-violet-500">Классификация каталога</p><h2 className="mt-2 text-lg font-bold">ABC / XYZ матрица</h2><p className="mt-1 text-xs text-muted-foreground">ABC по доле в спросе × цене; XYZ — демо-оценка стабильности по выбросам и риску.</p><div className="mt-5 grid grid-cols-3 gap-2">{groups.map((group) => <button key={group} onClick={() => setSelectedGroup(group)} aria-pressed={selected === group} className={`h-20 rounded-xl border text-left transition ${selected === group ? "border-primary ring-1 ring-primary" : "border-transparent hover:border-border"} ${tones[group]} px-4`}><strong className="text-lg">{group}</strong><span className="mt-1 block text-xs">{items.filter((item) => classified.get(item.id) === group).length} позиций</span></button>)}</div><div className="mt-5 border-t border-border pt-4"><p className="text-xs font-semibold">Группа {selected}</p>{matches.length === 0 ? <p className="mt-2 text-xs text-muted-foreground">Позиции этой группы отсутствуют в демо-наборе.</p> : <ul className="mt-2 space-y-2">{matches.slice(0, 4).map((item) => <li key={item.id} className="flex justify-between gap-3 text-xs"><span className="truncate">{item.name}</span><span className="font-mono text-muted-foreground">{item.sku}</span></li>)}</ul>}</div></Card>;
}
