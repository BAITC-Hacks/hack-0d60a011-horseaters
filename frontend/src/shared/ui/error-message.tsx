import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "./button";

export function ErrorMessage({ title = "Не удалось загрузить данные", error, onRetry }: { title?: string; error: unknown; onRetry?: () => void }) {
  return <div role="alert" className="rounded-2xl border border-red-500/25 bg-red-500/10 p-5 text-sm">
    <div className="flex items-start gap-3"><AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" /><div><p className="font-semibold text-red-600 dark:text-red-400">{title}</p><p className="mt-1 text-muted-foreground">{error instanceof Error ? error.message : "Неизвестная ошибка запроса."}</p></div></div>
    {onRetry && <Button type="button" variant="secondary" className="mt-4" onClick={onRetry}><RefreshCw className="h-4 w-4" />Повторить</Button>}
  </div>;
}
