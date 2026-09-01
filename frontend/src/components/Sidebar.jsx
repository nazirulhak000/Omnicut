import React, { useState } from 'react';
import {
  Rocket, Sparkles, FolderDown, Lightbulb, Settings, Layers,
  Smartphone, QrCode, Maximize, Minimize, X, Copy, Check, Wifi, Scissors
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

const NAV_ITEMS = [
  { id: 'flow',       icon: Rocket,     label: '1. สินค้า → สคริปต์ & คลิป',  shortLabel: 'สินค้า' },
  { id: 'tracker',    icon: Layers,     label: '2. คลังสินค้า & Tracker', shortLabel: 'Tracker' },
  { id: 'studio',     icon: Sparkles,   label: '3. 1-Click Studio', shortLabel: 'Studio' },
  { id: 'editor',     icon: Scissors,   label: '4. ตัดต่อมือ (Manual Editor)', shortLabel: 'Editor' },
  { id: 'gallery',    icon: FolderDown, label: '5. Export Gallery', shortLabel: 'Gallery' },
  { id: 'assets',     icon: Settings,   label: '6. System & Assets', shortLabel: 'System' },
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
      <aside className="hidden md:flex flex-col w-[68px] flex-shrink-0 h-screen bg-[#0A0D14] border-r border-white/[0.06] z-30">
        {/* Brand mark */}
        <div className="flex items-center justify-center h-[52px] border-b border-white/[0.06]">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center shadow-lg shadow-[#FE2C55]/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
        </div>

        {/* Navigation icons */}
        <nav className="flex-1 flex flex-col items-center pt-3 gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={item.label}
                className={`group relative w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-200 cursor-pointer
                  ${isActive
                    ? 'bg-[#25F4EE]/10 text-[#25F4EE] shadow-lg shadow-[#25F4EE]/10'
                    : 'text-slate-500 hover:text-slate-300 hover:bg-white/[0.04]'
                  }`}
              >
                {/* Active left accent */}
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-[#25F4EE] shadow-md shadow-[#25F4EE]/40" />
                )}
                <Icon className="w-[19px] h-[19px]" strokeWidth={isActive ? 2.2 : 1.8} />

                {/* Tooltip */}
                <span className="absolute left-full ml-3 px-2.5 py-1.5 rounded-lg bg-[#1A1F2E] border border-white/10 text-[11px] font-semibold text-slate-200 whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity shadow-xl z-50">
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>

        {/* Bottom utilities */}
        <div className="flex flex-col items-center gap-1 pb-3 border-t border-white/[0.06] pt-3">
          <button
            onClick={() => setShowMobileModal(true)}
            title="อัปโหลดผ่านมือถือ"
            className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-500 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all cursor-pointer"
          >
            <Smartphone className="w-[19px] h-[19px]" strokeWidth={1.8} />
          </button>
          <button
            onClick={toggleFullscreen}
            title={isFullscreen ? 'ย่อจอ' : 'เต็มจอ'}
            className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-white/[0.04] transition-all cursor-pointer"
          >
            {isFullscreen
              ? <Minimize className="w-[19px] h-[19px]" strokeWidth={1.8} />
              : <Maximize className="w-[19px] h-[19px]" strokeWidth={1.8} />
            }
          </button>
        </div>
      </aside>

      {/* ── Mobile Bottom Tab Bar ── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#0A0D14]/95 backdrop-blur-xl border-t border-white/[0.08] flex items-center justify-around px-1 py-1.5 safe-bottom">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center gap-0.5 py-1 px-2 rounded-xl transition-all cursor-pointer
                ${isActive
                  ? 'text-[#25F4EE]'
                  : 'text-slate-500'
                }`}
            >
              <Icon className="w-5 h-5" strokeWidth={isActive ? 2.2 : 1.6} />
              <span className="text-[9px] font-semibold">{item.shortLabel}</span>
            </button>
          );
        })}
      </nav>

      {/* ── Mobile Upload QR Modal ── */}
      {showMobileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-sm p-6 bg-[#0F131C] border border-white/10 rounded-2xl shadow-2xl text-center space-y-4">
            <button
              onClick={() => setShowMobileModal(false)}
              className="absolute top-3 right-3 p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="space-y-1.5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-[#25F4EE] flex items-center justify-center mx-auto">
                <Smartphone className="w-5 h-5 text-slate-950" />
              </div>
              <h3 className="text-base font-bold text-white">สแกน QR เปิดบนมือถือ</h3>
              <p className="text-[11px] text-slate-400">อัปโหลดวิดีโอจากมือถือเข้าคอมผ่าน Wi-Fi ทันที</p>
            </div>

            <div className="p-3 bg-white rounded-xl inline-block mx-auto">
              <QRCodeSVG value={mobileUrl} size={160} level="M" includeMargin={false} />
            </div>

            <div className="p-2.5 bg-black/50 rounded-xl border border-white/10 space-y-1.5">
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-medium">
                <Wifi className="w-3 h-3" />
                <span>Local Network URL:</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={mobileUrl}
                  className="w-full py-1.5 px-2 rounded-lg bg-[#121622] border border-white/10 text-[11px] font-mono text-slate-200 select-all"
                />
                <button
                  onClick={copyMobileLink}
                  className="px-2.5 py-1.5 rounded-lg bg-[#232A3B] hover:bg-[#323B52] text-white text-[11px] font-bold flex items-center gap-1 transition-colors flex-shrink-0 cursor-pointer"
                >
                  {copied ? <><Check className="w-3 h-3 text-emerald-400" />OK</> : <><Copy className="w-3 h-3 text-[#25F4EE]" />คัดลอก</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
