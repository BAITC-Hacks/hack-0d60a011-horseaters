import { create } from "zustand";

type ExplainState = { selectedId: string | null; open: (id: string) => void; close: () => void };

export const useExplainStore = create<ExplainState>((set) => ({
  selectedId: null,
  open: (id) => set({ selectedId: id }),
  close: () => set({ selectedId: null }),
}));
