import React from 'react';
import Editor from '@monaco-editor/react';
import { Save, FileCode, Terminal as TerminalIcon, Maximize2, ExternalLink } from 'lucide-react';
import type { OnMount } from '@monaco-editor/react';
import { cn } from '../../lib/utils';
import Terminal from '../Terminal';

interface EditorPanelProps {
  activeFile: string | null;
  fileContent: string;
  setFileContent: (val: string) => void;
  onSave: () => void;
  onRunTool: (tool: string) => void;
  onOpenAgent: () => void;
  onOpenVSCode: () => void;
  showTerminal: boolean;
  setShowTerminal: (val: boolean) => void;
  agentLogs: string[];
  handleEditorDidMount: OnMount;
  className?: string;
  diagnostics?: string;
}

export const EditorPanel = React.memo(function EditorPanel({
  activeFile,
  fileContent,
  setFileContent,
  onSave,
  onRunTool,
  onOpenAgent,
  onOpenVSCode,
  showTerminal,
  setShowTerminal,
  agentLogs,
  handleEditorDidMount,
  className,
  diagnostics
}: EditorPanelProps) {
  
  const getLanguage = (filename: string) => {
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

  return (
    <div className={cn("flex flex-col h-full bg-[#1e1e1e]", className)}>
      {/* Editor Tabs / Toolbar */}
      <div className="flex items-center justify-between bg-[#252526] border-b border-[#333] h-10 px-4">
        <div className="flex items-center gap-2 text-sm text-[#cccccc]">
          <FileCode className="w-4 h-4 text-blue-400" />
          <span className="font-medium">{activeFile || 'No file selected'}</span>
          {activeFile && <span className="text-xs text-muted-foreground ml-2 opacity-50">({getLanguage(activeFile)})</span>}
        </div>
        
        <div className="flex items-center gap-1">
           <button onClick={() => onRunTool('analyze')} className="p-1.5 hover:bg-[#333] rounded text-gray-300" title="Analyze">
             🔍
           </button>
           <button onClick={() => onRunTool('explain')} className="p-1.5 hover:bg-[#333] rounded text-gray-300" title="Explain">
             📖
           </button>
           <button onClick={onOpenAgent} className="p-1.5 hover:bg-[#333] rounded text-gray-300" title="Agent Task">
             🤖
           </button>
           <div className="w-px h-4 bg-[#444] mx-1" />
           <button onClick={onOpenVSCode} className="p-1.5 hover:bg-[#333] rounded text-gray-300" title="Open in VS Code">
             <ExternalLink className="w-4 h-4" />
           </button>
           <button onClick={onSave} disabled={!activeFile} className="p-1.5 hover:bg-[#333] rounded text-gray-300 disabled:opacity-50" title="Save">
             <Save className="w-4 h-4" />
           </button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 relative min-h-0">
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
            fontFamily: "'Fira Code', Consolas, 'Courier New', monospace",
            fontLigatures: true,
          }}
        />
      </div>

      {/* Diagnostics / Status Bar */}
      <div className="h-6 bg-[#007acc] text-white text-xs flex items-center px-3 justify-between">
         <div className="flex items-center">
            <span>{activeFile ? 'Ready' : 'Empty Workspace'}</span>
            {diagnostics && <span className="ml-4 text-yellow-200 truncate max-w-[300px]" title={diagnostics}>⚠ {diagnostics.split('\n')[0]}</span>}
         </div>
         <div className="flex items-center gap-4">
            <button onClick={() => setShowTerminal(!showTerminal)} className="flex items-center gap-1 hover:bg-white/10 px-2 h-full">
              <TerminalIcon className="w-3 h-3" /> {showTerminal ? 'Hide Terminal' : 'Show Terminal'}
            </button>
            <span>UTF-8</span>
         </div>
      </div>

      {/* Terminal Panel */}
      {showTerminal && (
        <div className="h-[40%] border-t border-[#333] bg-[#1e1e1e] flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 bg-[#252526] border-b border-[#333]">
             <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Terminal</span>
             <button onClick={() => setShowTerminal(false)} className="text-gray-400 hover:text-white"><Maximize2 className="w-3 h-3 rotate-45" /></button>
          </div>
          <div className="flex-1 overflow-hidden flex">
            <div className="flex-1 border-r border-[#333] p-2 overflow-hidden relative">
               <Terminal />
            </div>
            <div className="w-1/3 bg-[#1e1e1e] p-2 overflow-y-auto font-mono text-xs text-gray-400 border-l border-[#333]">
               <div className="mb-2 font-bold text-gray-500">Agent Logs</div>
               {agentLogs.length === 0 && <span className="opacity-50 italic">No logs yet...</span>}
               {agentLogs.map((log, i) => (
                 <div key={i} className="mb-1 border-b border-[#333]/50 pb-1">{log}</div>
               ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
