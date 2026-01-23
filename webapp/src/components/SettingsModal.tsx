import { X } from 'lucide-react';

interface SettingsModalProps {
  onClose: () => void;
  geminiKey: string;
  setGeminiKey: (val: string) => void;
  deepseekKey: string;
  setDeepseekKey: (val: string) => void;
  githubToken: string;
  setGithubToken: (val: string) => void;
  repoUrl: string;
  setRepoUrl: (val: string) => void;
  onSave: () => void;
}

export function SettingsModal({
  onClose,
  geminiKey,
  setGeminiKey,
  deepseekKey,
  setDeepseekKey,
  githubToken,
  setGithubToken,
  repoUrl,
  setRepoUrl,
  onSave
}: SettingsModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-lg shadow-xl border border-border flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="font-semibold">Settings</h2>
          <button onClick={onClose} className="p-1 hover:bg-muted rounded text-muted-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="p-4 space-y-4 overflow-y-auto">
          <div className="space-y-2">
            <label className="text-sm font-medium">Gemini API Key</label>
            <input 
              type="password" 
              value={geminiKey} 
              onChange={(e) => setGeminiKey(e.target.value)}
              className="w-full bg-muted border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="sk-..."
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium">DeepSeek API Key</label>
            <input 
              type="password" 
              value={deepseekKey} 
              onChange={(e) => setDeepseekKey(e.target.value)}
              className="w-full bg-muted border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="sk-..."
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">GitHub Token</label>
            <input 
              type="password" 
              value={githubToken} 
              onChange={(e) => setGithubToken(e.target.value)}
              className="w-full bg-muted border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="ghp_..."
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Repository URL</label>
            <input 
              type="text" 
              value={repoUrl} 
              onChange={(e) => setRepoUrl(e.target.value)}
              className="w-full bg-muted border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="https://github.com/owner/repo"
            />
          </div>
        </div>

        <div className="p-4 border-t border-border flex justify-end">
          <button 
            onClick={onSave}
            className="bg-primary text-primary-foreground px-4 py-2 rounded hover:opacity-90 transition-opacity text-sm font-medium"
          >
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  );
}
