import React, { useState, useEffect } from 'react';
import { Film, Wifi, WifiOff, Sparkles, Rocket, FolderDown, ChevronRight, Layers, ZoomIn, ZoomOut } from 'lucide-react';

const PIPELINE_STEPS = [
  { id: 'flow', label: '1. สินค้า → คลิป', icon: Rocket },
  { id: 'tracker', label: '2. คลังสินค้า & Tracker', icon: Layers },
  { id: 'studio', label: '3. 1-Click Studio', icon: Sparkles },
  { id: 'gallery', label: '4. Export Gallery', icon: FolderDown },
];

export default function Topbar({ activeTab, setActiveTab, status }) {
  const isOnline = status?.status === 'online';
  const [scale, setScale] = useState(1.05);

  useEffect(() => {
    document.documentElement.style.setProperty('--ui-scale', scale.toString());
  }, [scale]);

  const changeScale = (delta) => {
    const next = Math.min(1.4, Math.max(0.9, Number((scale + delta).toFixed(2))));
    setScale(next);
  };

  const resetScale = () => {
    setScale(1.0);
  };

  return (
    <header className="h-[58px] flex-shrink-0 bg-[#080B11]/95 backdrop-blur-2xl border-b border-white/[0.08] flex items-center justify-between px-4 sm:px-6 z-20 sticky top-0">
      {/* Left: brand + version */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center shadow-md shadow-[#FE2C55]/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-base font-black tracking-tight bg-gradient-to-r from-[#FE2C55] via-pink-400 to-[#25F4EE] bg-clip-text text-transparent font-kanit hidden sm:inline">
            TikTok Auto-Cutter Pro
          </span>
          <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-md bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/25 font-mono">
            v2.5
          </span>
        </div>
      </div>



      {/* Right: Scale zoomer & telemetry */}
      <div className="flex items-center gap-3">
        {/* UI Scale / Font Size Controller */}
        <div className="flex items-center gap-1 bg-black/60 px-2 py-1 rounded-xl border border-white/[0.08] text-xs font-mono">
          <button
            onClick={() => changeScale(-0.1)}
            className="w-5 h-5 flex items-center justify-center rounded hover:bg-white/10 text-slate-400 hover:text-white font-bold cursor-pointer"
            title="ลดขนาดตัวอักษร"
          >
            -
          </button>
          <span
            onClick={resetScale}
            className="px-1.5 text-xs text-[#25F4EE] font-bold cursor-pointer hover:underline select-none"
            title="คลิกเพื่อรีเซ็ตเป็น 100%"
          >
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => changeScale(0.1)}
            className="w-5 h-5 flex items-center justify-center rounded hover:bg-white/10 text-slate-400 hover:text-white font-bold cursor-pointer"
            title="เพิ่มขนาดตัวอักษร"
          >
            +
          </button>
        </div>

        {/* Connection status */}
        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold border ${
          isOnline
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            : 'bg-red-500/10 text-red-400 border-red-500/20'
        }`}>
          {isOnline ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="hidden sm:inline">Online</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-red-400" />
              <span className="hidden sm:inline">Offline</span>
            </>
          )}
        </div>

        {/* Export count pill */}
        <button
          onClick={() => setActiveTab && setActiveTab('gallery')}
          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-semibold text-slate-300 hover:text-white transition-all cursor-pointer"
          title="ดูคลังวิดีโอทั้งหมด"
        >
          <Film className="w-3.5 h-3.5 text-[#FE2C55]" />
          <span>{status?.total_exports || 0} คลิป</span>
        </button>
      </div>
    </header>
  );
}
