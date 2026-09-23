import type { ReactNode } from "react";

const tones = {
  green: "border-emerald-500/20 bg-emerald-500/10 text-emerald-500 dark:text-emerald-400",
  amber: "border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  red: "border-red-500/20 bg-red-500/10 text-red-500 dark:text-red-400",
  blue: "border-blue-500/20 bg-blue-500/10 text-blue-600 dark:text-blue-400",
  purple: "border-purple-500/20 bg-purple-500/10 text-purple-600 dark:text-purple-400",
  gray: "border-border bg-card-muted text-muted-foreground",
} as const;

export function Badge({ children, tone = "gray" }: { children: ReactNode; tone?: keyof typeof tones }) {
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.08em] ${tones[tone]}`}>{children}</span>;
}
