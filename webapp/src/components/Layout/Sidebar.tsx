import React from 'react';
import { Folder, File, Settings, RefreshCw, Upload, Github, Plus, Star } from 'lucide-react';
import { cn } from '../../lib/utils';

interface FileEntry {
  name: string;
  type: 'file' | 'directory';
  path: string;
}

interface ProjectSession {
  id: string;
  name: string;
}

interface SidebarProps {
  files: FileEntry[];
  activeFile: string | null;
  onFileClick: (path: string) => void;
  onRefresh: () => void;
  onSettingsClick: () => void;
  onCloneClick: () => void;
  onUploadClick: (e: React.ChangeEvent<HTMLInputElement>) => void;
  sessions: ProjectSession[];
  currentSessionId: string;
  onSessionChange: (id: string) => void;
  onCreateSession: () => void;
  pinnedFiles: string[];
  onTogglePin: (path: string) => void;
  className?: string;
}

export const Sidebar = React.memo(function Sidebar({
  files,
  activeFile,
  onFileClick,
  onRefresh,
  onSettingsClick,
  onCloneClick,
  onUploadClick,
  sessions,
  currentSessionId,
  onSessionChange,
  onCreateSession,
  pinnedFiles,
  onTogglePin,
  className
}: SidebarProps) {
  return (
    <div className={cn("flex flex-col h-full bg-card border-r border-border", className)}>
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h2 className="font-semibold text-lg tracking-tight">AI IDE</h2>
        <button onClick={onSettingsClick} className="p-2 hover:bg-accent rounded-md transition-colors">
          <Settings className="w-4 h-4" />
        </button>
      </div>

      <div className="p-3 border-b border-border flex items-center gap-2">
        <select
          value={currentSessionId}
          onChange={(e) => onSessionChange(e.target.value)}
          className="flex-1 text-xs bg-background border border-border rounded px-2 py-2 focus:outline-none focus:ring-1 focus:ring-ring"
        >
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <button
          onClick={onCreateSession}
          className="p-2 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80"
          title="New session"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="p-2 flex gap-2 border-b border-border bg-muted/30">
        <button 
          onClick={onCloneClick}
          className="flex-1 flex items-center justify-center gap-2 text-xs bg-primary text-primary-foreground px-3 py-2 rounded hover:opacity-90 transition-opacity"
        >
          <Github className="w-3 h-3" /> Clone
        </button>
        <label className="flex-1 flex items-center justify-center gap-2 text-xs bg-secondary text-secondary-foreground px-3 py-2 rounded hover:bg-secondary/80 cursor-pointer transition-colors">
          <Upload className="w-3 h-3" /> Upload
          <input type="file" className="hidden" onChange={onUploadClick} />
        </label>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <div className="flex items-center justify-between mb-2 px-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Workspace</span>
          <button onClick={onRefresh} className="p-1 hover:bg-accent rounded transition-colors">
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
        <ul className="space-y-0.5">
          {files.map((file, idx) => (
            <li 
              key={idx}
              className={cn(
                "flex items-center gap-2 px-2 py-1.5 rounded-md text-sm cursor-pointer transition-colors",
                activeFile === file.path 
                  ? "bg-accent text-accent-foreground font-medium" 
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              )}
              onClick={() => file.type === 'file' && onFileClick(file.path)}
            >
              {file.type === 'directory' ? <Folder className="w-4 h-4 text-blue-400" /> : <File className="w-4 h-4" />}
              <span className="truncate">{file.name}</span>
              {file.type === 'file' && (
                <button
                  className={cn(
                    "ml-auto p-1 rounded hover:bg-accent",
                    pinnedFiles.includes(file.path) ? "text-yellow-400" : "text-muted-foreground"
                  )}
                  title={pinnedFiles.includes(file.path) ? "Unpin file" : "Pin file"}
                  onClick={(e) => {
                    e.stopPropagation();
                    onTogglePin(file.path);
                  }}
                >
                  <Star className="w-3.5 h-3.5" />
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
});
