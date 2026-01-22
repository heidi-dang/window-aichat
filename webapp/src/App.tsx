import { useState, useEffect, useRef } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import * as MonacoEditor from 'monaco-editor';
import './App.css';

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/fs/list');
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
      const res = await fetch('http://localhost:8000/api/fs/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      if (res.ok) {
        const data = await res.json();
        setFileContent(data.content);
        setActiveFile(path);
      } else {
        const errorText = await res.text();
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
    if (!activeFile) return;
    const content = editorRef.current ? editorRef.current.getValue() : fileContent;
    
    try {
      const res = await fetch('http://localhost:8000/api/fs/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: activeFile, content })
      });
      if (res.ok) {
        console.log('File saved');
      } else {
        const errorText = await res.text();
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
    if (!editorRef.current) return;
    
    // Get selected text or full content
    const selection = editorRef.current.getModel()?.getValueInRange(editorRef.current.getSelection()!) || "";
    const code = selection || editorRef.current.getValue();

    if (!code.trim()) {
      alert("Please select code or open a file first.");
      return;
    }

    setIsLoading(true);
    // Add a system message to chat indicating the action
    setMessages(prev => [...prev, {
      sender: 'System',
      text: `Running ${tool}...`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);

    try {
      const res = await fetch('http://localhost:8000/api/tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool,
          code,
          gemini_key: geminiKey // Tools currently use Gemini
        })
      });

      if (!res.ok) {
        const errorText = await res.text();
        // Handle error directly instead of throwing
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
        text: data.result,
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

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    // Add keybinding for save
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      saveFile();
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
    if (!input.trim()) return;

    const userMsg: Message = {
      sender: 'You',
      text: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
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
        const errorText = await res.text();
        // Handle error directly instead of throwing
        setMessages(prev => [...prev, {
          sender: 'System',
          text: `Error: ${errorText}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
        return;
      }

      const data = await res.json();
      setMessages(prev => [...prev, data]);
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

  // Helper to determine language from file extension
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

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="sidebar">
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
      </div>

      {/* Editor Area */}
      <div className="editor-area">
        <div className="editor-header">
          <span className="file-name">{activeFile || 'No file selected'}</span>
          <div className="editor-actions">
            <button onClick={() => runTool('analyze')} title="Analyze Code">🔍 Analyze</button>
            <button onClick={() => runTool('explain')} title="Explain Code">📖 Explain</button>
            <button onClick={() => runTool('refactor')} title="Refactor Code">🛠 Refactor</button>
            <button onClick={() => runTool('docs')} title="Generate Docs">📝 Docs</button>
            <button className="primary" onClick={saveFile} disabled={!activeFile}>💾 Save</button>
          </div>
        </div>
        <div className="monaco-wrapper">
          <Editor
            height="100%"
            defaultLanguage="javascript"
            language={activeFile ? getLanguage(activeFile) : 'plaintext'}
            value={fileContent}
            theme="vs-dark"
            onMount={handleEditorDidMount}
            onChange={(value) => setFileContent(value || '')}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              wordWrap: 'on',
              automaticLayout: true,
              padding: { top: 10 }
            }}
          />
        </div>
      </div>

      {/* Chat Area */}
      <div className="chat-area">
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
                sendMessage();
              }
            }}
            placeholder="Ask AI..."
          />
          <button onClick={sendMessage} disabled={isLoading}>
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
