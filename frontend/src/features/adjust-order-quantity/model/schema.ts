import { z } from "zod";

export const orderQuantitySchema = z.number().int().min(0).max(1_000_000);
