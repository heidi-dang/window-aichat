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
npm install lucide-react

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
        border: "#333333"
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

# --- Main App Component ---
cat <<EOF > src/App.jsx
import React, { useState, useRef, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [messages, setMessages] = useState([
    { id: 1, sender: 'System', text: 'Welcome to AI Chat Web! Connect to Gemini or DeepSeek to start.', timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }
  ]);
  const [config, setConfig] = useState({
    model: 'both',
    repoUrl: '',
    geminiKey: '',
    deepseekKey: ''
  });

  const handleSendMessage = async (text) => {
    // Add User Message
    const newUserMsg = { 
      id: Date.now(), 
      sender: 'You', 
      text, 
      timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) 
    };
    setMessages(prev => [...prev, newUserMsg]);

    // Simulate AI Response (Placeholder for Backend API)
    setTimeout(() => {
      const aiResponse = {
        id: Date.now() + 1,
        sender: config.model === 'both' ? 'Gemini & DeepSeek' : config.model === 'gemini' ? 'Gemini' : 'DeepSeek',
        text: \`This is a simulated response from \${config.model}. \n\nTo make this functional, connect this React frontend to your Python backend via a REST API (e.g., FastAPI).\`,
        timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
      };
      setMessages(prev => [...prev, aiResponse]);
    }, 1000);
  };

  return (
    <div className="flex h-screen w-screen bg-bg text-text_primary overflow-hidden">
      {/* Sidebar */}
      <div className={\`\${isSidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 ease-in-out overflow-hidden border-r border-border bg-sidebar\`}>
        <Sidebar config={config} setConfig={setConfig} />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full relative">
        {/* Toggle Button */}
        <button 
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="absolute top-4 left-4 z-10 p-2 bg-input rounded-md hover:bg-border transition-colors"
        >
          {isSidebarOpen ? '◀' : '▶'}
        </button>

        <ChatWindow messages={messages} onSendMessage={handleSendMessage} />
      </div>
    </div>
  );
}

export default App;
EOF

# --- Sidebar Component ---
mkdir -p src/components
cat <<EOF > src/components/Sidebar.jsx
import React from 'react';
import { Settings, Github, Cpu, Activity, Trash2 } from 'lucide-react';

const Sidebar = ({ config, setConfig }) => {
  return (
    <div className="flex flex-col h-full p-5 min-w-[320px]">
      <div className="mb-8">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Cpu className="text-accent" />
          AI Agent Workspace
        </h1>
      </div>

      {/* Model Selection */}
      <div className="mb-6">
        <label className="text-xs font-bold text-text_dim mb-2 block">AI MODEL</label>
        <select 
          value={config.model}
          onChange={(e) => setConfig({...config, model: e.target.value})}
          className="w-full bg-input text-white p-2 rounded border border-border focus:border-accent outline-none"
        >
          <option value="gemini">Gemini 2.0 Flash</option>
          <option value="deepseek">DeepSeek Chat</option>
          <option value="both">Both Models</option>
        </select>
      </div>

      {/* GitHub Context */}
      <div className="mb-6">
        <label className="text-xs font-bold text-text_dim mb-2 block">GITHUB CONTEXT</label>
        <div className="flex flex-col gap-2">
          <input 
            type="text" 
            placeholder="https://github.com/owner/repo"
            value={config.repoUrl}
            onChange={(e) => setConfig({...config, repoUrl: e.target.value})}
            className="w-full bg-input text-white p-2 rounded border border-border focus:border-accent outline-none text-sm"
          />
          <button className="w-full bg-input hover:bg-border text-text_primary py-2 rounded text-sm font-medium transition-colors flex items-center justify-center gap-2">
            <Github size={16} />
            Fetch Repository
          </button>
        </div>
      </div>

      {/* System Status */}
      <div className="mb-auto">
        <label className="text-xs font-bold text-text_dim mb-2 block">SYSTEM STATUS</label>
        <div className="bg-input p-3 rounded border border-border">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-green-500"></div>
            <span className="text-sm">Gemini API</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-500"></div>
            <span className="text-sm">DeepSeek API</span>
          </div>
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="flex flex-col gap-2 mt-4">
        <button className="w-full bg-input hover:bg-border text-text_primary py-2 rounded text-sm flex items-center justify-center gap-2">
          <Settings size={16} />
          Settings
        </button>
        <button className="w-full bg-input hover:bg-border text-red-400 py-2 rounded text-sm flex items-center justify-center gap-2">
          <Trash2 size={16} />
          Clear Chat
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
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