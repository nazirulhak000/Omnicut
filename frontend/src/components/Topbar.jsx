import React, { useState, useEffect } from 'react';
import { Film, Wifi, WifiOff, Sparkles, Type, Keyboard } from 'lucide-react';

export default function Topbar({ activeTab, setActiveTab, status, uiFont = 'font-prompt', setUiFont, onOpenShortcuts }) {
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
    <header className="h-[56px] sm:h-[60px] flex-shrink-0 bg-[#080B11]/90 backdrop-blur-xl border-b border-white/[0.08] flex items-center justify-between px-3 sm:px-6 z-20 sticky top-0 w-full min-w-0">
      {/* Left: brand + version + mobile status indicator */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-white shadow-md shadow-[#FE2C55]/20 flex-shrink-0 relative">
            <Sparkles className="w-4 h-4" />
            {/* Mobile-only status pulse badge */}
            <span
              className={`sm:hidden absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[#080B11] ${
                isOnline ? 'bg-emerald-400' : 'bg-rose-500'
              }`}
              title={isOnline ? 'Online' : 'Offline'}
            />
          </div>
          <span className="text-sm sm:text-base font-bold tracking-tight text-white hidden xs:inline sm:inline truncate max-w-[120px] sm:max-w-none">
            CapCut Studio Pro
          </span>
          <span className="text-[9px] sm:text-[10px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full bg-white/[0.05] text-[#25F4EE] border border-[#25F4EE]/30 font-mono flex-shrink-0">
            v2.5 AI
          </span>
        </div>
      </div>

      {/* Right: UI Font Switcher, Scale zoomer & telemetry */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 min-w-0 flex-shrink-0">
        {/* Keyboard Shortcuts Trigger Button (Hidden on small mobile) */}
        <button
          onClick={onOpenShortcuts}
          className="hidden sm:flex items-center gap-1.5 bg-black/40 hover:bg-white/[0.08] px-2.5 py-1 rounded-xl border border-white/[0.08] text-xs text-slate-300 hover:text-white cursor-pointer transition-colors"
          title="คีย์ลัดด่วน (กด ? เพื่อเปิดดู)"
        >
          <Keyboard className="w-3.5 h-3.5 text-[#25F4EE]" />
          <span className="hidden md:inline font-mono">คีย์ลัด</span>
          <kbd className="hidden lg:inline px-1.5 py-0.5 rounded bg-white/[0.08] border border-white/[0.1] text-[10px] text-slate-400 font-mono">?</kbd>
        </button>

        {/* Global UI Font Switcher */}
        <div className="flex items-center gap-1 sm:gap-1.5 bg-black/40 px-2 sm:px-2.5 py-1 rounded-xl border border-white/[0.08] text-xs min-w-0">
          <Type className="w-3.5 h-3.5 text-[#25F4EE] flex-shrink-0" />
          <select
            value={uiFont}
            onChange={(e) => setUiFont && setUiFont(e.target.value)}
            className="bg-transparent text-slate-200 text-xs font-medium focus:outline-none cursor-pointer max-w-[90px] sm:max-w-[130px] md:max-w-none truncate"
            title="เปลี่ยนฟอนต์ของหน้าจอโปรแกรมทั้งระบบ (Global UI Font)"
          >
            <optgroup label="Modern Sans (โมเดิร์น ไร้หัว)">
              <option value="font-prompt" className="bg-[#080B11] text-white">Prompt</option>
              <option value="font-anuphan" className="bg-[#080B11] text-white">Anuphan</option>
              <option value="font-ibm" className="bg-[#080B11] text-white">IBM Plex</option>
              <option value="font-kanit" className="bg-[#080B11] text-white">Kanit</option>
              <option value="font-krub" className="bg-[#080B11] text-white">Krub</option>
              <option value="font-mitr" className="bg-[#080B11] text-white">Mitr</option>
              <option value="font-baijamjuree" className="bg-[#080B11] text-white">Bai Jamjuree</option>
            </optgroup>
            <optgroup label="Official & Editorial (ทางการ / ลายมือ / แฟชั่น)">
              <option value="font-sarabun" className="bg-[#080B11] text-white">Sarabun</option>
              <option value="font-mali" className="bg-[#080B11] text-white">Mali</option>
              <option value="font-chonburi" className="bg-[#080B11] text-white">Chonburi</option>
            </optgroup>
          </select>
        </div>

        {/* UI Scale Controller (Visible on Tablets & Desktops) */}
        <div className="hidden md:flex items-center gap-1 bg-black/40 px-2 py-1 rounded-xl border border-white/[0.08] text-xs">
          <button
            onClick={() => changeScale(-0.1)}
            className="w-5 h-5 flex items-center justify-center rounded-lg hover:bg-white/[0.1] text-slate-400 hover:text-white font-bold cursor-pointer transition-colors"
            title="ลดขนาดตัวอักษรหน้าจอ"
          >
            -
          </button>
          <span
            onClick={resetScale}
            className="px-1.5 text-xs text-[#25F4EE] font-bold cursor-pointer hover:underline select-none font-mono"
            title="คลิกเพื่อรีเซ็ตขนาด UI เป็น 100%"
          >
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => changeScale(0.1)}
            className="w-5 h-5 flex items-center justify-center rounded-lg hover:bg-white/[0.1] text-slate-400 hover:text-white font-bold cursor-pointer transition-colors"
            title="เพิ่มขนาดตัวอักษรหน้าจอ"
          >
            +
          </button>
        </div>

        {/* Desktop Connection status badge */}
        <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-medium border ${
          isOnline
            ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
            : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
        }`}>
          {isOnline ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Online</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-rose-400" />
              <span>Offline</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
