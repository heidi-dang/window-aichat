import VectorStoreService, { type SearchResult } from '../utils/VectorStoreService';
import * as api from '../api/routes';
import type { ChatUiMessage } from '../hooks/useChat';

export type ContextBucket = 'immediate' | 'working' | 'long_term' | 'artifacts';

export type ContextItemReason = {
  recency?: number;
  relevance?: number;
  pinned?: boolean;
  taskAffinity?: number;
};

export type ContextItem = {
  id: string;
  bucket: ContextBucket;
  title: string;
  content: string;
  score: number;
  reason: ContextItemReason;
  source: {
    type: 'chat' | 'pinned_file' | 'rag';
    ref?: string;
  };
};

export type ContextPack = {
  id: string;
  createdAt: number;
  query: string;
  items: ContextItem[];
  systemPrompt: string;
  totalScore: number;
};

function makeId(prefix: string) {
  const rnd = Math.random().toString(16).slice(2);
  return `${prefix}-${Date.now()}-${rnd}`;
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function scoreRecency(indexFromEnd: number) {
  const decay = Math.exp(-indexFromEnd / 6);
  return clamp(decay, 0, 1);
}

function normalizeRelevance(rawScore: number) {
  const s = 1 / (1 + Math.exp(-rawScore));
  return clamp(s, 0, 1);
}

export class ContextOrchestrator {
  private vectorStore = VectorStoreService.getInstance();

  async buildContextPack(params: {
    query: string;
    messages: ChatUiMessage[];
    pinnedFiles: string[];
    maxPinnedFiles?: number;
    maxRagChunks?: number;
    maxChatTurns?: number;
  }): Promise<ContextPack> {
    const createdAt = Date.now();
    const maxPinnedFiles = params.maxPinnedFiles ?? 5;
    const maxRagChunks = params.maxRagChunks ?? 6;
    const maxChatTurns = params.maxChatTurns ?? 10;

    const items: ContextItem[] = [];

    const recent = params.messages.slice(-maxChatTurns);
    for (let i = 0; i < recent.length; i++) {
      const msg = recent[i];
      const indexFromEnd = recent.length - 1 - i;
      const r = scoreRecency(indexFromEnd);
      const score = 0.35 * r;
      items.push({
        id: makeId('chat'),
        bucket: 'immediate',
        title: `Chat: ${msg.sender}`,
        content: msg.text,
        score,
        reason: { recency: r },
        source: { type: 'chat' }
      });
    }

    const pinnedFiles = params.pinnedFiles.slice(0, maxPinnedFiles);
    for (const path of pinnedFiles) {
      try {
        const data = await api.readFile(path);
        items.push({
          id: makeId('pin'),
          bucket: 'working',
          title: `Pinned File: ${path}`,
          content: data.content,
          score: 0.9,
          reason: { pinned: true },
          source: { type: 'pinned_file', ref: path }
        });
      } catch {
        items.push({
          id: makeId('pin'),
          bucket: 'working',
          title: `Pinned File (unreadable): ${path}`,
          content: '',
          score: 0.6,
          reason: { pinned: true },
          source: { type: 'pinned_file', ref: path }
        });
      }
    }

    let ragResults: SearchResult[] = [];
    try {
      ragResults = await this.vectorStore.search(params.query, maxRagChunks);
    } catch {
      ragResults = [];
    }

    for (const hit of ragResults) {
      const rel = normalizeRelevance(hit.score);
      const score = 0.55 * rel;
      items.push({
        id: makeId('rag'),
        bucket: 'working',
        title: `RAG: ${hit.url}`,
        content: hit.content,
        score,
        reason: { relevance: rel },
        source: { type: 'rag', ref: hit.url }
      });
    }

    const ranked = items
      .filter((i) => i.source.type !== 'chat' || i.content.trim().length > 0)
      .sort((a, b) => b.score - a.score);

    const top = ranked.slice(0, 16);
    const totalScore = top.reduce((acc, i) => acc + i.score, 0);

    const systemPrompt = [
      'You are an AI coding assistant inside an IDE.',
      'Use the following context if relevant.',
      'Prefer pinned files and retrieved code chunks over guesses.',
      'If context is insufficient, ask a precise question or suggest the next diagnostic step.',
      '',
      ...top.map((i) => `### ${i.title}\n${i.content}`)
    ].join('\n');

    return {
      id: makeId('ctx'),
      createdAt,
      query: params.query,
      items: top,
      systemPrompt,
      totalScore
    };
  }
}

