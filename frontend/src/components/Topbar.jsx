import React, { memo, useState, useCallback } from 'react';
import {
  Rocket, Layers, Scissors, FolderDown, Palette, Settings,
  Keyboard, WifiOff, RefreshCw, Package, BarChart3, BookOpen, Smartphone
} from 'lucide-react';

import { ActivityIndicatorButton } from './ActivityCenter';
import { ChannelSelector } from '../context/ChannelContext.jsx';

const TAB_CONFIG = {
  flow: {
    icon: Rocket,
    title: 'สินค้า → คลิป',
    badge: '1. AI Script Lab',
    badgeColor: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    description: 'ดึงสินค้า สร้างมุมขาย & Hook ไวรัล'
  },
  tracker: {
    icon: Layers,
    title: 'แทร็กเกอร์ 4 เฟส',
    badge: '2. Pipeline 4 Phases',
    badgeColor: 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/30',
    description: 'ติดตามสถานะคลิปตั้งแต่สคริปต์จนโพสต์เสร็จ'
  },
  editor: {
    icon: Scissors,
    title: 'ตัดต่อ & สร้างคลิป',
    badge: '3. Studio Timeline',
    badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    description: 'ตัดต่อคำบรรยาย ไทม์ไลน์ และเสียงประกอบ'
  },
  studio: {
    icon: Scissors,
    title: 'ตัดต่อ & สร้างคลิป',
    badge: '3. Studio Timeline',
    badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    description: 'ตัดต่อคำบรรยาย ไทม์ไลน์ และเสียงประกอบ'
  },
  gallery: {
    icon: FolderDown,
    title: 'Export Gallery',
    badge: '4. Ready to Post',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    description: 'คลังวิดีโอที่เรนเดอร์เสร็จ พร้อมแชร์เข้ามือถือ'
  },
  assets: {
    icon: Palette,
    title: 'Media Assets Hub',
    badge: '5. Studio Assets',
    badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    description: 'ระบบหลังบ้าน ฟอนต์ เสียง AI และสติกเกอร์ 3D'
  },
  analytics: {
    icon: BarChart3,
    title: 'ศูนย์วิเคราะห์ & สถิติรวม',
    badge: '6. Analytics Hub',
    badgeColor: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    description: 'วิเคราะห์การผลิตคลิป โทเคน AI พื้นที่จัดเก็บ และสุขภาพสินค้า'
  },
  settings: {
    icon: Settings,
    title: 'ตั้งค่าระบบ',
    badge: '7. Settings',
    badgeColor: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
    description: 'ปรับขนาดหน้าจอ ฟอนต์ระบบ โฟลเดอร์จัดเก็บ และความปลอดภัย'
  },
  dashboard: {
    icon: Settings,
    title: 'ตั้งค่าระบบ',
    badge: '7. Settings',
    badgeColor: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
    description: 'ปรับขนาดหน้าจอ ฟอนต์ระบบ โฟลเดอร์จัดเก็บ และความปลอดภัย'
  },
  guide: {
    icon: BookOpen,
    title: 'คู่มือใช้งาน',
    badge: '8. User Guide',
    badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    description: 'โฟลว์หลัก 7 ขั้น วิธีใช้ทุกเมนู และคำถามพบบ่อย'
  }
};

