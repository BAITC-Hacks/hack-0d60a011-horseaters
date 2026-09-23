import type { HTMLAttributes, TableHTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";

export function Table({ className = "", ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return <table {...props} className={`w-full border-collapse text-left ${className}`} />;
}

export function TableHeader({ className = "", ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} className={`bg-card-muted text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground ${className}`} />;
}

export function TableBody({ className = "", ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} className={`divide-y divide-border ${className}`} />;
}

export function TableRow({ className = "", ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr {...props} className={`transition-colors hover:bg-card-muted/70 ${className}`} />;
}

export function TableHead({ className = "", ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th {...props} className={`h-11 font-bold ${className}`} />;
}

export function TableCell({ className = "", ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td {...props} className={`py-4 ${className}`} />;
}
