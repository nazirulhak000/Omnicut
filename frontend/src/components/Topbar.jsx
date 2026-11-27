import React, { memo, useState, useCallback, useEffect } from 'react';
import {
  Rocket, Layers, Scissors, FolderDown, Palette, Settings,
  Keyboard, WifiOff, RefreshCw, Package, BarChart3, Zap, Smartphone
} from 'lucide-react';

import { ActivityIndicatorButton } from './ActivityCenter';
import EditorChannelSelector from './editor/EditorChannelSelector.jsx';
import GoogleFlowModal from './GoogleFlowModal.jsx';
import IPhoneDirectModal from './IPhoneDirectModal.jsx';
import { getFlowStatus } from '../api';

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
  _setActiveTab,
  status,
  _uiFont = 'font-anuphan',
  _uiScale = 'normal',
  _setUiScale,
  _setUiFont,
  onOpenShortcuts,
  onRefresh,
  activeProductContext,
  _exportsCount = 0,
  _videosCount = 0
}) {
  const isOnline = status?.status === 'online';
  const currentTab = TAB_CONFIG[activeTab] || TAB_CONFIG.flow;
  const Icon = currentTab.icon;

  const [latencyMs, setLatencyMs] = useState(() => (
    typeof status?.latency_ms === 'number' ? status.latency_ms : null
  ));
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Google Flow Real-Time Status & Credit State
  const [flowStatus, setFlowStatus] = useState(null);
  const [flowModalOpen, setFlowModalOpen] = useState(false);
  const [iphoneModalOpen, setIphoneModalOpen] = useState(false);

  const fetchFlowStatus = useCallback(async () => {
    try {
      const data = await getFlowStatus(false);
      setFlowStatus(data);
    } catch {
      setFlowStatus({ service_online: false, credits_remaining: 0 });
    }
  }, []);

  useEffect(() => {
    fetchFlowStatus();
    const interval = setInterval(fetchFlowStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchFlowStatus]);

  const handleRefreshWithPing = useCallback(async () => {
    try { navigator.vibrate?.(10); } catch {}
    if (!onRefresh) return;
    setIsRefreshing(true);
    const start = performance.now();
    try {
      await Promise.allSettled([
        onRefresh(),
        fetchFlowStatus(),
      ]);
      const elapsed = Math.max(1, Math.round(performance.now() - start));
      setLatencyMs(elapsed);
    } catch {
      setLatencyMs(null);
    } finally {
      setIsRefreshing(false);
    }
  }, [onRefresh, fetchFlowStatus]);

  const handleStatusKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleRefreshWithPing();
    }
  }, [handleRefreshWithPing]);

  const handleFlowKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setFlowModalOpen(true);
    }
  }, []);

  return (
    <header className="h-[calc(44px+env(safe-area-inset-top))] md:h-[56px] flex-shrink-0 bg-[#101114] border-b border-[#1E2026] flex flex-nowrap md:flex-wrap items-center justify-between gap-2 px-2.5 sm:px-6 pt-[env(safe-area-inset-top)] md:pt-0 z-20 sticky top-0 w-full min-w-0 transition-colors">
      {/* ── Left: Context-Aware Section Title & Badges ── */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 mr-2">
        {/* Menu Icon with Matte-Dark Box */}
        <div className="w-8 h-8 rounded-lg bg-[#1B1D22] border border-[#2B2E36] text-[#D4D4D8] flex items-center justify-center flex-shrink-0">
          <Icon className="w-4 h-4 text-[#D4D4D8]" />
        </div>

        {/* Menu Title & Dynamic Sub-Badge */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 min-w-0">
          <h1 className="text-sm sm:text-base font-bold tracking-tight text-[#F4F4F5] truncate">
            {currentTab.title}
          </h1>

          {/* Subtitle / Phase Tag */}
          {currentTab.badge && (
            <span className="hidden sm:inline-flex items-center text-xs font-mono font-medium px-2 py-0.5 rounded-md border border-[#23262D] bg-[#1B1D22] text-[#8E929B] flex-shrink-0 tracking-tight">
              {currentTab.badge}
            </span>
          )}

          {/* Active Product Indicator in Studio / Flow */}
          {activeProductContext?.productName && (activeTab === 'editor' || activeTab === 'flow') && (
            <>
              <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#131E33] border border-[#233B66] text-[#60A5FA] text-xs font-medium truncate max-w-[200px]" title={activeProductContext.productName}>
                <Package className="w-3 h-3 flex-shrink-0 text-[#60A5FA]" />
                <span className="truncate">{activeProductContext.productName}</span>
              </div>
              <div className="flex md:hidden items-center gap-1 px-2 py-0.5 rounded-md bg-[#131E33] border border-[#233B66] text-[#60A5FA] text-[11px] font-medium truncate max-w-[110px]" title={activeProductContext.productName}>
                <Package className="w-2.5 h-2.5 flex-shrink-0 text-[#60A5FA]" />
                <span className="truncate">{activeProductContext.productName}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Right: Quick Actions, Global Channel Selector & System Status ── */}
      <div className="flex flex-nowrap md:flex-wrap justify-end items-center gap-1.5 sm:gap-2 min-w-0 flex-shrink-0 md:flex-shrink">
        {/* Channel Selector */}
        <div className="hidden md:block">
          <EditorChannelSelector />
        </div>

        {/* Global Activity Center Button */}
        <ActivityIndicatorButton className="h-8 sm:h-9" />

        {/* iPhone USB Direct Ingest Button */}
        <button
          type="button"
          onClick={() => setIphoneModalOpen(true)}
          className="h-8 sm:h-9 px-2 sm:px-2.5 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] active:scale-95 border border-[#2B2E36] hover:border-[#3A3E4A] text-[#D4D4D8] hover:text-[#F4F4F5] text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer motion-press active:duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
          title="ดึงคลิปตรงจาก iPhone (USB Direct Ingest)"
        >
          <Smartphone className="w-3.5 h-3.5 text-[#60A5FA]" />
          <span className="hidden sm:inline">ดึงจาก iPhone</span>
          <span className="sr-only sm:hidden">ดึงคลิปจาก iPhone ผ่านสาย USB</span>
        </button>

        {/* Global Refresh Button */}
        {onRefresh && (
          <button
            type="button"
            onClick={handleRefreshWithPing}
            disabled={isRefreshing}
            className="h-8 sm:h-9 p-1.5 sm:px-2.5 rounded-lg bg-[#1B1D22] hover:bg-[#22252C] active:scale-95 disabled:active:scale-100 border border-[#2B2E36] hover:border-[#3A3E4A] text-[#D4D4D8] hover:text-[#F4F4F5] text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer motion-press active:duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
            title="รีเฟรชข้อมูลทั้งระบบ"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#8E929B] ${isRefreshing ? 'animate-spin text-[#F4F4F5]' : ''}`} />
            <span className="hidden sm:inline">รีเฟรชข้อมูล</span>
            <span className="sr-only sm:hidden">รีเฟรชข้อมูลทั้งระบบ</span>
          </button>
        )}

        {/* Keyboard Shortcuts Trigger (Desktop only) */}
        <button
          type="button"
          onClick={onOpenShortcuts}
          className="hidden md:flex items-center gap-1.5 h-8 sm:h-9 bg-[#1B1D22] hover:bg-[#22252C] px-2.5 rounded-lg border border-[#2B2E36] hover:border-[#3A3E4A] text-xs font-semibold text-[#D4D4D8] hover:text-[#F4F4F5] cursor-pointer active:scale-[0.96] motion-press active:duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
          title="คีย์ลัดด่วน (กด ? เพื่อเปิดดู)"
        >
          <Keyboard className="w-3.5 h-3.5 text-[#8E929B]" />
          <span className="hidden lg:inline text-[#D4D4D8]">คีย์ลัด</span>
          <span className="sr-only lg:hidden">เปิดหน้าต่างคีย์ลัดด่วน</span>
          <kbd aria-hidden="true" className="hidden lg:inline px-1.5 py-0.2 rounded bg-[#14161A] border border-[#23262D] text-xs text-[#8E929B] font-mono">?</kbd>
        </button>

        {/* ── Google Flow (Veo AI) Real-Time Status & Credit Badge ── */}
        <div
          onClick={() => setFlowModalOpen(true)}
          onKeyDown={handleFlowKeyDown}
          role="button"
          tabIndex={0}
          title={
            flowStatus?.service_online
              ? `Google Flow (Veo): ออนไลน์ · ${flowStatus?.active_account?.name || 'บัญชีหลัก'} (${flowStatus?.active_account?.credits ?? flowStatus?.credits_remaining ?? 0} cr)`
              : 'Google Flow (Veo): ออฟไลน์ · คลิกเพื่อเปิดระบบ'
          }
          className="flex items-center justify-center gap-1.5 min-h-11 sm:min-h-0 sm:h-9 px-2 sm:px-2.5 rounded-lg text-xs font-semibold border cursor-pointer active:scale-95 motion-press active:duration-100 bg-[#1B1D22] hover:bg-[#22252C] text-[#D4D4D8] hover:text-[#F4F4F5] border-[#2B2E36] hover:border-[#3A3E4A] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A]"
        >
          <span className="sr-only">
            {flowStatus?.service_online
              ? `Google Flow ออนไลน์ เครดิตคงเหลือ ${flowStatus?.active_account?.credits ?? flowStatus?.credits_remaining ?? 0} เครดิต`
              : 'Google Flow ออฟไลน์'}
          </span>

          <Zap className={`w-3.5 h-3.5 flex-shrink-0 ${flowStatus?.service_online ? 'text-[#FBBF24]' : 'text-[#5C6069]'}`} />

          {flowStatus?.service_online ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-[#34D399] flex-shrink-0" />
              <span className="font-mono tabular-nums text-[#F4F4F5]">
                <span className="hidden sm:inline text-[#8E929B] font-sans font-normal">Flow: </span>
                {flowStatus?.active_account?.credits ?? flowStatus?.credits_remaining ?? 0} cr
              </span>
            </>
          ) : (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-[#5C6069] flex-shrink-0" />
              <span className="font-mono text-[#8E929B] text-[11px]">Flow: ปิด</span>
            </>
          )}
        </div>

        {/* Server Connection Status Badge */}
        <div
          onClick={handleRefreshWithPing}
          onKeyDown={handleStatusKeyDown}
          role="button"
          tabIndex={0}
          title={isOnline ? `ระบบออนไลน์พร้อมใช้งาน ${latencyMs ? `(${latencyMs}ms)` : ''} (แตะเพื่อรีเฟรช)` : "ขาดการเชื่อมต่อ (แตะเพื่อรีเฟรชเชื่อมต่อใหม่)"}
          className={`flex items-center justify-center gap-1.5 min-h-11 sm:min-h-0 sm:h-9 px-2.5 sm:px-3 rounded-lg text-xs font-semibold border cursor-pointer active:scale-95 motion-press active:duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3A3E4A] ${
            isOnline
              ? 'bg-[#10241D] text-[#34D399] border-[#1E4D3B]'
              : 'bg-[#271417] text-[#F87171] border-[#52232A]'
          }`}
        >
          {/* Name comes from the content, so it always contains the visible text. */}
          <span className="sr-only">{isOnline ? `สถานะเซิร์ฟเวอร์ออนไลน์ ${latencyMs ? `ความหน่วง ${latencyMs} มิลลิวินาที` : ''} แตะเพื่อรีเฟรช` : 'ขาดการเชื่อมต่อเซิร์ฟเวอร์ แตะเพื่อเชื่อมต่อใหม่'}</span>
          {isOnline ? (
            <>
              <span className="w-2 h-2 rounded-full bg-[#34D399] flex-shrink-0" />
              <span className="hidden sm:inline font-mono tabular-nums">
                {latencyMs ? `${latencyMs}ms` : 'Online'}
              </span>
              <span className="sm:hidden font-mono tabular-nums text-[10px]">
                {latencyMs ? `${latencyMs}ms` : 'OK'}
              </span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-[#F87171] flex-shrink-0" />
              <span className="hidden sm:inline">Offline</span>
              <span className="sm:hidden text-[10px]">Off</span>
            </>
          )}
        </div>
      </div>

      {/* Global Google Flow Modal triggered from Topbar */}
      {flowModalOpen && (
        <GoogleFlowModal
          isOpen={flowModalOpen}
          onClose={() => {
            setFlowModalOpen(false);
            fetchFlowStatus();
          }}
          productId={activeProductContext?.productId || activeProductContext?.id}
          angleId={activeProductContext?.activeAngleId || activeProductContext?.angles?.[0]?.angle_id || activeProductContext?.angles?.[0]?.id}
          productName={activeProductContext?.productName || ''}
        />
      )}

      {/* Global iPhone Direct Modal triggered from Topbar */}
      {iphoneModalOpen && (
        <IPhoneDirectModal
          isOpen={iphoneModalOpen}
          onClose={() => setIphoneModalOpen(false)}
          onSuccess={() => onRefresh && onRefresh()}
        />
      )}
    </header>
  );
});
