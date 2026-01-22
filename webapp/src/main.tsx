import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import * as MonacoEditor from 'monaco-editor';
import { loader } from '@monaco-editor/react';

// Configure Monaco
loader.config({
  monaco: MonacoEditor,
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
