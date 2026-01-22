#!/bin/bash

# ==============================================================================
# AI Chat Web App - One-Click Build & Deploy Script
# Target: Ubuntu 24.04+ / 25.x VPS
# Stack: React + Vite + TailwindCSS
# ==============================================================================

set -e  # Exit on error

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting AI Chat Web App Build Process...${NC}"

# 1. System Updates & Dependencies
echo -e "${GREEN}[1/6] Updating system and installing dependencies...${NC}"
sudo apt-get update -y
sudo apt-get install -y curl git unzip

# 2. Install Node.js (LTS)
echo -e "${GREEN}[2/6] Installing Node.js...${NC}"
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
else
    echo "Node.js is already installed."
fi

# 3. Create Vite Project
echo -e "${GREEN}[3/6] Creating React project structure...${NC}"
APP_DIR="window-aichat-web"
rm -rf $APP_DIR
npm create vite@latest $APP_DIR -- --template react
cd $APP_DIR

# Install Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install Icons
npm install lucide-react @monaco-editor/react axios clsx tailwind-merge xterm xterm-addon-fit

# 4. Generate Application Code
echo -e "${GREEN}[4/6] Generating React components...${NC}"

# --- Configure Tailwind ---
cat <<EOF > tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#161616",
        sidebar: "#1E1E1E",
        chat: "#000000",
        input: "#2C2C2C",
        accent: "#6210CC",
        accent_hover: "#7B2FDD",
        text_primary: "#EEEEEE",
        text_dim: "#9E9E9E",
        border: "#333333",
        editor_bg: "#1e1e1e"
      }
    },
  },
  plugins: [],
}
EOF

# --- CSS Styles ---
cat <<EOF > src/index.css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #161616;
  color: #EEEEEE;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  overflow: hidden;
}
@import 'xterm/css/xterm.css';

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: #1E1E1E;
}
::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #555;
}
EOF

# --- Vite Config (Proxy) ---
cat <<EOF > vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      }
    }
  }
})
EOF

