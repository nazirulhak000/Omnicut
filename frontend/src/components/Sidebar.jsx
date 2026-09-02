import React, { useState } from 'react';
import {
  Rocket, Sparkles, FolderDown, Settings, Layers,
  Smartphone, Maximize, Minimize, X, Copy, Check, Wifi, Scissors
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

const NAV_ITEMS = [
  { id: 'flow',    icon: Rocket,     label: '1. สินค้า → คลิป',     shortLabel: 'สินค้า' },
  { id: 'tracker', icon: Layers,     label: '2. แทร็กเกอร์ 5 เฟส',    shortLabel: 'Tracker' },
  { id: 'editor',  icon: Scissors,   label: '3. ตัดต่อ & สร้างคลิป', shortLabel: 'Editor' },
  { id: 'gallery', icon: FolderDown, label: '4. Export Gallery',    shortLabel: 'Gallery' },
  { id: 'assets',  icon: Settings,   label: '5. Assets & System',   shortLabel: 'System' },
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
      {/* ── Desktop Sidebar ── */}
      <aside className="hidden md:flex flex-col w-[72px] flex-shrink-0 h-screen bg-[#080B11]/90 backdrop-blur-xl border-r border-white/[0.08] z-30">
        {/* Brand mark */}
        <div className="flex items-center justify-center h-[56px] border-b border-white/[0.08]">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center shadow-lg shadow-[#FE2C55]/20 text-white font-extrabold text-sm">
            <Sparkles className="w-5 h-5" />
          </div>
        </div>

        {/* Navigation icons */}
        <nav className="flex-1 flex flex-col items-center pt-3.5 gap-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={item.label}
                className={`group relative w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-150 cursor-pointer
                  ${isActive
                    ? 'bg-gradient-to-b from-[#25F4EE]/20 to-blue-500/10 text-[#25F4EE] border border-[#25F4EE]/40 shadow-md shadow-[#25F4EE]/10'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                  }`}
              >
                {/* Active left accent bar */}
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-[#25F4EE] shadow-[0_0_8px_#25F4EE]" />
                )}
                <Icon className="w-5 h-5" strokeWidth={isActive ? 2.3 : 1.8} />

                {/* Tooltip */}
                <span className="absolute left-full ml-3 px-3 py-1.5 rounded-xl bg-[#0D111A] border border-white/[0.1] text-xs font-semibold text-white whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity shadow-2xl z-50">
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>

        {/* Bottom utilities */}
        <div className="flex flex-col items-center gap-2 pb-4 border-t border-white/[0.08] pt-3">
          <button
            onClick={() => setShowMobileModal(true)}
            title="อัปโหลดผ่านมือถือ (QR Code)"
            className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-[#25F4EE] hover:bg-white/[0.05] transition-all cursor-pointer"
          >
            <Smartphone className="w-5 h-5" strokeWidth={1.8} />
          </button>
          <button
            onClick={toggleFullscreen}
            title={isFullscreen ? 'ย่อจอ' : 'เต็มจอ'}
            className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.05] transition-all cursor-pointer"
          >
            {isFullscreen
              ? <Minimize className="w-5 h-5" strokeWidth={1.8} />
              : <Maximize className="w-5 h-5" strokeWidth={1.8} />
            }
          </button>
        </div>
      </aside>

      {/* ── Mobile Bottom Tab Bar ── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#080B11]/95 backdrop-blur-xl border-t border-white/[0.08] flex items-center justify-around px-1 py-2 safe-bottom shadow-2xl">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center gap-0.5 py-1.5 px-2 rounded-xl transition-all cursor-pointer min-w-[48px]
                ${isActive
                  ? 'text-[#25F4EE] font-bold'
                  : 'text-slate-400'
                }`}
            >
              <Icon className="w-5 h-5" strokeWidth={isActive ? 2.3 : 1.6} />
              <span className="text-sm font-kanit">{item.shortLabel}</span>
            </button>
          );
        })}
      </nav>

      {/* ── Mobile Upload QR Modal ── */}
      {showMobileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-sm p-6 glass-card text-center space-y-4 shadow-2xl">
            <button
              onClick={() => setShowMobileModal(false)}
              className="absolute top-3 right-3 p-2 rounded-xl hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="space-y-1.5">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#25F4EE]/20 to-blue-500/20 border border-[#25F4EE]/30 flex items-center justify-center mx-auto text-[#25F4EE] shadow-md shadow-[#25F4EE]/10">
                <Smartphone className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white font-kanit">สแกน QR เปิดบนมือถือ</h3>
              <p className="text-xs text-slate-400">อัปโหลดวิดีโอจากมือถือเข้าเครื่องผ่าน Wi-Fi</p>
            </div>

            <div className="p-3 bg-white rounded-2xl inline-block mx-auto shadow-xl">
              <QRCodeSVG value={mobileUrl} size={160} level="M" includeMargin={false} />
            </div>

            <div className="p-3 bg-black/40 rounded-xl border border-white/[0.08] space-y-2">
              <div className="flex items-center gap-1.5 text-sm text-emerald-400 font-mono font-bold">
                <Wifi className="w-3.5 h-3.5" />
                <span>Local Network URL:</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={mobileUrl}
                  className="w-full py-2 px-3 rounded-xl bg-black/50 border border-white/[0.1] text-xs font-mono text-slate-200 select-all focus:outline-none"
                />
                <button
                  onClick={copyMobileLink}
                  className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:opacity-90 text-white text-xs font-bold flex items-center gap-1 transition-colors flex-shrink-0 cursor-pointer shadow-md"
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
