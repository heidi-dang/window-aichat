import Editor from '@monaco-editor/react'; // Removed OnMount
import type * as MonacoEditor from 'monaco-editor';

interface MonacoWrapperProps {
  fileContent: string;
  activeFile: string | null;
  onMount: (editor: MonacoEditor.editor.IStandaloneCodeEditor, monaco: typeof MonacoEditor) => void;
  onChange: (value: string | undefined) => void;
}

const MonacoWrapper = ({ fileContent, activeFile, onMount, onChange }: MonacoWrapperProps) => {
  const getLanguage = (filename: string | null) => {
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
    <Editor
      height="100%"
      language={getLanguage(activeFile)}
      value={fileContent}
      theme="vs-dark"
      onMount={onMount}
      onChange={onChange}
      options={{
        minimap: { enabled: true },
        fontSize: 14,
        wordWrap: 'on',
        automaticLayout: true,
        padding: { top: 10 }
      }}
    />
  );
};

export default MonacoWrapper;
