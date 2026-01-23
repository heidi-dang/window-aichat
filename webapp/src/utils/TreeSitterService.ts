
import { VectorStoreService } from './VectorStoreService';

class TreeSitterService {
  private static instance: TreeSitterService;
  private parser: any | null = null;
  private isInitializing = false;
  private language: any | null = null;

  private constructor() {}

  static getInstance(): TreeSitterService {
    if (!TreeSitterService.instance) {
      TreeSitterService.instance = new TreeSitterService();
    }
    return TreeSitterService.instance;
  }

  async init() {
    if (this.parser || this.isInitializing) return;
    this.isInitializing = true;

    try {
      console.log('[TreeSitter] Initializing...');
      
      // Dynamic import to handle module resolution safely
      const ParserModule = await import('web-tree-sitter');
      const ParserClass = (ParserModule as any).default || ParserModule;

      console.log('[TreeSitter] Resolved ParserClass:', ParserClass);

      if (typeof ParserClass.init !== 'function') {
          throw new Error(`ParserClass.init is not a function. Keys: ${Object.keys(ParserClass)}`);
      }

      // Initialize the library
      await ParserClass.init();
      this.parser = new ParserClass();
      
      // Load TypeScript language from unpkg
      // Using a fixed version to ensure compatibility
      const langUrl = 'https://unpkg.com/tree-sitter-typescript@0.20.5/tree-sitter-typescript.wasm';
      console.log(`[TreeSitter] Loading language from ${langUrl}`);
      
      this.language = await ParserClass.Language.load(langUrl);
      this.parser.setLanguage(this.language);
      
      console.log('[TreeSitter] Ready.');
    } catch (error) {
      console.error('[TreeSitter] Initialization failed:', error);
    } finally {
      this.isInitializing = false;
    }
  }

  getParser(): any | null {
    return this.parser;
  }

  getLanguage(): any | null {
    return this.language;
  }
}

export default TreeSitterService;
