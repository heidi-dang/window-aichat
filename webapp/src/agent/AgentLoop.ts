import WebContainerService from '../utils/WebContainerService';
import VectorStoreService from '../utils/VectorStoreService';

interface AgentOptions {
  apiBase: string;
  geminiKey?: string;
  deepseekKey?: string;
  githubToken?: string;
  repoUrl?: string;
  onLog: (message: string) => void;
  context?: {
    diagnostics?: string;
    currentFile?: string;
    currentFileContent?: string;
  };
}

export class AgentLoop {
  static async runTask(task: string, options: AgentOptions) {
    const { onLog, context } = options;
    onLog(`[Agent] Starting task: ${task}`);

    // Pre-load Vector Store
    const vectorStore = VectorStoreService.getInstance();
    await vectorStore.init();

    // If we have current file content, index it immediately so it's available for RAG
    if (context?.currentFile && context?.currentFileContent) {
        onLog(`[Agent] Indexing current file: ${context.currentFile}`);
        await vectorStore.addFile(context.currentFile, context.currentFileContent);
    }

    let currentTask = task;
    let attempts = 0;
    const maxAttempts = 3;

    while (attempts < maxAttempts) {
      attempts++;
      onLog(`[Agent] Attempt ${attempts}/${maxAttempts}`);

      // 1. Generate Code with RAG
      onLog('[Agent] Generating code...');
      
      // Search for relevant context
      const searchResults = await vectorStore.search(currentTask);
      const contextText = searchResults.map(r => `File: ${r.title}\nContent:\n${r.content}`).join('\n---\n');
      
      let fullPrompt = currentTask;
      
      if (contextText) {
        onLog(`[Agent] Found ${searchResults.length} relevant context chunks.`);
        fullPrompt += `\n\nRELEVANT CODEBASE CONTEXT:\n${contextText}`;
      }

      if (context?.diagnostics) {
        onLog('[Agent] Including editor diagnostics.');
        fullPrompt += `\n\nCURRENT EDITOR ERRORS:\n${context.diagnostics}`;
      }

      const code = await this.generateCode(fullPrompt, options);
      if (!code) {
        onLog('[Agent] Failed to generate code.');
        return;
      }

      // 2. Write to WebContainer
      onLog('[Agent] Writing code to file system...');
      
      // Extract filename from code or default to 'agent_script.js'
      const filenameMatch = code.match(/\/\/\s*filename:\s*([\w\.-]+)/);
      const filename = filenameMatch ? filenameMatch[1] : 'agent_script.js';
      
      await WebContainerService.writeFile(filename, code);
      onLog(`[Agent] Wrote to ${filename}`);

      // Index the NEW code so subsequent steps know about it
      await vectorStore.addFile(filename, code);

      // 3. Exec
      // Determine command. Default to node for .js
      const command = 'node';
      const args = [filename];

      onLog(`[Agent] Running command: ${command} ${args.join(' ')}`);
      
      let output = '';
      const exitCode = await WebContainerService.runCommand(command, args, (data) => {
        output += data;
        onLog(`[Output] ${data}`);
      });

      // 4. Verify
      if (exitCode === 0) {
        onLog('[Agent] Task completed successfully!');
        return;
      } else {
        onLog(`[Agent] Command failed with exit code ${exitCode}. Analyzing error...`);
        // Feed error back to AI
        currentTask = `The previous code for task "${task}" failed with this error:\n${output}\n\nPlease fix the code. Ensure the first line is "// filename: ${filename}".`;
      }
    }
    
    onLog('[Agent] Max attempts reached. Task failed.');
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
      const text = data.text;
      
      // Extract code block
      const match = text.match(/```(?:javascript|js|typescript|ts)?\n([\s\S]*?)```/);
      return match ? match[1] : text;
    } catch (e) {
      console.error(e);
      return '';
    }
  }
}
