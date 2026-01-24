import { useEffect, useMemo, useState } from 'react';

import type { ChatUiMessage } from './useChat';

export type ProjectSession = {
  id: string;
  name: string;
  model: string;
  pinnedFiles: string[];
  messages: ChatUiMessage[];
  updatedAt: number;
};

type SessionsState = {
  currentSessionId: string;
  sessions: ProjectSession[];
};

const STORAGE_KEY = 'project_sessions_v1';

function makeId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function loadState(): SessionsState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as SessionsState;
  } catch {
    return null;
  }
}

function saveState(state: SessionsState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function useSessions() {
  const [state, setState] = useState<SessionsState>(() => {
    const loaded = loadState();
    if (loaded && loaded.sessions.length > 0) return loaded;
    const first: ProjectSession = {
      id: makeId('session'),
      name: 'New Session',
      model: 'gemini',
      pinnedFiles: [],
      messages: [],
      updatedAt: Date.now()
    };
    return { currentSessionId: first.id, sessions: [first] };
  });

  useEffect(() => {
    saveState(state);
  }, [state]);

  const currentSession = useMemo(() => {
    return state.sessions.find((s) => s.id === state.currentSessionId) || state.sessions[0];
  }, [state.currentSessionId, state.sessions]);

  const setCurrentSessionId = (id: string) => {
    setState((prev) => ({ ...prev, currentSessionId: id }));
  };

  const createSession = (name?: string) => {
    const session: ProjectSession = {
      id: makeId('session'),
      name: name || 'New Session',
      model: 'gemini',
      pinnedFiles: [],
      messages: [],
      updatedAt: Date.now()
    };
    setState((prev) => ({
      currentSessionId: session.id,
      sessions: [session, ...prev.sessions]
    }));
  };

  const renameSession = (id: string, name: string) => {
    setState((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s) => (s.id === id ? { ...s, name, updatedAt: Date.now() } : s))
    }));
  };

  const updateSession = (id: string, patch: Partial<ProjectSession>) => {
    setState((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s) => (s.id === id ? { ...s, ...patch, updatedAt: Date.now() } : s))
    }));
  };

  return {
    sessions: state.sessions,
    currentSessionId: state.currentSessionId,
    currentSession,
    setCurrentSessionId,
    createSession,
    renameSession,
    updateSession
  };
}

