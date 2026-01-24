import { pipeline, env } from '@xenova/transformers';
import { Voy } from 'voy-search';
import TreeSitterService from './TreeSitterService';

// Disable local model checks to prevent Vite from serving index.html for missing model files
env.allowLocalModels = false;
env.useBrowserCache = true;

export interface SearchResult {
  id: string;
  title: string;
  url: string; // File path
  content: string; // The chunk content
  score: number;
}

type Embedder = (text: string, opts: { pooling: 'mean'; normalize: true }) => Promise<{ data: ArrayLike<number> }>;
type FsEntry = { type: string; name: string; path: string };

class VectorStoreService {
  private static instance: VectorStoreService;
  private embedder: Embedder | null = null;
  private voy: Voy | null = null;
  private documents: Record<string, SearchResult> = {}; // Map ID to content
  private isInitializing = false;
  private isIndexing = false;

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
      this.embedder = (await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2', {
        quantized: true,
      })) as unknown as Embedder;

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

  async indexWorkspace(apiBase: string) {
    if (this.isIndexing) {
      console.log('[VectorStore] Indexing already in progress, skipping.');
      return;
    }
    if (!this.embedder || !this.voy) await this.init();
    if (!this.embedder || !this.voy) return;

    this.isIndexing = true;
    try {
        console.log('[VectorStore] Indexing workspace...');
        const listRes = await fetch(`${apiBase}/api/fs/list`);
        if (!listRes.ok) throw new Error('Failed to list files');
        const rawFiles = (await listRes.json()) as unknown;
        const files: FsEntry[] = Array.isArray(rawFiles) ? (rawFiles as unknown[]).flatMap((v) => {
          if (!v || typeof v !== 'object') return [];
          const obj = v as Record<string, unknown>;
          if (typeof obj.type !== 'string' || typeof obj.name !== 'string' || typeof obj.path !== 'string') return [];
          return [{ type: obj.type, name: obj.name, path: obj.path }];
        }) : [];

        for (const file of files) {
            if (file.type !== 'file') continue;
            // Skip huge files or binaries if possible (by extension)
            if (file.name.match(/\.(png|jpg|jpeg|gif|ico|pdf|zip|tar|gz|map|json|lock|wasm|pyc)$/i)) continue;

            try {
                const readRes = await fetch(`${apiBase}/api/fs/read`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: file.path })
                });
                if (readRes.ok) {
                    const data = await readRes.json();
                    await this.addFile(file.path, data.content);
                }
            } catch (err) {
                console.error(`[VectorStore] Failed to index ${file.path}`, err);
            }
        }
        console.log('[VectorStore] Workspace indexing complete.');
    } catch (error) {
        console.error('[VectorStore] Workspace indexing failed:', error);
    } finally {
        this.isIndexing = false;
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
        embeddings: embedding
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
    const results = this.voy.search(queryEmbedding, limit) as unknown as { hits: Array<{ id: string; score: number }> };

    return results.hits
      .filter((hit) => typeof hit.id === 'string' && typeof hit.score === 'number' && Boolean(this.documents[hit.id]))
      .map((hit) => ({ ...this.documents[hit.id], score: hit.score }));
  }
}

export default VectorStoreService;
