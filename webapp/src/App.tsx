import { useState, useEffect, useRef } from 'react';
import * as MonacoEditor from 'monaco-editor';
import DiffModal from './components/DiffModal';
import { AgentLoop } from './agent/AgentLoop';
import VectorStoreService from './utils/VectorStoreService';
import { Sidebar } from './components/Layout/Sidebar';
import { EditorPanel } from './components/Editor/EditorPanel';
import { ChatInterface } from './components/Chat/ChatInterface';
import { SettingsModal } from './components/SettingsModal';

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

  useEffect(() => {
    void fetchFiles();
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
      } else {
        const errorText = await readErrorText(res);
        alert(`Failed to read file: ${errorText}`);
      }
    } catch (error) {
       alert('Failed to read file');
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
    } catch (error) {
      alert('Failed to save file');
    }
  };

  const openInVSCode = async () => {
    if (!activeFile) return;
    const normalized = activeFile.replace(/\\/g, '/');
    const vscodeUrl = `vscode://file/${normalized}`;
    try {
      await fetch(`${API_BASE}/api/system/open-vscode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: activeFile })
      });
    } catch { /* no-op */ }
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
    } catch (error) {
       // ... error handling
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditorDidMount = (editor: MonacoEditor.editor.IStandaloneCodeEditor, monaco: typeof MonacoEditor) => {
    editorRef.current = editor;
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      void saveFile();
    });

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
              deepseek_key: deepseekKeyRef.current,
              position: offset, // Updated backend expects position
              language: model.getLanguageId()
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

    monaco.languages.registerInlineCompletionsProvider('javascript', completionProvider);
    monaco.languages.registerInlineCompletionsProvider('typescript', completionProvider);
    monaco.languages.registerInlineCompletionsProvider('python', completionProvider);

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
        const isCurrent = activeFile && (activeFile.endsWith(filename) || activeFile === filename);
        const original = isCurrent ? fileContent : ''; 
        setDiffOriginal(original);
        setDiffModified(content);
        setDiffFilename(filename);
        setShowDiff(true);
      }
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
          github_token: githubToken,
          history: messages.map(m => ({ role: m.sender === 'You' ? 'user' : 'model', content: m.text }))
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
    } catch (error) {
       // Error handling
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
          text: `Clone successful: ${data.message || 'Done'}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
        fetchFiles(); 
      } else {
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Clone failed: ${data.detail || data.message}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (error) {
       // Error handling
    } finally {
      setIsLoading(false);
    }
  };

  const uploadFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsLoading(true);
    // ... same logic as before but just fetch call
    const formData = new FormData();
    formData.append('file', file);
    try {
       await fetch(`${API_BASE}/api/fs/upload`, { method: 'POST', body: formData });
       fetchFiles();
    } catch {}
    setIsLoading(false);
  };

  return (
    <div className="flex h-screen w-screen bg-background text-foreground overflow-hidden">
      <Sidebar 
        files={files}
        activeFile={activeFile}
        onFileClick={openFile}
        onRefresh={fetchFiles}
        onSettingsClick={() => setShowSettings(true)}
        onCloneClick={cloneRepo}
        onUploadClick={uploadFile}
        className="w-64 flex-shrink-0"
      />

      <div className="flex-1 flex min-w-0">
        <EditorPanel 
          activeFile={activeFile}
          fileContent={fileContent}
          setFileContent={setFileContent}
          onSave={saveFile}
          onRunTool={runTool}
          onOpenAgent={() => setShowAgentTaskModal(true)}
          onOpenVSCode={openInVSCode}
          showTerminal={showTerminal}
          setShowTerminal={setShowTerminal}
          agentLogs={agentLogs}
          handleEditorDidMount={handleEditorDidMount}
          className="flex-1 border-r border-border"
          diagnostics={diagnostics}
        />

        <ChatInterface 
          messages={messages}
          isLoading={isLoading}
          input={input}
          setInput={setInput}
          onSend={sendMessage}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          className="w-96 flex-shrink-0"
        />
      </div>

      {showSettings && (
        <SettingsModal 
          onClose={() => setShowSettings(false)}
          geminiKey={geminiKey}
          setGeminiKey={setGeminiKey}
          deepseekKey={deepseekKey}
          setDeepseekKey={setDeepseekKey}
          githubToken={githubToken}
          setGithubToken={setGithubToken}
          repoUrl={repoUrl}
          setRepoUrl={setRepoUrl}
          onSave={saveSettings}
        />
      )}

      {showAgentTaskModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card w-full max-w-lg rounded-lg shadow-xl border border-border p-6">
            <h3 className="text-lg font-semibold mb-4">Run Agent Task</h3>
            <textarea
              className="w-full bg-muted border border-border rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring mb-4"
              placeholder="Describe the task (e.g., 'Create a calculator in JS')"
              value={agentTaskInput}
              onChange={(e) => setAgentTaskInput(e.target.value)}
              rows={4}
            />
            <div className="flex justify-end gap-3">
              <button 
                className="px-4 py-2 text-sm font-medium hover:bg-muted rounded transition-colors"
                onClick={() => setShowAgentTaskModal(false)}
              >
                Cancel
              </button>
              <button 
                className="bg-primary text-primary-foreground px-4 py-2 rounded text-sm font-medium hover:opacity-90 transition-opacity"
                onClick={handleStartAgent}
              >
                Start Agent
              </button>
            </div>
          </div>
        </div>
      )}

      {showDiff && (
        <DiffModal
          original={diffOriginal}
          modified={diffModified}
          filename={diffFilename}
          onAccept={() => {
            setFileContent(diffModified);
            setShowDiff(false);
          }}
          onReject={() => setShowDiff(false)}
        />
      )}
    </div>
  );
}

export default App;
