import { useState, useEffect, useRef, useCallback } from 'react';
import * as MonacoEditor from 'monaco-editor';
import './App.css';
import MonacoWrapper from './components/IDE/MonacoWrapper';
import FileExplorer from './components/IDE/FileExplorer';
import StatusBar from './components/IDE/StatusBar';
import DiffViewer from './components/IDE/DiffViewer';
import { EvolveAI, LivingDocumentation } from './evolve';
import PullRequestPanel, { type PullRequest, type PullRequestFile } from './components/IDE/PullRequestPanel';

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

  // Settings State
  const [geminiKey, setGeminiKey] = useState(localStorage.getItem('gemini_key') || '');
  const [deepseekKey, setDeepseekKey] = useState(localStorage.getItem('deepseek_key') || '');
  const [githubToken, setGithubToken] = useState(localStorage.getItem('github_token') || '');
  const [repoUrl, setRepoUrl] = useState(localStorage.getItem('repo_url') || '');
  const [selectedModel, setSelectedModel] = useState('gemini');
  const [showSettings, setShowSettings] = useState(false);

  // File System & Editor State
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('// Select a file to edit');
  const editorRef = useRef<MonacoEditor.editor.IStandaloneCodeEditor | null>(null);
  const [editorLine, setEditorLine] = useState(1);
  const [editorColumn, setEditorColumn] = useState(1);

  // Panel Visibility State
  const [showSidebar, setShowSidebar] = useState(true);
  const [showChat, setShowChat] = useState(true);
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    void fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/fs/list`);
      if (res.ok) {
        const data = await res.json();
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

  const openFile = async (path: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/fs/read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      if (res.ok) {
        const data = await res.json();
        setFileContent(data.content);
        setActiveFile(path);
        setActiveMobilePanel('editor'); // Switch to editor on file open
      } else {
        const errorText = await readErrorText(res);
        alert(`Failed to read file: ${errorText}`);
      }
    } catch (error: unknown) {
      console.error("Failed to read file", error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      alert(`Failed to read file: ${errorMessage}`);
    }
  };

  const saveFile = async () => {
    if (!activeFile) { return; }
    const content = editorRef.current ? editorRef.current.getValue() : fileContent;
    
    try {
      const res = await fetch(`${API_BASE}/api/fs/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: activeFile, content })
      });
      if (res.ok) {
        console.log('File saved');
      } else {
        const errorText = await readErrorText(res);
        alert(`Failed to save file: ${errorText}`);
      }
    } catch (error: unknown) {
      console.error("Failed to save file", error);
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      alert(`Failed to save file: ${errorMessage}`);
    }
  };

  const runTool = async (tool: string) => {
    if (!editorRef.current) { return; }
    
    const model = editorRef.current.getModel();
    const selectionRange = editorRef.current.getSelection() || null;
    const selection = model && selectionRange ? model.getValueInRange(selectionRange) : "";
    const code = selection || editorRef.current.getValue();
    
    if (!code.trim()) {
      alert("Please select code or open a file first.");
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

      const data = await res.json();
      setMessages(prev => [...prev, {
        sender: 'AI Tool',
        text: typeof data?.result === 'string' ? data.result : JSON.stringify(data),
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
  };

  const sendMessage = async () => {
    if (!input.trim()) { return; }

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
    } catch (error: unknown) {
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
      alert("Please enter a GitHub repository URL.");
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
          alert('Failed to load pull request: invalid response payload');
          return;
        }
        setCurrentPR(pr);
        setShowPRPanel(true);
      } else {
        const errorText = await readErrorText(res);
        alert(`Failed to load pull request: ${errorText}`);
      }
    } catch (error: unknown) {
      console.error("Failed to load pull request", error);
      alert(`Failed to load pull request: ${error instanceof Error ? error.message : 'Unknown error'}`);
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
      {/* Panel Toggle Buttons */}
      <div className="panel-toggles">
        <button onClick={() => setShowSidebar(!showSidebar)} className="toggle-btn">
          {showSidebar ? '◀ Hide Sidebar' : '▶ Show Sidebar'}
        </button>
        <button onClick={() => setShowChat(!showChat)} className="toggle-btn">
          {showChat ? 'Hide Chat ▶' : '◀ Show Chat'}
        </button>
      </div>

      {/* Sidebar */}
      {showSidebar && (
        <div className={`sidebar ${activeMobilePanel === 'sidebar' ? 'visible' : ''}`} style={{ width: sidebarWidth }} ref={sidebarRef}>
          <div className="sidebar-header">
            <h2>AI IDE</h2>
          </div>
          
          <div className="sidebar-section">
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

          <div className="sidebar-section">
            <button onClick={() => void cloneRepo()} disabled={isLoading || !repoUrl}>
              {isLoading ? 'Cloning...' : 'Clone GitHub Repo'}
            </button>
            <input 
              type="file" 
              id="upload-zip" 
              style={{ display: 'none' }} 
              onChange={(e) => void uploadFile(e)} 
              disabled={isLoading}
            />
            <button onClick={() => document.getElementById('upload-zip')?.click()} disabled={isLoading}>
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
          <div className="resizer-handle" onMouseDown={startResizeSidebar}></div>
        </div>
      )}

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
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender === 'You' ? 'user' : 'ai'}`}>
              <div className="message-header">
                <span className="sender">{msg.sender}</span>
                <span className="time">{msg.timestamp}</span>
              </div>
              <div className="message-content">
                {msg.text}
              </div>
            </div>
          ))}
          {isLoading && <div className="message ai"><div className="message-content">Thinking...</div></div>}
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
