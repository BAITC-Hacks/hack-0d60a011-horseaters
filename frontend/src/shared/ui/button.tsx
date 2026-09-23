import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "icon";
};

export function Button({ variant = "primary", size = "md", className = "", ...props }: Props) {
  const variants = {
    primary: "bg-primary text-primary-foreground shadow-[0_10px_30px_-14px_var(--primary)] hover:brightness-110",
    secondary: "border border-border bg-card-muted text-card-foreground hover:bg-muted",
    ghost: "text-muted-foreground hover:bg-card-muted hover:text-foreground",
    danger: "bg-red-500/10 text-red-500 ring-1 ring-inset ring-red-500/20 hover:bg-red-500/15",
  };
  const sizes = {
    sm: "min-h-9 rounded-xl px-3.5 text-xs",
    md: "min-h-11 rounded-xl px-5 text-sm",
    icon: "h-10 w-10 rounded-full",
  };

  return <button {...props} className={`inline-flex items-center justify-center gap-2 font-semibold transition duration-200 disabled:cursor-not-allowed disabled:opacity-45 ${variants[variant]} ${sizes[size]} ${className}`} />;
}
