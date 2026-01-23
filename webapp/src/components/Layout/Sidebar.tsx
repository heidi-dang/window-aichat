import React from 'react';
import { Folder, File, Settings, RefreshCw, Upload, Github } from 'lucide-react';
import { cn } from '../../lib/utils';

interface FileEntry {
  name: string;
  type: 'file' | 'directory';
  path: string;
}

interface SidebarProps {
  files: FileEntry[];
  activeFile: string | null;
  onFileClick: (path: string) => void;
  onRefresh: () => void;
  onSettingsClick: () => void;
  onCloneClick: () => void;
  onUploadClick: (e: React.ChangeEvent<HTMLInputElement>) => void;
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
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
});
