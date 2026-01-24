import React, { useState, useRef } from 'react';
import * as MonacoEditor from 'monaco-editor';
import { DiffEditor } from '@monaco-editor/react';

interface DiffViewerProps {
  originalContent: string;
  modifiedContent: string;
  originalFileName?: string;
  modifiedFileName?: string;
  readOnly?: boolean;
  onMount?: (editor: MonacoEditor.editor.IStandaloneDiffEditor) => void;
}

const DiffViewer: React.FC<DiffViewerProps> = ({
  originalContent,
  modifiedContent,
  originalFileName = 'Original',
  modifiedFileName = 'Modified',
  readOnly = true,
  onMount
}) => {
  const [viewMode, setViewMode] = useState<'unified' | 'side-by-side'>('side-by-side');
  const [showWhitespace, setShowWhitespace] = useState(true);
  const [ignoreTrimWhitespace, setIgnoreTrimWhitespace] = useState(false);
  const diffEditorRef = useRef<MonacoEditor.editor.IStandaloneDiffEditor | null>(null);

  const getLanguage = (filename: string): string => {
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
      case 'xml': return 'xml';
      case 'yaml': case 'yml': return 'yaml';
      case 'sql': return 'sql';
      case 'java': return 'java';
      case 'cpp': case 'cc': case 'cxx': return 'cpp';
      case 'c': return 'c';
      case 'h': case 'hpp': return 'c';
      case 'rs': return 'rust';
      case 'go': return 'go';
      default: return 'plaintext';
    }
  };

  const handleEditorDidMount = (editor: MonacoEditor.editor.IStandaloneDiffEditor) => {
    diffEditorRef.current = editor;
    
    // Configure diff editor options
    const model = editor.getModel();
    if (model) {
      const originalModel = model.original;
      const modifiedModel = model.modified;
      
      // Set language for both models
      MonacoEditor.editor.setModelLanguage(originalModel, getLanguage(originalFileName));
      MonacoEditor.editor.setModelLanguage(modifiedModel, getLanguage(modifiedFileName));
    }

    // Add keyboard shortcuts
    editor.addCommand(MonacoEditor.KeyMod.CtrlCmd | MonacoEditor.KeyCode.KeyF, () => {
      // Navigate to next change - simplified implementation
      navigateToNextChange();
    });

    if (onMount) {
      onMount(editor);
    }
  };

  const navigateToNextChange = () => {
    // For now, we'll use a simple implementation
    // In a full implementation, this would integrate with Monaco's diff navigation
    console.log('Navigate to next change');
  };

  const navigateToPreviousChange = () => {
    // For now, we'll use a simple implementation
    // In a full implementation, this would integrate with Monaco's diff navigation
    console.log('Navigate to previous change');
  };

  const toggleViewMode = () => {
    setViewMode(prev => prev === 'side-by-side' ? 'unified' : 'side-by-side');
  };

  const getDiffEditorOptions = (): MonacoEditor.editor.IStandaloneDiffEditorConstructionOptions => {
    return {
      theme: 'vs-dark',
      readOnly,
      renderSideBySide: viewMode === 'side-by-side',
      renderWhitespace: showWhitespace ? 'all' : 'none',
      ignoreTrimWhitespace,
      enableSplitViewResizing: true,
      renderLineHighlight: 'none',
      scrollBeyondLastLine: false,
      minimap: { enabled: true },
      wordWrap: 'on',
      automaticLayout: true,
      padding: { top: 10 },
      diffAlgorithm: 'advanced',
      diffCodeLens: true,
      renderOverviewRuler: true,
      renderMarginRevertIcon: true,
    };
  };

  return (
    <div className="diff-viewer">
      <div className="diff-toolbar">
        <div className="diff-info">
          <span className="file-info">
            📄 {originalFileName} → {modifiedFileName}
          </span>
        </div>
        
        <div className="diff-controls">
          <button 
            onClick={toggleViewMode}
            title={`Switch to ${viewMode === 'side-by-side' ? 'unified' : 'side-by-side'} view`}
            className="diff-btn"
          >
            {viewMode === 'side-by-side' ? '↔️ Unified' : '↔️ Side-by-Side'}
          </button>
          
          <button 
            onClick={() => setShowWhitespace(!showWhitespace)}
            title={showWhitespace ? 'Hide whitespace' : 'Show whitespace'}
            className={`diff-btn ${showWhitespace ? 'active' : ''}`}
          >
            {showWhitespace ? '👁️' : '👁️‍🗨️'} Whitespace
          </button>
          
          <button 
            onClick={() => setIgnoreTrimWhitespace(!ignoreTrimWhitespace)}
            title={ignoreTrimWhitespace ? 'Consider trim whitespace' : 'Ignore trim whitespace'}
            className={`diff-btn ${ignoreTrimWhitespace ? 'active' : ''}`}
          >
            ✂️ Trim
          </button>
          
          <div className="separator"></div>
          
          <button 
            onClick={navigateToPreviousChange}
            title="Previous change (Ctrl+F)"
            className="diff-btn"
          >
            ⬆️ Previous
          </button>
          
          <button 
            onClick={navigateToNextChange}
            title="Next change (Ctrl+F)"
            className="diff-btn"
          >
            ⬇️ Next
          </button>
        </div>
      </div>
      
      <div className="diff-editor-container">
        <DiffEditor
          height="100%"
          original={originalContent}
          modified={modifiedContent}
          onMount={handleEditorDidMount}
          options={getDiffEditorOptions()}
          language={getLanguage(modifiedFileName)}
        />
      </div>
    </div>
  );
};

export default DiffViewer;
