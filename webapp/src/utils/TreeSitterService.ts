class TreeSitterService {
  private static instance: TreeSitterService;
  private parser: { parse: (content: string) => { rootNode: unknown }; setLanguage: (lang: unknown) => void } | null = null;
  private isInitializing = false;
  private language: unknown | null = null;
  private initFailed = false;

  private constructor() {}

  static getInstance(): TreeSitterService {
    if (!TreeSitterService.instance) {
      TreeSitterService.instance = new TreeSitterService();
    }
    return TreeSitterService.instance;
  }

  async init() {
    if (this.parser || this.isInitializing || this.initFailed) return;
    this.isInitializing = true;

    try {
      console.log('[TreeSitter] Initializing...');
      
      // Dynamic import to handle module resolution safely
      const ParserModule = (await import('web-tree-sitter')) as unknown as {
        default?: unknown;
        Parser?: unknown;
        init?: () => Promise<void>;
        Language?: { load: (url: string) => Promise<unknown> };
      };
      const parserApi = (ParserModule.default ?? ParserModule) as {
        Parser?: unknown;
        init?: () => Promise<void>;
        Language?: { load: (url: string) => Promise<unknown> };
      };
      const ParserClass = (parserApi.Parser ?? parserApi) as unknown as {
        init?: () => Promise<void>;
        Language?: { load: (url: string) => Promise<unknown> };
        new (): { parse: (content: string) => { rootNode: unknown }; setLanguage: (lang: unknown) => void };
      };

      const initFn = parserApi.init ?? ParserClass.init;
      const Language = parserApi.Language ?? ParserClass.Language;

      console.log('[TreeSitter] Resolved ParserClass:', ParserClass);

      if (typeof initFn !== 'function' || !Language) {
        console.warn('[TreeSitter] init() not available in this environment, disabling TreeSitter.');
        this.initFailed = true;
        return;
      }

      await initFn();
      this.parser = new ParserClass();
      
      // Load TypeScript language via Vite-resolved URL to ensure correct MIME type
      const langUrl = new URL('tree-sitter-typescript/tree-sitter-typescript.wasm', import.meta.url).toString();
      console.log(`[TreeSitter] Loading language from ${langUrl}`);
      
      this.language = await Language.load(langUrl);
      this.parser.setLanguage(this.language);
      
      console.log('[TreeSitter] Ready.');
    } catch (error) {
      console.error('[TreeSitter] Initialization failed:', error);
      this.initFailed = true;
    } finally {
      this.isInitializing = false;
    }
  }

  getParser() {
    return this.parser;
  }

  getLanguage() {
    return this.language;
  }

  async getFunctions(content: string): Promise<string[]> {
    await this.init();
    if (!this.parser) return [];

    try {
      const tree = this.parser.parse(content);
      const chunks: string[] = [];
      const types = new Set([
        'function_declaration',
        'method_definition',
        'class_declaration'
      ]);

      const visit = (node: unknown) => {
        if (!node || typeof node !== 'object') return;
        const n = node as {
          type?: unknown;
          startIndex?: unknown;
          endIndex?: unknown;
          childCount?: unknown;
          child?: (i: number) => unknown;
        };
        if (typeof n.type === 'string' && types.has(n.type)) {
          const start = typeof n.startIndex === 'number' ? n.startIndex : 0;
          const end = typeof n.endIndex === 'number' ? n.endIndex : 0;
          const snippet = content.slice(start, end);
          if (snippet.trim()) chunks.push(snippet);
        }
        const childCount = typeof n.childCount === 'number' ? n.childCount : 0;
        for (let i = 0; i < childCount; i++) {
          visit(typeof n.child === 'function' ? n.child(i) : null);
        }
      };

      visit(tree.rootNode);
      return chunks;
    } catch (e) {
      console.warn('[TreeSitter] Parse failed', e);
      return [];
    }
  }
}

export default TreeSitterService;
