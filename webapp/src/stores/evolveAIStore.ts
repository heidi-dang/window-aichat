import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { PredictiveInsight, EvolutionSuggestion } from '../evolve/EvolutionEngine';

interface EvolveAIState {
  // Core state
  insights: PredictiveInsight[];
  suggestions: EvolutionSuggestion[];
  isAnalyzing: boolean;
  selectedInsight: PredictiveInsight | null;
  
  // Performance optimization
  lastAnalysisTime: number;
  analysisCache: Map<string, { data: any; timestamp: number }>;
  
  // Actions
  setInsights: (insights: PredictiveInsight[]) => void;
  setSuggestions: (suggestions: EvolutionSuggestion[]) => void;
  setIsAnalyzing: (isAnalyzing: boolean) => void;
  setSelectedInsight: (insight: PredictiveInsight | null) => void;
  
  // Optimized actions
  updateInsights: (insights: PredictiveInsight[]) => void;
  getCachedAnalysis: (key: string) => any | null;
  setCachedAnalysis: (key: string, data: any) => void;
  clearCache: () => void;
}

export const useEvolveAIStore = create<EvolveAIState>()(
  devtools(
    (set, get) => ({
      // Initial state
      insights: [],
      suggestions: [],
      isAnalyzing: false,
      selectedInsight: null,
      lastAnalysisTime: 0,
      analysisCache: new Map(),
      
      // Basic setters
      setInsights: (insights) => set({ insights }),
      setSuggestions: (suggestions) => set({ suggestions }),
      setIsAnalyzing: (isAnalyzing) => set({ isAnalyzing }),
      setSelectedInsight: (selectedInsight) => set({ selectedInsight }),
      
      // Optimized updates with caching
      updateInsights: (insights) => {
        const currentTime = Date.now();
        const cacheKey = 'latest-insights';
        
        // Cache the insights
        get().setCachedAnalysis(cacheKey, insights);
        
        set({ 
          insights, 
          lastAnalysisTime: currentTime 
        });
      },
      
      getCachedAnalysis: (key) => {
        const cache = get().analysisCache;
        const cached = cache.get(key);
        
        if (!cached) return null;
        
        // Cache expires after 5 minutes
        const CACHE_TTL = 5 * 60 * 1000;
        if (Date.now() - cached.timestamp > CACHE_TTL) {
          cache.delete(key);
          return null;
        }
        
        return cached.data;
      },
      
      setCachedAnalysis: (key, data) => {
        const cache = get().analysisCache;
        cache.set(key, {
          data,
          timestamp: Date.now()
        });
        
        // Prevent cache from growing too large
        if (cache.size > 50) {
          const oldestKey = cache.keys().next().value;
          if (oldestKey) {
            cache.delete(oldestKey);
          }
        }
      },
      
      clearCache: () => set({ analysisCache: new Map() })
    }),
    {
      name: 'evolveai-store'
    }
  )
);
