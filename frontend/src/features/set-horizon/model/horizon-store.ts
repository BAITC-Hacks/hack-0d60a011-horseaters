import { create } from "zustand";
import { z } from "zod";

export const horizonSchema = z.union([z.literal(30), z.literal(60), z.literal(90)]);
export type HorizonDays = z.infer<typeof horizonSchema>;

type HorizonState = { days: HorizonDays; setDays: (value: number) => void };

export const useHorizonStore = create<HorizonState>((set) => ({
  days: 30,
  setDays: (value) => {
    const result = horizonSchema.safeParse(value);
    if (result.success) set({ days: result.data });
  },
}));
