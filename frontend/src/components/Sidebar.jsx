import React, { useState } from 'react';
import {
  Rocket, Sparkles, FolderDown, Settings, Layers,
  Smartphone, Maximize, Minimize, X, Copy, Check, Wifi, Scissors,
  Palette, MoreHorizontal, BarChart3, ChevronRight
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

// ── Desktop Navigation Items (6 items) ──
const DESKTOP_NAV_ITEMS = [
  { id: 'flow',     icon: Rocket,     label: '1. สินค้า → คลิป',     shortLabel: 'สินค้า' },
  { id: 'tracker',  icon: Layers,     label: '2. แทร็กเกอร์ 4 เฟส',    shortLabel: 'Tracker' },
  { id: 'editor',   icon: Scissors,   label: '3. ตัดต่อ & สร้างคลิป', shortLabel: 'Editor' },
  { id: 'gallery',  icon: FolderDown, label: '4. Export Gallery',    shortLabel: 'Gallery' },
  { id: 'assets',   icon: Palette,    label: '5. Media Assets Hub',   shortLabel: 'Assets' },
  { id: 'settings', icon: Settings,   label: '6. ตั้งค่า & โทเคน AI',  shortLabel: 'Settings' },
];

// ── Mobile Primary Tabs (4 items + 1 'More' button) ──
const MOBILE_PRIMARY_TABS = [
  { id: 'flow',    icon: Rocket,     label: 'สินค้า' },
  { id: 'tracker', icon: Layers,     label: 'Tracker' },
  { id: 'editor',  icon: Scissors,   label: 'Editor' },
  { id: 'gallery', icon: FolderDown, label: 'Gallery' },
];

export default function Sidebar({ activeTab, setActiveTab, status }) {
  const [showMobileModal, setShowMobileModal] = useState(false);
  const [showMoreDrawer, setShowMoreDrawer] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);

  const mobileUrl = status?.mobile_url || `https://${window.location.hostname}:5173`;

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

  const isMoreActive = activeTab === 'assets' || activeTab === 'settings' || activeTab === 'dashboard';

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
          {DESKTOP_NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id || (item.id === 'settings' && activeTab === 'dashboard');
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

      {/* ── Mobile Bottom Tab Bar (Strict 5 items limit) ── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#080B11]/95 backdrop-blur-2xl border-t border-white/[0.08] flex items-center justify-around px-2 py-1.5 safe-bottom shadow-2xl">
        {MOBILE_PRIMARY_TABS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl transition-all cursor-pointer flex-1
                ${isActive
                  ? 'text-[#25F4EE] font-bold'
                  : 'text-slate-400 hover:text-slate-200'
                }`}
            >
              <Icon className="w-5 h-5" strokeWidth={isActive ? 2.3 : 1.7} />
              <span className="text-[11px] font-kanit tracking-tight">{item.label}</span>
            </button>
          );
        })}

        {/* 5th Tab: 'อื่นๆ' (More Drawer Button) */}
        <button
          onClick={() => setShowMoreDrawer(true)}
          className={`flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl transition-all cursor-pointer flex-1
            ${isMoreActive || showMoreDrawer
              ? 'text-[#25F4EE] font-bold'
              : 'text-slate-400 hover:text-slate-200'
            }`}
        >
          <MoreHorizontal className="w-5 h-5" strokeWidth={isMoreActive ? 2.5 : 1.8} />
          <span className="text-[11px] font-kanit tracking-tight">อื่นๆ</span>
        </button>
      </nav>

      {/* ── Mobile 'More' Action Drawer (Bottom Sheet) ── */}
      {showMoreDrawer && (
        <div className="md:hidden fixed inset-0 z-[90] flex flex-col justify-end bg-black/80 backdrop-blur-md animate-fadeIn">
          {/* Backdrop click to dismiss */}
          <div className="flex-1" onClick={() => setShowMoreDrawer(false)} />

          {/* Drawer Card */}
          <div className="w-full bg-[#0D111A] border-t border-white/[0.12] rounded-t-3xl p-5 pb-8 space-y-4 shadow-2xl animate-slideUp safe-bottom">
            {/* Drawer Handle */}
            <div className="w-12 h-1.5 rounded-full bg-white/[0.2] mx-auto mb-2" />

            <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
              <h3 className="text-sm font-bold text-white font-kanit flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#25F4EE]" />
                เมนูเพิ่มเติม (More Options)
              </h3>
              <button
                onClick={() => setShowMoreDrawer(false)}
                className="p-1.5 rounded-xl bg-white/[0.05] text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 gap-2.5">
              {/* Option 1: Media Assets Hub */}
              <button
                onClick={() => {
                  setActiveTab('assets');
                  setShowMoreDrawer(false);
                }}
                className={`flex items-center justify-between p-3.5 rounded-2xl border transition-all cursor-pointer ${
                  activeTab === 'assets'
                    ? 'bg-[#25F4EE]/10 border-[#25F4EE]/40 text-[#25F4EE]'
                    : 'bg-white/[0.03] border-white/[0.06] text-slate-200 hover:bg-white/[0.06]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                    <Palette className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-bold text-white font-kanit">Media Assets Hub</div>
                    <div className="text-[10px] text-slate-400">คลังเสียง SFX, เพลง BGM, ฟอนต์ และสติกเกอร์ 3D</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </button>

              {/* Option 2: Settings & Token Analytics */}
              <button
                onClick={() => {
                  setActiveTab('settings');
                  setShowMoreDrawer(false);
                }}
                className={`flex items-center justify-between p-3.5 rounded-2xl border transition-all cursor-pointer ${
                  activeTab === 'settings' || activeTab === 'dashboard'
                    ? 'bg-[#25F4EE]/10 border-[#25F4EE]/40 text-[#25F4EE]'
                    : 'bg-white/[0.03] border-white/[0.06] text-slate-200 hover:bg-white/[0.06]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE]">
                    <Settings className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-bold text-white font-kanit flex items-center gap-1.5">
                      ตั้งค่าระบบ & สถิติโทเคน AI
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-500/20 text-[#25F4EE] border border-cyan-500/30">
                        Tokens
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400">สถิติโทเคน AI, ปรับขนาดจอ, ฟอนต์ระบบ, โฟลเดอร์</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </button>

              {/* Utilities Row: QR & Fullscreen */}
              <div className="grid grid-cols-2 gap-2.5 pt-1">
                <button
                  onClick={() => {
                    setShowMoreDrawer(false);
                    setShowMobileModal(true);
                  }}
                  className="flex items-center justify-center gap-2 p-3 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-slate-200 text-xs font-bold cursor-pointer"
                >
                  <Smartphone className="w-4 h-4 text-[#25F4EE]" />
                  <span>สแกน QR มือถือ</span>
                </button>

                <button
                  onClick={() => {
                    toggleFullscreen();
                    setShowMoreDrawer(false);
                  }}
                  className="flex items-center justify-center gap-2 p-3 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-slate-200 text-xs font-bold cursor-pointer"
                >
                  {isFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
                  <span>{isFullscreen ? 'ย่อหน้าจอ' : 'เต็มหน้าจอ'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Mobile Upload QR Modal ── */}
      {showMobileModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-4 w-screen h-[100dvh] max-h-[100dvh] overflow-hidden overscroll-none bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-sm p-5 sm:p-6 glass-panel border border-white/[0.14] rounded-2xl sm:rounded-3xl text-center space-y-4 shadow-2xl max-h-[85dvh] overflow-y-auto no-scrollbar my-auto">
            <button
              onClick={() => setShowMobileModal(false)}
              className="absolute top-3 right-3 p-2 rounded-xl hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center border border-white/[0.06]"
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
