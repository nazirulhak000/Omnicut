import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ChannelProvider, ChannelWorkspaceBar, useChannel } from './context/ChannelContext.jsx'

function Workspace() {
  const { channelId, selectionInvalid, selected, loading } = useChannel();
  if (selectionInvalid || (!loading && !selected)) return <main className="min-h-screen bg-slate-950 text-slate-100"><ChannelWorkspaceBar /><p className="p-6">เลือกช่องที่ถูกต้องเพื่อเปิดพื้นที่ทำงาน</p></main>;
  return <App key={channelId} />;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ChannelProvider><Workspace /></ChannelProvider>
  </StrictMode>,
)
