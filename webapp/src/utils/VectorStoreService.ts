import { pipeline } from '@xenova/transformers';
import { Voy } from 'voy-search';
import TreeSitterService from './TreeSitterService';

export interface SearchResult {
  id: string;
  title: string;
  url: string; // File path
  content: string; // The chunk content
  score: number;
}

class VectorStoreService {
  private static instance: VectorStoreService;
  private embedder: any | null = null;
  private voy: any | null = null;
  private documents: Record<string, SearchResult> = {}; // Map ID to content
  private isInitializing = false;

  private constructor() {}

  static getInstance(): VectorStoreService {
    if (!VectorStoreService.instance) {
      VectorStoreService.instance = new VectorStoreService();
    }
    return VectorStoreService.instance;
  }

  async init() {
    if (this.voy || this.isInitializing) return;
    this.isInitializing = true;

    try {
      console.log('[VectorStore] Initializing embedding model...');
      // Use a quantized model for browser efficiency
      this.embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2', {
        quantized: true,
      });

      console.log('[VectorStore] Initializing Voy index...');
      this.voy = new Voy({
        embeddings: [] // Start empty
      });
      
      console.log('[VectorStore] Ready.');
    } catch (error) {
      console.error('[VectorStore] Initialization failed:', error);
    } finally {
      this.isInitializing = false;
    }
  }

  async addFile(filePath: string, content: string) {
    if (!this.embedder || !this.voy) await this.init();
    if (!this.embedder || !this.voy) return;

    console.log(`[VectorStore] Indexing ${filePath}...`);
    let chunks: string[] = [];

    // Try to use Tree-Sitter for structural chunking
    try {
      const treeSitter = TreeSitterService.getInstance();
      // Initialize if needed (it handles its own init state)
      await treeSitter.init();
      
      const functions = await treeSitter.getFunctions(content);
      if (functions.length > 0) {
        console.log(`[VectorStore] Using TreeSitter chunking: found ${functions.length} functions.`);
        chunks = functions;
      }
    } catch (e) {
      console.warn('[VectorStore] TreeSitter chunking failed, falling back to lines:', e);
    }

    // Fallback to line-based chunking if no structural chunks found
    if (chunks.length === 0) {
      const lines = content.split('\n');
      let currentChunk = '';
      
      for (let i = 0; i < lines.length; i++) {
        currentChunk += lines[i] + '\n';
        if ((i + 1) % 20 === 0 || i === lines.length - 1) {
          chunks.push(currentChunk);
          currentChunk = '';
        }
      }
    }

    console.log(`[VectorStore] Total chunks to index: ${chunks.length}`);

    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i];
      if (!chunk.trim()) continue;

      const output = await this.embedder(chunk, { pooling: 'mean', normalize: true });
      const embedding = Array.from(output.data);
      
      const id = `${filePath}#chunk${i}`;
      
      this.voy.add({
        id,
        title: filePath,
        url: filePath,
        embeddings: embedding as any
      });

      this.documents[id] = {
        id,
        title: filePath,
        url: filePath,
        content: chunk,
        score: 0
      };
    }
  }

  async search(query: string, limit = 5): Promise<SearchResult[]> {
    if (!this.embedder || !this.voy) await this.init();
    if (!this.embedder || !this.voy) return [];

    console.log(`[VectorStore] Searching for: "${query}"`);

    const output = await this.embedder(query, { pooling: 'mean', normalize: true });
    const queryEmbedding = Array.from(output.data);

    // Voy search returns { id: string, score: number }
    const results = this.voy.search(queryEmbedding as any, limit);

    return results.hits.map((hit: any) => ({
      ...this.documents[hit.id],
      score: hit.score
    }));
  }
}

export default VectorStoreService;
