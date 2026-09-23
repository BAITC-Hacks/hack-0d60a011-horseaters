import { create } from "zustand";

type EditState = {
  editingId: string | null;
  open: (id: string) => void;
  close: () => void;
};

export const useEditStore = create<EditState>((set) => ({
  editingId: null,
  open: (id) => set({ editingId: id }),
  close: () => set({ editingId: null }),
}));
