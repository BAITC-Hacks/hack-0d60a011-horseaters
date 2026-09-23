"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { currentUserQueryOptions, login, logout, userKeys, SessionUserProvider } from "@/entities/user";
import { authFormSchema, type AuthFormValues } from "../model/login-schema";
import { Button, Input } from "@/shared/ui";

function LoginForm() {
  const queryClient = useQueryClient();
  const form = useForm<AuthFormValues>({ resolver: zodResolver(authFormSchema), defaultValues: { username: "", password: "" } });
  const mutation = useMutation({ mutationFn: login, onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: userKeys.me }); } });
  const submit = form.handleSubmit(async (values) => { await mutation.mutateAsync(values); });
  return <main className="grid min-h-screen place-items-center bg-background p-6"><form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-3xl border border-border bg-card p-7"><h1 className="text-2xl font-bold">StockWise</h1><p className="text-sm text-muted-foreground">Войдите в рабочую систему закупок.</p><label className="block space-y-1 text-sm">Логин<Input autoComplete="username" {...form.register("username")} /></label>{form.formState.errors.username && <p className="text-xs text-destructive">{form.formState.errors.username.message}</p>}<label className="block space-y-1 text-sm">Пароль<Input type="password" autoComplete="current-password" {...form.register("password")} /></label>{form.formState.errors.password && <p className="text-xs text-destructive">{form.formState.errors.password.message}</p>}{mutation.isError && <p role="alert" className="text-sm text-destructive">{mutation.error.message}</p>}<Button className="w-full" disabled={mutation.isPending}>{mutation.isPending ? "Входим…" : "Войти"}</Button></form></main>;
}

export function SessionGate({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const session = useQuery(currentUserQueryOptions());
  useEffect(() => {
    const reset = () => { queryClient.setQueryData(userKeys.me, undefined); void queryClient.invalidateQueries({ queryKey: userKeys.me }); };
    window.addEventListener("stockwise:unauthorized", reset);
    return () => window.removeEventListener("stockwise:unauthorized", reset);
  }, [queryClient]);
  if (session.isPending) return <main className="grid min-h-screen place-items-center text-sm text-muted-foreground">Проверяем сессию…</main>;
  if (session.isError) return <LoginForm />;
  return <RoleContext user={session.data}>{children}</RoleContext>;
}

function RoleContext({ user, children }: { user: import("@/entities/user").User; children: React.ReactNode }) { return <SessionUserProvider user={user}>{children}</SessionUserProvider>; }
export function LogoutButton() {
  const client = useQueryClient();
  const mutation = useMutation({ mutationFn: logout, onSuccess: () => { client.removeQueries({ queryKey: userKeys.me }); void client.invalidateQueries({ queryKey: userKeys.me }); } });
  return <button type="button" className="text-xs text-muted-foreground hover:text-foreground" onClick={() => mutation.mutate()}>Выйти</button>;
}
