import React from 'react';
import { DiffEditor } from '@monaco-editor/react';

interface DiffModalProps {
  original: string;
  modified: string;
  filename: string;
  onAccept: () => void;
  onReject: () => void;
}

const DiffModal: React.FC<DiffModalProps> = ({ original, modified, filename, onAccept, onReject }) => {
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
            onClick={onReject}
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
          <button 
            onClick={onAccept}
            style={{ 
              padding: '8px 16px', 
              backgroundColor: '#4CAF50', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Accept Changes
          </button>
        </div>
      </div>
      
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
