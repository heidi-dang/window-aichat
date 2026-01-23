import { useEffect, useRef, useState } from 'react';

import { ApiError, API_BASE } from '../api/client';

export interface ChatUiMessage {
  sender: string;
  text: string;
  timestamp: string;
  streamId?: string;
}

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
  const base = API_BASE || window.location.origin;
  const url = new URL(base);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = path;
  url.search = '';
  return url.toString();
}

export function useChat() {
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState('gemini');

  const pushMessage = (msg: ChatUiMessage) => setMessages((prev) => [...prev, msg]);
  const wsRef = useRef<WebSocket | null>(null);
  const activeStreamIdRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      try {
        wsRef.current?.close();
      } catch {
        // no-op
      }
      wsRef.current = null;
      activeStreamIdRef.current = null;
    };
  }, []);

  const pushSystemMessage = (text: string) => {
    pushMessage({
      sender: 'System',
      text,
      timestamp: new Date().toLocaleTimeString()
    });
  };

  const sendMessage = async (opts: { geminiKey: string; deepseekKey: string; setIsLoading: (v: boolean) => void }) => {
    if (!input.trim()) return;

    const userText = input;
    const userMsg: ChatUiMessage = {
      sender: 'You',
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const streamId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    activeStreamIdRef.current = streamId;
    const assistantMsg: ChatUiMessage = {
      sender: selectedModel === 'deepseek' ? 'DeepSeek' : 'Gemini',
      text: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      streamId
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput('');
    opts.setIsLoading(true);

    try {
      try {
        wsRef.current?.send(JSON.stringify({ type: 'cancel' }));
        wsRef.current?.close();
      } catch {
        // no-op
      }

      const socket = new WebSocket(getWsUrl('/ws/chat'));
      wsRef.current = socket;

      const history = messages.map((m) => ({ role: toChatRole(m.sender), content: m.text }));

      const finalize = () => {
        if (activeStreamIdRef.current === streamId) {
          activeStreamIdRef.current = null;
        }
        opts.setIsLoading(false);
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
            message: userText,
            model: selectedModel,
            history,
            gemini_key: opts.geminiKey || undefined,
            deepseek_key: opts.deepseekKey || undefined
          }));
          resolve();
        };
        socket.onerror = () => reject(new Error('WebSocket connection failed'));
      });

      socket.onmessage = (evt) => {
        try {
          const msg = JSON.parse(String(evt.data)) as any;
          if (msg?.type === 'chunk' && typeof msg.content === 'string') {
            setMessages((prev) =>
              prev.map((m) => (m.streamId === streamId ? { ...m, text: m.text + msg.content } : m))
            );
            return;
          }
          if (msg?.type === 'done') {
            finalize();
            return;
          }
          if (msg?.type === 'error') {
            const message = typeof msg?.error?.message === 'string' ? msg.error.message : 'Streaming failed';
            pushSystemMessage(`Error: ${message}`);
            finalize();
            return;
          }
          if (msg?.type === 'cancelled') {
            finalize();
          }
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        if (activeStreamIdRef.current === streamId) {
          finalize();
        }
      };
    } catch (error: unknown) {
      pushSystemMessage(`Error: ${describeError(error)}`);
      opts.setIsLoading(false);
    }
  };

  return {
    messages,
    setMessages,
    pushMessage,
    pushSystemMessage,
    input,
    setInput,
    selectedModel,
    setSelectedModel,
    sendMessage
  };
}
