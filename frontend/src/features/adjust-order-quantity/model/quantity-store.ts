import { create } from "zustand";
import { orderQuantitySchema } from "./schema";

type QuantityState = {
  quantityById: Record<string, number>;
  setQuantity: (id: string, quantity: number) => boolean;
  clearQuantity: (id: string) => void;
};

export const useOrderQuantityStore = create<QuantityState>((set) => ({
  quantityById: {},
  setQuantity: (id, quantity) => {
    const parsed = orderQuantitySchema.safeParse(quantity);
    if (!parsed.success) return false;
    set((state) => ({ quantityById: { ...state.quantityById, [id]: parsed.data } }));
    return true;
  },
  clearQuantity: (id) => set((state) => {
    const next = { ...state.quantityById };
    delete next[id];
    return { quantityById: next };
  }),
}));
