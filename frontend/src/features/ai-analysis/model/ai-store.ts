import { create } from "zustand";
import type { InventoryItem } from "@/entities/inventory";

interface AiStore {
  activeDrawerItem: InventoryItem | null;
  isLetterModalOpen: boolean;
  isExecutiveModalOpen: boolean;
  openDrawer: (item: InventoryItem) => void;
  closeDrawer: () => void;
  openLetterModal: () => void;
  closeLetterModal: () => void;
  openExecutiveModal: () => void;
  closeExecutiveModal: () => void;
}

export const useAiStore = create<AiStore>((set) => ({
  activeDrawerItem: null,
  isLetterModalOpen: false,
  isExecutiveModalOpen: false,
  openDrawer: (item) => set({ activeDrawerItem: item }),
  closeDrawer: () => set({ activeDrawerItem: null }),
  openLetterModal: () => set({ isLetterModalOpen: true }),
  closeLetterModal: () => set({ isLetterModalOpen: false }),
  openExecutiveModal: () => set({ isExecutiveModalOpen: true }),
  closeExecutiveModal: () => set({ isExecutiveModalOpen: false }),
}));
