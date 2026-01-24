import React, { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Alert } from '../components/ui/alert';
import { Lightbulb, TrendingUp, Shield, Zap, Code, CheckCircle, AlertTriangle } from 'lucide-react';
import EvolutionEngine, { type PredictiveInsight, type EvolutionSuggestion } from './EvolutionEngine';

interface EvolveAIProps {
  apiBase: string;
}

export const EvolveAI: React.FC<EvolveAIProps> = ({ apiBase }) => {
  const [engine, setEngine] = useState<EvolutionEngine | null>(null);
  const [insights, setInsights] = useState<PredictiveInsight[]>([]);
  const [suggestions, setSuggestions] = useState<EvolutionSuggestion[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const initializeEvolutionSystem = useCallback(
    async (activeEngine: EvolutionEngine) => {
      setIsAnalyzing(true);
      try {
        await activeEngine.initializeEvolutionSystem(apiBase);
        const nextInsights = await activeEngine.generatePredictiveInsights();
        const nextSuggestions = await activeEngine.generateEvolutionSuggestions();

        setInsights(nextInsights);
        setSuggestions(nextSuggestions);
      } catch (error) {
        console.error('[EvolveAI] Failed to initialize:', error);
      } finally {
        setIsAnalyzing(false);
      }
    },
    [apiBase]
  );

  useEffect(() => {
    const evolutionEngine = EvolutionEngine.getInstance();
    setEngine(evolutionEngine);
    void initializeEvolutionSystem(evolutionEngine);
  }, [initializeEvolutionSystem]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'architecture': return <Code className="h-4 w-4" />;
      case 'performance': return <Zap className="h-4 w-4" />;
      case 'security': return <Shield className="h-4 w-4" />;
      case 'maintainability': return <TrendingUp className="h-4 w-4" />;
      default: return <Lightbulb className="h-4 w-4" />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'architecture': return 'bg-blue-100 text-blue-800';
      case 'performance': return 'bg-yellow-100 text-yellow-800';
      case 'security': return 'bg-red-100 text-red-800';
      case 'maintainability': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const applySuggestion = async (suggestion: EvolutionSuggestion) => {
    if (!engine) return;
    
    try {
      // This would integrate with the AI system to apply the suggestion
      console.log('[EvolveAI] Applying suggestion:', suggestion.title);
      
      // Track the usage for learning
      await engine.trackUsage(suggestion.targetPattern.id);
      
      // Remove applied suggestion from list
      setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
    } catch (error) {
      console.error('[EvolveAI] Failed to apply suggestion:', error);
    }
  };

  if (isAnalyzing) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Analyzing codebase for evolution opportunities...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Lightbulb className="h-6 w-6 text-yellow-500" />
            EvolveAI - Predictive Code Evolution
          </h2>
          <p className="text-gray-600 mt-1">
            AI-powered insights to proactively improve your codebase
          </p>
        </div>
        <Button
          onClick={() => engine && initializeEvolutionSystem(engine)}
          disabled={isAnalyzing || !engine}
          variant="outline"
        >
          Refresh Analysis
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-blue-500" />
              <div>
                <p className="text-sm text-gray-600">Total Insights</p>
                <p className="text-2xl font-bold">{insights.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-500" />
              <div>
                <p className="text-sm text-gray-600">Evolution Suggestions</p>
                <p className="text-2xl font-bold">{suggestions.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-red-500" />
              <div>
                <p className="text-sm text-gray-600">Security Issues</p>
                <p className="text-2xl font-bold">
                  {insights.filter(i => i.category === 'security').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-yellow-500" />
              <div>
                <p className="text-sm text-gray-600">Performance</p>
                <p className="text-2xl font-bold">
                  {insights.filter(i => i.category === 'performance').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Critical Insights */}
      {insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              Predictive Insights
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {insights.map((insight) => (
                <Alert key={insight.id} className="border-l-4 border-l-blue-500">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-full ${getCategoryColor(insight.category)}`}>
                      {getCategoryIcon(insight.category)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold">{insight.title}</h4>
                        <Badge variant="outline">
                          {Math.round(insight.confidence * 100)}% confidence
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{insight.description}</p>
                      
                      {insight.affectedFiles.length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs font-medium text-gray-700 mb-1">Affected Files:</p>
                          <div className="flex flex-wrap gap-1">
                            {insight.affectedFiles.map((file, idx) => (
                              <Badge key={idx} variant="secondary" className="text-xs">
                                {file.split('/').pop()}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      <div>
                        <p className="text-xs font-medium text-gray-700 mb-1">Recommendations:</p>
                        <ul className="text-sm text-gray-600 space-y-1">
                          {insight.recommendations.map((rec, idx) => (
                            <li key={idx} className="flex items-center gap-2">
                              <CheckCircle className="h-3 w-3 text-green-500" />
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Evolution Suggestions */}
      {suggestions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-500" />
              Evolution Suggestions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {suggestions.slice(0, 5).map((suggestion) => (
                <div
                  key={suggestion.id}
                  className={`border rounded-lg p-4 ${getPriorityColor(suggestion.priority)}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h4 className="font-semibold">{suggestion.title}</h4>
                        <Badge variant="outline">{suggestion.type}</Badge>
                        <Badge variant="outline">{suggestion.priority}</Badge>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{suggestion.description}</p>
                      <p className="text-xs text-gray-500">{suggestion.reasoning}</p>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <Badge variant="secondary">
                        {Math.round(suggestion.confidence * 100)}% confidence
                      </Badge>
                      <Button
                        size="sm"
                        onClick={() => applySuggestion(suggestion)}
                        className="ml-2"
                      >
                        Apply
                      </Button>
                    </div>
                  </div>
                  
                  <div className="text-xs text-gray-500">
                    Target: <code>{suggestion.targetPattern.name}</code> in{' '}
                    <code>{suggestion.targetPattern.filePath.split('/').pop()}</code>
                  </div>
                </div>
              ))}
            </div>
            
            {suggestions.length > 5 && (
              <div className="mt-4 text-center">
                <Button variant="outline">
                  View {suggestions.length - 5} more suggestions
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {insights.length === 0 && suggestions.length === 0 && !isAnalyzing && (
        <Card>
          <CardContent className="p-8 text-center">
            <Lightbulb className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              No evolution opportunities detected
            </h3>
            <p className="text-gray-500">
              Your codebase appears to be in good shape! EvolveAI will continue monitoring for improvement opportunities.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default EvolveAI;
