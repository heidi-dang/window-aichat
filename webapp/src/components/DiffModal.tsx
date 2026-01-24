import React, { useState } from 'react';
import { DiffEditor } from '@monaco-editor/react';

interface DiffModalProps {
  original: string;
  modified: string;
  filename: string;
  onAccept: () => void;
  onReject: () => void;
  onRunChecks?: () => Promise<boolean>;
  provenance?: Record<string, unknown>;
}

const DiffModal: React.FC<DiffModalProps> = ({ original, modified, filename, onAccept, onReject, onRunChecks, provenance }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [checksPassed, setChecksPassed] = useState<boolean | null>(null);
  const [checkOutput, setCheckOutput] = useState('');

  const persistProvenance = (accepted: boolean) => {
    try {
      const raw = localStorage.getItem('artifact_provenance_v1');
      let prev: unknown = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(prev)) prev = [];
      const entry = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        accepted,
        filename,
        createdAt: Date.now(),
        provenance: provenance || null
      };
      localStorage.setItem('artifact_provenance_v1', JSON.stringify([entry, ...(prev as unknown[])].slice(0, 200)));
    } catch {
      // no-op
    }
  };

  const runChecks = async () => {
    if (!onRunChecks) return;
    setIsRunning(true);
    setCheckOutput('');
    try {
      const passed = await onRunChecks();
      setChecksPassed(passed);
    } catch (e) {
      setChecksPassed(false);
      setCheckOutput(e instanceof Error ? e.message : String(e));
    } finally {
      setIsRunning(false);
    }
  };

  const accept = (force: boolean) => {
    persistProvenance(true);
    if (!force && onRunChecks && checksPassed !== true) return;
    onAccept();
  };

  const reject = () => {
    persistProvenance(false);
    onReject();
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      zIndex: 3000,
      display: 'flex',
      flexDirection: 'column',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: '#1e1e1e',
        padding: '10px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #333'
      }}>
        <h3 style={{ margin: 0, color: '#fff' }}>Review Changes: {filename}</h3>
        <div>
          <button 
            onClick={reject}
            style={{ 
              marginRight: '10px', 
              padding: '8px 16px', 
              backgroundColor: '#d9534f', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Reject
          </button>
          {onRunChecks && (
            <button
              onClick={runChecks}
              disabled={isRunning}
              style={{
                marginRight: '10px',
                padding: '8px 16px',
                backgroundColor: '#0275d8',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: isRunning ? 'not-allowed' : 'pointer',
                opacity: isRunning ? 0.7 : 1
              }}
            >
              {isRunning ? 'Running…' : 'Run checks'}
            </button>
          )}
          <button 
            onClick={() => accept(false)}
            disabled={Boolean(onRunChecks) && checksPassed !== true}
            style={{ 
              marginRight: '10px',
              padding: '8px 16px', 
              backgroundColor: '#4CAF50', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: Boolean(onRunChecks) && checksPassed !== true ? 'not-allowed' : 'pointer',
              opacity: Boolean(onRunChecks) && checksPassed !== true ? 0.6 : 1
            }}
          >
            Accept Changes
          </button>
          {onRunChecks && (
            <button
              onClick={() => accept(true)}
              style={{
                padding: '8px 16px',
                backgroundColor: '#5bc0de',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Accept Anyway
            </button>
          )}
        </div>
      </div>
      {onRunChecks && (
        <div style={{ padding: '10px', backgroundColor: '#111', color: '#ddd', borderBottom: '1px solid #333' }}>
          <div style={{ fontSize: '12px' }}>
            {checksPassed === null ? 'Checks not run yet.' : (checksPassed ? 'Checks passed.' : 'Checks failed.')}
          </div>
          {checkOutput && (
            <div style={{ marginTop: '6px', fontSize: '11px', whiteSpace: 'pre-wrap', opacity: 0.85 }}>
              {checkOutput}
            </div>
          )}
        </div>
      )}
      
      <div style={{ flex: 1, position: 'relative' }}>
        <DiffEditor
          height="100%"
          original={original}
          modified={modified}
          language="javascript" 
          theme="vs-dark"
          options={{
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false }
          }}
        />
      </div>
    </div>
  );
};

export default DiffModal;
