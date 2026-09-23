import type { ReactNode } from "react";

const tones = {
  green: "bg-[#e9f7ee] text-[#287c4e]",
  amber: "bg-[#fff3dc] text-[#a66b0e]",
  red: "bg-[#fcebea] text-[#b94843]",
  gray: "bg-[#eef1f2] text-[#687579]",
} as const;

export function Badge({ children, tone = "gray" }: { children: ReactNode; tone?: keyof typeof tones }) {
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${tones[tone]}`}>{children}</span>;
}
