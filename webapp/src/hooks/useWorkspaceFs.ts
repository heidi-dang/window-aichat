import { useEffect, useState } from 'react';

import * as api from '../api/routes';

export function useWorkspaceFs() {
  const [files, setFiles] = useState<api.FileEntry[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('// Select a file to edit');

  const fetchFiles = async () => {
    try {
      const data = await api.listFiles();
      setFiles(data);
    } catch (error: unknown) {
      console.error('Failed to fetch files', error);
    }
  };

  useEffect(() => {
    const id = window.setTimeout(() => {
      void fetchFiles();
    }, 0);
    return () => window.clearTimeout(id);
  }, []);

  const openFile = async (path: string) => {
    try {
      const data = await api.readFile(path);
      setFileContent(data.content);
      setActiveFile(path);
    } catch (error: unknown) {
      alert(`Failed to read file: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const saveFile = async (opts: { getContent: () => string }) => {
    if (!activeFile) return;
    const content = opts.getContent();
    try {
      await api.writeFile(activeFile, content);
    } catch (error: unknown) {
      alert(`Failed to save file: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const openInVSCode = async () => {
    if (!activeFile) return;
    const normalized = activeFile.replace(/\\/g, '/');
    const vscodeUrl = `vscode://file/${normalized}`;
    try {
      await api.openVSCode(activeFile);
    } catch { /* no-op */ }
    try {
      window.location.href = vscodeUrl;
    } catch {
      alert(`Failed to open VS Code: ${normalized}`);
    }
  };

  return {
    files,
    setFiles,
    activeFile,
    setActiveFile,
    fileContent,
    setFileContent,
    fetchFiles,
    openFile,
    saveFile,
    openInVSCode
  };
}
