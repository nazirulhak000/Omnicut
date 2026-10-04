import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import EditorShell from './components/editor/EditorShell.jsx';
import { TaskProvider } from './context/TaskContext.jsx';

const clip = new URLSearchParams(window.location.search).get('clip') || '';
const clip2 = new URLSearchParams(window.location.search).get('clip2') || '';
const renderAudit = new URLSearchParams(window.location.search).get('renderAudit') === '1';
const videos = [
  ...(clip ? [{ path: clip, name: 'audit clip', duration: 2 }] : []),
  ...(clip2 ? [{ path: clip2, name: 'audit second clip', duration: 1.2 }] : []),
];

createRoot(document.getElementById('root')).render(
  <TaskProvider>
    <EditorShell
      initialProjectName="editor-audit"
      videos={videos}
      workspaceData={renderAudit ? undefined : { loadProducts: async () => [] }}
    />
  </TaskProvider>,
);
