import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface DocumentationState {
  sections: any[];
  isSyncing: boolean;
  lastSyncTime: number;
  needsUpdate: boolean;
  
  // Performance optimization
  syncCache: Map<string, { data: any; timestamp: number }>;
  
  // Actions
  setSections: (sections: any[]) => void;
  setIsSyncing: (isSyncing: boolean) => void;
  setNeedsUpdate: (needsUpdate: boolean) => void;
  
  // Optimized actions
  updateSections: (sections: any[]) => void;
  getCachedSync: (key: string) => any | null;
  setCachedSync: (key: string, data: any) => void;
  clearSyncCache: () => void;
}

export const useDocumentationStore = create<DocumentationState>()(
  devtools(
    (set, get) => ({
      // Initial state
      sections: [],
      isSyncing: false,
      lastSyncTime: 0,
      needsUpdate: false,
      syncCache: new Map(),
      
      // Basic setters
      setSections: (sections) => set({ sections }),
      setIsSyncing: (isSyncing) => set({ isSyncing }),
      setNeedsUpdate: (needsUpdate) => set({ needsUpdate }),
      
      // Optimized updates with caching
      updateSections: (sections) => {
        const currentTime = Date.now();
        const cacheKey = 'latest-docs';
        
        // Cache the sections
        get().setCachedSync(cacheKey, sections);
        
        set({ 
          sections, 
          lastSyncTime: currentTime,
          needsUpdate: false
        });
      },
      
      getCachedSync: (key) => {
        const cache = get().syncCache;
        const cached = cache.get(key);
        
        if (!cached) return null;
        
        // Cache expires after 3 minutes
        const CACHE_TTL = 3 * 60 * 1000;
        if (Date.now() - cached.timestamp > CACHE_TTL) {
          cache.delete(key);
          return null;
        }
        
        return cached.data;
      },
      
      setCachedSync: (key, data) => {
        const cache = get().syncCache;
        cache.set(key, {
          data,
          timestamp: Date.now()
        });
        
        // Prevent cache from growing too large
        if (cache.size > 30) {
          const oldestKey = cache.keys().next().value;
          if (oldestKey) {
            cache.delete(oldestKey);
          }
        }
      },
      
      clearSyncCache: () => set({ syncCache: new Map() })
    }),
    {
      name: 'documentation-store'
    }
  )
);
