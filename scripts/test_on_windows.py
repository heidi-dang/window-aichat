import os
import sys
import subprocess
import shutil
import time
import threading
import webbrowser
import urllib.request

# Configuration
PROJECT_NAME = "window-aichat-web"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173


def install_backend_deps():
    print(">>> [1/4] Installing Backend Dependencies...")
    # Check if pip is installed
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print("⚠️ pip not found. Attempting to install...")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--default-pip"])
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
            )
            print("✅ pip installed via ensurepip.")
        except subprocess.CalledProcessError:
            print("⚠️ ensurepip failed. Downloading get-pip.py...")
            try:
                urllib.request.urlretrieve(
                    "https://bootstrap.pypa.io/get-pip.py", "get-pip.py"
                )
                subprocess.check_call([sys.executable, "get-pip.py"])
                if os.path.exists("get-pip.py"):
                    os.remove("get-pip.py")
                print("✅ pip installed via get-pip.py.")
            except Exception as e:
                print(
                    f"❌ Error: Could not install pip. {e}\nPlease install Python with pip enabled."
                )
                sys.exit(1)

    if not os.path.exists("requirements.txt"):
        print("ℹ️ requirements.txt not found. Creating default...")
        with open("requirements.txt", "w") as f:
            f.write(
                "fastapi\nuvicorn\npydantic\npython-multipart\naiofiles\npsutil\nrequests\ngoogle-generativeai\ncryptography\n"
            )

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
    except subprocess.CalledProcessError:
        print(
            "Error installing requirements. Please check the requirements.txt file and your pip installation."
        )
        sys.exit(1)


