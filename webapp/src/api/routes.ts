import { apiFetchJson } from './client';

export type FileEntry = {
  name: string;
  type: 'file' | 'directory';
  path: string;
};

export type ChatMessage = {
  role: string;
  content: string;
};

export type ChatResponse = {
  role: string;
  content: string;
  model: string;
};

export type CompletionResponse = {
  completion: string;
};

export type CloneResponse = {
  status: string;
  path: string;
};

export type FileReadResponse = {
  content: string;
};

export type FileWriteResponse = {
  status: string;
  path: string;
};

export async function listFiles(): Promise<FileEntry[]> {
  return apiFetchJson<FileEntry[]>('/api/fs/list');
}

export async function readFile(path: string): Promise<FileReadResponse> {
  return apiFetchJson<FileReadResponse>('/api/fs/read', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
}

export async function writeFile(path: string, content: string): Promise<FileWriteResponse> {
  return apiFetchJson<FileWriteResponse>('/api/fs/write', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, content })
  });
}

export async function uploadFile(file: File): Promise<FileWriteResponse> {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetchJson<FileWriteResponse>('/api/fs/upload', {
    method: 'POST',
    body: formData
  });
}

export async function chat(req: {
  message: string;
  history: ChatMessage[];
  model: string;
  gemini_key?: string;
  deepseek_key?: string;
}): Promise<ChatResponse> {
  return apiFetchJson<ChatResponse>('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
}

export async function completion(req: {
  code: string;
  language: string;
  position: number;
  gemini_key?: string;
  deepseek_key?: string;
}): Promise<CompletionResponse> {
  return apiFetchJson<CompletionResponse>('/api/completion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
}

export async function runTool(req: {
  tool: string;
  code: string;
  gemini_key?: string;
  deepseek_key?: string;
}): Promise<{ result: string }> {
  return apiFetchJson<{ result: string }>('/api/tool', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
}

export async function cloneRepo(req: { repo_url: string; target_dir?: string }): Promise<CloneResponse> {
  return apiFetchJson<CloneResponse>('/api/git/clone', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
}

export async function openVSCode(path: string): Promise<{ status: string; message?: string }> {
  return apiFetchJson<{ status: string; message?: string }>('/api/system/open-vscode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
}

