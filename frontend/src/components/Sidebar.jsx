import React, { useCallback, useRef, useState } from 'react';
import { ModalLayer } from './ui/ModalLayer';
import {
  Rocket, Sparkles, FolderDown, Settings, Layers,
  Smartphone, Maximize, Minimize, X, Copy, Check, Wifi, Scissors,
  Palette, MoreHorizontal, BarChart3, ChevronRight, LogOut
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { ChannelSelector } from '../context/ChannelContext.jsx';
import { useBackToClose } from '../hooks/useBackToClose';
import { useAuth } from './LoginScreen.jsx';

function isLocalHostname(hostname) {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1' || hostname === '[::1]';
}

// ── Desktop Navigation Items (7 items) ──
const DESKTOP_NAV_ITEMS = [
  { id: 'flow',      icon: Rocket,     label: '1. สินค้า → คลิป',     shortLabel: 'สินค้า' },
  { id: 'tracker',   icon: Layers,     label: '2. แทร็กเกอร์ 4 เฟส',    shortLabel: 'Tracker' },
  { id: 'editor',    icon: Scissors,   label: '3. ตัดต่อ & สร้างคลิป', shortLabel: 'Editor' },
  { id: 'gallery',   icon: FolderDown, label: '4. Export Gallery',    shortLabel: 'Gallery' },
  { id: 'assets',    icon: Palette,    label: '5. Media Assets Hub',   shortLabel: 'Assets' },
  { id: 'analytics', icon: BarChart3,  label: '6. สถิติ & วิเคราะห์รวม', shortLabel: 'สถิติ' },
  { id: 'settings',  icon: Settings,   label: '7. ตั้งค่าระบบ',        shortLabel: 'Settings' },
];

// ── Mobile Primary Tabs (4 items + 1 'More' button) ──
const MOBILE_PRIMARY_TABS = [
  { id: 'flow',    icon: Rocket,     label: 'สินค้า' },
  { id: 'tracker', icon: Layers,     label: 'Tracker' },
  { id: 'editor',  icon: Scissors,   label: 'Editor' },
  { id: 'gallery', icon: FolderDown, label: 'Gallery' },
];

export default function Sidebar({
  activeTab,
  setActiveTab,
  status,
  isImmersive = false,
  onToggleImmersive,
}) {
  const [showMobileModal, setShowMobileModal] = useState(false);
  const [showMoreDrawer, setShowMoreDrawer] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const { authRequired, logout } = useAuth();

  // The page's own origin is what a phone can open (e.g. the public studio
  // domain). Only when this desktop is on localhost does the backend's LAN
  // URL make sense for the QR handoff.
  const mobileUrl = isLocalHostname(window.location.hostname)
    ? (status?.mobile_url || window.location.origin)
    : window.location.origin;

  const closeMoreDrawer = useCallback(() => setShowMoreDrawer(false), []);
  const moreSheetTouchStartRef = useRef(0);
  const handleMoreSheetTouchStart = (e) => {
    moreSheetTouchStartRef.current = e.touches[0].clientY;
  };
  const handleMoreSheetTouchEnd = (e) => {
    const diff = e.changedTouches[0].clientY - moreSheetTouchStartRef.current;
    if (diff > 80) {
      try { navigator.vibrate?.(10); } catch {}
      setShowMoreDrawer(false);
    }
  };
  const closeMobileModal = useCallback(() => setShowMobileModal(false), []);
  // Phone back gesture closes the sheet / QR dialog instead of leaving the app.
  useBackToClose(showMoreDrawer, closeMoreDrawer);
  useBackToClose(showMobileModal, closeMobileModal);

  const handleLogout = async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    try { await logout(); } finally { setLoggingOut(false); }
  };

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

  const isMoreActive = activeTab === 'assets' || activeTab === 'analytics' || activeTab === 'settings' || activeTab === 'dashboard';

  return (
    <>
      {/* ── Desktop Sidebar ── */}
      <aside className="hidden md:flex flex-col w-[72px] flex-shrink-0 h-dvh bg-[#0A0D14] border-r border-white/[0.08] z-30">
        {/* Brand mark */}
        <div className="flex items-center justify-center h-[56px] border-b border-white/[0.08]">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FE2C55]/90 to-[#25F4EE]/90 border border-white/10 flex items-center justify-center shadow-sm text-white font-extrabold text-sm">
            <Sparkles className="w-5 h-5" />
          </div>
        </div>

        {/* Navigation icons */}
        <nav aria-label="แถบเมนูหลัก" className="flex-1 flex flex-col items-center pt-3.5 gap-2">
          {DESKTOP_NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id || (item.id === 'settings' && activeTab === 'dashboard');
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => { try { navigator.vibrate?.(10); } catch {} setActiveTab(item.id); }}
                title={item.label}
                aria-label={item.label}
                aria-current={isActive ? 'page' : undefined}
                className={`group relative w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/70
                  ${isActive
                    ? 'bg-white/[0.08] text-[#25F4EE] border border-white/[0.12]'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.05] border border-transparent'
                  }`}
              >
                {/* Active left accent bar */}
                {isActive && (
                  <span aria-hidden="true" className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-[#25F4EE] shadow-[0_0_8px_#25F4EE]" />
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
            type="button"
            onClick={() => setShowMobileModal(true)}
            aria-label="อัปโหลดผ่านมือถือ (QR Code)"
            title="อัปโหลดผ่านมือถือ (QR Code)"
            className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-[#25F4EE] hover:bg-white/[0.05] transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/70"
          >
            <Smartphone className="w-5 h-5" strokeWidth={1.8} />
          </button>
          <button
            type="button"
            onClick={toggleFullscreen}
            aria-label={isFullscreen ? 'ย่อจอ' : 'เต็มจอ'}
            title={isFullscreen ? 'ย่อจอ' : 'เต็มจอ'}
            className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.05] transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]/70"
          >
            {isFullscreen
              ? <Minimize className="w-5 h-5" strokeWidth={1.8} />
              : <Maximize className="w-5 h-5" strokeWidth={1.8} />
            }
          </button>
        </div>
      </aside>

      {/* ── Mobile Bottom Tab Bar (Strict 5 items limit) ── */}
      <nav
        aria-label="เมนูหลัก"
        // Hidden off-screen in immersive mode: also out of the Tab order and
        // the accessibility tree, not just invisible.
        inert={isImmersive || undefined}
        aria-hidden={isImmersive || undefined}
        className={`md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#050811]/80 backdrop-blur-2xl border-t border-white/[0.12] flex items-stretch justify-around px-1.5 h-[var(--nav-h)] pb-[env(safe-area-inset-bottom)] shadow-2xl transition-all duration-300 ${
          isImmersive ? 'translate-y-full opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'
        }`}
      >
        {MOBILE_PRIMARY_TABS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => { try { navigator.vibrate?.(10); } catch {} setActiveTab(item.id); }}
              aria-current={isActive ? 'page' : undefined}
              className={`relative flex flex-col items-center justify-center min-h-[48px] py-1 px-1 rounded-xl transition-all cursor-pointer flex-1 min-w-0 select-none active:scale-95 ${
                isActive
                  ? 'text-[#25F4EE] font-bold'
                  : 'text-slate-400 font-medium hover:text-slate-200'
              }`}
            >
              {/* Active indicator: a bar, not color alone */}
              <span
                aria-hidden="true"
                className={`absolute top-0 left-1/2 -translate-x-1/2 h-[3px] w-8 rounded-b-full transition-opacity ${isActive ? 'bg-[#25F4EE] opacity-100' : 'opacity-0'}`}
              />
              <Icon className="w-5 h-5" strokeWidth={isActive ? 2.4 : 1.7} />
              <span className="text-[12px] leading-tight tracking-tight mt-0.5 truncate max-w-full">{item.label}</span>
            </button>
          );
        })}

        {/* 5th Tab: 'อื่นๆ' (More Drawer Button) */}
        <button
          type="button"
          onClick={() => setShowMoreDrawer(true)}
          aria-haspopup="dialog"
          aria-expanded={showMoreDrawer}
          aria-current={isMoreActive ? 'page' : undefined}
          className={`relative flex flex-col items-center justify-center min-h-[48px] py-1 px-1 rounded-xl transition-all cursor-pointer flex-1 min-w-0 select-none active:scale-95 ${
            isMoreActive
              ? 'text-[#25F4EE] font-bold'
              : 'text-slate-400 font-medium hover:text-slate-200'
          }`}
        >
          <span
            aria-hidden="true"
            className={`absolute top-0 left-1/2 -translate-x-1/2 h-[3px] w-8 rounded-b-full transition-opacity ${isMoreActive ? 'bg-[#25F4EE] opacity-100' : 'opacity-0'}`}
          />
          <MoreHorizontal className="w-5 h-5" strokeWidth={isMoreActive ? 2.4 : 1.7} />
          <span className="text-[12px] leading-tight tracking-tight mt-0.5">อื่นๆ</span>
        </button>
      </nav>

      {/* ── Mobile More Bottom Sheet / Drawer ── */}
      {showMoreDrawer && (
        <div
          className="md:hidden fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex flex-col justify-end animate-fadeIn"
          onClick={() => setShowMoreDrawer(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="more-sheet-title"
            onTouchStart={handleMoreSheetTouchStart}
            onTouchEnd={handleMoreSheetTouchEnd}
            className="glass-panel rounded-t-3xl px-4 pt-2.5 pb-[max(1.25rem,env(safe-area-inset-bottom))] space-y-4 max-h-[85dvh] overflow-y-auto overscroll-contain"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Native Mobile Sheet Grab Handle */}
            <div className="w-12 h-1.5 rounded-full bg-white/20 mx-auto -mt-0.5 mb-1.5 flex-shrink-0" />

            {/* Header */}
            <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[#25F4EE]" />
                <h3 id="more-sheet-title" className="text-base font-bold text-white">เมนูเพิ่มเติม</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowMoreDrawer(false)}
                aria-label="ปิดเมนูเพิ่มเติม"
                className="w-11 h-11 -mr-1 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/[0.06] cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Workspace: channel */}
            <div className="space-y-3 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-3">
              <ChannelSelector />
            </div>

            {/* Menu List */}
            <div className="space-y-2">
              {/* Option 1: Media Assets Hub */}
              <button
                onClick={() => {
                  setActiveTab('assets');
                  setShowMoreDrawer(false);
                }}
                className={`w-full flex items-center justify-between min-h-11 p-3.5 rounded-2xl border transition-all cursor-pointer ${
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
                    <div className="text-sm font-bold text-white">Media Assets Hub</div>
                    <div className="text-xs text-slate-400">คลังเสียง SFX, เพลง BGM, ฟอนต์ และสติกเกอร์ 3D</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </button>

              {/* Option 2: Analytics Hub */}
              <button
                onClick={() => {
                  setActiveTab('analytics');
                  setShowMoreDrawer(false);
                }}
                className={`w-full flex items-center justify-between min-h-11 p-3.5 rounded-2xl border transition-all cursor-pointer ${
                  activeTab === 'analytics'
                    ? 'bg-[#25F4EE]/10 border-[#25F4EE]/40 text-[#25F4EE]'
                    : 'bg-white/[0.03] border-white/[0.06] text-slate-200 hover:bg-white/[0.06]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-[#25F4EE]/10 border border-[#25F4EE]/20 flex items-center justify-center text-[#25F4EE]">
                    <BarChart3 className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-bold text-white flex items-center gap-1.5">
                      ศูนย์วิเคราะห์ & สถิติรวม
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-500/20 text-[#25F4EE] border border-cyan-500/30">
                        Analytics
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">สถิติการผลิตคลิป, โทเคน AI, พื้นที่จัดเก็บ, สุขภาพสินค้า</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </button>

              {/* Option 3: Settings */}
              <button
                onClick={() => {
                  setActiveTab('settings');
                  setShowMoreDrawer(false);
                }}
                className={`w-full flex items-center justify-between min-h-11 p-3.5 rounded-2xl border transition-all cursor-pointer ${
                  activeTab === 'settings'
                    ? 'bg-[#25F4EE]/10 border-[#25F4EE]/40 text-[#25F4EE]'
                    : 'bg-white/[0.03] border-white/[0.06] text-slate-200 hover:bg-white/[0.06]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-slate-800 border border-white/[0.1] flex items-center justify-center text-slate-300">
                    <Settings className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-bold text-white flex items-center gap-1.5">
                      ตั้งค่าระบบ
                    </div>
                    <div className="text-xs text-slate-400">ขนาดจอ, ฟอนต์ระบบ, โฟลเดอร์จัดเก็บ, ความปลอดภัย</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </button>


              {/* Utilities Row: QR (desktop -> phone handoff only) & Fullscreen */}
              <div className="flex flex-wrap gap-2.5 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setShowMoreDrawer(false);
                    setShowMobileModal(true);
                  }}
                  className="pointer-coarse:hidden flex-1 min-h-11 flex items-center justify-center gap-2 p-3 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-slate-200 text-sm font-bold cursor-pointer"
                >
                  <Smartphone className="w-4 h-4 text-[#25F4EE]" />
                  <span>สแกน QR มือถือ</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    toggleFullscreen();
                    setShowMoreDrawer(false);
                  }}
                  className="flex-1 min-h-11 flex items-center justify-center gap-2 p-3 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-slate-200 text-sm font-bold cursor-pointer"
                >
                  {isFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
                  <span>{isFullscreen ? 'ย่อหน้าจอ' : 'ขยายเต็มหน้าจอ'}</span>
                </button>
              </div>

              {authRequired && (
                <button
                  type="button"
                  onClick={handleLogout}
                  disabled={loggingOut}
                  className="w-full min-h-11 flex items-center justify-center gap-2 p-3 rounded-2xl bg-rose-500/10 hover:bg-rose-500/15 border border-rose-500/30 text-rose-200 text-sm font-bold cursor-pointer disabled:opacity-60"
                >
                  <LogOut className="w-4 h-4" />
                  <span>{loggingOut ? 'กำลังออกจากระบบ' : 'ออกจากระบบ'}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Mobile Upload QR Modal ── */}
      {showMobileModal && (
        <ModalLayer onClose={() => setShowMobileModal(false)}
          className="fixed inset-0 flex items-center justify-center p-3 sm:p-4 w-screen h-[100dvh] max-h-[100dvh] overflow-hidden overscroll-none bg-black/80 backdrop-blur-md animate-fadeIn"
          aria-labelledby="mobile-qr-title"
        >
          <div className="relative w-full max-w-sm p-5 sm:p-6 glass-panel border border-white/[0.14] rounded-2xl sm:rounded-3xl text-center space-y-4 shadow-2xl max-h-[85dvh] overflow-y-auto no-scrollbar my-auto">
            <button
              autoFocus
              onClick={() => setShowMobileModal(false)}
              aria-label="ปิด QR modal"
              className="absolute top-3 right-3 w-11 h-11 p-2 rounded-xl hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors cursor-pointer flex items-center justify-center border border-white/[0.06]"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="space-y-1.5">
              <div className="w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/[0.12] flex items-center justify-center mx-auto text-[#25F4EE]">
                <Smartphone className="w-6 h-6" />
              </div>
              <h3 id="mobile-qr-title" className="text-base font-bold text-white">สแกน QR เปิดบนมือถือ</h3>
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
                  {copied ? <><Check className="w-3.5 h-3.5 text-white" /> คัดลอกแล้ว</> : <><Copy className="w-3.5 h-3.5" /> คัดลอกลิงก์</>}
                </button>
              </div>
            </div>
          </div>
        </ModalLayer>
      )}
    </>
  );
}
