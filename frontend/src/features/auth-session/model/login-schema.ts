import { loginInputSchema } from "@/entities/user";
export const authFormSchema = loginInputSchema;
export type AuthFormValues = { username: string; password: string };
