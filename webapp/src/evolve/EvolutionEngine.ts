import VectorStoreService from '../utils/VectorStoreService';
export interface CodePattern {
  id: string;
  type: 'function' | 'class' | 'component' | 'hook' | 'api' | 'config';
  name: string;
  signature: string;
  content: string;
  filePath: string;
  dependencies: string[];
  usage: number;
  lastModified: number;
  evolutionScore: number;
}

export interface EvolutionSuggestion {
  id: string;
  type: 'refactor' | 'optimize' | 'modernize' | 'secure' | 'test' | 'document';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  targetPattern: CodePattern;
  suggestedCode: string;
  reasoning: string;
  confidence: number;
}

export interface PredictiveInsight {
  id: string;
  category: 'architecture' | 'performance' | 'security' | 'maintainability';
  title: string;
  description: string;
  affectedFiles: string[];
  recommendations: string[];
  confidence: number;
}

export class EvolutionEngine {
  private static instance: EvolutionEngine;
  private vectorStore = VectorStoreService.getInstance();
  private patterns: Map<string, CodePattern> = new Map();
  private insights: PredictiveInsight[] = [];

  private constructor() {
    void this.vectorStore.init?.();
  }

  static getInstance(): EvolutionEngine {
    if (!EvolutionEngine.instance) {
      EvolutionEngine.instance = new EvolutionEngine();
    }
    return EvolutionEngine.instance;
  }

  async initializeEvolutionSystem(apiBase: string) {
    console.log('[EvolveAI] Initializing predictive evolution system...');
    await this.analyzeCodebasePatterns(apiBase);
    await this.generatePredictiveInsights();
    console.log('[EvolveAI] Evolution system ready with', this.patterns.size, 'patterns');
  }

  private async analyzeCodebasePatterns(apiBase: string) {
    try {
      const files = await this.getAllCodeFiles(apiBase);
      
      for (const filePath of files) {
        const content = await this.getFileContent(apiBase, filePath);
        const patterns = await this.extractPatterns(filePath, content);
        
        patterns.forEach(pattern => {
          this.patterns.set(pattern.id, pattern);
        });
      }

      // Calculate evolution scores based on usage and complexity
      this.calculateEvolutionScores();
    } catch (error) {
      console.error('[EvolveAI] Failed to analyze codebase patterns:', error);
    }
  }

