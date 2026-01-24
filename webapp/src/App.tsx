import { useState, useEffect, useRef } from 'react';
import * as MonacoEditor from 'monaco-editor';
import DiffModal from './components/DiffModal';
import { AgentLoop } from './agent/AgentLoop';
import VectorStoreService from './utils/VectorStoreService';
import WebContainerService from './utils/WebContainerService';
import { Sidebar } from './components/Layout/Sidebar';
import { EditorPanel } from './components/Editor/EditorPanel';
import { ChatInterface } from './components/Chat/ChatInterface';
import { SettingsModal } from './components/SettingsModal';
import { API_BASE } from './api/client';
import * as api from './api/routes';
import { useChat } from './hooks/useChat';
import { useSettings } from './hooks/useSettings';
import { useWorkspaceFs } from './hooks/useWorkspaceFs';
import { useSessions } from './hooks/useSessions';
import { ContextOrchestrator, type ContextPack } from './context/ContextOrchestrator';

function App() {
  const chat = useChat();
  const settings = useSettings();
  const workspace = useWorkspaceFs();
  const sessions = useSessions();

  const [isLoading, setIsLoading] = useState(false);
  const [pinnedFiles, setPinnedFiles] = useState<string[]>(sessions.currentSession.pinnedFiles);
  const [lastContextPack, setLastContextPack] = useState<ContextPack | null>(null);
  const orchestratorRef = useRef<ContextOrchestrator | null>(null);
  const isHydratingSessionRef = useRef(false);
  const editorRef = useRef<MonacoEditor.editor.IStandaloneCodeEditor | null>(null);
  const geminiKeyRef = useRef(settings.geminiKey);
  const deepseekKeyRef = useRef(settings.deepseekKey);
  const lastCompletionTsRef = useRef(0);

  useEffect(() => {
    geminiKeyRef.current = settings.geminiKey;
  }, [settings.geminiKey]);

  useEffect(() => {
    deepseekKeyRef.current = settings.deepseekKey;
  }, [settings.deepseekKey]);

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
    VectorStoreService.getInstance().indexWorkspace(API_BASE);
  }, []);

  useEffect(() => {
    isHydratingSessionRef.current = true;
    chat.setMessages(sessions.currentSession.messages);
    chat.setSelectedModel(sessions.currentSession.model);
    setPinnedFiles(sessions.currentSession.pinnedFiles);
    queueMicrotask(() => {
      isHydratingSessionRef.current = false;
    });
  }, [sessions.currentSessionId]);

  useEffect(() => {
    if (isHydratingSessionRef.current) return;
    sessions.updateSession(sessions.currentSessionId, {
      messages: chat.messages,
      model: chat.selectedModel,
      pinnedFiles
    });
  }, [chat.messages, chat.selectedModel, pinnedFiles, sessions.currentSessionId]);

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
    chat.pushSystemMessage(`Running ${tool}...`);

    try {
      const data = await api.runTool({ tool, code, gemini_key: settings.geminiKey });
      chat.pushMessage({
        sender: 'AI Tool',
        text: typeof data?.result === 'string' ? data.result : JSON.stringify(data),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      });
    } catch (error) {
      chat.pushSystemMessage(`Error running tool ${tool}: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditorDidMount = (editor: MonacoEditor.editor.IStandaloneCodeEditor, monaco: typeof MonacoEditor) => {
    editorRef.current = editor;
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      void workspace.saveFile({
        getContent: () => (editorRef.current ? editorRef.current.getValue() : workspace.fileContent)
      });
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
          const data = await api.completion({
            code: fullText,
            language: model.getLanguageId(),
            position: offset,
            gemini_key: geminiKeyRef.current,
            deepseek_key: deepseekKeyRef.current
          });
          if (data.completion) {
            return {
              items: [{
                insertText: data.completion
              }]
            };
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
      geminiKey: settings.geminiKey,
      deepseekKey: settings.deepseekKey,
      githubToken: settings.githubToken,
      repoUrl: settings.repoUrl,
      onLog: (msg) => setAgentLogs(prev => [...prev, msg]),
      onEvent: (evt) => {
        if (evt.type === 'tool') {
          chat.pushSystemMessage(`[Tool:${evt.stage}] ${evt.message}`);
        }
      },
      context: {
        diagnostics,
        currentFile: workspace.activeFile || undefined,
        currentFileContent: workspace.fileContent
      },
      onSuccess: (filename, content) => {
        const isCurrent = workspace.activeFile && (workspace.activeFile.endsWith(filename) || workspace.activeFile === filename);
        const original = isCurrent ? workspace.fileContent : ''; 
        setDiffOriginal(original);
        setDiffModified(content);
        setDiffFilename(filename);
        setShowDiff(true);
      }
    });
  };

  const sendMessage = async () => {
    if (!orchestratorRef.current) orchestratorRef.current = new ContextOrchestrator();

    const pack = await orchestratorRef.current.buildContextPack({
      query: chat.input,
      messages: chat.messages,
      pinnedFiles
    });
    setLastContextPack(pack);

    const historyOverride = [
      { role: 'system', content: pack.systemPrompt },
      ...chat.messages.map((m) => ({
        role: m.sender === 'You' ? 'user' : (m.sender === 'System' ? 'system' : 'assistant'),
        content: m.text
      }))
    ];

    await chat.sendMessage({
      geminiKey: settings.geminiKey,
      deepseekKey: settings.deepseekKey,
      setIsLoading,
      historyOverride,
      contextPackId: pack.id
    });
  };

  const cloneRepo = async () => {
    if (!settings.repoUrl) {
      alert("Please enter a GitHub repository URL.");
      return;
    }
    setIsLoading(true);
    chat.pushSystemMessage(`Cloning ${settings.repoUrl}...`);

    try {
      const data = await api.cloneRepo({ repo_url: settings.repoUrl });
      chat.pushSystemMessage(`Clone successful: ${data.path}`);
      workspace.fetchFiles();
    } catch (error: unknown) {
      chat.pushSystemMessage(`Clone failed: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const uploadFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsLoading(true);
    try {
      await api.uploadFile(file);
      workspace.fetchFiles();
    } catch {}
    setIsLoading(false);
  };

  const togglePinFile = (path: string) => {
    setPinnedFiles((prev) => (prev.includes(path) ? prev.filter((p) => p !== path) : [path, ...prev]));
  };

  return (
    <div className="flex h-screen w-screen bg-background text-foreground overflow-hidden">
      <Sidebar 
        files={workspace.files}
        activeFile={workspace.activeFile}
        onFileClick={workspace.openFile}
        onRefresh={workspace.fetchFiles}
        onSettingsClick={() => settings.setShowSettings(true)}
        onCloneClick={cloneRepo}
        onUploadClick={uploadFile}
        sessions={sessions.sessions.map((s) => ({ id: s.id, name: s.name }))}
        currentSessionId={sessions.currentSessionId}
        onSessionChange={sessions.setCurrentSessionId}
        onCreateSession={() => sessions.createSession()}
        pinnedFiles={pinnedFiles}
        onTogglePin={togglePinFile}
        className="w-64 flex-shrink-0"
      />

      <div className="flex-1 flex min-w-0">
        <EditorPanel 
          activeFile={workspace.activeFile}
          fileContent={workspace.fileContent}
          setFileContent={workspace.setFileContent}
          onSave={() => workspace.saveFile({ getContent: () => (editorRef.current ? editorRef.current.getValue() : workspace.fileContent) })}
          onRunTool={runTool}
          onOpenAgent={() => setShowAgentTaskModal(true)}
          onOpenVSCode={workspace.openInVSCode}
          showTerminal={showTerminal}
          setShowTerminal={setShowTerminal}
          agentLogs={agentLogs}
          handleEditorDidMount={handleEditorDidMount}
          className="flex-1 border-r border-border"
          diagnostics={diagnostics}
        />

        <ChatInterface 
          messages={chat.messages}
          isLoading={isLoading}
          input={chat.input}
          setInput={chat.setInput}
          onSend={sendMessage}
          onCancel={chat.isStreaming ? chat.cancel : undefined}
          onRegenerate={chat.canRegenerate ? chat.regenerate : undefined}
          canRegenerate={chat.canRegenerate}
          contextPack={lastContextPack}
          selectedModel={chat.selectedModel}
          setSelectedModel={chat.setSelectedModel}
          className="w-96 flex-shrink-0"
        />
      </div>

      {settings.showSettings && (
        <SettingsModal 
          onClose={() => settings.setShowSettings(false)}
          geminiKey={settings.geminiKey}
          setGeminiKey={settings.setGeminiKey}
          deepseekKey={settings.deepseekKey}
          setDeepseekKey={settings.setDeepseekKey}
          githubToken={settings.githubToken}
          setGithubToken={settings.setGithubToken}
          repoUrl={settings.repoUrl}
          setRepoUrl={settings.setRepoUrl}
          onSave={settings.saveSettings}
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
          onRunChecks={async () => {
            const code = await WebContainerService.runWebappTests();
            return code === 0;
          }}
          provenance={{
            sessionId: sessions.currentSessionId,
            model: chat.selectedModel,
            contextPackId: lastContextPack?.id || null,
            createdAt: Date.now()
          }}
          onAccept={() => {
            workspace.setFileContent(diffModified);
            setShowDiff(false);
          }}
          onReject={() => setShowDiff(false)}
        />
      )}
    </div>
  );
}

export default App;
