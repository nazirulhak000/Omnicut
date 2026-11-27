import React, { memo, useEffect, useState } from 'react';
import { Smartphone } from 'lucide-react';

function formatClock(date) {
  return date.toLocaleTimeString('th-TH', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

export default memo(function StatusBar({
  status,
  activeTab,
  isEditorImmersive = false,
  mobileBridgeStatus = null,
}) {
  const [clockText, setClockText] = useState(() => formatClock(new Date()));

  useEffect(() => {
    const timer = setInterval(() => {
      setClockText(formatClock(new Date()));
    }, 15000);
    return () => clearInterval(timer);
  }, []);

  if (activeTab === 'editor' && isEditorImmersive) {
    return null;
  }

  const isOnline = status?.status === 'online';
  const latencyMs = typeof status?.latency_ms === 'number' ? status.latency_ms : null;
  const port = typeof window !== 'undefined' && window.location?.port ? window.location.port : '8000';
  const bridgeEnabled = Boolean(mobileBridgeStatus?.enabled);
  const bridgeMode = mobileBridgeStatus?.mode || null;

  return (
    <footer
      aria-label="แถบสถานะระบบ"
      className="hidden md:flex h-7 flex-shrink-0 bg-[#101114] border-t border-[#1E2026] px-4 items-center justify-between text-[11px] text-[#8E929B] select-none"
    >
      {/* Left: Live status dot + server/mobile-bridge summary + last status */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
              isOnline ? 'bg-[#34D399]' : 'bg-[#F87171]'
            }`}
          />
          <span className={isOnline ? 'text-[#D4D4D8] font-medium' : 'text-[#F87171] font-medium'}>
            {isOnline ? 'Studio Online' : 'Disconnected'}
          </span>
        </div>

        <span className="text-[#2B2E36]" aria-hidden="true">|</span>

        <div className="flex items-center gap-1.5 truncate">
          <Smartphone className={`w-3 h-3 flex-shrink-0 ${bridgeEnabled ? 'text-[#34D399]' : 'text-[#5C6069]'}`} />
          <span className="truncate">
            {bridgeEnabled
              ? `Mobile Bridge: ${bridgeMode === 'tailscale' ? 'Tailscale HTTPS' : 'LAN HTTPS'}`
              : 'Mobile Bridge: Standby'}
          </span>
        </div>
      </div>

      {/* Right: Port / Latency + Live Clock */}
      <div className="flex items-center gap-3 font-mono tabular-nums flex-shrink-0">
        {latencyMs != null && (
          <span className="text-[#8E929B]">{latencyMs}ms</span>
        )}
        <span className="text-[#5C6069]">:{port}</span>
        <span className="text-[#2B2E36]" aria-hidden="true">|</span>
        <span className="text-[#D4D4D8]">{clockText}</span>
      </div>
    </footer>
  );
});
