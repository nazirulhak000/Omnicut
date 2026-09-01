import React, { useState } from 'react';
import {
  Rocket, Sparkles, FolderDown, Settings, Layers,
  Smartphone, Maximize, Minimize, X, Copy, Check, Wifi, Scissors
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

const NAV_ITEMS = [
  { id: 'flow',    icon: Rocket,     label: '1. สินค้า → คลิป',     shortLabel: 'สินค้า' },
  { id: 'tracker', icon: Layers,     label: '2. แทร็กเกอร์ 5 เฟส',    shortLabel: 'Tracker' },
  { id: 'studio',  icon: Sparkles,   label: '3. 1-Click Studio',    shortLabel: 'Studio' },
  { id: 'editor',  icon: Scissors,   label: '4. ตัดต่อมือ & ซับไตเติล', shortLabel: 'Editor' },
  { id: 'gallery', icon: FolderDown, label: '5. Export Gallery',    shortLabel: 'Gallery' },
  { id: 'assets',  icon: Settings,   label: '6. Assets & System',   shortLabel: 'System' },
];

export default function Sidebar({ activeTab, setActiveTab, status }) {
  const [showMobileModal, setShowMobileModal] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);

  const mobileUrl = status?.mobile_url || `http://${window.location.hostname}:5173`;

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen?.();
    }
    setIsFullscreen(!isFullscreen);
  };

  const copyMobileLink = () => {
    navigator.clipboard.writeText(mobileUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      {/* ── Desktop Sidebar (Frame.io Matte Minimal) ── */}
      <aside className="hidden md:flex flex-col w-[68px] flex-shrink-0 h-screen bg-[#0B0D13] border-r border-white/[0.07] z-30">
        {/* Brand mark */}
        <div className="flex items-center justify-center h-[54px] border-b border-white/[0.07]">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#7C3AED] to-[#6366F1] flex items-center justify-center shadow-md shadow-purple-900/30 text-white font-extrabold text-sm">
            <Sparkles className="w-4 h-4" />
          </div>
        </div>

        {/* Navigation icons */}
        <nav className="flex-1 flex flex-col items-center pt-3.5 gap-1.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={item.label}
                className={`group relative w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-150 cursor-pointer
                  ${isActive
                    ? 'bg-[#7C3AED]/20 text-[#A78BFA] border border-[#7C3AED]/40 shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                  }`}
              >
                {/* Active left accent bar */}
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-[#8B5CF6]" />
                )}
                <Icon className="w-4.5 h-4.5" strokeWidth={isActive ? 2.2 : 1.8} />

                {/* Tooltip */}
                <span className="absolute left-full ml-2.5 px-2.5 py-1.5 rounded-lg bg-[#181C28] border border-white/[0.1] text-xs font-semibold text-white whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity shadow-xl z-50">
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>

        {/* Bottom utilities */}
        <div className="flex flex-col items-center gap-1.5 pb-3.5 border-t border-white/[0.07] pt-2.5">
          <button
            onClick={() => setShowMobileModal(true)}
            title="อัปโหลดผ่านมือถือ (QR Code)"
            className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:text-[#A78BFA] hover:bg-white/[0.05] transition-all cursor-pointer"
          >
            <Smartphone className="w-4.5 h-4.5" strokeWidth={1.8} />
          </button>
          <button
            onClick={toggleFullscreen}
            title={isFullscreen ? 'ย่อจอ' : 'เต็มจอ'}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.05] transition-all cursor-pointer"
          >
            {isFullscreen
              ? <Minimize className="w-4.5 h-4.5" strokeWidth={1.8} />
              : <Maximize className="w-4.5 h-4.5" strokeWidth={1.8} />
            }
          </button>
        </div>
      </aside>

      {/* ── Mobile Bottom Tab Bar ── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#0B0D13]/95 backdrop-blur-xl border-t border-white/[0.07] flex items-center justify-around px-1 py-1.5 safe-bottom shadow-2xl">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center gap-0.5 py-1 px-2 rounded-lg transition-all cursor-pointer min-w-[48px]
                ${isActive
                  ? 'text-[#A78BFA] font-bold'
                  : 'text-slate-400 hover:text-white'
                }`}
            >
              <Icon className="w-5 h-5" strokeWidth={isActive ? 2.2 : 1.6} />
              <span className="text-[10px] font-kanit">{item.shortLabel}</span>
            </button>
          );
        })}
      </nav>

      {/* ── Mobile Upload QR Modal ── */}
      {showMobileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-sm p-5 bg-[#12151E] border border-white/[0.08] rounded-2xl text-center space-y-4 shadow-2xl">
            <button
              onClick={() => setShowMobileModal(false)}
              className="absolute top-3 right-3 p-1.5 rounded-lg hover:bg-white/[0.08] text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="space-y-1.5">
              <div className="w-11 h-11 rounded-xl bg-[#7C3AED]/15 border border-[#7C3AED]/30 flex items-center justify-center mx-auto text-[#A78BFA]">
                <Smartphone className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-white font-kanit">สแกน QR เปิดบนมือถือ</h3>
              <p className="text-xs text-slate-400">อัปโหลดวิดีโอจากมือถือเข้าเครื่องผ่าน Wi-Fi</p>
            </div>

            <div className="p-3 bg-white rounded-xl inline-block mx-auto shadow-md">
              <QRCodeSVG value={mobileUrl} size={150} level="M" includeMargin={false} />
            </div>

            <div className="p-2.5 bg-[#0B0D13] rounded-xl border border-white/[0.07] space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-mono font-bold">
                <Wifi className="w-3.5 h-3.5" />
                <span>Local Network URL:</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={mobileUrl}
                  className="w-full py-1.5 px-2.5 rounded-lg bg-black/40 border border-white/[0.08] text-xs font-mono text-slate-200 select-all focus:outline-none"
                />
                <button
                  onClick={copyMobileLink}
                  className="px-3 py-1.5 rounded-lg bg-[#7C3AED] hover:bg-[#6D28D9] text-white text-xs font-bold flex items-center gap-1 transition-colors flex-shrink-0 cursor-pointer shadow-sm"
                >
                  {copied ? <><Check className="w-3.5 h-3.5 text-white" />OK</> : <><Copy className="w-3.5 h-3.5" />คัดลอก</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
