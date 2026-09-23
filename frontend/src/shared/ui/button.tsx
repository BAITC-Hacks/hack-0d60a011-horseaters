import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" };

export function Button({ variant = "primary", className = "", ...props }: Props) {
  const variants = {
    primary: "bg-[#17835b] text-white hover:bg-[#126b49] disabled:bg-[#a6c6b8]",
    secondary: "border border-[#d9e1e3] bg-white text-[#243136] hover:bg-[#f5f8f7]",
    ghost: "text-[#5e6e73] hover:bg-[#edf2f0]",
  };
  return <button {...props} className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition disabled:cursor-not-allowed ${variants[variant]} ${className}`} />;
}
