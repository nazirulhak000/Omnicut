import React, { memo } from 'react';
import {
  Rocket, Layers, Sparkles, Scissors, FolderDown, Settings,
  Keyboard, Wifi, WifiOff, RefreshCw, Package
} from 'lucide-react';
import { ActivityIndicatorButton } from './ActivityCenter';

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
    title: 'Content Tracker',
    badge: '2. Pipeline 5 Phases',
    badgeColor: 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/30',
    description: 'ติดตามสถานะคลิปตั้งแต่สคริปต์จนโพสต์เสร็จ'
  },
  studio: {
    icon: Sparkles,
    title: '1-Click Studio',
    badge: '3. Video Generator',
    badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    description: 'สร้างคลิป AI พากย์เสียง & เบิร์นซับ 1 คลิก'
  },
  editor: {
    icon: Scissors,
    title: 'Video Editor',
    badge: '4. NLE Timeline',
    badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    description: 'ตัดต่อคำบรรยาย ไทม์ไลน์ และเสียงประกอบ'
  },
  gallery: {
    icon: FolderDown,
    title: 'Export Gallery',
    badge: '5. Ready to Post',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    description: 'คลังวิดีโอที่เรนเดอร์เสร็จ พร้อมแชร์เข้ามือถือ'
  },
  assets: {
    icon: Settings,
    title: 'Assets & System',
    badge: '6. Studio Engine',
    badgeColor: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
    description: 'ระบบหลังบ้าน ฟอนต์ เสียง AI และสติกเกอร์'
  }
};

export default memo(function Topbar({
  activeTab = 'flow',
  setActiveTab,
  status,
  uiFont = 'font-prompt',
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

  return (
    <header className="h-[52px] sm:h-[56px] flex-shrink-0 bg-[#080B11]/95 backdrop-blur-xl border-b border-white/[0.08] flex items-center justify-between px-3 sm:px-6 z-20 sticky top-0 w-full min-w-0 transition-colors">
      {/* ── Left: Context-Aware Section Title & Badges ── */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-shrink-0">
        {/* Menu Icon with Cyan Glow Pill */}
        <div className="w-8 h-8 rounded-xl bg-white/[0.04] border border-white/[0.1] text-[#25F4EE] flex items-center justify-center shadow-sm flex-shrink-0">
          <Icon className="w-4 h-4" />
        </div>

        {/* Menu Title & Dynamic Sub-Badge */}
        <div className="flex items-center gap-2 min-w-0">
          <h1 className="text-sm sm:text-base font-bold tracking-tight text-white font-kanit truncate">
            {currentTab.title}
          </h1>

          {/* Tab Number Badge */}
          <span className={`hidden sm:inline-flex items-center text-sm font-bold px-2 py-0.5 rounded-full border font-mono flex-shrink-0 ${currentTab.badgeColor}`}>
            {currentTab.badge}
          </span>

          {/* Active Product Indicator in Studio / Flow */}
          {activeProductContext?.productName && (activeTab === 'editor' || activeTab === 'flow') && (
            <div className="hidden md:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-bold truncate max-w-[200px]">
              <Package className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">{activeProductContext.productName}</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Right: Quick Actions, Global Font Selector & System Status ── */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 min-w-0 flex-shrink-0">
        {/* Global Activity Center Button (Pulsing badge when active) */}
        <ActivityIndicatorButton />

        {/* Global Refresh Button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-1.5 sm:px-2.5 sm:py-1 rounded-xl bg-black/40 hover:bg-white/[0.08] active:bg-white/[0.12] border border-white/[0.08] text-slate-300 hover:text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors"
            title="รีเฟรชข้อมูลทั้งระบบ"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[#25F4EE]" />
            <span className="hidden sm:inline">รีเฟรช</span>
          </button>
        )}

        {/* Keyboard Shortcuts Trigger (Desktop only) */}
        <button
          onClick={onOpenShortcuts}
          className="hidden md:flex items-center gap-1.5 bg-black/40 hover:bg-white/[0.08] px-2.5 py-1 rounded-xl border border-white/[0.08] text-xs text-slate-300 hover:text-white cursor-pointer transition-colors"
          title="คีย์ลัดด่วน (กด ? เพื่อเปิดดู)"
        >
          <Keyboard className="w-3.5 h-3.5 text-[#25F4EE]" />
          <kbd className="hidden lg:inline px-1.5 py-0.2 rounded bg-white/[0.08] border border-white/[0.1] text-sm text-slate-400 font-mono">?</kbd>
        </button>

        {/* Server Connection Status Badge */}
        <div className={`flex items-center gap-1.5 px-2 sm:px-2.5 py-1 rounded-xl text-xs font-medium border ${
          isOnline
            ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
            : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
        }`}>
          {isOnline ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse flex-shrink-0" />
              <span className="hidden sm:inline">Online</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
              <span className="hidden sm:inline">Offline</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
});
