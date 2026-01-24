import WebContainerService from '../utils/WebContainerService';
import VectorStoreService from '../utils/VectorStoreService';

interface AgentOptions {
  apiBase: string;
  geminiKey?: string;
  deepseekKey?: string;
  githubToken?: string;
  repoUrl?: string;
  onLog: (message: string) => void;
  onEvent?: (event: { type: 'tool'; stage: string; message: string; progress?: number }) => void;
  context?: {
    diagnostics?: string;
    currentFile?: string;
    currentFileContent?: string;
  };
  onSuccess?: (filename: string, content: string) => void;
}

export class AgentLoop {
  static async runTask(task: string, options: AgentOptions) {
    const { onLog, onEvent, context, onSuccess } = options;
    onLog(`[Agent] Starting task: ${task}`);
    onEvent?.({ type: 'tool', stage: 'start', message: `Starting: ${task}`, progress: 0 });

    // Pre-load Vector Store
    const vectorStore = VectorStoreService.getInstance();
    await vectorStore.init();

    // If we have current file content, index it immediately so it's available for RAG
    if (context?.currentFile && context?.currentFileContent) {
        onLog(`[Agent] Indexing current file: ${context.currentFile}`);
        onEvent?.({ type: 'tool', stage: 'index', message: `Indexing current file: ${context.currentFile}` });
        await vectorStore.addFile(context.currentFile, context.currentFileContent);
    }

    let currentTask = task;
    let attempts = 0;
    const maxAttempts = 3;

    while (attempts < maxAttempts) {
      attempts++;
      onLog(`[Agent] Attempt ${attempts}/${maxAttempts}`);
      onEvent?.({ type: 'tool', stage: 'attempt', message: `Attempt ${attempts}/${maxAttempts}`, progress: attempts / maxAttempts });

      // 0. Planning Phase
      onLog('[Agent] Planning...');
      onEvent?.({ type: 'tool', stage: 'plan', message: 'Planning…' });
      const planPrompt = `Task: ${currentTask}\n\nAnalyze the request and return a JSON plan with steps to achieve it. Format: { "steps": ["step 1", "step 2"], "files_to_create": ["filename"], "command_to_run": "cmd" }.`;
      
      const planJson = await this.generatePlan(planPrompt, options);
      if (planJson) {
         onLog(`[Agent] Plan: ${JSON.stringify(planJson, null, 2)}`);
         onEvent?.({ type: 'tool', stage: 'plan', message: 'Plan generated' });
      }

      // 1. Generate Code with RAG
      onLog('[Agent] Generating code...');
      onEvent?.({ type: 'tool', stage: 'generate', message: 'Generating code…' });
      
      // Search for relevant context
      const searchResults = await vectorStore.search(currentTask);
      const contextText = searchResults.map(r => `File: ${r.title}\nContent:\n${r.content}`).join('\n---\n');
      
      let fullPrompt = currentTask;
      
      if (contextText) {
        onLog(`[Agent] Found ${searchResults.length} relevant context chunks.`);
        onEvent?.({ type: 'tool', stage: 'retrieve', message: `Retrieved ${searchResults.length} context chunks` });
        fullPrompt += `\n\nRELEVANT CODEBASE CONTEXT:\n${contextText}`;
      }

      if (context?.diagnostics) {
        onLog('[Agent] Including editor diagnostics.');
        fullPrompt += `\n\nCURRENT EDITOR ERRORS:\n${context.diagnostics}`;
      }

      const code = await this.generateCode(fullPrompt, options);
      if (!code) {
        onLog('[Agent] Failed to generate code.');
        onEvent?.({ type: 'tool', stage: 'error', message: 'Failed to generate code' });
        return;
      }

      // 2. Write to WebContainer
      onLog('[Agent] Writing code to file system...');
      onEvent?.({ type: 'tool', stage: 'write', message: 'Writing code to filesystem…' });
      
      // Extract filename from code or default to 'agent_script.js'
      const filenameMatch = code.match(/\/\/\s*filename:\s*([\w\.-]+)/);
      const filename = filenameMatch ? filenameMatch[1] : 'agent_script.js';
      
      await WebContainerService.writeFile(filename, code);
      onLog(`[Agent] Wrote to ${filename}`);
      onEvent?.({ type: 'tool', stage: 'write', message: `Wrote ${filename}` });

      // Persistence: Write to backend filesystem
      try {
        const saveRes = await fetch(`${options.apiBase}/api/fs/write`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: filename, content: code })
        });
        if (saveRes.ok) {
           onLog(`[Agent] Persisted ${filename} to backend.`);
           onEvent?.({ type: 'tool', stage: 'persist', message: `Persisted ${filename} to backend` });
        } else {
           onLog(`[Agent] Failed to persist ${filename} to backend.`);
           onEvent?.({ type: 'tool', stage: 'persist', message: `Failed to persist ${filename} to backend` });
        }
      } catch (err) {
        onLog(`[Agent] Error persisting ${filename}: ${err}`);
        onEvent?.({ type: 'tool', stage: 'persist', message: `Error persisting ${filename}` });
      }

      // Index the NEW code so subsequent steps know about it
      await vectorStore.addFile(filename, code);

      // 3. Exec
      // Determine command. Default to node for .js
      const command = 'node';
      const args = [filename];

      onLog(`[Agent] Running command: ${command} ${args.join(' ')}`);
      onEvent?.({ type: 'tool', stage: 'exec', message: `Running: ${command} ${args.join(' ')}` });
      
      let output = '';
      const exitCode = await WebContainerService.runCommand(command, args, (data) => {
        output += data;
        onLog(`[Output] ${data}`);
      });

      // 4. Verify
      if (exitCode === 0) {
        onLog('[Agent] Task completed successfully!');
        onEvent?.({ type: 'tool', stage: 'done', message: 'Task completed successfully', progress: 1 });
        if (onSuccess) {
            onSuccess(filename, code);
        }
        return;
      } else {
        onLog(`[Agent] Command failed with exit code ${exitCode}. Analyzing error...`);
        onEvent?.({ type: 'tool', stage: 'error', message: `Command failed (exit ${exitCode})` });
        // Feed error back to AI
        currentTask = `The previous code for task "${task}" failed with this error:\n${output}\n\nPlease fix the code. Ensure the first line is "// filename: ${filename}".`;
      }
    }
    
    onLog('[Agent] Max attempts reached. Task failed.');
    onEvent?.({ type: 'tool', stage: 'error', message: 'Max attempts reached. Task failed.' });
  }

  static async generatePlan(prompt: string, options: AgentOptions): Promise<any> {
    try {
        const res = await fetch(`${options.apiBase}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: `${prompt}\n\nReturn ONLY the JSON.`,
            model: 'gemini',
            gemini_key: options.geminiKey,
            deepseek_key: options.deepseekKey
          })
        });
        const data = await res.json();
        const text = data.content || data.text;
        if (!text) return null;
        const match = text.match(/```(?:json)?\n([\s\S]*?)```/);
        const jsonStr = match ? match[1] : text;
        return JSON.parse(jsonStr);
    } catch (e) {
        console.warn('Failed to generate plan JSON', e);
        return null;
    }
  }

  static async generateCode(prompt: string, options: AgentOptions): Promise<string> {
    try {
      const res = await fetch(`${options.apiBase}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify({
          message: `${prompt}\n\nIMPORTANT: Return ONLY the code. If you create a file, add a comment on the first line like "// filename: myscript.js".`,
          model: 'gemini',
          gemini_key: options.geminiKey,
          deepseek_key: options.deepseekKey,
          repo_url: options.repoUrl
        })
      });
      
      if (!res.ok) throw new Error(res.statusText);
      
      const data = await res.json();
      const text = data.content || data.text || '';
      
      // Extract code block
      const match = text.match(/```(?:javascript|js|typescript|ts)?\n([\s\S]*?)```/);
      return match ? match[1] : text;
    } catch (e) {
      console.error(e);
      return '';
    }
  }
}
