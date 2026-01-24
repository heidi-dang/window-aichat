// Centralized store exports for performance optimization
export { useEvolveAIStore } from './evolveAIStore';
export { useDocumentationStore } from './documentationStore';
export { useUIStore } from './uiStore';

// Import hooks for performance monitoring
import { useEvolveAIStore } from './evolveAIStore';
import { useDocumentationStore } from './documentationStore';
import { useUIStore } from './uiStore';

// Performance monitoring utilities
export const getStorePerformance = () => {
  const evolveStore = useEvolveAIStore.getState();
  const docsStore = useDocumentationStore.getState();
  const uiStore = useUIStore.getState();
  
  return {
    evolveAI: {
      cacheSize: evolveStore.analysisCache.size,
      lastAnalysis: evolveStore.lastAnalysisTime,
      isAnalyzing: evolveStore.isAnalyzing
    },
    documentation: {
      cacheSize: docsStore.syncCache.size,
      lastSync: docsStore.lastSyncTime,
      isSyncing: docsStore.isSyncing,
      needsUpdate: docsStore.needsUpdate
    },
    ui: {
      modalPerformance: Object.fromEntries(uiStore.modalLoadTimes),
      activeModals: {
        evolveAI: uiStore.showEvolveAI,
        livingDocs: uiStore.showLivingDocs,
        settings: uiStore.showSettings,
        diffViewer: uiStore.showDiffViewer,
        prPanel: uiStore.showPRPanel
      }
    }
  };
};

// Cache cleanup utility for high-concurrency scenarios
export const performCacheCleanup = () => {
  const evolveStore = useEvolveAIStore.getState();
  const docsStore = useDocumentationStore.getState();
  
  // Clear caches if they're getting too large
  if (evolveStore.analysisCache.size > 100) {
    evolveStore.clearCache();
  }
  
  if (docsStore.syncCache.size > 50) {
    docsStore.clearSyncCache();
  }
  
  // Clear performance data periodically
  const uiStore = useUIStore.getState();
  if (uiStore.modalLoadTimes.size > 20) {
    uiStore.clearPerformanceData();
  }
};
