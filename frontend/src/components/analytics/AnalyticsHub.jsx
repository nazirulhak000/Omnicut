import React, { useState } from 'react';
import {
  Clapperboard, Zap, HardDrive, Package, Eye
} from 'lucide-react';
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
      activeBg: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400',
      badge: 'Funnel'
    },
    {
      id: 'performance',
      label: 'ผลงาน TikTok',
      shortLabel: 'ผลงาน TikTok',
      icon: Eye,
      color: 'text-rose-400',
      activeBg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
      badge: 'Stats'
    },
    {
      id: 'tokens',
      label: 'โทเคน & ประสิทธิภาพ AI',
      shortLabel: 'โทเคน AI',
      icon: Zap,
      color: 'text-amber-400',
      activeBg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
      badge: 'Tokens'
    },
    {
      id: 'storage',
      label: 'พื้นที่จัดเก็บ & ระบบ',
      shortLabel: 'พื้นที่จัดเก็บ',
      icon: HardDrive,
      color: 'text-purple-400',
      activeBg: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
      badge: 'Storage'
    },
    {
      id: 'inventory',
      label: 'คลังเนื้อหา & วัตถุดิบ',
      shortLabel: 'คลังเนื้อหา',
      icon: Package,
      color: 'text-rose-400',
      activeBg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
      badge: 'Health'
    }
  ];

  return (
    <div className="h-full flex flex-col overflow-y-auto bg-transparent relative z-10 p-4 sm:p-6 space-y-4">

      {/* ── Tab Navigation Bar ── */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar border-b border-white/[0.08]">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 min-h-[44px] px-4 py-2.5 rounded-2xl border text-xs font-bold transition-all cursor-pointer whitespace-nowrap active:scale-[0.98] ${
                isActive
                  ? `${tab.activeBg} shadow-lg shadow-black/20`
                  : 'glass-tile text-slate-400 hover:text-white hover:border-white/[0.25]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-white/[0.08] text-slate-300 ml-1">
                {tab.badge}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Tab Contents Container ── */}
      <div className="flex-1">
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
