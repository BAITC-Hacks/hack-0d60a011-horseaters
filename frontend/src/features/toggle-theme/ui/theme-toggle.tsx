"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/shared/ui";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme !== "light";

  return (
    <Button type="button" variant="secondary" size="icon" aria-label={isDark ? "Включить светлую тему" : "Включить тёмную тему"} title={isDark ? "Светлая тема" : "Тёмная тема"} onClick={() => setTheme(isDark ? "light" : "dark")} suppressHydrationWarning className="group relative overflow-hidden">
      <Sun className={`absolute h-4 w-4 transition-all duration-300 ${isDark ? "-rotate-90 scale-0" : "rotate-0 scale-100"}`} />
      <Moon className={`absolute h-4 w-4 transition-all duration-300 ${isDark ? "rotate-0 scale-100" : "rotate-90 scale-0"}`} />
    </Button>
  );
}
