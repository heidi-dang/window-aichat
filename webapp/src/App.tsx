import { useState, useEffect, useRef, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import * as MonacoEditor from 'monaco-editor';
import Terminal from './components/Terminal';
import DiffModal from './components/DiffModal';
import { AgentLoop } from './agent/AgentLoop';
import VectorStoreService from './utils/VectorStoreService';
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
  const geminiKeyRef = useRef(geminiKey);
  const deepseekKeyRef = useRef(deepseekKey);
  const lastCompletionTsRef = useRef(0);

  useEffect(() => {
    geminiKeyRef.current = geminiKey;
  }, [geminiKey]);

  useEffect(() => {
    deepseekKeyRef.current = deepseekKey;
  }, [deepseekKey]);

  // Panel Visibility State
  const [showTerminal, setShowTerminal] = useState(false);
  const [activeMobilePanel, setActiveMobilePanel] = useState('editor');

  // Agent State
  const [agentLogs, setAgentLogs] = useState<string[]>([]);
  const [diagnostics, setDiagnostics] = useState<string>("");
  const [showAgentTaskModal, setShowAgentTaskModal] = useState(false);
  const [agentTaskInput, setAgentTaskInput] = useState('');

  // Diff Modal State
  const [showDiff, setShowDiff] = useState(false);
  const [diffOriginal, setDiffOriginal] = useState('');
  const [diffModified, setDiffModified] = useState('');
  const [diffFilename, setDiffFilename] = useState('');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    void fetchFiles();
    // Deep Context: Index workspace on startup
    VectorStoreService.getInstance().indexWorkspace(API_BASE);
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

  const openInVSCode = async () => {
    if (!activeFile) return;
    const normalized = activeFile.replace(/\\/g, '/');
    const vscodeUrl = `vscode://file/${normalized}`;
    try {
      const res = await fetch(`${API_BASE}/api/system/open-vscode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: activeFile })
      });
      if (res.ok) { return; }
    } catch (error: unknown) {
      /* no-op */
    }
    try {
      window.location.href = vscodeUrl;
    } catch {
      alert(`Failed to open VS Code: ${normalized}`);
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

    // Predictive Editing (Ghost Text)
    const completionProvider = {
      provideInlineCompletions: async (model: MonacoEditor.editor.ITextModel, position: MonacoEditor.Position) => {
        const now = Date.now();
        if (now - lastCompletionTsRef.current < 300) {
          return { items: [] };
        }
        lastCompletionTsRef.current = now;
        const fullText = model.getValue();
        const offset = model.getOffsetAt(position);

        try {
          const res = await fetch(`${API_BASE}/api/completion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              code: fullText,
              cursor_offset: offset,
              gemini_key: geminiKeyRef.current,
              deepseek_key: deepseekKeyRef.current
            })
          });
          
          if (res.ok) {
            const data = await res.json();
            if (data.completion) {
               return {
                 items: [{
                   insertText: data.completion
                 }]
               };
            }
          }
        } catch (e) {
          console.error(e);
        }
        return { items: [] };
      },
      freeInlineCompletions: () => {},
      disposeInlineCompletions: () => {}
    };

    // Register for supported languages
    // Note: In a real app, manage disposables to avoid duplicate registration
    monaco.languages.registerInlineCompletionsProvider('javascript', completionProvider);
    monaco.languages.registerInlineCompletionsProvider('typescript', completionProvider);
    monaco.languages.registerInlineCompletionsProvider('python', completionProvider);

    // LSP Diagnostic Hook
    monaco.editor.onDidChangeMarkers(() => {
      const model = editor.getModel();
      if (model) {
        const markers = monaco.editor.getModelMarkers({ resource: model.uri });
        const errors = markers
          .map(m => `Line ${m.startLineNumber}: [${m.severity === monaco.MarkerSeverity.Error ? 'Error' : 'Warning'}] ${m.message}`)
          .join('\n');
        setDiagnostics(errors);
      }
    });
  };

  const openAgentModal = () => {
    setShowAgentTaskModal(true);
    setAgentTaskInput('');
  };

  const handleStartAgent = async () => {
    if (!agentTaskInput.trim()) return;
    setShowAgentTaskModal(false);
    
    const task = agentTaskInput;

    setShowTerminal(true);
    setAgentLogs([]);
    
    await AgentLoop.runTask(task, {
      apiBase: API_BASE,
      geminiKey,
      deepseekKey,
      githubToken,
      repoUrl,
      onLog: (msg) => setAgentLogs(prev => [...prev, msg]),
      context: {
        diagnostics,
        currentFile: activeFile || undefined,
        currentFileContent: fileContent
      },
      onSuccess: (filename, content) => {
        // If the modified file matches the current file (or if we want to show diff regardless)
        // For now, assume we are editing the current file or creating a new one.
        // If creating new, original is empty.
        
        // If filename matches activeFile, use fileContent as original.
        // Otherwise, it might be a new file or another file.
        // Simplified: If filename is activeFile (basename check), use fileContent.
        
        const isCurrent = activeFile && (activeFile.endsWith(filename) || activeFile === filename);
        const original = isCurrent ? fileContent : ''; 
        
        setDiffOriginal(original);
        setDiffModified(content);
        setDiffFilename(filename);
        setShowDiff(true);
      }
    });
  };

  const handleAcceptDiff = () => {
    setFileContent(diffModified);
    setShowDiff(false);
    // Optionally save immediately? For now, just update editor.
    alert('Changes applied to editor. Don\'t forget to Save!');
  };

  const handleRejectDiff = () => {
    setShowDiff(false);
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
        fetchFiles(); // Refresh file explorer
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
        fetchFiles(); // Refresh file explorer
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

  const getLanguage = (filename: string) => {
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
      {/* Sidebar */}
      <div className={`sidebar ${activeMobilePanel === 'sidebar' ? 'visible' : ''}`} style={{ width: sidebarWidth }} ref={sidebarRef}>
        <div className="sidebar-header">
          <h2>AI IDE</h2>
        </div>
        
        <div className="sidebar-section">
          <button onClick={() => setShowSettings(!showSettings)}>
            ⚙ Settings
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
          <button onClick={cloneRepo} disabled={isLoading || !repoUrl}>
            {isLoading ? 'Cloning...' : 'Clone GitHub Repo'}
          </button>
          <input 
            type="file" 
            id="upload-zip" 
            style={{ display: 'none' }} 
            onChange={uploadFile} 
            disabled={isLoading}
          />
          <button onClick={() => document.getElementById('upload-zip')?.click()} disabled={isLoading}>
            Upload Zip/File
          </button>
        </div>

        <div className="file-explorer">
          <h3>Workspace</h3>
          <button className="refresh-btn" onClick={fetchFiles}>↻ Refresh</button>
          <ul>
            {files.map((file, idx) => (
              <li 
                key={idx} 
                className={`${file.type} ${activeFile === file.path ? 'active' : ''}`}
                onClick={() => file.type === 'file' && openFile(file.path)}
              >
                {file.type === 'directory' ? '📁' : '📄'} {file.name}
              </li>
            ))}
          </ul>
        </div>
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
            <button onClick={openAgentModal} title="Run Agent Task">🤖 Agent</button>
            <button className="btn-vscode" onClick={openInVSCode} title="Open in VS Code">Open VS Code</button>
            <button className="btn-primary" onClick={() => void saveFile()} disabled={!activeFile}>💾 Save</button>
          </div>
        </div>
        <div className="monaco-wrapper" style={{ height: showTerminal ? '60%' : '100%' }}>
          <Editor
            height="100%"
            defaultLanguage="javascript"
            language={activeFile ? getLanguage(activeFile) : 'plaintext'}
            value={fileContent}
            theme="vs-dark"
            onMount={handleEditorDidMount}
            onChange={(value) => setFileContent(value || '')}
            options={{
              minimap: { enabled: true },
              fontSize: 14,
              wordWrap: 'on',
              automaticLayout: true,
              padding: { top: 10 },
              scrollBeyondLastLine: false,
              folding: true,
            }}
          />
        </div>
        {showTerminal && (
          <div className="terminal-wrapper">
             <div className="terminal-header">
               <span>Terminal / Agent Logs</span>
               <button onClick={() => setShowTerminal(false)}>×</button>
             </div>
             <div className="terminal-body">
               <div className="terminal-pane">
                 <Terminal />
               </div>
               <div className="agent-logs">
                 {agentLogs.map((log, i) => <div key={i}>{log}</div>)}
               </div>
             </div>
          </div>
        )}
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
            placeholder="Type a message... (Shift+Enter for new line)"
          />
          <button onClick={() => void sendMessage()} disabled={isLoading || !input.trim()}>
            Send
          </button>
        </div>
        <div className="resizer-handle left" onMouseDown={startResizeChat}></div>
      </div>
      
      {/* Mobile Nav */}
      <div className="mobile-nav">
        <button className={activeMobilePanel === 'sidebar' ? 'active' : ''} onClick={() => setActiveMobilePanel('sidebar')}>📁 Files</button>
        <button className={activeMobilePanel === 'editor' ? 'active' : ''} onClick={() => setActiveMobilePanel('editor')}>📝 Code</button>
        <button className={activeMobilePanel === 'chat' ? 'active' : ''} onClick={() => setActiveMobilePanel('chat')}>💬 Chat</button>
      </div>
      {showAgentTaskModal && (
        <div className="modal-overlay" onClick={() => setShowAgentTaskModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Run Agent Task</h3>
            <textarea
              className="modal-textarea"
              placeholder="Describe the task (e.g., 'Create a calculator in JS')"
              value={agentTaskInput}
              onChange={(e) => setAgentTaskInput(e.target.value)}
              rows={4}
            />
            <div className="modal-actions">
              <button className="modal-btn" onClick={() => setShowAgentTaskModal(false)}>Cancel</button>
              <button className="modal-btn primary" onClick={handleStartAgent}>Start Agent</button>
            </div>
          </div>
        </div>
      )}
      {showDiff && (
        <DiffModal
          original={diffOriginal}
          modified={diffModified}
          filename={diffFilename}
          onAccept={handleAcceptDiff}
          onReject={handleRejectDiff}
        />
      )}
    </div>
  );
}

export default App;
