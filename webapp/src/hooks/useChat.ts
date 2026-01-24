import { useEffect, useRef, useState } from 'react';

import { ApiError, API_BASE } from '../api/client';

export interface ChatUiMessage {
  sender: string;
  text: string;
  timestamp: string;
  streamId?: string;
}

type ChatHistoryItem = { role: string; content: string };
type LastRequestSnapshot = {
  message: string;
  model: string;
  history: ChatHistoryItem[];
  geminiKey?: string;
  deepseekKey?: string;
  assistantStreamId: string;
  contextPackId?: string;
};

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    const requestSuffix = error.requestId ? ` (requestId: ${error.requestId})` : '';
    return `${error.message}${requestSuffix}`;
  }
  if (error instanceof Error) return error.message;
  return String(error);
}

function toChatRole(sender: string): string {
  if (sender === 'You') return 'user';
  if (sender === 'System') return 'system';
  return 'assistant';
}

function getWsUrl(path: string): string {
  const base = API_BASE?.trim() || window.location.origin;
  const url = base.startsWith('/') ? new URL(base, window.location.origin) : new URL(base);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = path;
  url.search = '';
  return url.toString();
}

export function useChat() {
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState('gemini');
  const [activeStreamId, setActiveStreamId] = useState<string | null>(null);
  const [lastContextPackId, setLastContextPackId] = useState<string | null>(null);
  const [hasLastRequest, setHasLastRequest] = useState(false);

  const pushMessage = (msg: ChatUiMessage) => setMessages((prev) => [...prev, msg]);
  const wsRef = useRef<WebSocket | null>(null);
  const activeStreamIdRef = useRef<string | null>(null);
  const lastRequestRef = useRef<LastRequestSnapshot | null>(null);
  const setLoadingRef = useRef<((v: boolean) => void) | null>(null);

  useEffect(() => {
    return () => {
      try {
        wsRef.current?.close();
      } catch {
        // no-op
      }
      wsRef.current = null;
      activeStreamIdRef.current = null;
      setActiveStreamId(null);
    };
  }, []);

  const pushSystemMessage = (text: string) => {
    pushMessage({
      sender: 'System',
      text,
      timestamp: new Date().toLocaleTimeString()
    });
  };

  const cancel = () => {
    try {
      wsRef.current?.send(JSON.stringify({ type: 'cancel' }));
    } catch {
      // no-op
    }
    try {
      wsRef.current?.close();
    } catch {
      // no-op
    }
    wsRef.current = null;
    activeStreamIdRef.current = null;
    setActiveStreamId(null);
    setLoadingRef.current?.(false);
  };

  const startStream = async (req: {
    message: string;
    model: string;
    history: ChatHistoryItem[];
    geminiKey?: string;
    deepseekKey?: string;
    streamId: string;
  }) => {
    try {
      cancel();

      const socket = new WebSocket(getWsUrl('/ws/chat'));
      wsRef.current = socket;

      const finalize = () => {
        if (activeStreamIdRef.current === req.streamId) {
          activeStreamIdRef.current = null;
          setActiveStreamId(null);
        }
        setLoadingRef.current?.(false);
        try {
          socket.close();
        } catch {
          // no-op
        }
      };

      await new Promise<void>((resolve, reject) => {
        socket.onopen = () => {
          socket.send(JSON.stringify({
            type: 'start',
            message: req.message,
            model: req.model,
            history: req.history,
            gemini_key: req.geminiKey || undefined,
            deepseek_key: req.deepseekKey || undefined
          }));
          resolve();
        };
        socket.onerror = () => reject(new Error('WebSocket connection failed'));
      });

      socket.onmessage = (evt) => {
        try {
          const parsed = JSON.parse(String(evt.data)) as unknown;
          if (!parsed || typeof parsed !== 'object') return;
          const msg = parsed as { type?: unknown; content?: unknown; error?: { message?: unknown } };
          if (msg.type === 'chunk' && typeof msg.content === 'string') {
            setMessages((prev) =>
              prev.map((m) => (m.streamId === req.streamId ? { ...m, text: m.text + msg.content } : m))
            );
            return;
          }
          if (msg.type === 'done') {
            finalize();
            return;
          }
          if (msg.type === 'error') {
            const message = typeof msg.error?.message === 'string' ? msg.error.message : 'Streaming failed';
            pushSystemMessage(`Error: ${message}`);
            finalize();
            return;
          }
          if (msg.type === 'cancelled') {
            finalize();
          }
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        if (activeStreamIdRef.current === req.streamId) {
          finalize();
        }
      };
    } catch (error: unknown) {
      pushSystemMessage(`Error: ${describeError(error)}`);
      setLoadingRef.current?.(false);
      activeStreamIdRef.current = null;
      setActiveStreamId(null);
    }
  };

  const sendMessage = async (opts: {
    geminiKey: string;
    deepseekKey: string;
    setIsLoading: (v: boolean) => void;
    historyOverride?: ChatHistoryItem[];
    contextPackId?: string;
  }) => {
    if (!input.trim()) return;

    setLoadingRef.current = opts.setIsLoading;

    const userText = input;
    const userMsg: ChatUiMessage = {
      sender: 'You',
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const streamId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    activeStreamIdRef.current = streamId;
    setActiveStreamId(streamId);

    const assistantSender = selectedModel === 'deepseek' ? 'DeepSeek' : 'Gemini';
    const assistantMsg: ChatUiMessage = {
      sender: assistantSender,
      text: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      streamId
    };

    const historySnapshot = opts.historyOverride ?? messages.map((m) => ({ role: toChatRole(m.sender), content: m.text }));
    lastRequestRef.current = {
      message: userText,
      model: selectedModel,
      history: historySnapshot,
      geminiKey: opts.geminiKey || undefined,
      deepseekKey: opts.deepseekKey || undefined,
      assistantStreamId: streamId,
      contextPackId: opts.contextPackId
    };
    setLastContextPackId(opts.contextPackId ?? null);
    setHasLastRequest(true);

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput('');
    opts.setIsLoading(true);

    await startStream({
      message: userText,
      model: selectedModel,
      history: historySnapshot,
      geminiKey: opts.geminiKey || undefined,
      deepseekKey: opts.deepseekKey || undefined,
      streamId
    });
  };

  const regenerate = async () => {
    const last = lastRequestRef.current;
    if (!last) return;

    const streamId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    activeStreamIdRef.current = streamId;
    setActiveStreamId(streamId);

    lastRequestRef.current = { ...last, assistantStreamId: streamId };
    setLastContextPackId(last.contextPackId ?? null);

    setMessages((prev) =>
      prev.map((m) =>
        m.streamId === last.assistantStreamId
          ? { ...m, text: '', streamId, sender: last.model === 'deepseek' ? 'DeepSeek' : 'Gemini' }
          : m
      )
    );

    setLoadingRef.current?.(true);
    await startStream({
      message: last.message,
      model: last.model,
      history: last.history,
      geminiKey: last.geminiKey,
      deepseekKey: last.deepseekKey,
      streamId
    });
  };

  return {
    messages,
    setMessages,
    pushMessage,
    pushSystemMessage,
    isStreaming: activeStreamId !== null,
    activeStreamId,
    cancel,
    canRegenerate: hasLastRequest && activeStreamId === null,
    regenerate,
    lastContextPackId,
    input,
    setInput,
    selectedModel,
    setSelectedModel,
    sendMessage
  };
}