def setup_frontend():
    print(">>> [2/4] Setting up React Frontend...")

    def check_node():
        try:
            subprocess.run(
                ["node", "-v"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    # Check if node is installed
    if not check_node():
        # Try standard path
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        node_path = os.path.join(program_files, "nodejs")
        if os.path.exists(node_path):
            os.environ["PATH"] += os.pathsep + node_path

        if not check_node():
            print("⚠️ Node.js not found. Attempting to install via winget...")
            try:
                # Check for winget
                subprocess.run(
                    ["winget", "--version"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print("📦 Installing Node.js LTS (Accept prompts if any)...")
                subprocess.check_call(
                    ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS"]
                )

                if os.path.exists(node_path):
                    os.environ["PATH"] += os.pathsep + node_path
                    print("✅ Node.js installed and added to PATH.")
                else:
                    print(
                        "✅ Node.js installed. Please restart the script to pick up the new PATH."
                    )
                    sys.exit(0)
            except (FileNotFoundError, subprocess.CalledProcessError):
                print("❌ Error: Node.js is not installed and winget failed.")
                print("Please install Node.js manually from https://nodejs.org/")
                sys.exit(1)

    if not os.path.exists(PROJECT_NAME):
        print("Creating Vite project...")
        subprocess.check_call(
            f"npm create vite@latest {PROJECT_NAME} -- --template react", shell=True
        )

    os.chdir(PROJECT_NAME)

    print("Installing Frontend Dependencies (this may take a minute)...")
    subprocess.check_call("npm install", shell=True)
    subprocess.check_call("npm install -D tailwindcss postcss autoprefixer", shell=True)
    subprocess.check_call("npx tailwindcss init -p", shell=True)
    subprocess.check_call(
        "npm install lucide-react @monaco-editor/react axios clsx tailwind-merge xterm xterm-addon-fit",
        shell=True,
    )

    print("Generating Component Files...")
    generate_files()

    os.chdir("..")


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {path}")


def generate_files():
    # Clean up boilerplate files from default Vite template to prevent conflicts
    print("Cleaning up default Vite boilerplate...")
    files_to_remove = [
        "src/App.css",
        "src/App.jsx",
        "src/assets/react.svg",
    ]
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed boilerplate: {file_path}")

    if os.path.exists("src/assets"):
        shutil.rmtree("src/assets", ignore_errors=True)
        print("Removed boilerplate folder: src/assets")

    # 1. Tailwind Config
    write_file(
        "tailwind.config.js",
        """/** @type {import('tailwindcss').Config} */
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
}""",
    )

    # 1.5 PostCSS Config
    write_file(
        "postcss.config.js",
        """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}""",
    )

    # 2. CSS
    write_file(
        "src/index.css",
        """@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #161616;
  color: #EEEEEE;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  overflow: hidden;
}
@import 'xterm/css/xterm.css';

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #1E1E1E; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #555; }
""",
    )

    # 2.5 Vite Config (Proxy for Local Dev)
    write_file(
        "vite.config.js",
        """import { defineConfig } from 'vite'
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
})""",
    )

    # 3. App.jsx
    write_file(
        "src/App.jsx",
        """import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import FileExplorer from './components/FileExplorer';
import EditorArea from './components/EditorArea'; 
import TerminalPanel from './components/TerminalPanel';
import axios from 'axios';

function App() {
  const [activeFile, setActiveFile] = useState(null);
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

  const handleFileSelect = async (file) => {
    try {
      const res = await axios.post('/api/fs/read', { path: file.path });
      setActiveFile({ ...file, language: getLanguage(file.path) });
      setFileContent(res.data.content);
    } catch (err) {
      alert("Error reading file: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleSaveFile = async (content) => {
    if (!activeFile) return;
    try {
      await axios.post('/api/fs/write', { path: activeFile.path, content });
      setFileContent(content);
      alert("File Saved!");
    } catch (err) {
      alert("Error saving file: " + (err.response?.data?.detail || err.message));
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

  const handleSendMessage = async (text) => {
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
        context_file: fileContent
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
      <div className="w-64 border-r border-border bg-sidebar flex flex-col">
        <FileExplorer onFileSelect={handleFileSelect} />
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-hidden">
          <EditorArea file={activeFile} content={fileContent} onSave={handleSaveFile} onChange={setFileContent} />
        </div>
        <div className={`border-t border-border bg-black transition-all duration-300 ${isTerminalOpen ? 'h-48' : 'h-8'}`}>
           <TerminalPanel isOpen={isTerminalOpen} onToggle={() => setIsTerminalOpen(!isTerminalOpen)} />
        </div>
      </div>
      <div className="w-96 border-l border-border bg-sidebar flex flex-col">
        <Sidebar config={config} setConfig={setConfig} messages={messages} onSendMessage={handleSendMessage} activeCode={fileContent} />
      </div>
    </div>
  );
}
export default App;""",
    )

    # 4. Components
    write_file(
        "src/components/Sidebar.jsx",
        """import React, { useState } from 'react';
import { Wrench, MessageSquare } from 'lucide-react';
import ChatWindow from './ChatWindow';
import ToolsPanel from './ToolsPanel';

const Sidebar = ({ config, setConfig, messages, onSendMessage, activeCode }) => {
  const [tab, setTab] = useState('chat');
  return (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-border">
        <button onClick={() => setTab('chat')} className={`flex-1 p-3 text-sm font-bold flex items-center justify-center gap-2 ${tab === 'chat' ? 'bg-input text-white border-b-2 border-accent' : 'text-text_dim hover:bg-input'}`}>
          <MessageSquare size={16} /> Chat
        </button>
        <button onClick={() => setTab('tools')} className={`flex-1 p-3 text-sm font-bold flex items-center justify-center gap-2 ${tab === 'tools' ? 'bg-input text-white border-b-2 border-accent' : 'text-text_dim hover:bg-input'}`}>
          <Wrench size={16} /> Tools
        </button>
      </div>
      <div className="flex-1 overflow-hidden flex flex-col">
        {tab === 'chat' ? (
          <>
            <div className="p-4 border-b border-border bg-sidebar">
               <select value={config.model} onChange={(e) => setConfig({...config, model: e.target.value})} className="w-full bg-input text-white p-2 rounded border border-border text-xs mb-2">
                <option value="gemini">Gemini 2.0 Flash</option>
                <option value="deepseek">DeepSeek Chat</option>
                <option value="both">Both Models</option>
              </select>
              <input type="text" placeholder="GitHub URL..." value={config.repoUrl} onChange={(e) => setConfig({...config, repoUrl: e.target.value})} className="w-full bg-input text-white p-1 px-2 rounded border border-border text-xs" />
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
export default Sidebar;""",
    )

    write_file(
        "src/components/ToolsPanel.jsx",
        """import React, { useState } from 'react';
import axios from 'axios';
import { Copy } from 'lucide-react';

const ToolsPanel = ({ activeCode, config }) => {
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  const runTool = async (toolName) => {
    if (!activeCode) { alert("Open a file first!"); return; }
    setLoading(true);
    try {
      const res = await axios.post('/api/tool', { tool: toolName, code: activeCode, gemini_key: config.geminiKey });
      setResult(typeof res.data.result === 'string' ? res.data.result : JSON.stringify(res.data.result, null, 2));
    } catch (err) { setResult("Error: " + err.message); }
    setLoading(false);
  };

  const tools = [
    { id: 'analyze', label: 'Analyze Code' }, { id: 'docs', label: 'Generate Docs' },
    { id: 'refactor', label: 'Refactor' }, { id: 'security', label: 'Security Check' },
    { id: 'tests', label: 'Generate Tests' }, { id: 'explain', label: 'Explain Code' },
    { id: 'optimize', label: 'Optimize' }
  ];

  return (
    <div className="flex flex-col h-full p-4 overflow-y-auto">
      <h3 className="text-sm font-bold text-text_dim mb-4">DEVELOPER TOOLS</h3>
      <div className="grid grid-cols-2 gap-2 mb-6">
        {tools.map(tool => (
          <button key={tool.id} onClick={() => runTool(tool.id)} disabled={loading} className="bg-input hover:bg-border text-white p-2 rounded text-xs flex items-center justify-center gap-2 transition-colors">
            {loading ? '...' : tool.label}
          </button>
        ))}
      </div>
      <div className="flex-1 flex flex-col">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-bold text-text_dim">RESULT</span>
          <button onClick={() => navigator.clipboard.writeText(result)} className="text-accent hover:text-white"><Copy size={14} /></button>
        </div>
        <textarea readOnly value={result} className="flex-1 bg-input text-text_primary p-3 rounded text-sm font-mono resize-none outline-none border border-border" placeholder="Tool output..." />
      </div>
    </div>
  );
};
export default ToolsPanel;""",
    )

    write_file(
        "src/components/FileExplorer.jsx",
        """import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Folder, FileCode, RefreshCw, Plus } from 'lucide-react';

const FileExplorer = ({ onFileSelect }) => {
  const [files, setFiles] = useState([]);
  const fetchFiles = async () => {
    try { const res = await axios.get('/api/fs/list'); setFiles(res.data); } catch (err) { console.error(err); }
  };
  useEffect(() => { fetchFiles(); const interval = setInterval(fetchFiles, 5000); return () => clearInterval(interval); }, []);
  const createFile = async () => {
    const name = prompt("Enter file name (e.g., test.py):");
    if (!name) return;
    try { await axios.post('/api/fs/write', { path: name, content: "" }); fetchFiles(); } catch (err) { alert("Error creating file"); }
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
          <div key={file.path} onClick={() => file.type === 'file' && onFileSelect(file)} className="flex items-center gap-2 p-2 hover:bg-input rounded cursor-pointer text-sm text-text_primary">
            {file.type === 'directory' ? <Folder size={16} className="text-accent" /> : <FileCode size={16} className="text-blue-400" />}
            <span className="truncate">{file.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
export default FileExplorer;""",
    )

    write_file(
        "src/components/EditorArea.jsx",
        """import React from 'react';
import Editor from '@monaco-editor/react';
import { Save } from 'lucide-react';

const EditorArea = ({ file, content, onSave, onChange }) => {
  if (!file) return <div className="flex-1 flex items-center justify-center bg-bg text-text_dim"><p>No file open</p></div>;
  return (
    <div className="flex flex-col h-full">
      <div className="h-10 bg-input border-b border-border flex items-center justify-between px-4">
        <span className="text-sm font-mono text-white">{file.path}</span>
        <button onClick={() => onSave(content)} className="flex items-center gap-2 text-xs bg-accent hover:bg-accent_hover text-white px-3 py-1 rounded transition-colors"><Save size={14} /> Save</button>
      </div>
      <div className="flex-1">
        <Editor height="100%" theme="vs-dark" path={file.path} defaultLanguage={file.language} value={content} onChange={(value) => onChange(value)} options={{ minimap: { enabled: false }, fontSize: 14, automaticLayout: true }} />
      </div>
    </div>
  );
};
export default EditorArea;""",
    )

    write_file(
        "src/components/TerminalPanel.jsx",
        """import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { Terminal as TerminalIcon, ChevronUp, ChevronDown } from 'lucide-react';

const TerminalPanel = ({ isOpen, onToggle }) => {
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const fitAddonRef = useRef(null);

  useEffect(() => {
    if (!isOpen || xtermRef.current) return;
    const term = new Terminal({
      theme: { background: '#1e1e1e', foreground: '#d4d4d4', cursor: '#ffffff' },
      fontSize: 13, fontFamily: 'Consolas, monospace', cursorBlink: true
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();
    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/terminal`);
    ws.onmessage = (event) => term.write(event.data);
    term.onData((data) => ws.send(data));

    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); ws.close(); term.dispose(); xtermRef.current = null; };
  }, [isOpen]);

  useEffect(() => { if (isOpen && fitAddonRef.current) setTimeout(() => fitAddonRef.current.fit(), 100); }, [isOpen]);

  return (
    <div className="flex flex-col h-full">
      <div className="h-8 bg-input border-b border-border flex items-center justify-between px-4 cursor-pointer hover:bg-border transition-colors" onClick={onToggle}>
        <div className="flex items-center gap-2 text-xs font-bold text-text_dim"><TerminalIcon size={14} /> TERMINAL</div>
        {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </div>
      <div className={`flex-1 bg-black p-2 overflow-hidden ${!isOpen && 'hidden'}`}>
        <div ref={terminalRef} className="h-full w-full" />
      </div>
    </div>
  );
};
export default TerminalPanel;""",
    )

    write_file(
        "src/components/ChatWindow.jsx",
        """import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

const ChatWindow = ({ messages, onSendMessage }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  const handleSubmit = () => { if (!input.trim()) return; onSendMessage(input); setInput(''); };
  return (
    <div className="flex flex-col h-full bg-chat">
      <div className="h-16 border-b border-border flex items-center px-6 bg-bg"><h2 className="text-lg font-bold ml-8">Chat Session</h2></div>
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex flex-col ${msg.sender === 'You' ? 'items-end' : 'items-start'}`}>
            <div className="flex items-center gap-2 mb-1"><span className="text-xs font-bold text-text_dim">{msg.sender}</span><span className="text-[10px] text-text_dim">{msg.timestamp}</span></div>
            <div className={`max-w-[80%] p-4 rounded-lg whitespace-pre-wrap ${msg.sender === 'You' ? 'bg-accent text-white rounded-tr-none' : msg.sender === 'System' ? 'bg-transparent text-text_dim italic border border-border w-full text-center' : 'bg-input text-text_primary rounded-tl-none'}`}>{msg.text}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="p-6 bg-bg border-t border-border">
        <div className="bg-input rounded-lg p-2 border border-border focus-within:border-accent transition-colors">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && e.ctrlKey && handleSubmit()} placeholder="Type a message... (Ctrl+Enter to send)" className="w-full bg-transparent text-white p-2 outline-none resize-none min-h-[80px] font-sans" />
          <div className="flex justify-between items-center px-2 pb-1">
            <div className="text-xs text-text_dim">Supports Markdown</div>
            <button onClick={handleSubmit} className="bg-accent hover:bg-accent_hover text-white px-4 py-2 rounded-md flex items-center gap-2 text-sm font-bold transition-colors"><Send size={16} /> Send</button>
          </div>
        </div>
      </div>
    </div>
  );
};
export default ChatWindow;""",
    )


def run_servers():
    print(">>> [3/4] Starting Backend Server...")
    backend_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(BACKEND_PORT),
        ],
        cwd=os.getcwd(),
    )

    print(">>> [4/4] Starting Frontend Server...")
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"], cwd=os.path.join(os.getcwd(), PROJECT_NAME), shell=True
    )

    print(f"\n{'='*50}")
    print(f"✅ App Running!")
    print(f"👉 Frontend: http://localhost:{FRONTEND_PORT}")
    print(f"👉 Backend:  http://localhost:{BACKEND_PORT}")
    print(f"{'='*50}\n")

    # Open browser after a short delay
    time.sleep(5)
    webbrowser.open(f"http://localhost:{FRONTEND_PORT}")

    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nStopping servers...")
        backend_process.terminate()
        frontend_process.terminate()


if __name__ == "__main__":
    # Ensure we are in the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Check if backend.py is in script_dir (root) or parent (if script is in scripts/)
    if os.path.exists(os.path.join(script_dir, "backend.py")):
        os.chdir(script_dir)
    elif os.path.exists(os.path.join(script_dir, "..", "backend.py")):
        os.chdir(os.path.join(script_dir, ".."))

    install_backend_deps()
    setup_frontend()
    run_servers()
