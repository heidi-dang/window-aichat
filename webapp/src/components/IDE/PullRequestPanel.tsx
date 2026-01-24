import React, { useState } from 'react';
import DiffViewer from './DiffViewer';

interface PullRequestFile {
  path: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  originalContent?: string;
  modifiedContent?: string;
}

interface PullRequest {
  id: string;
  title: string;
  description: string;
  sourceBranch: string;
  targetBranch: string;
  author: string;
  createdAt: string;
  status: 'open' | 'closed' | 'merged';
  files: PullRequestFile[];
  aiAnalysis?: {
    summary: string;
    risks: string[];
    suggestions: string[];
    confidence: number;
  };
}

interface PullRequestPanelProps {
  pr?: PullRequest;
  onClose: () => void;
  onApprove?: (prId: string) => void;
  onRequestChanges?: (prId: string, feedback: string) => void;
  onMerge?: (prId: string) => void;
  onAnalyzeWithAI?: (prId: string) => void;
}

const PullRequestPanel: React.FC<PullRequestPanelProps> = ({
  pr,
  onClose,
  onApprove,
  onRequestChanges,
  onMerge,
  onAnalyzeWithAI
}) => {
  const [selectedFile, setSelectedFile] = useState<PullRequestFile | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'files' | 'ai-analysis'>('overview');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [feedback, setFeedback] = useState('');

  if (!pr) {
    return null;
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'added': return '➕';
      case 'modified': return '📝';
      case 'deleted': return '🗑️';
      case 'renamed': return '🔄';
      default: return '❓';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'added': return '#28a745';
      case 'modified': return '#0366d6';
      case 'deleted': return '#d73a49';
      case 'renamed': return '#6f42c1';
      default: return '#586069';
    }
  };

  const handleAnalyzeWithAI = async () => {
    if (onAnalyzeWithAI) {
      setIsAnalyzing(true);
      try {
        await onAnalyzeWithAI(pr.id);
      } finally {
        setIsAnalyzing(false);
      }
    }
  };

  const handleRequestChanges = () => {
    if (onRequestChanges && feedback.trim()) {
      onRequestChanges(pr.id, feedback);
      setFeedback('');
    }
  };

  const totalAdditions = pr.files.reduce((sum, file) => sum + file.additions, 0);
  const totalDeletions = pr.files.reduce((sum, file) => sum + file.deletions, 0);

  return (
    <div className="pr-panel">
      <div className="pr-header">
        <div className="pr-title">
          <h2>{pr.title}</h2>
          <span className={`pr-status pr-status-${pr.status}`}>
            {pr.status.toUpperCase()}
          </span>
        </div>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      <div className="pr-meta">
        <div className="pr-branches">
          <span className="branch-tag">{pr.sourceBranch}</span>
          <span className="arrow">→</span>
          <span className="branch-tag">{pr.targetBranch}</span>
        </div>
        <div className="pr-stats">
          <span className="author">👤 {pr.author}</span>
          <span className="date">📅 {new Date(pr.createdAt).toLocaleDateString()}</span>
          <span className="changes">
            <span className="additions">+{totalAdditions}</span>
            <span className="deletions">-{totalDeletions}</span>
          </span>
        </div>
      </div>

      <div className="pr-tabs">
        <button 
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📋 Overview
        </button>
        <button 
          className={`tab-btn ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          📁 Files ({pr.files.length})
        </button>
        <button 
          className={`tab-btn ${activeTab === 'ai-analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('ai-analysis')}
        >
          🤖 AI Analysis
        </button>
      </div>

      <div className="pr-content">
        {activeTab === 'overview' && (
          <div className="pr-overview">
            <div className="pr-description">
              <h3>Description</h3>
              <p>{pr.description}</p>
            </div>

            <div className="pr-actions">
              <button 
                className="action-btn approve"
                onClick={() => onApprove?.(pr.id)}
              >
                ✅ Approve
              </button>
              <button 
                className="action-btn analyze"
                onClick={handleAnalyzeWithAI}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? '🔄 Analyzing...' : '🤖 AI Analysis'}
              </button>
              <button 
                className="action-btn merge"
                onClick={() => onMerge?.(pr.id)}
                disabled={pr.status !== 'open'}
              >
                🔄 Merge
              </button>
            </div>

            <div className="pr-feedback">
              <h4>Request Changes</h4>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Provide feedback for changes..."
                rows={4}
              />
              <button 
                className="action-btn request-changes"
                onClick={handleRequestChanges}
                disabled={!feedback.trim()}
              >
                💬 Request Changes
              </button>
            </div>
          </div>
        )}

        {activeTab === 'files' && (
          <div className="pr-files">
            <div className="files-list">
              <h3>Changed Files</h3>
              {pr.files.map((file, index) => (
                <div 
                  key={index}
                  className={`file-item ${selectedFile === file ? 'selected' : ''}`}
                  onClick={() => setSelectedFile(file)}
                >
                  <div className="file-info">
                    <span 
                      className="file-status"
                      style={{ color: getStatusColor(file.status) }}
                    >
                      {getStatusIcon(file.status)}
                    </span>
                    <span className="file-path">{file.path}</span>
                  </div>
                  <div className="file-stats">
                    <span className="additions">+{file.additions}</span>
                    <span className="deletions">-{file.deletions}</span>
                  </div>
                </div>
              ))}
            </div>

            {selectedFile && (
              <div className="file-diff">
                <div className="diff-header">
                  <h4>{selectedFile.path}</h4>
                  <button 
                    className="close-diff"
                    onClick={() => setSelectedFile(null)}
                  >
                    ✕
                  </button>
                </div>
                <DiffViewer
                  originalContent={selectedFile.originalContent || ''}
                  modifiedContent={selectedFile.modifiedContent || ''}
                  originalFileName={selectedFile.path}
                  modifiedFileName={selectedFile.path}
                />
              </div>
            )}
          </div>
        )}

        {activeTab === 'ai-analysis' && (
          <div className="pr-ai-analysis">
            {!pr.aiAnalysis ? (
              <div className="no-analysis">
                <p>No AI analysis available yet.</p>
                <button 
                  className="action-btn analyze"
                  onClick={handleAnalyzeWithAI}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? '🔄 Analyzing...' : '🤖 Run AI Analysis'}
                </button>
              </div>
            ) : (
              <div className="ai-analysis-results">
                <div className="analysis-section">
                  <h3>📊 Summary</h3>
                  <p>{pr.aiAnalysis.summary}</p>
                  <div className="confidence-meter">
                    <span>Confidence: {Math.round(pr.aiAnalysis.confidence * 100)}%</span>
                    <div className="confidence-bar">
                      <div 
                        className="confidence-fill"
                        style={{ width: `${pr.aiAnalysis.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                </div>

                <div className="analysis-section">
                  <h3>⚠️ Potential Risks</h3>
                  <ul>
                    {pr.aiAnalysis.risks.map((risk, index) => (
                      <li key={index} className="risk-item">⚠️ {risk}</li>
                    ))}
                  </ul>
                </div>

                <div className="analysis-section">
                  <h3>💡 Suggestions</h3>
                  <ul>
                    {pr.aiAnalysis.suggestions.map((suggestion, index) => (
                      <li key={index} className="suggestion-item">💡 {suggestion}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PullRequestPanel;
