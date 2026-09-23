import { z } from "zod";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function getApiBaseUrl(): string {
  const raw = typeof window === "undefined"
    ? process.env.INTERNAL_API_URL ?? process.env.SERVER_API_URL ?? process.env.NEXT_PUBLIC_API_URL
    : process.env.NEXT_PUBLIC_API_URL;
  if (!raw) throw new ApiError(0, "Адрес FastAPI не задан. Укажите INTERNAL_API_URL или NEXT_PUBLIC_API_URL.");
  return raw.replace(/\/$/, "");
}

export async function apiRequest<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  const baseUrl = getApiBaseUrl();
  const normalizedPath = baseUrl.endsWith("/api/v1") && path.startsWith("/api/v1")
    ? path.slice("/api/v1".length)
    : path;
  const url = `${baseUrl}${normalizedPath.startsWith("/") ? "" : "/"}${normalizedPath}`;

  try {
    response = await fetch(url, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "Не удалось подключиться к серверу. Проверьте адрес API и сеть.");
  }

  if (!response.ok) {
    let detail = `Ошибка сервера (${response.status})`;
    try {
      const body: unknown = await response.json();
      if (typeof body === "object" && body !== null && "detail" in body) {
        const value = body.detail;
        if (typeof value === "string") detail = value;
      }
    } catch { /* A non-JSON error response keeps the status message. */ }
    throw new ApiError(response.status, detail);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(response.status, "Сервер вернул некорректный JSON.");
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw new ApiError(response.status, "Ответ сервера не соответствует контракту данных.");
  return parsed.data;
}
