import React, { memo, useState, useCallback } from 'react';
import {
  Rocket, Layers, Scissors, FolderDown, Palette, Settings,
  Keyboard, WifiOff, RefreshCw, Package, BarChart3
} from 'lucide-react';

import { ActivityIndicatorButton } from './ActivityCenter';
import EditorChannelSelector from './editor/EditorChannelSelector.jsx';

const TAB_CONFIG = {
  flow: {
    icon: Rocket,
    title: 'สินค้า → คลิป',
    badge: '1. AI Script Lab',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'ดึงสินค้า สร้างมุมขาย & Hook ไวรัล'
  },
  tracker: {
    icon: Layers,
    title: 'แทร็กเกอร์ 4 เฟส',
    badge: '2. Pipeline 4 Phases',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'ติดตามสถานะคลิปตั้งแต่สคริปต์จนโพสต์เสร็จ'
  },
  editor: {
    icon: Scissors,
    title: 'ตัดต่อ & สร้างคลิป',
    badge: '3. Studio Timeline',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'ตัดต่อคำบรรยาย ไทม์ไลน์ และเสียงประกอบ'
  },
  studio: {
    icon: Scissors,
    title: 'ตัดต่อ & สร้างคลิป',
    badge: '3. Studio Timeline',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'ตัดต่อคำบรรยาย ไทม์ไลน์ และเสียงประกอบ'
  },
  gallery: {
    icon: FolderDown,
    title: 'Export Gallery',
    badge: '4. Ready to Post',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'คลังวิดีโอที่เรนเดอร์เสร็จ พร้อมแชร์เข้ามือถือ'
  },
  assets: {
    icon: Palette,
    title: 'Media Assets Hub',
    badge: '5. Studio Assets',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'ระบบหลังบ้าน ฟอนต์ เสียง AI และสติกเกอร์ 3D'
  },
  analytics: {
    icon: BarChart3,
    title: 'ศูนย์วิเคราะห์ & สถิติรวม',
    badge: '6. Analytics Hub',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'วิเคราะห์การผลิตคลิป โทเคน AI พื้นที่จัดเก็บ และสุขภาพสินค้า'
  },
  settings: {
    icon: Settings,
    title: 'ตั้งค่าระบบ',
    badge: '7. Settings',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'ปรับขนาดหน้าจอ ฟอนต์ระบบ โฟลเดอร์จัดเก็บ และความปลอดภัย'
  },
  dashboard: {
    icon: Settings,
    title: 'ตั้งค่าระบบ',
    badge: '7. Settings',
    badgeColor: 'border-white/[0.08] bg-white/[0.03] text-slate-400',
    description: 'ปรับขนาดหน้าจอ ฟอนต์ระบบ โฟลเดอร์จัดเก็บ และความปลอดภัย'
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
    <header className="h-[calc(44px+env(safe-area-inset-top))] md:h-[56px] flex-shrink-0 bg-[#0A0D14]/90 backdrop-blur-md border-b border-white/[0.08] shadow-sm flex flex-nowrap md:flex-wrap items-center justify-between gap-2 px-2.5 sm:px-6 pt-[env(safe-area-inset-top)] md:pt-0 z-20 sticky top-0 w-full min-w-0 transition-colors">
      {/* ── Left: Context-Aware Section Title & Badges ── */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 mr-2">
        {/* Menu Icon with Quiet Obsidian Box */}
        <div className="w-8 h-8 rounded-xl bg-white/[0.04] border border-white/[0.08] text-slate-300 flex items-center justify-center flex-shrink-0">
          <Icon className="w-4 h-4 text-slate-300" />
        </div>

        {/* Menu Title & Dynamic Sub-Badge */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 min-w-0">
          <h1 className="text-sm sm:text-base font-bold tracking-tight text-white truncate">
            {currentTab.title}
          </h1>

          {/* Subtitle / Phase Tag (Quiet Muted Obsidian Pill) */}
          {currentTab.badge && (
            <span className="hidden sm:inline-flex items-center text-xs font-mono font-medium px-2 py-0.5 rounded-lg border border-white/[0.08] bg-white/[0.03] text-slate-400 flex-shrink-0 tracking-tight">
              {currentTab.badge}
            </span>
          )}

          {/* Active Product Indicator in Studio / Flow */}
          {activeProductContext?.productName && (activeTab === 'editor' || activeTab === 'flow') && (
            <>
              <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-medium truncate max-w-[200px]" title={activeProductContext.productName}>
                <Package className="w-3 h-3 flex-shrink-0 text-cyan-400" />
                <span className="truncate">{activeProductContext.productName}</span>
              </div>
              <div className="flex md:hidden items-center gap-1 px-2 py-0.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-[11px] font-medium truncate max-w-[110px]" title={activeProductContext.productName}>
                <Package className="w-2.5 h-2.5 flex-shrink-0 text-cyan-400" />
                <span className="truncate">{activeProductContext.productName}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Right: Quick Actions, Global Channel Selector & System Status ── */}
      <div className="flex flex-nowrap md:flex-wrap justify-end items-center gap-1.5 sm:gap-2 min-w-0 flex-shrink-0 md:flex-shrink">
        {/* Channel Selector with Pro NLE Glass Pill */}
        <div className="hidden md:block">
          <EditorChannelSelector />
        </div>

        {/* Global Activity Center Button */}
        <ActivityIndicatorButton className="h-8 sm:h-9" />

        {/* Global Refresh Button */}
        {onRefresh && (
          <button
            type="button"
            onClick={handleRefreshWithPing}
            disabled={isRefreshing}
            className="h-8 sm:h-9 p-1.5 sm:px-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] active:bg-white/[0.12] active:scale-95 border border-white/[0.08] text-slate-300 hover:text-white text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer transition-all shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/70"
            title="รีเฟรชข้อมูลทั้งระบบ"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span className="hidden sm:inline">รีเฟรชข้อมูล</span>
            <span className="sr-only sm:hidden">รีเฟรชข้อมูลทั้งระบบ</span>
          </button>
        )}

        {/* Keyboard Shortcuts Trigger (Desktop only) */}
        <button
          type="button"
          onClick={onOpenShortcuts}
          className="hidden md:flex items-center gap-1.5 h-8 sm:h-9 bg-white/[0.04] hover:bg-white/[0.08] px-2.5 rounded-xl border border-white/[0.08] text-xs font-semibold text-slate-300 hover:text-white cursor-pointer transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/70"
          title="คีย์ลัดด่วน (กด ? เพื่อเปิดดู)"
        >
          <Keyboard className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden lg:inline text-slate-300">คีย์ลัด</span>
          <span className="sr-only lg:hidden">เปิดหน้าต่างคีย์ลัดด่วน</span>
          <kbd aria-hidden="true" className="hidden lg:inline px-1.5 py-0.2 rounded bg-white/[0.08] border border-white/[0.1] text-xs text-slate-400 font-mono">?</kbd>
        </button>

        {/* Server Connection Status Badge */}
        <div
          onClick={handleRefreshWithPing}
          onKeyDown={handleStatusKeyDown}
          role="button"
          tabIndex={0}
          title={isOnline ? `ระบบออนไลน์พร้อมใช้งาน ${latencyMs ? `(${latencyMs}ms)` : ''} (แตะเพื่อรีเฟรช)` : "ขาดการเชื่อมต่อ (แตะเพื่อรีเฟรชเชื่อมต่อใหม่)"}
          className={`flex items-center justify-center gap-1.5 min-h-11 sm:min-h-0 sm:h-9 px-2.5 sm:px-3 rounded-xl text-xs font-semibold border cursor-pointer active:scale-95 transition-all shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/70 ${
            isOnline
              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/25'
              : 'bg-rose-500/10 text-rose-300 border-rose-500/25'
          }`}
        >
          {/* Name comes from the content, so it always contains the visible text. */}
          <span className="sr-only">{isOnline ? `สถานะเซิร์ฟเวอร์ออนไลน์ ${latencyMs ? `ความหน่วง ${latencyMs} มิลลิวินาที` : ''} แตะเพื่อรีเฟรช` : 'ขาดการเชื่อมต่อเซิร์ฟเวอร์ แตะเพื่อเชื่อมต่อใหม่'}</span>
          {isOnline ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
              <span className="hidden sm:inline font-mono tabular-nums">
                {latencyMs ? `${latencyMs}ms` : 'Online'}
              </span>
              <span className="sm:hidden font-mono tabular-nums text-[10px]">
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
