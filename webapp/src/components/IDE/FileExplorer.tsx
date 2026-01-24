import React from 'react';

interface FileEntry {
  name: string;
  type: 'file' | 'directory';
  path: string;
}

interface FileExplorerProps {
  files: FileEntry[];
  activeFile: string | null;
  onFileClick: (path: string) => void;
  onRefresh: () => void;
  onCloneRepo: () => void;
  onUploadFile: (event: React.ChangeEvent<HTMLInputElement>) => void;
  isLoading: boolean;
  repoUrl: string;
}

const FileExplorer = ({
  files,
  activeFile,
  onFileClick,
  onRefresh,
  onCloneRepo,
  onUploadFile,
  isLoading,
  repoUrl,
}: FileExplorerProps) => {
  return (
    <div className="file-explorer">
      <h3>Workspace</h3>
      <div className="file-explorer-actions">
        <button className="refresh-btn" onClick={onRefresh} disabled={isLoading}>
          ↻ Refresh
        </button>
        <button onClick={onCloneRepo} disabled={isLoading || !repoUrl}>
          {isLoading ? 'Cloning...' : 'Clone GitHub Repo'}
        </button>
        <input
          type="file"
          id="upload-zip"
          style={{ display: 'none' }}
          onChange={onUploadFile}
          disabled={isLoading}
        />
        <button onClick={() => document.getElementById('upload-zip')?.click()} disabled={isLoading}>
          Upload Zip/File
        </button>
      </div>
      <ul>
        {files.map((file, idx) => (
          <li
            key={idx}
            className={`${file.type} ${activeFile === file.path ? 'active' : ''}`}
            onClick={() => file.type === 'file' && onFileClick(file.path)}
          >
            {file.type === 'directory' ? '📁' : '📄'} {file.name}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FileExplorer;