  private async extractPatterns(filePath: string, content: string): Promise<CodePattern[]> {
    const patterns: CodePattern[] = [];
    
    // Extract function patterns
    const functionMatches = content.matchAll(/(?:function|const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)\s*=>|function\s*\([^)]*\))/g);
    for (const match of functionMatches) {
      patterns.push({
        id: `${filePath}#func#${match[1]}`,
        type: 'function',
        name: match[1],
        signature: match[0],
        content: this.extractFunctionContent(content, match.index),
        filePath,
        dependencies: this.extractDependencies(content),
        usage: 0,
        lastModified: Date.now(),
        evolutionScore: 0
      });
    }

    // Extract React component patterns
    const componentMatches = content.matchAll(/(?:const|function)\s+(\w+)\s*(?:=\s*\([^)]*\)\s*=>|function\s*\([^)]*\))\s*{[\s\S]*?return[\s\S]*?<(?:div|Fragment)/g);
    for (const match of componentMatches) {
      patterns.push({
        id: `${filePath}#component#${match[1]}`,
        type: 'component',
        name: match[1],
        signature: match[0],
        content: this.extractFunctionContent(content, match.index),
        filePath,
        dependencies: this.extractDependencies(content),
        usage: 0,
        lastModified: Date.now(),
        evolutionScore: 0
      });
    }

    // Extract class patterns
    const classMatches = content.matchAll(/class\s+(\w+)(?:\s+extends\s+\w+)?\s*{/g);
    for (const match of classMatches) {
      patterns.push({
        id: `${filePath}#class#${match[1]}`,
        type: 'class',
        name: match[1],
        signature: match[0],
        content: this.extractClassContent(content, match.index),
        filePath,
        dependencies: this.extractDependencies(content),
        usage: 0,
        lastModified: Date.now(),
        evolutionScore: 0
      });
    }

    return patterns;
  }

  private extractFunctionContent(content: string, startIndex?: number): string {
    if (!startIndex) return '';
    const lines = content.substring(startIndex).split('\n');
    let braceCount = 0;
    const contentLines: string[] = [];
    let foundOpening = false;

    for (const line of lines) {
      if (line.includes('{')) {
        foundOpening = true;
        braceCount += (line.match(/{/g) || []).length;
      }
      
      if (foundOpening) {
        contentLines.push(line);
        braceCount -= (line.match(/}/g) || []).length;
        
        if (braceCount === 0) break;
      }
    }

    return contentLines.join('\n');
  }

  private extractClassContent(content: string, startIndex?: number): string {
    if (!startIndex) return '';
    const lines = content.substring(startIndex).split('\n');
    let braceCount = 0;
    const contentLines: string[] = [];

    for (const line of lines) {
      contentLines.push(line);
      braceCount += (line.match(/{/g) || []).length;
      braceCount -= (line.match(/}/g) || []).length;
      
      if (braceCount === 0) break;
    }

    return contentLines.join('\n');
  }

  private extractDependencies(content: string): string[] {
    const imports = content.match(/import.*from\s+['"]([^'"]+)['"]/g) || [];
    return imports.map(imp => imp.match(/from\s+['"]([^'"]+)['"]/)?.[1] || '').filter(Boolean);
  }

  private calculateEvolutionScores() {
    for (const pattern of this.patterns.values()) {
      let score = 0;
      
      // Complexity factor
      const complexity = this.calculateComplexity(pattern.content);
      score += complexity * 0.3;
      
      // Usage factor (placeholder - would be tracked over time)
      score += pattern.usage * 0.2;
      
      // Age factor (older code gets higher evolution priority)
      const age = Date.now() - pattern.lastModified;
      score += Math.min(age / (1000 * 60 * 60 * 24 * 30), 1) * 0.3; // Max 1 month old
      
      // Dependency factor (more dependencies = higher priority)
      score += pattern.dependencies.length * 0.1;
      
      pattern.evolutionScore = Math.min(score, 1);
    }
  }

  private calculateComplexity(code: string): number {
    let complexity = 0;
    
    // Cyclomatic complexity indicators
    complexity += (code.match(/if\s*\(/g) || []).length;
    complexity += (code.match(/for\s*\(/g) || []).length;
    complexity += (code.match(/while\s*\(/g) || []).length;
    complexity += (code.match(/switch\s*\(/g) || []).length * 2;
    complexity += (code.match(/catch\s*\(/g) || []).length;
    complexity += (code.match(/\?./g) || []).length * 0.5;
    
    // Length factor
    const lines = code.split('\n').length;
    complexity += Math.min(lines / 50, 1); // Normalize to max 1 for 50+ lines
    
    return Math.min(complexity / 10, 1); // Normalize to 0-1
  }

  async generateEvolutionSuggestions(): Promise<EvolutionSuggestion[]> {
    const suggestions: EvolutionSuggestion[] = [];
    
    for (const pattern of this.patterns.values()) {
      if (pattern.evolutionScore > 0.6) { // Only suggest for high-priority patterns
        const patternSuggestions = await this.analyzePatternForEvolution(pattern);
        suggestions.push(...patternSuggestions);
      }
    }
    
    return suggestions.sort((a, b) => {
      const priorityWeight = { high: 3, medium: 2, low: 1 };
      return priorityWeight[b.priority] - priorityWeight[a.priority] || b.confidence - a.confidence;
    });
  }

  private async analyzePatternForEvolution(pattern: CodePattern): Promise<EvolutionSuggestion[]> {
    const suggestions: EvolutionSuggestion[] = [];
    
    // Analyze for modernization opportunities
    if (this.needsModernization(pattern)) {
      suggestions.push({
        id: `modernize-${pattern.id}`,
        type: 'modernize',
        priority: 'medium',
        title: `Modernize ${pattern.name}`,
        description: `Update ${pattern.name} to use modern JavaScript/TypeScript patterns`,
        targetPattern: pattern,
        suggestedCode: await this.generateModernizedCode(pattern),
        reasoning: 'This function uses legacy patterns that could be modernized for better performance and readability',
        confidence: 0.8
      });
    }
    
    // Analyze for optimization opportunities
    if (pattern.evolutionScore > 0.8) {
      suggestions.push({
        id: `optimize-${pattern.id}`,
        type: 'optimize',
        priority: 'high',
        title: `Optimize ${pattern.name}`,
        description: `Performance optimization opportunities detected in ${pattern.name}`,
        targetPattern: pattern,
        suggestedCode: await this.generateOptimizedCode(pattern),
        reasoning: 'High complexity and usage patterns suggest optimization opportunities',
        confidence: 0.9
      });
    }
    
    // Analyze for testing opportunities
    if (!pattern.name.includes('test') && pattern.type === 'function') {
      suggestions.push({
        id: `test-${pattern.id}`,
        type: 'test',
        priority: 'medium',
        title: `Add tests for ${pattern.name}`,
        description: `Generate comprehensive unit tests for ${pattern.name}`,
        targetPattern: pattern,
        suggestedCode: await this.generateTestCode(pattern),
        reasoning: 'This function lacks test coverage despite being a core utility',
        confidence: 0.7
      });
    }
    
    return suggestions;
  }

  private needsModernization(pattern: CodePattern): boolean {
    const legacyPatterns = [
      /var\s+/,
      /\.then\s*\(/,
      /function\s*\(\s*\)\s*{\s*return/,
      /Promise\.resolve/,
      /console\.log/
    ];
    
    return legacyPatterns.some(regex => regex.test(pattern.content));
  }

  private async generateModernizedCode(pattern: CodePattern): Promise<string> {
    // This would integrate with AI to generate modernized code
    // For now, return a placeholder
    return `// Modernized version of ${pattern.name}\n// AI-generated modernization would appear here`;
  }

  private async generateOptimizedCode(pattern: CodePattern): Promise<string> {
    // This would integrate with AI to generate optimized code
    return `// Optimized version of ${pattern.name}\n// AI-generated optimization would appear here`;
  }

  private async generateTestCode(pattern: CodePattern): Promise<string> {
    // This would integrate with AI to generate comprehensive tests
    return `// Test suite for ${pattern.name}\n// AI-generated tests would appear here`;
  }

  async generatePredictiveInsights(): Promise<PredictiveInsight[]> {
    const insights: PredictiveInsight[] = [];
    
    // Architectural insights
    const architecturalIssues = await this.analyzeArchitecture();
    insights.push(...architecturalIssues);
    
    // Performance insights
    const performanceIssues = await this.analyzePerformance();
    insights.push(...performanceIssues);
    
    // Security insights
    const securityIssues = await this.analyzeSecurity();
    insights.push(...securityIssues);
    
    this.insights = insights;
    return insights;
  }

  private async analyzeArchitecture(): Promise<PredictiveInsight[]> {
    const insights: PredictiveInsight[] = [];
    
    // Check for circular dependencies
    const circularDeps = this.detectCircularDependencies();
    if (circularDeps.length > 0) {
      insights.push({
        id: 'circular-deps',
        category: 'architecture',
        title: 'Circular Dependencies Detected',
        description: `Found ${circularDeps.length} circular dependencies that could cause maintenance issues`,
        affectedFiles: circularDeps,
        recommendations: [
          'Refactor to use dependency injection',
          'Create a shared module for common utilities',
          'Consider event-driven architecture'
        ],
        confidence: 0.9
      });
    }
    
    return insights;
  }

  private async analyzePerformance(): Promise<PredictiveInsight[]> {
    const insights: PredictiveInsight[] = [];
    
    // Check for large functions
    const largeFunctions = Array.from(this.patterns.values())
      .filter(p => p.content.split('\n').length > 50);
    
    if (largeFunctions.length > 0) {
      insights.push({
        id: 'large-functions',
        category: 'performance',
        title: 'Large Functions Detected',
        description: `Found ${largeFunctions.length} functions that are too large and may impact performance`,
        affectedFiles: largeFunctions.map(f => f.filePath),
        recommendations: [
          'Break down large functions into smaller, focused units',
          'Extract common logic into utility functions',
          'Consider using memoization for expensive operations'
        ],
        confidence: 0.8
      });
    }
    
    return insights;
  }

  private async analyzeSecurity(): Promise<PredictiveInsight[]> {
    const insights: PredictiveInsight[] = [];
    
    // Check for security anti-patterns
    const securityIssues: string[] = [];
    
    for (const pattern of this.patterns.values()) {
      if (pattern.content.includes('eval(')) {
        securityIssues.push(pattern.filePath);
      }
      if (pattern.content.includes('innerHTML')) {
        securityIssues.push(pattern.filePath);
      }
    }
    
    if (securityIssues.length > 0) {
      insights.push({
        id: 'security-issues',
        category: 'security',
        title: 'Security Vulnerabilities',
        description: `Found ${securityIssues.length} potential security vulnerabilities`,
        affectedFiles: [...new Set(securityIssues)],
        recommendations: [
          'Replace eval() with safer alternatives',
          'Use textContent instead of innerHTML',
          'Implement proper input sanitization',
          'Add Content Security Policy headers'
        ],
        confidence: 0.95
      });
    }
    
    return insights;
  }

  private detectCircularDependencies(): string[] {
    // Simplified circular dependency detection
    // In a real implementation, this would build a full dependency graph
    return [];
  }

  private async getAllCodeFiles(apiBase: string): Promise<string[]> {
    try {
      const response = await fetch(`${apiBase}/api/fs/list`);
      if (!response.ok) {
        console.warn('[EvolveAI] Failed to list files:', response.status, response.statusText);
        return [];
      }
      const files = (await response.json()) as unknown;
      const list = Array.isArray(files) ? files : [];

      return list
        .filter((entry): entry is Record<string, unknown> => !!entry && typeof entry === 'object')
        .filter((entry) => entry.type === 'file')
        .filter((entry) => typeof entry.name === 'string' && /\.(ts|tsx|js|jsx)$/.test(entry.name))
        .map((entry) => String(entry.path ?? ''))
        .filter(Boolean);
    } catch (error) {
      console.error('[EvolveAI] Failed to get code files:', error);
      return [];
    }
  }

  private async getFileContent(apiBase: string, path: string): Promise<string> {
    try {
      const response = await fetch(`${apiBase}/api/fs/read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      const data = await response.json();
      return data.content || '';
    } catch (error) {
      console.error(`[EvolveAI] Failed to read file ${path}:`, error);
      return '';
    }
  }

  getPatterns(): CodePattern[] {
    return Array.from(this.patterns.values());
  }

  getInsights(): PredictiveInsight[] {
    return this.insights;
  }

  async trackUsage(patternId: string) {
    const pattern = this.patterns.get(patternId);
    if (pattern) {
      pattern.usage++;
      pattern.lastModified = Date.now();
      this.calculateEvolutionScores();
    }
  }
}

export default EvolutionEngine;
