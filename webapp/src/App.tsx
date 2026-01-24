import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type * as MonacoEditor from 'monaco-editor';
import { AnimatePresence, motion } from 'framer-motion';
import './App.css';
import {
  getStorageMode,
  setStorageMode,
  setToken as persistToken,
  clearToken as removeToken,
  getToken,
  setCredentials,
  getCredentials,
  clearCredentials
} from './utils/authStorage';
import MonacoWrapper from './components/IDE/MonacoWrapper';
import FileExplorer from './components/IDE/FileExplorer';
import StatusBar from './components/IDE/StatusBar';
import DiffViewer from './components/IDE/DiffViewer';
import { EvolveAI, LivingDocumentation } from './evolve';
import PullRequestPanel, { type PullRequest, type PullRequestFile } from './components/IDE/PullRequestPanel';
import { AgentLoop } from './agent/AgentLoop';
import { readJsonResponse } from './utils/apiResponse';

interface Message {
  sender: string;
  text: string;
  timestamp: string;
}

interface FileEntry {
  name: string;
  type: 'file' | 'directory';
  path: string;
}
function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function asPullRequestStatus(value: unknown): PullRequest['status'] {
  if (value === 'open' || value === 'closed' || value === 'merged' || value === 'approved') return value;
  return 'open';
}

function asPullRequestFileStatus(value: unknown): PullRequestFile['status'] {
  if (value === 'added' || value === 'modified' || value === 'deleted' || value === 'renamed') return value;
  return 'modified';
}

function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function formatExpiry(exp?: number | null): string {
  if (!exp || !Number.isFinite(exp)) return 'Unknown expiry';
  const date = new Date(exp * 1000);
  return date.toLocaleString();
}

