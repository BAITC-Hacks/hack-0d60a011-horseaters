import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE = "stockwise_access_token";

function apiOrigin(): string {
  const configured = process.env.INTERNAL_API_URL ?? process.env.SERVER_API_URL ?? "http://localhost:8000";
  const url = new URL(configured);
  url.pathname = url.pathname.replace(/\/(?:api\/v1|api)\/?$/, "").replace(/\/$/, "");
  return url.toString().replace(/\/$/, "");
}

async function proxy(request: NextRequest, context: { params: Promise<{ segments: string[] }> }) {
  const { segments } = await context.params;
  const path = segments.map(encodeURIComponent).join("/");
  const backendUrl = new URL(`/api/${path}${request.nextUrl.search}`, apiOrigin());
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("cookie");
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (token && !(segments[0] === "auth" && segments[1] === "login")) headers.set("Authorization", `Bearer ${token}`);

  if (segments[0] === "auth" && segments[1] === "logout") {
    const response = NextResponse.json({ success: true });
    response.cookies.set(SESSION_COOKIE, "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 0 });
    return response;
  }

  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();
  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, { method: request.method, headers, body, cache: "no-store", redirect: "manual" });
  } catch {
    return NextResponse.json({ detail: { code: "backend_unavailable", message: "Сервис API временно недоступен." } }, { status: 502 });
  }

  const outgoingHeaders = new Headers();
  for (const name of ["content-type", "content-disposition", "x-request-id", "cache-control", "etag"]) {
    const value = upstream.headers.get(name);
    if (value) outgoingHeaders.set(name, value);
  }
  let response = new NextResponse(upstream.body, { status: upstream.status, headers: outgoingHeaders });
  if (upstream.status === 401) {
    response.cookies.set(SESSION_COOKIE, "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 0 });
  }

  if (segments[0] === "auth" && segments[1] === "login" && request.method === "POST" && upstream.ok) {
    const payload: unknown = await upstream.clone().json().catch(() => null);
    if (!payload || typeof payload !== "object" || !("access_token" in payload) || typeof payload.access_token !== "string") {
      return NextResponse.json({ detail: { code: "invalid_auth_response", message: "Сервер авторизации вернул неверный ответ." } }, { status: 502 });
    }
    const token = payload.access_token;
    const expires = "expires_in" in payload && typeof payload.expires_in === "number" ? payload.expires_in : 3600;
    response = NextResponse.json({ token_type: "bearer", expires_in: expires }, { status: upstream.status, headers: outgoingHeaders });
    response.cookies.set(SESSION_COOKIE, token, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: Math.max(1, expires) });
  }
  return response;
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