# --- Main App Component ---
cat <<EOF > src/App.jsx
import React, { useState, useRef, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import FileExplorer from './components/FileExplorer';
import EditorArea from './components/EditorArea';
import TerminalPanel from './components/TerminalPanel';
import ChatWindow from './components/ChatWindow';
import axios from 'axios';

function App() {
  const [activeFile, setActiveFile] = useState(null); // { path, content, language }
  const [fileContent, setFileContent] = useState("");
  const [isTerminalOpen, setIsTerminalOpen] = useState(true);
  const [messages, setMessages] = useState([
    { id: 1, sender: 'System', text: 'Welcome to AI Chat Web! Connect to Gemini or DeepSeek to start.', timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }
  ]);
  const [config, setConfig] = useState({
    model: 'both',
    repoUrl: '',
    geminiKey: '',
    deepseekKey: ''
  });

  // --- File System Operations ---
  const handleFileSelect = async (path) => {
    try {
      const res = await axios.post('/api/fs/read', { path });
      setActiveFile({ path, language: getLanguage(path) });
      setFileContent(res.data.content);
    } catch (err) {
      console.error("Error reading file", err);
    }
  };

  const handleSaveFile = async (content) => {
    if (!activeFile) return;
    try {
      await axios.post('/api/fs/write', { path: activeFile.path, content });
      setFileContent(content);
      alert("File Saved!");
    } catch (err) {
      alert("Error saving file");
    }
  };

  const getLanguage = (path) => {
    if (path.endsWith('.py')) return 'python';
    if (path.endsWith('.js')) return 'javascript';
    if (path.endsWith('.html')) return 'html';
    if (path.endsWith('.css')) return 'css';
    if (path.endsWith('.json')) return 'json';
    return 'plaintext';
  };

  // --- Chat Operations ---
  const handleSendMessage = async (text) => {
    // Add User Message
    const newUserMsg = { 
      id: Date.now(), 
      sender: 'You', 
      text, 
      timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) 
    };
    setMessages(prev => [...prev, newUserMsg]);

    try {
      const res = await axios.post('/api/chat', {
        message: text,
        model: config.model,
        repo_url: config.repoUrl,
        gemini_key: config.geminiKey,
        deepseek_key: config.deepseekKey,
        context_file: fileContent // Send current code context
      });

      const aiResponse = {
        id: Date.now() + 1,
        sender: res.data.sender,
        text: res.data.text,
        timestamp: res.data.timestamp
      };
      setMessages(prev => [...prev, aiResponse]);
    } catch (err) {
      setMessages(prev => [...prev, { id: Date.now(), sender: 'System', text: 'Error connecting to backend.', timestamp: 'Now' }]);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-bg text-text_primary overflow-hidden">
      {/* Left: File Explorer */}
      <div className="w-64 border-r border-border bg-sidebar flex flex-col">
        <FileExplorer onFileSelect={handleFileSelect} />
      </div>

      {/* Center: Editor */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-hidden">
          <EditorArea file={activeFile} content={fileContent} onSave={handleSaveFile} onChange={setFileContent} />
        </div>
        
        {/* Terminal Section */}
        <div className={\`border-t border-border bg-black transition-all duration-300 \${isTerminalOpen ? 'h-48' : 'h-8'}\`}>
           <TerminalPanel isOpen={isTerminalOpen} onToggle={() => setIsTerminalOpen(!isTerminalOpen)} />
        </div>
      </div>

      {/* Right: Chat & Tools */}
      <div className="w-96 border-l border-border bg-sidebar flex flex-col">
        <Sidebar config={config} setConfig={setConfig} messages={messages} onSendMessage={handleSendMessage} activeCode={fileContent} />
      </div>
    </div>
  );
}

export default App;
EOF

# --- Sidebar (Chat + Tools) Component ---
mkdir -p src/components
cat <<EOF > src/components/Sidebar.jsx
import React, { useState } from 'react';
import { Settings, Github, Cpu, Wrench, MessageSquare } from 'lucide-react';
import ChatWindow from './ChatWindow';
import ToolsPanel from './ToolsPanel';

const Sidebar = ({ config, setConfig, messages, onSendMessage, activeCode }) => {
  const [tab, setTab] = useState('chat'); // 'chat' or 'tools'

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-border">
        <button 
          onClick={() => setTab('chat')}
          className={\`flex-1 p-3 text-sm font-bold flex items-center justify-center gap-2 \${tab === 'chat' ? 'bg-input text-white border-b-2 border-accent' : 'text-text_dim hover:bg-input'}\`}
        >
          <MessageSquare size={16} /> Chat
        </button>
        <button 
          onClick={() => setTab('tools')}
          className={\`flex-1 p-3 text-sm font-bold flex items-center justify-center gap-2 \${tab === 'tools' ? 'bg-input text-white border-b-2 border-accent' : 'text-text_dim hover:bg-input'}\`}
        >
          <Wrench size={16} /> Tools
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {tab === 'chat' ? (
          <>
            {/* Config Area (Mini) */}
            <div className="p-4 border-b border-border bg-sidebar">
               <select 
                value={config.model}
                onChange={(e) => setConfig({...config, model: e.target.value})}
                className="w-full bg-input text-white p-2 rounded border border-border text-xs mb-2"
              >
                <option value="gemini">Gemini 2.0 Flash</option>
                <option value="deepseek">DeepSeek Chat</option>
                <option value="both">Both Models</option>
              </select>
              <div className="flex gap-2">
                 <input 
                  type="text" 
                  placeholder="GitHub URL..."
                  value={config.repoUrl}
                  onChange={(e) => setConfig({...config, repoUrl: e.target.value})}
                  className="flex-1 bg-input text-white p-1 px-2 rounded border border-border text-xs"
                />
              </div>
            </div>
            <ChatWindow messages={messages} onSendMessage={onSendMessage} />
          </>
        ) : (
          <ToolsPanel activeCode={activeCode} config={config} />
        )}
      </div>
    </div>
  );
};

export default Sidebar;
EOF

# --- Tools Panel Component ---
cat <<EOF > src/components/ToolsPanel.jsx
import React, { useState } from 'react';
import axios from 'axios';
import { Play, Copy } from 'lucide-react';

const ToolsPanel = ({ activeCode, config }) => {
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  const runTool = async (toolName) => {
    if (!activeCode) {
      alert("Open a file first!");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post('/api/tool', {
        tool: toolName,
        code: activeCode,
        gemini_key: config.geminiKey
      });
      setResult(res.data.result);
    } catch (err) {
      setResult("Error running tool: " + err.message);
    }
    setLoading(false);
  };

  const tools = [
    { id: 'analyze', label: 'Analyze Code' },
    { id: 'docs', label: 'Generate Docs' },
    { id: 'refactor', label: 'Refactor' },
    { id: 'security', label: 'Security Check' },
    { id: 'tests', label: 'Generate Tests' },
    { id: 'explain', label: 'Explain Code' },
    { id: 'optimize', label: 'Optimize' },
  ];

  return (
    <div className="flex flex-col h-full p-4 overflow-y-auto">
      <h3 className="text-sm font-bold text-text_dim mb-4">DEVELOPER TOOLS</h3>
      
      <div className="grid grid-cols-2 gap-2 mb-6">
        {tools.map(tool => (
          <button
            key={tool.id}
            onClick={() => runTool(tool.id)}
            disabled={loading}
            className="bg-input hover:bg-border text-white p-2 rounded text-xs flex items-center justify-center gap-2 transition-colors"
          >
            {loading ? '...' : tool.label}
          </button>
        ))}
      </div>

      <div className="flex-1 flex flex-col">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-bold text-text_dim">RESULT</span>
          <button onClick={() => navigator.clipboard.writeText(result)} className="text-accent hover:text-white">
            <Copy size={14} />
          </button>
        </div>
        <textarea
          readOnly
          value={result}
          className="flex-1 bg-input text-text_primary p-3 rounded text-sm font-mono resize-none outline-none border border-border"
          placeholder="Tool output will appear here..."
        />
      </div>
    </div>
  );
};

export default ToolsPanel;
EOF

# --- File Explorer Component ---
cat <<EOF > src/components/FileExplorer.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Folder, FileCode, RefreshCw, Plus } from 'lucide-react';

const FileExplorer = ({ onFileSelect }) => {
  const [files, setFiles] = useState([]);

  const fetchFiles = async () => {
    try {
      const res = await axios.get('/api/fs/list');
      setFiles(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { fetchFiles(); }, []);

  const createFile = async () => {
    const name = prompt("Enter file name (e.g., test.py):");
    if (!name) return;
    try {
      await axios.post('/api/fs/write', { path: name, content: "" });
      fetchFiles();
    } catch (err) { alert("Error creating file"); }
  };

  return (
    <div className="flex flex-col h-full bg-sidebar">
      <div className="p-4 border-b border-border flex justify-between items-center">
        <span className="font-bold text-sm text-text_dim">EXPLORER</span>
        <div className="flex gap-2">
          <button onClick={createFile} className="text-text_dim hover:text-white"><Plus size={16}/></button>
          <button onClick={fetchFiles} className="text-text_dim hover:text-white"><RefreshCw size={16}/></button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {files.map((file) => (
          <div 
            key={file.path}
            onClick={() => file.type === 'file' && onFileSelect(file.path)}
            className="flex items-center gap-2 p-2 hover:bg-input rounded cursor-pointer text-sm text-text_primary"
          >
            {file.type === 'directory' ? <Folder size={16} className="text-accent" /> : <FileCode size={16} className="text-blue-400" />}
            <span className="truncate">{file.name}</span>
          </div>
        ))}
        {files.length === 0 && <div className="text-center text-xs text-text_dim mt-4">Workspace Empty</div>}
      </div>
    </div>
  );
};

export default FileExplorer;
EOF

# --- Editor Area Component (Monaco) ---
cat <<EOF > src/components/EditorArea.jsx
import React from 'react';
import Editor from '@monaco-editor/react';
import { Save } from 'lucide-react';

const EditorArea = ({ file, content, onSave, onChange }) => {
  if (!file) {
    return (
      <div className="flex-1 flex items-center justify-center bg-bg text-text_dim">
        <div className="text-center">
          <p className="mb-2">No file open</p>
          <p className="text-xs">Select a file from the explorer to start editing</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Editor Header */}
      <div className="h-10 bg-input border-b border-border flex items-center justify-between px-4">
        <span className="text-sm font-mono text-white">{file.path}</span>
        <button 
          onClick={() => onSave(content)}
          className="flex items-center gap-2 text-xs bg-accent hover:bg-accent_hover text-white px-3 py-1 rounded transition-colors"
        >
          <Save size={14} /> Save
        </button>
      </div>
      
      {/* Monaco Editor */}
      <div className="flex-1">
        <Editor
          height="100%"
          theme="vs-dark"
          path={file.path}
          defaultLanguage={file.language}
          value={content}
          onChange={(value) => onChange(value)}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
};

export default EditorArea;
EOF

# --- Terminal Component ---
cat <<EOF > src/components/TerminalPanel.jsx
import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { Terminal as TerminalIcon, ChevronUp, ChevronDown } from 'lucide-react';

const TerminalPanel = ({ isOpen, onToggle }) => {
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const fitAddonRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!isOpen || xtermRef.current) return;

    // Initialize XTerm
    const term = new Terminal({
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
        selection: '#264f78',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5'
      },
      fontSize: 13,
      fontFamily: 'Consolas, monospace',
      cursorBlink: true
    });
    
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Connect WebSocket (Dynamic Protocol/Host)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(\`\${protocol}//\${window.location.host}/ws/terminal\`);
    ws.onmessage = (event) => term.write(event.data);
    term.onData((data) => ws.send(data));
    wsRef.current = ws;

    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      ws.close();
      term.dispose();
      xtermRef.current = null;
    };
  }, [isOpen]);

  // Re-fit when toggled
  useEffect(() => {
    if (isOpen && fitAddonRef.current) {
      setTimeout(() => fitAddonRef.current.fit(), 100);
    }
  }, [isOpen]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div 
        className="h-8 bg-input border-b border-border flex items-center justify-between px-4 cursor-pointer hover:bg-border transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-2 text-xs font-bold text-text_dim">
          <TerminalIcon size={14} /> TERMINAL
        </div>
        {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </div>

      {/* Terminal Container */}
      <div className={\`flex-1 bg-black p-2 overflow-hidden \${!isOpen && 'hidden'}\`}>
        <div ref={terminalRef} className="h-full w-full" />
      </div>
    </div>
  );
};

export default TerminalPanel;
EOF

# --- Chat Window Component ---
cat <<EOF > src/components/ChatWindow.jsx
import React, { useState, useRef, useEffect } from 'react';
import { Send, Code } from 'lucide-react';

const ChatWindow = ({ messages, onSendMessage }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-chat">
      {/* Header */}
      <div className="h-16 border-b border-border flex items-center px-6 bg-bg">
        <h2 className="text-lg font-bold ml-8">Chat Session</h2>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={\`flex flex-col \${msg.sender === 'You' ? 'items-end' : 'items-start'}\`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold text-text_dim">{msg.sender}</span>
              <span className="text-[10px] text-text_dim">{msg.timestamp}</span>
            </div>
            <div 
              className={\`max-w-[80%] p-4 rounded-lg whitespace-pre-wrap \${
                msg.sender === 'You' 
                  ? 'bg-accent text-white rounded-tr-none' 
                  : msg.sender === 'System'
                  ? 'bg-transparent text-text_dim italic border border-border w-full text-center'
                  : 'bg-input text-text_primary rounded-tl-none'
              }\`}
            >
              {msg.text}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-6 bg-bg border-t border-border">
        <div className="bg-input rounded-lg p-2 border border-border focus-within:border-accent transition-colors">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (Ctrl+Enter to send)"
            className="w-full bg-transparent text-white p-2 outline-none resize-none min-h-[80px] font-sans"
          />
          <div className="flex justify-between items-center px-2 pb-1">
            <div className="text-xs text-text_dim">
              Supports Markdown & Code Blocks
            </div>
            <button 
              onClick={handleSubmit}
              className="bg-accent hover:bg-accent_hover text-white px-4 py-2 rounded-md flex items-center gap-2 text-sm font-bold transition-colors"
            >
              <Send size={16} />
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
EOF

# 5. Build the Application
echo -e "${GREEN}[5/6] Building the application...${NC}"
npm run build

# 6. Serve Instructions
echo -e "${GREEN}[6/6] Setup Complete!${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "To preview the app immediately, run:"
echo -e "  cd $APP_DIR"
echo -e "  npm run preview"
echo -e ""
echo -e "To deploy for production, configure Nginx to serve:"
echo -e "  $PWD/$APP_DIR/dist"
echo -e "${BLUE}====================================================${NC}"

# Make script executable
chmod +x build_web_app.sh