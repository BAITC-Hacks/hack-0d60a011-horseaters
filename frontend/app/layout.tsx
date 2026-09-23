import type { Metadata } from "next";
import type { ReactNode } from "react";
import { QueryProvider } from "@/app/providers";
import "@/app/styles/globals.css";

export const metadata: Metadata = {
  title: "Stockwise — управление запасами",
  description: "Планирование закупок и контроль складских остатков",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body className="bg-[#f7f8fa] font-sans text-[#182125] antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