export default memo(function Topbar({
  activeTab = 'flow',
  setActiveTab,
  status,
  uiFont = 'font-anuphan',
  uiScale = 'normal',
  setUiScale,
  setUiFont,
  onOpenShortcuts,
  onRefresh,
  onSwitchToMobile,
  activeProductContext,
  exportsCount = 0,
  videosCount = 0
}) {
  const isOnline = status?.status === 'online';
  const currentTab = TAB_CONFIG[activeTab] || TAB_CONFIG.flow;
  const Icon = currentTab.icon;

  const [latencyMs, setLatencyMs] = useState(() => (
    typeof status?.latency_ms === 'number' ? status.latency_ms : null
  ));
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefreshWithPing = useCallback(async () => {
    try { navigator.vibrate?.(10); } catch {}
    if (!onRefresh) return;
    setIsRefreshing(true);
    const start = performance.now();
    try {
      await onRefresh();
      const elapsed = Math.max(1, Math.round(performance.now() - start));
      setLatencyMs(elapsed);
    } catch {
      setLatencyMs(null);
    } finally {
      setIsRefreshing(false);
    }
  }, [onRefresh]);

  const handleStatusKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleRefreshWithPing();
    }
  }, [handleRefreshWithPing]);

  return (
    <header data-oc-surface="shell" className="h-[calc(44px+env(safe-area-inset-top))] md:h-[56px] flex-shrink-0 bg-[#050811]/75 backdrop-blur-2xl border-b border-white/[0.12] shadow-[0_4px_24px_-4px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.12)] flex flex-nowrap md:flex-wrap items-center justify-between gap-2 px-2.5 sm:px-6 pt-[env(safe-area-inset-top)] md:pt-0 z-20 sticky top-0 w-full min-w-0 transition-colors">
      {/* ── Left: Context-Aware Section Title & Badges ── */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 mr-2">
        {/* Menu Icon with Cyan Glow Pill */}
        <div className="w-8 h-8 rounded-xl bg-white/[0.05] border border-white/[0.12] text-[#25F4EE] flex items-center justify-center shadow-[inset_0_1px_0_rgba(255,255,255,0.2)] flex-shrink-0">
          <Icon className="w-4 h-4" />
        </div>

        {/* Menu Title & Dynamic Sub-Badge */}
        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
          <h1 className="text-sm sm:text-base font-bold tracking-tight text-white truncate">
            {currentTab.title}
          </h1>

          {/* Tab Number Badge */}
          <span className={`hidden sm:inline-flex items-center text-xs sm:text-sm font-bold px-2.5 py-0.5 rounded-full border flex-shrink-0 ${currentTab.badgeColor}`}>
            {currentTab.badge}
          </span>

          {/* Active Product Indicator in Studio / Flow */}
          {activeProductContext?.productName && (activeTab === 'editor' || activeTab === 'flow') && (
            <>
              <div className="hidden md:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-bold truncate max-w-[200px] shadow-[inset_0_1px_0_rgba(0,242,254,0.2)]">
                <Package className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">{activeProductContext.productName}</span>
              </div>
              <div className="flex md:hidden items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-[11px] font-bold truncate max-w-[110px]" title={activeProductContext.productName}>
                <Package className="w-2.5 h-2.5 flex-shrink-0" />
                <span className="truncate">{activeProductContext.productName}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Right: Quick Actions, Global Font Selector & System Status ── */}
      <div className="flex flex-nowrap md:flex-wrap justify-end items-center gap-1 sm:gap-2.5 min-w-0 flex-shrink-0 md:flex-shrink">
        <div className="hidden md:block"><ChannelSelector /></div>

        {/* Open AGY Cloud Terminal (/agy) */}
        <a
          href="/agy"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden md:flex min-h-11 px-3 py-1 rounded-xl bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/40 text-teal-300 hover:text-white text-xs font-bold items-center justify-center transition-colors shadow-sm"
          title="เปิดหน้าต่าง AGY Cloud Terminal สั่งงาน AI อิสระบน Cloud"
        >
          เปิด AGY Terminal
        </a>

        {/* Global Activity Center Button (Pulsing badge when active) */}
        <ActivityIndicatorButton className="min-h-11 min-w-11" />

        {/* Switch to Mobile Quick Studio Button */}
        {onSwitchToMobile && (
          <button
            type="button"
            onClick={onSwitchToMobile}
            aria-label="สลับไปโหมดสตูดิโอมือถือ"
            className="hidden md:flex min-h-11 min-w-11 p-1.5 sm:px-2.5 sm:py-1 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 active:bg-cyan-500/30 border border-cyan-500/30 text-cyan-300 hover:text-white text-xs font-bold items-center justify-center gap-1.5 cursor-pointer transition-colors shadow-sm"
            title="สลับไปโหมด OmniCut Mobile Studio"
          >
            <Smartphone className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">สลับโหมดมือถือ</span>
          </button>
        )}

        {/* Global Refresh Button */}
        {onRefresh && (
          <button
            type="button"
            onClick={handleRefreshWithPing}
            aria-label="รีเฟรชข้อมูลทั้งระบบ"
            disabled={isRefreshing}
            className="min-h-11 min-w-11 p-1.5 sm:px-2.5 sm:py-1 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] active:bg-white/[0.12] active:scale-95 border border-white/[0.10] text-slate-300 hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all shadow-sm"
            title="รีเฟรชข้อมูลทั้งระบบ"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#25F4EE] ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">รีเฟรชข้อมูล</span>
          </button>
        )}

        {/* Keyboard Shortcuts Trigger (Desktop only) */}
        <button
          type="button"
          onClick={onOpenShortcuts}
          aria-label="เปิดหน้าต่างคีย์ลัดด่วน"
          className="hidden md:flex items-center gap-1.5 min-h-11 bg-white/[0.04] hover:bg-white/[0.08] px-2.5 py-1 rounded-xl border border-white/[0.10] text-xs text-slate-300 hover:text-white cursor-pointer transition-colors shadow-sm"
          title="คีย์ลัดด่วน (กด ? เพื่อเปิดดู)"
        >
          <Keyboard className="w-3.5 h-3.5 text-[#25F4EE]" />
          <kbd className="hidden lg:inline px-1.5 py-0.2 rounded bg-white/[0.08] border border-white/[0.1] text-sm text-slate-400 font-mono">?</kbd>
        </button>

        {/* Server Connection Status Badge */}
        <div
          onClick={handleRefreshWithPing}
          onKeyDown={handleStatusKeyDown}
          role="button"
          tabIndex={0}
          aria-label={isOnline ? `สถานะเซิร์ฟเวอร์ออนไลน์ ${latencyMs ? `ความหน่วง ${latencyMs} มิลลิวินาที` : ''} แตะเพื่อรีเฟรช` : 'ขาดการเชื่อมต่อเซิร์ฟเวอร์ แตะเพื่อเชื่อมต่อใหม่'}
          title={isOnline ? `ระบบออนไลน์พร้อมใช้งาน ${latencyMs ? `(${latencyMs}ms)` : ''} (แตะเพื่อรีเฟรช)` : "ขาดการเชื่อมต่อ (แตะเพื่อรีเฟรชเชื่อมต่อใหม่)"}
          className={`flex items-center justify-center gap-1.5 min-h-11 sm:min-h-[36px] px-2.5 sm:px-3 py-1 rounded-xl text-xs font-semibold border cursor-pointer active:scale-95 transition-all shadow-sm ${
          isOnline
            ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 shadow-[inset_0_1px_0_rgba(16,185,129,0.2)]'
            : 'bg-rose-500/15 text-rose-300 border-rose-500/30 shadow-[inset_0_1px_0_rgba(244,63,94,0.2)]'
        }`}>
          {isOnline ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse flex-shrink-0" />
              <span className="hidden sm:inline font-mono">
                {latencyMs ? `${latencyMs}ms` : 'Online'}
              </span>
              <span className="sm:hidden font-mono text-[10px]">
                {latencyMs ? `${latencyMs}ms` : 'OK'}
              </span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
              <span className="hidden sm:inline">Offline</span>
              <span className="sm:hidden text-[10px]">Off</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
});