function formatCountdown(exp?: number | null): string {
  if (!exp || !Number.isFinite(exp)) return 'No expiry';
  const diffMs = exp * 1000 - Date.now();
  if (diffMs <= 0) return 'Expired';
  const minutes = Math.floor(diffMs / 60000);
  const seconds = Math.floor((diffMs % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

function toPullRequest(value: unknown): PullRequest | null {
  if (!value || typeof value !== 'object') return null;
  const v = value as Record<string, unknown>;
  const filesValue = v.files;
  const filesArray = Array.isArray(filesValue) ? filesValue : [];

  const files: PullRequestFile[] = filesArray
    .filter((entry) => entry && typeof entry === 'object')
    .map((entry) => {
      const e = entry as Record<string, unknown>;
      return {
        path: asString(e.path),
        status: asPullRequestFileStatus(e.status),
        additions: asNumber(e.additions),
        deletions: asNumber(e.deletions),
        originalContent: asString(e.original_content ?? e.originalContent),
        modifiedContent: asString(e.modified_content ?? e.modifiedContent)
      };
    });

  const maybeAi = v.aiAnalysis;
  const aiAnalysis =
    maybeAi && typeof maybeAi === 'object'
      ? (maybeAi as { summary?: unknown; risks?: unknown; suggestions?: unknown; confidence?: unknown })
      : null;

  return {
    id: asString(v.id),
    title: asString(v.title),
    description: asString(v.description),
    sourceBranch: asString(v.sourceBranch ?? v.source_branch),
    targetBranch: asString(v.targetBranch ?? v.target_branch),
    author: asString(v.author),
    createdAt: asString(v.createdAt ?? v.created_at),
    status: asPullRequestStatus(v.status),
    files,
    aiAnalysis: aiAnalysis
      ? {
          summary: asString(aiAnalysis.summary),
          risks: Array.isArray(aiAnalysis.risks) ? (aiAnalysis.risks.filter((r) => typeof r === 'string') as string[]) : [],
          suggestions: Array.isArray(aiAnalysis.suggestions)
            ? (aiAnalysis.suggestions.filter((s) => typeof s === 'string') as string[])
            : [],
          confidence: asNumber(aiAnalysis.confidence)
        }
      : undefined
  };
}

type ChatApiResponse = Partial<Message> & Record<string, unknown>;

const API_BASE =
  (import.meta as { env: Record<string, string | undefined> }).env?.VITE_API_BASE?.replace(/\/$/, '') ||
  '';
const GOOGLE_CONFIGURED = Boolean(
  (import.meta as { env: Record<string, string | undefined> }).env?.VITE_GOOGLE_CLIENT_ID
);
const GITHUB_CONFIGURED = Boolean(
  (import.meta as { env: Record<string, string | undefined> }).env?.VITE_GITHUB_CLIENT_ID
);
const AUDIT_STORAGE_KEY = 'window-aichat:auth-audit';
const AUDIT_PERSIST_KEY = 'window-aichat:auth-audit-persist';
const REFRESH_COOLDOWN_MS = 60_000;
const EXPIRY_WARNING_SECONDS = 300;

async function readErrorText(res: Response): Promise<string> {
  try {
    const text = await res.text();
    return text || `${res.status} ${res.statusText}`;
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}

function toMessage(obj: unknown, fallbackSender = 'System'): Message {
  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if (!obj || typeof obj !== 'object') {
    return { sender: fallbackSender, text: String(obj ?? ''), timestamp: now };
  }
  const anyObj = obj as ChatApiResponse;
  return {
    sender: typeof anyObj.sender === 'string' ? anyObj.sender : fallbackSender,
    text: typeof anyObj.text === 'string' ? anyObj.text : JSON.stringify(anyObj),
    timestamp: typeof anyObj.timestamp === 'string' ? anyObj.timestamp : now
  };
}

function App() {
  // Chat State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sendAbortRef = useRef<AbortController | null>(null);

  // Settings State
  const [geminiKey, setGeminiKey] = useState(localStorage.getItem('gemini_key') || '');
  const [deepseekKey, setDeepseekKey] = useState(localStorage.getItem('deepseek_key') || '');
  const [githubToken, setGithubToken] = useState(localStorage.getItem('github_token') || '');
  const [repoUrl, setRepoUrl] = useState(localStorage.getItem('repo_url') || '');
  const [selectedModel, setSelectedModel] = useState('gemini');
  const [showSettings, setShowSettings] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authStorageMode, setAuthStorageMode] = useState<'local' | 'session'>(getStorageMode());
  const [authToken, setAuthToken] = useState(getToken());
  const [authPayload, setAuthPayload] = useState<Record<string, unknown> | null>(decodeJwt(getToken()));
  const [authError, setAuthError] = useState<string | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [manualToken, setManualToken] = useState('');
  const [authToast, setAuthToast] = useState<string | null>(null);
  const [authTelemetry, setAuthTelemetry] = useState<{ count: number; lastAt?: string }>(() => ({ count: 0 }));
  const [authAuditLog, setAuthAuditLog] = useState<Array<{ time: string; context: string }>>(() => {
    const raw = localStorage.getItem(AUDIT_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Array<{ time: string; context: string }>) : [];
  });
  const [persistAuthAudit, setPersistAuthAudit] = useState(() => localStorage.getItem(AUDIT_PERSIST_KEY) === 'true');
  const [authCountdown, setAuthCountdown] = useState(() => formatCountdown(decodeJwt(getToken())?.exp as number | null));
  const [showAuthDashboard, setShowAuthDashboard] = useState(false);
  const [showTokenPlain, setShowTokenPlain] = useState(false);
  const [rateLimitWarnings, setRateLimitWarnings] = useState<Array<{ time: string; message: string }>>([]);
  const [authHealthStatus, setAuthHealthStatus] = useState<'ok' | 'error' | 'unknown'>('unknown');
  const [refreshCooldownUntil, setRefreshCooldownUntil] = useState<number | null>(null);
  const expiryWarningRef = useRef<number | null>(null);

  // File System & Editor State
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('// Select a file to edit');
  const editorRef = useRef<MonacoEditor.editor.IStandaloneCodeEditor | null>(null);
  const [editorLine, setEditorLine] = useState(1);
  const [editorColumn, setEditorColumn] = useState(1);

  // Panel Visibility State
  const [activeMobilePanel, setActiveMobilePanel] = useState('editor');

  // Pull Request State
  const [showPRPanel, setShowPRPanel] = useState(false);
  const [currentPR, setCurrentPR] = useState<PullRequest | null>(null);
  const [showDiffViewer, setShowDiffViewer] = useState(false);
  const diffOriginalContent = '';
  const diffModifiedContent = '';
  const diffFileName = '';

  // EvolveAI State
  const [showEvolveAI, setShowEvolveAI] = useState(false);
  const [showLivingDocs, setShowLivingDocs] = useState(false);
  const [showAutonomousModal, setShowAutonomousModal] = useState(false);

  // Autonomous Mode State
  const [autonomousTask, setAutonomousTask] = useState('');
  const [isAutonomousRunning, setIsAutonomousRunning] = useState(false);
  const [autonomousLogs, setAutonomousLogs] = useState<string[]>([]);
  const autonomousAbortRef = useRef<AbortController | null>(null);
  const [autonomousAuthError, setAutonomousAuthError] = useState<string | null>(null);

  const autonomousPresets = [
    { label: 'Refactor module', task: 'Refactor the currently active module for readability and performance.' },
    { label: 'Fix errors', task: 'Scan the project for TypeScript errors and fix them.' },
    { label: 'Generate docs', task: 'Generate or refresh documentation for the current module.' }
  ];

  const authExpiry = useMemo(() => {
    const exp = authPayload?.exp;
    return typeof exp === 'number' ? exp : null;
  }, [authPayload]);

  const isAuthExpired = Boolean(authExpiry && authExpiry * 1000 <= Date.now());
  const authRole = useMemo(() => {
    const role = authPayload?.role ?? authPayload?.scope ?? authPayload?.roles;
    if (!role) return 'standard';
    if (Array.isArray(role)) return role.join(', ');
    return String(role);
  }, [authPayload]);

  const isAuthValid = Boolean(authToken && authPayload && (!authExpiry || authExpiry * 1000 > Date.now()));

  const setToken = (token: string) => {
    persistToken(token, authStorageMode);
    setAuthToken(token);
    setAuthPayload(decodeJwt(token));
  };

  const clearToken = () => {
    removeToken();
    clearCredentials();
    setAuthToken('');
    setAuthPayload(null);
  };

  const reportUnauthorized = (context: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setAuthTelemetry(prev => ({ count: prev.count + 1, lastAt: timestamp }));
    setAuthAuditLog(prev => [{ time: timestamp, context }, ...prev].slice(0, 20));
    setAuthToast(`Login required for ${context}.`);
    setTimeout(() => setAuthToast(null), 3500);
  };

  const ensureAuth = (context: string) => {
    if (isAuthValid) return true;
    setAuthError(`Authentication required to ${context}.`);
    setShowAuthModal(true);
    reportUnauthorized(context);
    setMessages(prev => [...prev, {
      sender: 'System',
      text: `Authentication required to ${context}. Please log in or paste a token.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
    return false;
  };

  const handleAuthFailure = async (res: Response, context: string) => {
    if (res.status !== 401 && res.status !== 429) return false;
    const errorText = await readErrorText(res);
    if (res.status === 429) {
      const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const resetHeader = res.headers.get('X-RateLimit-Reset');
      const resetSeconds = resetHeader ? Number(resetHeader) : null;
      if (resetSeconds && !Number.isNaN(resetSeconds)) {
        setRefreshCooldownUntil(Date.now() + resetSeconds * 1000);
      } else {
        setRefreshCooldownUntil(Date.now() + REFRESH_COOLDOWN_MS);
      }
      setRateLimitWarnings(prev => [{ time: timestamp, message: errorText }, ...prev].slice(0, 10));
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Rate limit hit (${context}): ${errorText}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
      return true;
    }
    setAuthError(errorText);
    setShowAuthModal(true);
    reportUnauthorized(context);
    setMessages(prev => [...prev, {
      sender: 'System',
      text: `Authentication required (${context}): ${errorText}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
    return true;
  };

  const submitAuth = async () => {
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/${authMode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername.trim(), password: authPassword })
      });
      if (!res.ok) {
        const errorText = await readErrorText(res);
        setAuthError(errorText);
        return;
      }
      const data = await readJsonResponse<{ token?: string }>(res);
      if (data.token) {
        setToken(data.token);
        setCredentials(authUsername.trim(), authPassword, authStorageMode);
        setShowAuthModal(false);
        setAuthPassword('');
      } else {
        setAuthError('No token returned by server.');
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Failed to authenticate.');
    }
  };

  const saveManualToken = () => {
    if (!manualToken.trim()) {
      setAuthError('Paste a token before saving.');
      return;
    }
    setToken(manualToken.trim());
    setManualToken('');
    setShowTokenModal(false);
    setShowAuthModal(false);
    setAuthError(null);
  };

  const refreshToken = async () => {
    setAuthError(null);
    if (refreshCooldownUntil && Date.now() < refreshCooldownUntil) {
      setAuthToast('Refresh cooldown active. Please wait a moment.');
      setTimeout(() => setAuthToast(null), 2500);
      return;
    }
    const creds = getCredentials();
    if (!creds) {
      setAuthError('No stored credentials. Please login again.');
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: creds.username, password: creds.password })
      });
      if (!res.ok) {
        const errorText = await readErrorText(res);
        setAuthError(errorText);
        setRefreshCooldownUntil(Date.now() + REFRESH_COOLDOWN_MS);
        return;
      }
      const data = (await res.json()) as { token?: string };
      if (data.token) {
        setToken(data.token);
        setRefreshCooldownUntil(null);
      } else {
        setAuthError('No token returned by server.');
        setRefreshCooldownUntil(Date.now() + REFRESH_COOLDOWN_MS);
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Failed to refresh token.');
      setRefreshCooldownUntil(Date.now() + REFRESH_COOLDOWN_MS);
    }
  };

  const copyText = async (text: string, successMessage: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setAuthToast(successMessage);
    } catch {
      setAuthToast('Failed to copy to clipboard.');
    } finally {
      setTimeout(() => setAuthToast(null), 2500);
    }
  };

  const copyToken = async () => {
    if (!authToken) {
      setAuthToast('No token to copy.');
      setTimeout(() => setAuthToast(null), 2500);
      return;
    }
    await copyText(authToken, 'Token copied to clipboard.');
  };

  const copyMaskedToken = async () => {
    if (!authToken) {
      setAuthToast('No token to copy.');
      setTimeout(() => setAuthToast(null), 2500);
      return;
    }
    const masked = authToken.length > 12
      ? `${authToken.slice(0, 6)}...${authToken.slice(-4)}`
      : authToken.replace(/.(?=.{2})/g, '*');
    await copyText(masked, 'Masked token copied.');
  };

  const toggleStorageMode = () => {
    const nextMode = authStorageMode === 'local' ? 'session' : 'local';
    setAuthStorageMode(nextMode);
    setStorageMode(nextMode);
    if (authToken) {
      persistToken(authToken, nextMode);
    }
  };

  const oauthLogin = async (provider: 'google' | 'github') => {
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/login/${provider}`);
      if (!res.ok) {
        const errorText = await readErrorText(res);
        setAuthError(errorText);
        return;
      }
      const data = await readJsonResponse<{ url?: string; error?: string }>(res);
      if (data.error) {
        setAuthError(data.error);
        return;
      }
      if (data.url && /^https?:\/\//.test(data.url)) {
        window.location.href = data.url;
      } else {
        setAuthError('OAuth URL missing or invalid.');
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Failed to start OAuth flow.');
    }
  };

  const logoutEverywhere = () => {
    clearToken();
    setAuthAuditLog([]);
    setRateLimitWarnings([]);
    localStorage.removeItem(AUDIT_STORAGE_KEY);
    setAuthToast('Signed out from all sessions.');
    setTimeout(() => setAuthToast(null), 2500);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const renderedMessages = useMemo(() => (
    <AnimatePresence initial={false}>
      {messages.map((msg, index) => {
        const isUser = msg.sender === 'You';
        const isSystem = msg.sender === 'System';
        const isTool = msg.sender === 'AI Tool' || msg.sender === 'AI Analysis';
        const messageClass = isUser
          ? 'message user'
          : isSystem
            ? 'message ai message-system'
            : isTool
              ? 'message ai message-tool'
              : 'message ai';

        return (
        <motion.div
          key={`${msg.timestamp}-${index}`}
          className={messageClass}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          layout
        >
          <div className="message-header">
            <span className="sender">{msg.sender}</span>
            <span className="time">{msg.timestamp}</span>
          </div>
          <div className="message-content">
            {msg.text}
          </div>
        </motion.div>
      );
      })}
    </AnimatePresence>
  ), [messages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const url = new URL(window.location.href);
    const tokenParam = url.searchParams.get('token');
    if (tokenParam) {
      setToken(tokenParam);
      url.searchParams.delete('token');
      window.history.replaceState({}, '', url.toString());
    }
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setAuthCountdown(formatCountdown(authExpiry));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [authExpiry]);

  useEffect(() => {
    if (authExpiry) {
      const timeLeft = authExpiry * 1000 - Date.now();
      if (timeLeft <= 0) {
        if (!refreshCooldownUntil || Date.now() >= refreshCooldownUntil) {
          void refreshToken();
        }
      } else if (timeLeft <= EXPIRY_WARNING_SECONDS * 1000 && expiryWarningRef.current !== authExpiry) {
        expiryWarningRef.current = authExpiry;
        setAuthToast('Token expiring soon. Refresh or re-authenticate.');
        setTimeout(() => setAuthToast(null), 3500);
      }
    }
  }, [authExpiry, refreshCooldownUntil]);

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const healthRes = await fetch(`${API_BASE}/health`);
        if (healthRes.ok) {
          setAuthHealthStatus('ok');
          return;
        }
        const rootRes = await fetch(`${API_BASE}/`);
        setAuthHealthStatus(rootRes.ok ? 'ok' : 'error');
      } catch {
        setAuthHealthStatus('error');
      }
    };
    void loadHealth();
  }, []);

  useEffect(() => {
    if (persistAuthAudit) {
      localStorage.setItem(AUDIT_STORAGE_KEY, JSON.stringify(authAuditLog));
    }
  }, [authAuditLog, persistAuthAudit]);

  useEffect(() => {
    localStorage.setItem(AUDIT_PERSIST_KEY, String(persistAuthAudit));
    if (!persistAuthAudit) {
      localStorage.removeItem(AUDIT_STORAGE_KEY);
    }
  }, [persistAuthAudit]);

  useEffect(() => {
    void fetchFiles();
  }, []);

  useEffect(() => {
    return () => {
      sendAbortRef.current?.abort();
    };
  }, []);

  const fetchFiles = async () => {
    try {
      if (!ensureAuth('list files')) return;
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/fs/list`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      if (await handleAuthFailure(res, 'listing files')) return;
      if (res.ok) {
        const data = await readJsonResponse<FileEntry[]>(res);
        setFiles(data);
      }
    } catch (error: unknown) {
      console.error("Failed to fetch files", error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error fetching files: ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    }
  };

  const applyAutonomousPreset = (task: string) => {
    setAutonomousTask(task);
  };

  const openFile = async (path: string) => {
    try {
      if (!ensureAuth('read files')) return;
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/fs/read`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ path })
      });
      if (await handleAuthFailure(res, 'reading files')) return;
      if (res.ok) {
        const data = await readJsonResponse<{ content: string }>(res);
        setFileContent(data.content);
        setActiveFile(path);
        setActiveMobilePanel('editor'); // Switch to editor on file open
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Opened ${path} successfully.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      } else {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Failed to read file: ${errorText}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to read file", error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Failed to read file: ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }
  };

  const saveFile = async () => {
    if (!activeFile) { return; }
    const content = editorRef.current ? editorRef.current.getValue() : fileContent;
    
    try {
      if (!ensureAuth('write files')) return;
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/fs/write`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ path: activeFile, content })
      });
      if (await handleAuthFailure(res, 'writing files')) return;
      if (res.ok) {
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Saved ${activeFile} successfully.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      } else {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Failed to save file: ${errorText}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to save file", error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Failed to save file: ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }
  };

  const runTool = async (tool: string) => {
    if (!editorRef.current) { return; }
    
    const model = editorRef.current.getModel();
    const selectionRange = editorRef.current.getSelection() || null;
    const selection = model && selectionRange ? model.getValueInRange(selectionRange) : "";
    const code = selection || editorRef.current.getValue();
    
    if (!code.trim()) {
      setMessages(prev => [...prev, {
        sender: 'System',
        text: 'Please select code or open a file first.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
      return;
    }

    setIsLoading(true);
    setMessages(prev => [...prev, {
      sender: 'System',
      text: `Running ${tool}...`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/tool`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool,
          code,
          gemini_key: geminiKey
        })
      });

      if (!res.ok) {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Error running tool ${tool}: ${errorText}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
        return;
      }

      const data = await readJsonResponse<{ result?: string }>(res);
      setMessages(prev => [...prev, {
        sender: 'AI Tool',
        text: typeof data?.result === 'string' ? data.result : JSON.stringify(data),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `${tool} completed successfully.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } catch (error: unknown) {
      console.error(`Failed to run tool ${tool}`, error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error running tool ${tool}: ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditorDidMount = (editor: MonacoEditor.editor.IStandaloneCodeEditor, monaco: typeof MonacoEditor) => {
    editorRef.current = editor;
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      void saveFile();
    });

    editor.onDidChangeCursorPosition((e) => {
      setEditorLine(e.position.lineNumber);
      setEditorColumn(e.position.column);
    });
  };

  const saveSettings = () => {
    localStorage.setItem('gemini_key', geminiKey);
    localStorage.setItem('deepseek_key', deepseekKey);
    localStorage.setItem('github_token', githubToken);
    localStorage.setItem('repo_url', repoUrl);
    setShowSettings(false);
    setMessages(prev => [...prev, {
      sender: 'System',
      text: 'Settings saved successfully.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
  };

  const startAutonomousMode = async () => {
    if (!autonomousTask.trim() || isAutonomousRunning) return;
    if (!ensureAuth('run autonomous tasks')) return;
    if (refreshCooldownUntil && Date.now() < refreshCooldownUntil) {
      setMessages(prev => [...prev, {
        sender: 'System',
        text: 'Rate limit cooldown active. Try again shortly.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
      return;
    }

    const abortController = new AbortController();
    autonomousAbortRef.current?.abort();
    autonomousAbortRef.current = abortController;
    setIsAutonomousRunning(true);
    setAutonomousLogs([]);
    setAutonomousAuthError(null);

    setMessages(prev => [...prev, {
      sender: 'System',
      text: `Autonomous mode started: ${autonomousTask}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);

    try {
      await AgentLoop.runTask(autonomousTask, {
        apiBase: API_BASE,
        geminiKey,
        deepseekKey,
        githubToken,
        repoUrl,
        abortSignal: abortController.signal,
        onLog: (message) => {
          if (abortController.signal.aborted) return;
          setAutonomousLogs(prev => [...prev, message]);
          setMessages(prev => [...prev, {
            sender: 'AI Tool',
            text: `[Autonomous] ${message}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }]);
        },
        onEvent: (event) => {
          if (abortController.signal.aborted) return;
          if (event.stage === 'persist' && event.message.toLowerCase().includes('authentication')) {
            setAutonomousAuthError('Authentication required to persist files. Add your token in Settings.');
            setShowAuthModal(true);
          }
          setMessages(prev => [...prev, {
            sender: 'System',
            text: `[Autonomous] ${event.message}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }]);
        },
        context: {
          currentFile: activeFile ?? undefined,
          currentFileContent: activeFile ? fileContent : undefined
        },
        onSuccess: (filename) => {
          setMessages(prev => [...prev, {
            sender: 'System',
            text: `Autonomous task completed. Output: ${filename}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }]);
        }
      });
    } catch (error) {
      if (!abortController.signal.aborted) {
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Autonomous mode failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      }
    } finally {
      setIsAutonomousRunning(false);
    }
  };

  const stopAutonomousMode = () => {
    autonomousAbortRef.current?.abort();
    setIsAutonomousRunning(false);
    setMessages(prev => [...prev, {
      sender: 'System',
      text: 'Autonomous mode stopped.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) { return; }

    sendAbortRef.current?.abort();
    const abortController = new AbortController();
    sendAbortRef.current = abortController;

    const userMsg: Message = {
      sender: 'You',
      text: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortController.signal,
        body: JSON.stringify({
          message: userMsg.text,
          model: selectedModel,
          repo_url: repoUrl,
          gemini_key: geminiKey,
          deepseek_key: deepseekKey,
          github_token: githubToken
        })
      });

      if (!res.ok) {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Error: ${errorText}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
        return;
      }

      const data = await res.json();
      setMessages(prev => [...prev, toMessage(data, selectedModel === 'deepseek' ? 'DeepSeek' : 'Gemini')]);
      setMessages(prev => [...prev, {
        sender: 'System',
        text: 'Response delivered successfully.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } catch (error: unknown) {
      if (abortController.signal.aborted) {
        setMessages(prev => [...prev, {
          sender: 'System',
          text: 'Request cancelled.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
        return;
      }
      console.error("Failed to send message", error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error: ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const cloneRepo = async () => {
    if (!repoUrl) {
      setMessages(prev => [...prev, {
        sender: 'System',
        text: 'Please enter a GitHub repository URL before cloning.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
      return;
    }
    setIsLoading(true);
    setMessages(prev => [...prev, {
      sender: 'System',
      text: `Cloning ${repoUrl}...`,
      timestamp: new Date().toLocaleTimeString()
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/git/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl })
      });

      const data = await res.json();
      if (res.ok) {
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Clone successful: ${data.message}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: 'Repository ready. Files refreshed successfully.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
        void fetchFiles(); // Refresh file explorer
      } else {
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Clone failed: ${data.detail || data.message}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to clone repo", error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error cloning repo: ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const uploadFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setMessages(prev => [...prev, {
      sender: 'System',
      text: `Uploading ${file.name}...`,
      timestamp: new Date().toLocaleTimeString()
    }]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/api/fs/upload`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (res.ok) {
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Upload successful: ${data.message}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: 'Upload complete. File explorer refreshed.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
        void fetchFiles(); // Refresh file explorer
      } else {
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Upload failed: ${data.detail || data.message}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to upload file", error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error uploading file: ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Pull Request Functions
  const openPullRequest = async (prId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/pr/${prId}`);
      if (res.ok) {
        const data = await res.json();
        const pr = toPullRequest((data as Record<string, unknown>).pull_request);
        if (!pr) {
          setMessages(prev => [...prev, {
            sender: 'System',
            text: 'Failed to load pull request: invalid response payload.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }]);
          return;
        }
        setCurrentPR(pr);
        setShowPRPanel(true);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: 'Pull request loaded successfully.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      } else {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Failed to load pull request: ${errorText}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to load pull request", error);
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Failed to load pull request: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }
  };

  const analyzePRWithAI = async (prId: string) => {
    if (!currentPR) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/pr/${prId}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pr_id: prId,
          gemini_key: geminiKey
        })
      });

      if (res.ok) {
        const data = await res.json();
        setCurrentPR(prev => prev ? { ...prev, aiAnalysis: data.analysis } : null);
        setMessages(prev => [...prev, {
          sender: 'AI Analysis',
          text: `PR Analysis completed:\n\n${data.analysis.summary}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      } else {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `AI Analysis failed: ${errorText}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to analyze PR", error);
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error analyzing PR: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    }
  };

  const approvePR = async (prId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/pr/${prId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pr_id: prId,
          action: 'approve'
        })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          sender: 'System',
          text: data.message,
          timestamp: new Date().toLocaleTimeString()
        }]);
        if (currentPR) {
          setCurrentPR({ ...currentPR, status: 'approved' });
        }
        setMessages(prev => [...prev, {
          sender: 'System',
          text: 'Pull request approved successfully.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      } else {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Failed to approve PR: ${errorText}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to approve PR", error);
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error approving PR: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    }
  };

  const requestChanges = async (prId: string, feedback: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/pr/${prId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pr_id: prId,
          action: 'request_changes',
          feedback
        })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          sender: 'System',
          text: data.message,
          timestamp: new Date().toLocaleTimeString()
        }]);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: 'Review feedback submitted successfully.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      } else {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Failed to request changes: ${errorText}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to request changes", error);
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error requesting changes: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    }
  };

  const mergePR = async (prId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/pr/${prId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pr_id: prId,
          action: 'merge'
        })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          sender: 'System',
          text: data.message,
          timestamp: new Date().toLocaleTimeString()
        }]);
        if (currentPR) {
          setCurrentPR({ ...currentPR, status: 'merged' });
        }
        setMessages(prev => [...prev, {
          sender: 'System',
          text: 'Pull request merged successfully.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      } else {
        const errorText = await readErrorText(res);
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Failed to merge PR: ${errorText}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (error: unknown) {
      console.error("Failed to merge PR", error);
      setMessages(prev => [...prev, {
        sender: 'System',
        text: `Error merging PR: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    }
  };

  const getLanguage = (filename: string | null) => {
    if (!filename) return 'plaintext';
    const ext = filename.split('.').pop();
    switch (ext) {
      case 'js': return 'javascript';
      case 'ts': return 'typescript';
      case 'tsx': return 'typescript';
      case 'jsx': return 'javascript';
      case 'py': return 'python';
      case 'html': return 'html';
      case 'css': return 'css';
      case 'json': return 'json';
      case 'md': return 'markdown';
      default: return 'plaintext';
    }
  };

  // Resizable Panel Logic
  const sidebarRef = useRef<HTMLDivElement>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const [sidebarWidth, setSidebarWidth] = useState(250); // Default width
  const [chatWidth, setChatWidth] = useState(350); // Default width
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);
  const [isResizingChat, setIsResizingChat] = useState(false);

  const startResizeSidebar = useCallback((e: React.MouseEvent) => {
    setIsResizingSidebar(true);
    e.preventDefault();
  }, []);

  const startResizeChat = useCallback((e: React.MouseEvent) => {
    setIsResizingChat(true);
    e.preventDefault();
  }, []);

  const stopResize = useCallback(() => {
    setIsResizingSidebar(false);
    setIsResizingChat(false);
  }, []);

  const resizePanel = useCallback((e: MouseEvent) => {
    if (isResizingSidebar && sidebarRef.current) {
      const newWidth = e.clientX;
      if (newWidth > 150 && newWidth < window.innerWidth / 2) {
        setSidebarWidth(newWidth);
      }
    } else if (isResizingChat && chatRef.current) {
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth > 150 && newWidth < window.innerWidth / 2) {
        setChatWidth(newWidth);
      }
    }
  }, [isResizingSidebar, isResizingChat]);

  useEffect(() => {
    window.addEventListener('mousemove', resizePanel);
    window.addEventListener('mouseup', stopResize);
    return () => {
      window.removeEventListener('mousemove', resizePanel);
      window.removeEventListener('mouseup', stopResize);
    };
  }, [resizePanel, stopResize]);
  return (
    <div className="app-container">
      {authToast && (
        <div className="auth-toast" onClick={() => setShowAuthModal(true)}>
          {authToast}
        </div>
      )}

      {/* Auth Dashboard Modal */}
      {showAuthDashboard && (
        <div className="modal-overlay">
          <div className="modal-content auth-modal">
            <div className="modal-header">
              <h3>📊 Auth Dashboard</h3>
              <button onClick={() => setShowAuthDashboard(false)} className="close-btn">✕</button>
            </div>
            <div className="auth-modal-body">
              <div className="auth-dashboard-grid">
                <div className="auth-card">
                  <h4>Status</h4>
                  <p>{isAuthValid ? 'Authenticated' : 'Not authenticated'}</p>
                  <p>Role: {authRole}</p>
                </div>
                <div className="auth-card">
                  <h4>Expiry</h4>
                  <p>{formatExpiry(authExpiry)}</p>
                  <p>{authCountdown}</p>
                </div>
                <div className="auth-card">
                  <h4>Unauthorized Attempts</h4>
                  <p>{authTelemetry.count}</p>
                  <p>Last: {authTelemetry.lastAt ?? '—'}</p>
                </div>
                <div className="auth-card">
                  <h4>Rate Limits</h4>
                  <p>{rateLimitWarnings.length}</p>
                </div>
              </div>
              <div className="auth-sparkline">
                {authAuditLog.length === 0 ? 'No activity yet.' : authAuditLog.map((_, idx) => (
                  <span key={idx} style={{ height: `${8 + idx * 2}px` }} />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Sidebar */}
      <div className={`sidebar-area ${activeMobilePanel === 'sidebar' ? 'visible' : ''}`} style={{ width: sidebarWidth }} ref={sidebarRef}>
        <div className="sidebar-header">
          <h2>Window-AIChat</h2>
          <span className={`auth-health ${authHealthStatus}`}>{authHealthStatus === 'ok' ? 'API ✓' : authHealthStatus === 'error' ? 'API ✕' : 'API …'}</span>
          <span className={`auth-oauth-status ${(GOOGLE_CONFIGURED && GITHUB_CONFIGURED) ? 'ready' : 'missing'}`}>
            OAuth {GOOGLE_CONFIGURED && GITHUB_CONFIGURED ? 'Ready' : 'Missing'}
          </span>
          <span className="auth-role">{authRole}</span>
          <span className="auth-countdown">{authCountdown}</span>
          <button
            className={`auth-badge ${isAuthValid ? 'auth-ok' : 'auth-missing'}`}
            onClick={() => setShowAuthModal(true)}
            title={isAuthValid ? 'Authenticated' : 'Authentication required'}
          >
            {isAuthValid ? 'Auth ✓' : 'Auth ✕'}
          </button>
        </div>

        <div className="sidebar-section">
          <button onClick={() => setShowAuthModal(true)}>
            🔐 Login / Register
          </button>
          <button onClick={() => setShowAuthDashboard(true)}>
            📊 Auth Dashboard
          </button>
          <button onClick={() => setShowTokenModal(true)}>
            🧾 Paste Token
          </button>
          {isAuthValid && (
            <button onClick={clearToken}>
              🚪 Logout
            </button>
          )}
          <button onClick={() => setShowSettings(!showSettings)}>
            ⚙ Settings
          </button>
          <button onClick={() => openPullRequest('sample-pr-123')}>
            🔄 Pull Requests
          </button>
          <button onClick={() => setShowDiffViewer(!showDiffViewer)}>
            📊 Compare Files
          </button>
          <button onClick={() => setShowEvolveAI(!showEvolveAI)}>
            🧬 EvolveAI
          </button>
          <button onClick={() => setShowLivingDocs(!showLivingDocs)}>
            📚 Living Docs
          </button>
          <button onClick={() => setShowAutonomousModal(true)}>
            🤖 Autonomous Mode
          </button>
        </div>

        {showSettings && (
          <div className="settings-panel">
            <h3>Configuration</h3>
            <input
              type="password"
              placeholder="Gemini API Key"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
            />
            <input
              type="password"
              placeholder="DeepSeek API Key"
              value={deepseekKey}
              onChange={(e) => setDeepseekKey(e.target.value)}
            />
            <input
              type="password"
              placeholder="GitHub Token"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
            />
            <input
              type="text"
              placeholder="GitHub Repo URL"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
            <button className="save-btn" onClick={saveSettings}>Save</button>
          </div>
        )}

        <div className="sidebar-section" title={!isAuthValid ? 'Login required to manage workspace files.' : undefined}>
          <button onClick={() => void cloneRepo()} disabled={isLoading || !repoUrl || !isAuthValid}>
            {isLoading ? 'Cloning...' : 'Clone GitHub Repo'}
          </button>
          <input
            type="file"
            id="upload-zip"
            style={{ display: 'none' }}
            onChange={(e) => void uploadFile(e)}
            disabled={isLoading || !isAuthValid}
          />
          <button onClick={() => document.getElementById('upload-zip')?.click()} disabled={isLoading || !isAuthValid}>
            Upload Zip/File
          </button>
        </div>

        <FileExplorer
          files={files}
          activeFile={activeFile}
          onFileClick={openFile}
          onRefresh={() => void fetchFiles()}
          onCloneRepo={() => void cloneRepo()}
          onUploadFile={(e) => void uploadFile(e)}
          isLoading={isLoading}
          repoUrl={repoUrl}
        />
        {!isAuthValid && (
          <div className="auth-lock">
            <div>
              <strong>Login required</strong>
              <p>Authenticate to access your workspace files.</p>
            </div>
            <button onClick={() => setShowAuthModal(true)}>Login</button>
          </div>
        )}
        <div className="resizer-handle" onMouseDown={startResizeSidebar}></div>
      </div>

      {/* Editor Area */}
      <div className={`editor-area ${activeMobilePanel === 'editor' ? 'visible' : ''}`}>
        <div className="editor-header">
          <span className="file-name">{activeFile || 'No file selected'}</span>
          <div className="editor-actions">
            <button onClick={() => void runTool('analyze')} title="Analyze Code">🔍 Analyze</button>
            <button onClick={() => void runTool('explain')} title="Explain Code">📖 Explain</button>
            <button onClick={() => void runTool('refactor')} title="Refactor Code">🛠 Refactor</button>
            <button onClick={() => void runTool('docs')} title="Generate Docs">📝 Docs</button>
            <button className="primary" onClick={() => void saveFile()} disabled={!activeFile}>💾 Save</button>
          </div>
        </div>
        <div className="monaco-wrapper">
          <MonacoWrapper
            fileContent={fileContent}
            activeFile={activeFile}
            onMount={handleEditorDidMount}
            onChange={(value) => setFileContent(value || '')}
          />
        </div>
        <StatusBar activeFile={activeFile} language={getLanguage(activeFile)} line={editorLine} column={editorColumn} />
      </div>

      {/* Chat Area */}
      <div className={`chat-area ${activeMobilePanel === 'chat' ? 'visible' : ''}`} style={{ width: chatWidth }} ref={chatRef}>
        <div className="chat-header">
          <h3>AI Assistant</h3>
          <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
            <option value="gemini">Gemini</option>
            <option value="deepseek">DeepSeek</option>
          </select>
        </div>
        <div className="messages-list">
          {renderedMessages}
          {isLoading && (
            <motion.div
              className="message ai message-loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
            >
              <div className="message-content">Thinking...</div>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void sendMessage();
              }
            }}
            placeholder="Ask AI..."
          />
          <button onClick={() => void sendMessage()} disabled={isLoading}>
            ➤
          </button>
        </div>
        <div className="resizer-handle" onMouseDown={startResizeChat}></div>
      </div>

      {/* Diff Viewer Modal */}
      {showDiffViewer && (
        <div className="modal-overlay">
          <div className="modal-content diff-modal">
            <div className="modal-header">
              <h3>File Comparison</h3>
              <button onClick={() => setShowDiffViewer(false)} className="close-btn">✕</button>
            </div>
            <div className="diff-viewer-container">
              <DiffViewer
                originalContent={diffOriginalContent}
                modifiedContent={diffModifiedContent}
                originalFileName={diffFileName}
                modifiedFileName={diffFileName}
              />
            </div>
          </div>
        </div>
      )}

      {/* Auth Modal */}
      {showAuthModal && (
        <div className="modal-overlay">
          <div className="modal-content auth-modal">
            <div className="modal-header">
              <h3>🔐 Authentication</h3>
              <button onClick={() => setShowAuthModal(false)} className="close-btn">✕</button>
            </div>
            <div className="auth-modal-body">
              <div className="auth-tabs">
                <button
                  className={authMode === 'login' ? 'active' : ''}
                  onClick={() => setAuthMode('login')}
                >
                  Login
                </button>
                <button
                  className={authMode === 'register' ? 'active' : ''}
                  onClick={() => setAuthMode('register')}
                >
                  Register
                </button>
              </div>
              <div className="auth-form">
                <input
                  type="text"
                  placeholder="Username"
                  value={authUsername}
                  onChange={(e) => setAuthUsername(e.target.value)}
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                />
                {authError && <div className="auth-error">{authError}</div>}
                <button className="primary" onClick={() => void submitAuth()}>
                  {authMode === 'login' ? 'Login' : 'Create Account'}
                </button>
              </div>
              <div className="auth-divider">or</div>
              <div className="auth-actions">
                <button onClick={() => void oauthLogin('google')}>
                  Continue with Google
                </button>
                <button onClick={() => void oauthLogin('github')}>
                  Continue with GitHub
                </button>
                <button onClick={() => setShowTokenModal(true)}>
                  Paste Token Manually
                </button>
                <button onClick={() => void refreshToken()}>
                  Refresh Token
                </button>
                <button onClick={logoutEverywhere}>
                  Logout Everywhere
                </button>
              </div>
              <div className="auth-status">
                <span>Status: {isAuthValid ? 'Authenticated' : 'Not authenticated'}</span>
                <span>Expiry: {formatExpiry(authExpiry)}</span>
                <span>Countdown: {authCountdown}</span>
              </div>
              {(!GOOGLE_CONFIGURED || !GITHUB_CONFIGURED) && (
                <div className="auth-oauth-hint">
                  OAuth not configured: set {(!GOOGLE_CONFIGURED && 'VITE_GOOGLE_CLIENT_ID') || ''}{(!GOOGLE_CONFIGURED && !GITHUB_CONFIGURED ? ' & ' : '')}{(!GITHUB_CONFIGURED && 'VITE_GITHUB_CLIENT_ID') || ''} in webapp env.
                </div>
              )}
              {isAuthExpired && (
                <div className="auth-expired">Session expired. Re-authenticate to refresh your token.</div>
              )}
              <div className="auth-telemetry">
                <span>Unauthorized attempts: {authTelemetry.count}</span>
                <span>Last seen: {authTelemetry.lastAt ?? '—'}</span>
              </div>
              <label className="auth-persist">
                <input
                  type="checkbox"
                  checked={persistAuthAudit}
                  onChange={() => setPersistAuthAudit(prev => !prev)}
                />
                Persist audit log
              </label>
              <button className="auth-toggle" onClick={toggleStorageMode}>
                Storage: {authStorageMode === 'local' ? 'Local (persistent)' : 'Session (temporary)'}
              </button>
              <div className="auth-claims">
                <div className="auth-claims-title">JWT Claims</div>
                <pre>{authPayload ? JSON.stringify(authPayload, null, 2) : 'No token claims available.'}</pre>
                <div className="auth-claims-actions">
                  <button onClick={() => void copyToken()}>Copy Token</button>
                  <button onClick={() => void copyText(JSON.stringify(authPayload ?? {}, null, 2), 'Claims JSON copied.')}>Copy Claims JSON</button>
                </div>
              </div>
              <div className="auth-audit">
                <div className="auth-audit-title">Auth Audit Log</div>
                {authAuditLog.length === 0 ? (
                  <span>No unauthorized attempts yet.</span>
                ) : (
                  <ul>
                    {authAuditLog.map((entry, index) => (
                      <li key={`${entry.time}-${index}`}>
                        <span>{entry.time}</span>
                        <span>{entry.context}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {rateLimitWarnings.length > 0 && (
                <div className="auth-rate-limit">
                  <div className="auth-audit-title">Rate Limit Warnings</div>
                  <ul>
                    {rateLimitWarnings.map((entry, index) => (
                      <li key={`${entry.time}-${index}`}>
                        <span>{entry.time}</span>
                        <span>{entry.message}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Token Modal */}
      {showTokenModal && (
        <div className="modal-overlay">
          <div className="modal-content token-modal">
            <div className="modal-header">
              <h3>🧾 Paste Token</h3>
              <button onClick={() => setShowTokenModal(false)} className="close-btn">✕</button>
            </div>
            <div className="auth-modal-body">
              <textarea
                className="token-input"
                rows={4}
                placeholder="Paste JWT token here"
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
              />
              <div className="token-toggle">
                <label>
                  <input
                    type="checkbox"
                    checked={showTokenPlain}
                    onChange={() => setShowTokenPlain((prev) => !prev)}
                  />
                  Show token text
                </label>
              </div>
              {showTokenPlain && authToken && (
                <pre className="token-preview">{authToken}</pre>
              )}
              <div className="token-actions">
                <button onClick={() => void copyToken()} disabled={!authToken}>Copy Token</button>
                <button onClick={() => void copyMaskedToken()} disabled={!authToken}>Copy Masked Token</button>
              </div>
              {authError && <div className="auth-error">{authError}</div>}
              <div className="token-meta">
                <span>Current status: {isAuthValid ? 'Authenticated' : 'Not authenticated'}</span>
                <span>Expiry: {formatExpiry(authExpiry)}</span>
                <span>Countdown: {authCountdown}</span>
              </div>
              <div className="auth-actions">
                <button className="primary" onClick={saveManualToken}>Save Token</button>
                {authToken && (
                  <button onClick={clearToken}>Logout</button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Autonomous Mode Modal */}
      {showAutonomousModal && (
        <div className="modal-overlay">
          <div className="modal-content autonomous-modal">
            <div className="modal-header">
              <h3>🤖 Autonomous Mode</h3>
              <button onClick={() => setShowAutonomousModal(false)} className="close-btn">✕</button>
            </div>
            <div className="autonomous-modal-body">
              <p className="autonomous-description">Describe the task and let the AI execute it end-to-end.</p>
              {autonomousAuthError && (
                <div className="autonomous-warning">{autonomousAuthError}</div>
              )}
              <div className="autonomous-presets">
                {autonomousPresets.map((preset) => (
                  <button key={preset.label} onClick={() => applyAutonomousPreset(preset.task)}>
                    {preset.label}
                  </button>
                ))}
              </div>
              <textarea
                className="autonomous-input"
                value={autonomousTask}
                onChange={(e) => setAutonomousTask(e.target.value)}
                placeholder="Describe the task for autonomous execution..."
                rows={4}
              />
              {!isAuthValid && (
                <div className="autonomous-auth-cta">
                  <span>Authentication required to run autonomous tasks.</span>
                  <button onClick={() => setShowAuthModal(true)}>
                    Login to Continue
                  </button>
                </div>
              )}
              <div className="autonomous-actions">
                <button
                  onClick={() => void startAutonomousMode()}
                  disabled={!autonomousTask.trim() || isAutonomousRunning || !isAuthValid}
                >
                  {isAutonomousRunning ? 'Running…' : 'Start Autonomous'}
                </button>
                <button onClick={stopAutonomousMode} disabled={!isAutonomousRunning}>
                  Stop
                </button>
              </div>
              <div className="autonomous-log">
                {autonomousLogs.length === 0 ? (
                  <span className="autonomous-empty">No autonomous logs yet.</span>
                ) : (
                  autonomousLogs.slice(-12).map((log, index) => (
                    <div key={`${log}-${index}`} className="autonomous-log-line">
                      {log}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pull Request Panel */}
      {showPRPanel && currentPR && (
        <PullRequestPanel
          pr={currentPR}
          onClose={() => setShowPRPanel(false)}
          onApprove={approvePR}
          onRequestChanges={requestChanges}
          onMerge={mergePR}
          onAnalyzeWithAI={analyzePRWithAI}
        />
      )}

      {/* Bottom Navigation for Mobile */}
      <div className="bottom-nav">
        <button 
          className={activeMobilePanel === 'sidebar' ? 'active' : ''} 
          onClick={() => setActiveMobilePanel('sidebar')}
        >
          Files
        </button>
        <button 
          className={activeMobilePanel === 'editor' ? 'active' : ''} 
          onClick={() => setActiveMobilePanel('editor')}
        >
          Editor
        </button>
        <button 
          className={activeMobilePanel === 'chat' ? 'active' : ''} 
          onClick={() => setActiveMobilePanel('chat')}
        >
          Chat
        </button>
      </div>

      {/* EvolveAI Modal */}
      {showEvolveAI && (
        <div className="modal-overlay">
          <div className="modal-content evolve-modal">
            <div className="modal-header">
              <h3>🧬 EvolveAI - Predictive Code Evolution</h3>
              <button onClick={() => setShowEvolveAI(false)} className="close-btn">✕</button>
            </div>
            <div className="evolve-container">
              <EvolveAI apiBase={API_BASE} />
            </div>
          </div>
        </div>
      )}

      {/* Living Documentation Modal */}
      {showLivingDocs && (
        <div className="modal-overlay">
          <div className="modal-content docs-modal">
            <div className="modal-header">
              <h3>📚 Living Documentation</h3>
              <button onClick={() => setShowLivingDocs(false)} className="close-btn">✕</button>
            </div>
            <div className="docs-container">
              <LivingDocumentation apiBase={API_BASE} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
