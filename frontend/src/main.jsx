import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ChannelProvider, ChannelWorkspaceBar, useChannel } from './context/ChannelContext.jsx'
import { AuthGate } from './components/LoginScreen.jsx'
import { installAuthFetchWatcher } from './api.js'
import { ThemeProvider } from './context/ThemeContext.jsx'

// Direct fetch('/api/...') calls report 401 {login_required} the same way the
// axios client does, so the login screen appears instead of silent failures.
installAuthFetchWatcher()

function Workspace() {
  const { channelId, selectionInvalid, selected, loading } = useChannel();
  if (selectionInvalid || (!loading && !selected)) return <main className="min-h-dvh bg-slate-950 text-slate-100"><ChannelWorkspaceBar /><p className="p-6">เลือกช่องที่ถูกต้องเพื่อเปิดพื้นที่ทำงาน</p></main>;
  return <App key={channelId} />;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
    <AuthGate>
      <ChannelProvider><Workspace /></ChannelProvider>
    </AuthGate>
    </ThemeProvider>
  </StrictMode>,
)
