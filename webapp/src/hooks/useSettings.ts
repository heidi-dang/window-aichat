import { useState } from 'react';

export function useSettings() {
  const [geminiKey, setGeminiKey] = useState(localStorage.getItem('gemini_key') || '');
  const [deepseekKey, setDeepseekKey] = useState(localStorage.getItem('deepseek_key') || '');
  const [githubToken, setGithubToken] = useState(localStorage.getItem('github_token') || '');
  const [repoUrl, setRepoUrl] = useState(localStorage.getItem('repo_url') || '');
  const [showSettings, setShowSettings] = useState(false);

  const saveSettings = () => {
    localStorage.setItem('gemini_key', geminiKey);
    localStorage.setItem('deepseek_key', deepseekKey);
    localStorage.setItem('github_token', githubToken);
    localStorage.setItem('repo_url', repoUrl);
    setShowSettings(false);
  };

  return {
    geminiKey,
    setGeminiKey,
    deepseekKey,
    setDeepseekKey,
    githubToken,
    setGithubToken,
    repoUrl,
    setRepoUrl,
    showSettings,
    setShowSettings,
    saveSettings
  };
}

