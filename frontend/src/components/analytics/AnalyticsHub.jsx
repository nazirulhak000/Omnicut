import React, { useState } from 'react';
import {
  Clapperboard, Zap, HardDrive, Package, Eye, BarChart3, Activity
} from 'lucide-react';
import { PageHeader } from '../ui';
import ProductionAnalyticsTab from './tabs/ProductionAnalyticsTab';
import TokenDashboard from '../TokenDashboard';
import StorageAnalyticsTab from './tabs/StorageAnalyticsTab';
import InventoryAnalyticsTab from './tabs/InventoryAnalyticsTab';
import PerformanceAnalyticsTab from './tabs/PerformanceAnalyticsTab';

export default function AnalyticsHub({
  initialTab = 'production',
  refreshKey = 0,
  onNavigateToEditor,
  onNavigateToTracker,
  onNavigateToFlow
}) {
  const [activeTab, setActiveTab] = useState(initialTab); // 'production' | 'tokens' | 'storage' | 'inventory' | 'performance'

  const tabs = [
    {
      id: 'production',
      label: 'การผลิต & ภาพรวมคลิป',
      shortLabel: 'การผลิตคลิป',
      icon: Clapperboard,
      color: 'text-cyan-400',
      activeBg: 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300',
      badge: 'Funnel'
    },
    {
      id: 'performance',
      label: 'ผลงาน TikTok',
      shortLabel: 'ผลงาน TikTok',
      icon: Eye,
      color: 'text-rose-400',
      activeBg: 'bg-rose-500/15 border-rose-500/40 text-rose-300',
      badge: 'Stats'
    },
    {
      id: 'tokens',
      label: 'โทเคน & ประสิทธิภาพ AI',
      shortLabel: 'โทเคน AI',
      icon: Zap,
      color: 'text-amber-400',
      activeBg: 'bg-amber-500/15 border-amber-500/40 text-amber-300',
      badge: 'Tokens'
    },
    {
      id: 'storage',
      label: 'พื้นที่จัดเก็บ & ระบบ',
      shortLabel: 'พื้นที่จัดเก็บ',
      icon: HardDrive,
      color: 'text-purple-400',
      activeBg: 'bg-purple-500/15 border-purple-500/40 text-purple-300',
      badge: 'Storage'
    },
    {
      id: 'inventory',
      label: 'คลังเนื้อหา & วัตถุดิบ',
      shortLabel: 'คลังเนื้อหา',
      icon: Package,
      color: 'text-emerald-400',
      activeBg: 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300',
      badge: 'Health'
    }
  ];

  return (
    <div className="h-full flex flex-col overflow-y-auto bg-transparent relative z-10 p-3 sm:p-5 lg:p-6 space-y-4 max-w-[2200px] mx-auto animate-fadeIn">
      {/* ── 1. Unified Command Bar Header (Obsidian Pro Dark NLE) ── */}
      <PageHeader
        icon={BarChart3}
        iconGradient="from-cyan-500/20 to-blue-500/20"
        iconColor="text-cyan-400"
        eyebrow="Intelligence & Analytics Studio"
        title="ศูนย์วิเคราะห์ข้อมูล & สถิติการผลิต"
        badges={
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/25 font-mono">
            PRO METRICS
          </span>
        }
        secondRow={
          <div className="space-y-2.5 pt-2 border-t border-white/[0.06]">
            {/* Description */}
            <p className="text-xs text-slate-400 leading-relaxed">
              ติดตามประสิทธิภาพขั้นตอนการผลิตคลิป 9:16 สถิติผู้ชม TikTok อัตราการใช้โทเคน AI และสถานะพื้นที่จัดเก็บข้อมูล
            </p>

            {/* Tab Navigation Bar (Obsidian Pro Dark Rail) */}
            <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-1 no-scrollbar">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 min-h-[44px] px-3.5 sm:px-4 py-2 rounded-xl border text-xs font-bold transition-all cursor-pointer whitespace-nowrap active:scale-[0.98] ${
                      isActive
                        ? `${tab.activeBg} shadow-sm shadow-black/40 ring-1 ring-white/10`
                        : 'bg-[#080B11]/80 border-white/[0.06] text-slate-400 hover:text-white hover:border-white/[0.16] hover:bg-white/[0.03]'
                    }`}
                  >
                    <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? tab.color : 'text-slate-400'}`} />
                    <span>{tab.label}</span>
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ml-1 ${
                      isActive
                        ? 'bg-white/10 text-white border-white/20'
                        : 'bg-white/[0.04] text-slate-400 border-white/[0.06]'
                    }`}>
                      {tab.badge}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        }
      />

      {/* ── 2. Tab Contents Container ── */}
      <div className="flex-1 min-h-0">
        {activeTab === 'production' && (
          <ProductionAnalyticsTab
            onNavigateToEditor={onNavigateToEditor}
            onNavigateToTracker={onNavigateToTracker}
          />
        )}
        {activeTab === 'tokens' && (
          <TokenDashboard refreshKey={refreshKey} />
        )}
        {activeTab === 'storage' && (
          <StorageAnalyticsTab />
        )}
        {activeTab === 'inventory' && (
          <InventoryAnalyticsTab
            onNavigateToFlow={onNavigateToFlow}
          />
        )}
        {activeTab === 'performance' && (
          <PerformanceAnalyticsTab />
        )}
      </div>
    </div>
  );
}
