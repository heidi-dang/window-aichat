import { describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useSettings } from './useSettings';

describe('useSettings', () => {
  it('persists keys to localStorage on save', () => {
    localStorage.clear();
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.setGeminiKey('g');
      result.current.setDeepseekKey('d');
      result.current.setGithubToken('t');
      result.current.setRepoUrl('r');
    });

    act(() => {
      result.current.saveSettings();
    });

    expect(localStorage.getItem('gemini_key')).toBe('g');
    expect(localStorage.getItem('deepseek_key')).toBe('d');
    expect(localStorage.getItem('github_token')).toBe('t');
    expect(localStorage.getItem('repo_url')).toBe('r');
  });
});

