import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`rounded-2xl border border-border bg-card text-card-foreground shadow-[0_20px_60px_-38px_rgba(0,0,0,0.45)] ${className}`} />;
}
