import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppProvider } from "@/app/providers";
import "@/app/styles/globals.css";

export const metadata: Metadata = {
  title: "StockWise — планирование закупок",
  description: "Рекомендации к закупке, аналитика спроса и заказы поставщикам",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className="bg-background font-sans text-foreground antialiased">
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
