import React from 'react';

interface StatusBarProps {
  activeFile: string | null;
  language: string;
  line: number;
  column: number;
}

const StatusBar = ({ activeFile, language, line, column }: StatusBarProps) => {
  return (
    <div className="status-bar">
      <div className="status-bar-left">
        <span>{activeFile || 'No file selected'}</span>
      </div>
      <div className="status-bar-right">
        <span>Ln {line}, Col {column}</span>
        <span>{language}</span>
        <span>Prettier</span>
      </div>
    </div>
  );
};

export default StatusBar;
