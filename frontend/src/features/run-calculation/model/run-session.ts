import { create } from "zustand";

type CalculationSession = {
  activeRunId: string | null;
  setActiveRunId: (id: string) => void;
  clearActiveRunId: () => void;
};

export const useCalculationSessionStore = create<CalculationSession>((set) => ({
  activeRunId: null,
  setActiveRunId: (id) => set({ activeRunId: id }),
  clearActiveRunId: () => set({ activeRunId: null }),
}));
