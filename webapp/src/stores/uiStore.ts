import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface GlobalUIState {
  // Modal states
  showEvolveAI: boolean;
  showLivingDocs: boolean;
  showSettings: boolean;
  showDiffViewer: boolean;
  showPRPanel: boolean;
  
  // Performance tracking
  modalLoadTimes: Map<string, number>;
  
  // Actions
  setShowEvolveAI: (show: boolean) => void;
  setShowLivingDocs: (show: boolean) => void;
  setShowSettings: (show: boolean) => void;
  setShowDiffViewer: (show: boolean) => void;
  setShowPRPanel: (show: boolean) => void;
  
  // Performance tracking
  trackModalLoadTime: (modal: string, time: number) => void;
  getModalLoadTime: (modal: string) => number | null;
  clearPerformanceData: () => void;
  
  // Bulk actions for better performance
  closeAllModals: () => void;
  openModal: (modal: keyof Pick<GlobalUIState, 'showEvolveAI' | 'showLivingDocs' | 'showSettings' | 'showDiffViewer' | 'showPRPanel'>) => void;
}

export const useUIStore = create<GlobalUIState>()(
  devtools(
    (set, get) => ({
      // Initial state
      showEvolveAI: false,
      showLivingDocs: false,
      showSettings: false,
      showDiffViewer: false,
      showPRPanel: false,
      modalLoadTimes: new Map(),
      
      // Individual setters
      setShowEvolveAI: (showEvolveAI) => set({ showEvolveAI }),
      setShowLivingDocs: (showLivingDocs) => set({ showLivingDocs }),
      setShowSettings: (showSettings) => set({ showSettings }),
      setShowDiffViewer: (showDiffViewer) => set({ showDiffViewer }),
      setShowPRPanel: (showPRPanel) => set({ showPRPanel }),
      
      // Performance tracking
      trackModalLoadTime: (modal, time) => {
        const modalLoadTimes = get().modalLoadTimes;
        modalLoadTimes.set(modal, time);
        set({ modalLoadTimes: new Map(modalLoadTimes) });
      },
      
      getModalLoadTime: (modal) => {
        return get().modalLoadTimes.get(modal) || null;
      },
      
      clearPerformanceData: () => set({ modalLoadTimes: new Map() }),
      
      // Optimized bulk actions
      closeAllModals: () => set({
        showEvolveAI: false,
        showLivingDocs: false,
        showSettings: false,
        showDiffViewer: false,
        showPRPanel: false
      }),
      
      openModal: (modal) => {
        // Close all modals first, then open the requested one
        const closeState = {
          showEvolveAI: false,
          showLivingDocs: false,
          showSettings: false,
          showDiffViewer: false,
          showPRPanel: false
        };
        
        const openState = { ...closeState, [`show${modal}`]: true };
        set(openState);
      }
    }),
    {
      name: 'ui-store'
    }
  )
);
