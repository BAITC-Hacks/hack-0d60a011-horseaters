import { create } from "zustand";

type SelectionState = {
  selectedIds: string[];
  toggle: (id: string) => void;
  selectMany: (ids: string[]) => void;
  clearMany: (ids: string[]) => void;
  clear: () => void;
};

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedIds: [],
  toggle: (id) => set((state) => ({
    selectedIds: state.selectedIds.includes(id)
      ? state.selectedIds.filter((selected) => selected !== id)
      : [...state.selectedIds, id],
  })),
  selectMany: (ids) => set((state) => ({ selectedIds: [...new Set([...state.selectedIds, ...ids])] })),
  clearMany: (ids) => set((state) => ({ selectedIds: state.selectedIds.filter((id) => !ids.includes(id)) })),
  clear: () => set({ selectedIds: [] }),
}));
