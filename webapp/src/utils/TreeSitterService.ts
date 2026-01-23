import * as Parser from 'web-tree-sitter';

// Cast to any to bypass type issues with the library
const ParserAny = Parser as any;

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
      await ParserAny.init();
      this.parser = new ParserAny();
      
      // Load TypeScript language from unpkg
      // Using a fixed version to ensure compatibility
      const langUrl = 'https://unpkg.com/tree-sitter-typescript@0.20.5/tree-sitter-typescript.wasm';
      console.log(`[TreeSitter] Loading language from ${langUrl}`);
      
      this.language = await ParserAny.Language.load(langUrl);
      this.parser.setLanguage(this.language);
      
      console.log('[TreeSitter] Ready.');
    } catch (error) {
      console.error('[TreeSitter] Initialization failed:', error);
    } finally {
      this.isInitializing = false;
    }
  }

  async parse(content: string) {
    if (!this.parser) await this.init();
    if (!this.parser) return null;

    return this.parser.parse(content);
  }

  /**
   * Extract function names from the code
   */
  async getFunctions(content: string): Promise<string[]> {
    const tree = await this.parse(content);
    if (!tree) return [];

    const query = this.language?.query(`
      (function_declaration name: (identifier) @name)
      (method_definition name: (property_identifier) @name)
      (arrow_function) @arrow
    `);

    if (!query) return [];

    const captures = query.captures(tree.rootNode);
    return captures.map((c: any) => c.node.text);
  }
  
  /**
   * Get a structured outline of the code
   */
  async getOutline(content: string) {
      const tree = await this.parse(content);
      if (!tree) return "Unable to parse structure.";
      
      // Simple recursive walker to print the tree structure for debugging/context
      const walk = (node: any, depth = 0): string => {
          let result = "";
          const indent = "  ".repeat(depth);
          
          if (node.type === 'function_declaration' || node.type === 'class_declaration' || node.type === 'method_definition') {
              const nameNode = node.childForFieldName('name');
              const name = nameNode ? nameNode.text : 'anonymous';
              result += `${indent}${node.type}: ${name} (Line ${node.startPosition.row})\n`;
          }
          
          for (const child of node.children) {
              result += walk(child, depth + 1);
          }
          return result;
      };

      return walk(tree.rootNode);
  }
}

export default TreeSitterService;
