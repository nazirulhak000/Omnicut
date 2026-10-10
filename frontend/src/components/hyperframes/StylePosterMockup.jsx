import React from 'react';
import { 
  Zap, 
  Flame, 
  BarChart3, 
  MessageSquare, 
  Play, 
  ShieldAlert, 
  Cpu, 
  Thermometer, 
  BatteryCharging, 
  Phone, 
  Camera, 
  Image as ImageIcon, 
  Mic, 
  Send 
} from 'lucide-react';

/**
 * StylePosterMockup
 * Renders an ultra-crisp, zero-latency 9:16 vector mockup of the 4 approved viral styles.
 * Designed to give creators instant visual comprehension of the editing aesthetic.
 */
export default function StylePosterMockup({ styleId, onPreviewClick }) {
  return (
    <div className="relative w-full aspect-[9/16] rounded-xl overflow-hidden shadow-2xl border border-slate-700/60 bg-slate-950 select-none group transition-all duration-300">
      {/* ── Render Style-Specific 9:16 Canvas ── */}
      {styleId === 'vs_battle' && <VsBattlePoster />}
      {styleId === 'tech_explainer' && <TechExplainerPoster />}
      {styleId === 'meme_pas' && <MemePasPoster />}
      {styleId === 'pov_chat' && <PovChatPoster />}

      {/* ── Hover Overlay with Preview Button ── */}
      <div className="absolute inset-0 bg-slate-950/60 opacity-0 group-hover:opacity-100 backdrop-blur-[2px] transition-all duration-200 flex flex-col items-center justify-center p-3 gap-2">
        <button
          type="button"
          onClick={onPreviewClick}
          className="px-3.5 py-1.5 rounded-lg bg-white/95 hover:bg-white text-slate-950 text-xs font-semibold shadow-lg transition-transform transform active:scale-95 text-center"
        >
          เปิดดูพรีวิว
        </button>
        <span className="text-[10px] text-slate-300 font-mono tracking-wider uppercase">
          9:16 Vertical HUD
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. VS Battle Poster (Street Fighter HUD)
// ─────────────────────────────────────────────────────────────────────────────
function VsBattlePoster() {
  return (
    <div className="absolute inset-0 flex flex-col justify-between p-3.5 bg-gradient-to-b from-rose-950/80 via-slate-950 to-amber-950/80 text-white font-sans overflow-hidden">
      {/* Top Street Fighter HP HUD */}
      <div className="space-y-1.5 z-10">
        <div className="flex items-center justify-between text-[10px] font-black tracking-widest text-slate-300">
          <span className="text-rose-400">OLD 5W</span>
          <span className="text-amber-400">ESSAGER 65W</span>
        </div>

        {/* Dual Health Bar with Center Timer */}
        <div className="relative flex items-center gap-1">
          {/* Left HP Bar (Depleted red) */}
          <div className="flex-1 h-3.5 bg-slate-800 rounded-l skew-x-[-15deg] overflow-hidden p-0.5 border border-rose-500/40">
            <div className="h-full bg-gradient-to-r from-red-600 to-rose-400 w-1/4 rounded-l" />
          </div>

          {/* Center 99 Countdown Timer */}
          <div className="w-7 h-7 rounded bg-gradient-to-b from-amber-400 to-yellow-600 border border-yellow-200 flex items-center justify-center text-slate-950 font-black text-xs shadow-[0_0_12px_rgba(251,191,36,0.5)] z-20 shrink-0">
            99
          </div>

          {/* Right HP Bar (Full Golden Green) */}
          <div className="flex-1 h-3.5 bg-slate-800 rounded-r skew-x-[-15deg] overflow-hidden p-0.5 border border-amber-500/40">
            <div className="h-full bg-gradient-to-r from-amber-400 to-emerald-400 w-full rounded-r" />
          </div>
        </div>

        {/* Round 1 Banner */}
        <div className="text-center">
          <span className="inline-block px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[9px] font-black tracking-wider uppercase">
            ROUND 1 • SPEED TEST
          </span>
        </div>
      </div>

      {/* Middle Center: Dramatic VS Clash */}
      <div className="relative flex flex-col items-center justify-center my-auto z-10">
        {/* Background diagonal split line */}
        <div className="absolute inset-0 -rotate-12 bg-gradient-to-r from-rose-500/10 via-transparent to-amber-500/10 blur-xl" />

        <div className="relative flex items-center justify-center">
          <span className="text-5xl font-black italic tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-yellow-300 via-amber-400 to-rose-500 drop-shadow-[0_4px_16px_rgba(244,63,94,0.7)]">
            VS
          </span>
        </div>

        <div className="mt-2 text-center">
          <p className="text-[11px] font-bold text-white tracking-wide">
            หัวชาร์จเก่า <span className="text-slate-400 font-normal">ปะทะ</span> ไนโตร 65W
          </p>
          <span className="text-[9px] text-amber-300/90 font-mono">
            3 ยก K.O. • ตัดสลับดุเดือด
          </span>
        </div>
      </div>

      {/* Bottom Telemetry Comparison Cards */}
      <div className="grid grid-cols-2 gap-2 z-10 pt-2 border-t border-slate-800">
        <div className="p-2 rounded-lg bg-rose-950/40 border border-rose-900/60 text-center">
          <span className="block text-[9px] text-rose-400 font-bold">ของแถม 5W</span>
          <span className="text-xs font-black text-white">4 ชั่วโมง</span>
          <span className="block text-[8px] text-rose-300/80 mt-0.5">ร้อน 58°C 🔥</span>
        </div>
        <div className="p-2 rounded-lg bg-amber-950/40 border border-amber-900/60 text-center">
          <span className="block text-[9px] text-amber-400 font-bold">ESSAGER 65W</span>
          <span className="text-xs font-black text-amber-300">30 นาทีเต็ม</span>
          <span className="block text-[8px] text-emerald-300/90 mt-0.5">เย็น 34°C ❄️</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. Tech Explainer Poster (Vox Style Blueprint)
// ─────────────────────────────────────────────────────────────────────────────
function TechExplainerPoster() {
  return (
    <div className="absolute inset-0 flex flex-col justify-between p-3.5 bg-gradient-to-b from-[#050D1A] via-[#091528] to-[#030811] text-white font-sans overflow-hidden">
      {/* Background Engineering Blueprint Grid */}
      <div className="absolute inset-0 opacity-15 pointer-events-none" style={{
        backgroundImage: `linear-gradient(#00f0ff 1px, transparent 1px), linear-gradient(90deg, #00f0ff 1px, transparent 1px)`,
        backgroundSize: '16px 16px'
      }} />

      {/* Top Vox Technical Header */}
      <div className="relative z-10 flex items-center justify-between pb-2 border-b border-cyan-500/20">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span className="text-[10px] font-mono tracking-widest text-cyan-300 uppercase">
            VOX LAB // 04-SPEC
          </span>
        </div>
        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60">
          1080P 60FPS
        </span>
      </div>

      {/* Middle Blueprint Schematic Breakdown */}
      <div className="relative z-10 my-auto py-3 space-y-3">
        {/* Schematic Box */}
        <div className="relative p-3 rounded-lg bg-slate-900/80 border border-cyan-500/40 shadow-[0_0_20px_rgba(6,182,212,0.15)]">
          <div className="absolute top-1.5 right-1.5 text-[8px] font-mono text-cyan-400/80">
            GaN III ARCHITECTURE
          </div>

          <div className="flex items-center justify-center py-2">
            <Cpu className="w-12 h-12 text-cyan-400 drop-shadow-[0_0_10px_rgba(6,182,212,0.8)]" />
          </div>

          {/* Component Annotation Callouts */}
          <div className="space-y-1.5 pt-2 border-t border-cyan-500/20 text-[9px]">
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-cyan-400 font-mono">01. ชิป GaN III:</span>
              <span className="font-semibold text-white">เล็กกว่า 50%</span>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-cyan-400 font-mono">02. ประสิทธิภาพ:</span>
              <span className="font-semibold text-white">93.8% Energy Transfer</span>
            </div>
          </div>
        </div>

        {/* Minimal Swiss Callout Tagline */}
        <div className="text-center space-y-0.5">
          <p className="text-xs font-bold text-white tracking-tight">
            ทำไมหัวชาร์จ 65W ถึงไม่ร้อน?
          </p>
          <p className="text-[10px] text-cyan-300/80 font-mono">
            1 ภาพต่อ 1 ไอเดีย • อธิบายด้วยฟิสิกส์จริง
          </p>
        </div>
      </div>

      {/* Bottom Telemetry Gauges */}
      <div className="relative z-10 p-2 rounded-lg bg-cyan-950/30 border border-cyan-500/20 space-y-1">
        <div className="flex items-center justify-between text-[9px] font-mono text-cyan-300">
          <span className="flex items-center gap-1">
            <BatteryCharging className="w-3 h-3 text-cyan-400" />
            POWER OUTPUT
          </span>
          <span className="font-bold text-white">65.4 WATTS</span>
        </div>
        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 w-[92%]" />
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. Meme-PAS Poster (Viral Hook + Problem Burst)
// ─────────────────────────────────────────────────────────────────────────────
function MemePasPoster() {
  return (
    <div className="absolute inset-0 flex flex-col justify-between p-3.5 bg-gradient-to-b from-[#1E0B05] via-[#120808] to-[#1E1100] text-white font-sans overflow-hidden">
      {/* Top Hazard Warning Banner */}
      <div className="space-y-1.5 z-10">
        <div className="flex items-center justify-center gap-1.5 py-1 px-2 rounded-md bg-amber-500 text-slate-950 font-black text-[10px] tracking-wider uppercase shadow-md">
          <ShieldAlert className="w-3.5 h-3.5 fill-slate-950" />
          เตือนแล้วนะ! ห้ามซื้อถ้าไม่อยาก...
        </div>

        <div className="p-2 rounded-lg bg-rose-950/60 border border-rose-500/40 text-center">
          <p className="text-[11px] font-black text-rose-300 leading-tight">
            "บิลค่าไฟพุ่ง 3,500.- เพราะแอร์กินไฟ?!"
          </p>
        </div>
      </div>

      {/* Middle Explosive Hook Graphic */}
      <div className="relative my-auto flex flex-col items-center justify-center z-10 py-2">
        <div className="relative flex items-center justify-center">
          {/* Pulsing Heat Halo */}
          <div className="absolute w-20 h-20 rounded-full bg-orange-500/20 animate-pulse blur-xl" />
          
          {/* Bursting Thermometer & Meme Badge */}
          <div className="p-3.5 rounded-full bg-gradient-to-tr from-orange-600 to-amber-400 shadow-[0_0_24px_rgba(249,115,22,0.6)]">
            <Thermometer className="w-9 h-9 text-slate-950 stroke-[2.5]" />
          </div>
        </div>

        <div className="mt-3 text-center space-y-1">
          <span className="inline-block px-2.5 py-0.5 rounded-full bg-amber-400 text-slate-950 text-[10px] font-black tracking-wide uppercase">
            0.8s MEME PAUSE ⏸️
          </span>
          <p className="text-[11px] font-extrabold text-white">
            ฮุกปัญหาคนเจอจริง ➔ ตบด้วยมีม ➔ ขาย
          </p>
          <p className="text-[9px] text-amber-300/80 font-mono">
            SFX แตรลม + ไฮไลต์ซับเหลืองนีออน
          </p>
        </div>
      </div>

      {/* Bottom TikTok Basket Callout */}
      <div className="z-10 p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-amber-400 text-slate-950 flex items-center justify-center font-black text-xs">
            🛒
          </div>
          <div>
            <span className="text-[10px] font-bold text-amber-300 block leading-none">
              พิกัดตะกร้าเหลือง
            </span>
            <span className="text-[8px] text-slate-400">
              ปิดคลิปพร้อม Call-to-Action
            </span>
          </div>
        </div>
        <span className="text-[9px] px-2 py-0.5 rounded bg-amber-400 text-slate-950 font-bold">
          กดเลย
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. POV Chat Story Poster (Authentic LINE Chat Interface)
// ─────────────────────────────────────────────────────────────────────────────
function PovChatPoster() {
  return (
    <div className="absolute inset-0 flex flex-col justify-between bg-[#7596C5] text-slate-900 font-sans overflow-hidden">
      {/* Top Phone Status Bar & LINE Header */}
      <div className="z-10">
        {/* iOS-style Top Status Bar */}
        <div className="flex items-center justify-between px-3 py-0.5 text-[9px] font-semibold text-white/90">
          <span>14:02</span>
          <div className="flex items-center gap-1 text-[8px]">
            <span>5G</span>
            <span>85%</span>
          </div>
        </div>

        {/* LINE Chat Header */}
        <div className="px-3 py-2 bg-[#06C755] text-white flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-xs">❮</span>
            <div className="w-5 h-5 rounded-full bg-white/20 border border-white/40 flex items-center justify-center text-[10px]">
              👩
            </div>
            <div>
              <p className="text-xs font-bold leading-tight">เตง ❤️</p>
              <span className="text-[8px] text-white/80 block leading-none">LINE Chat</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-white/90 text-xs">
            <Phone className="w-3.5 h-3.5" />
            <span>☰</span>
          </div>
        </div>
      </div>

      {/* Middle Chat Dialogue Messages */}
      <div className="p-3 space-y-2.5 my-auto z-10 text-[10px]">
        {/* Date pill */}
        <div className="text-center">
          <span className="px-2 py-0.5 rounded-full bg-black/20 text-white/90 text-[8px]">
            วันนี้
          </span>
        </div>

        {/* Message 1: Incoming from girlfriend */}
        <div className="flex items-end gap-1.5 max-w-[85%]">
          <div className="w-5 h-5 rounded-full bg-white/30 text-[9px] flex items-center justify-center shrink-0">
            👩
          </div>
          <div className="relative p-2 rounded-2xl rounded-bl-none bg-white text-slate-900 shadow-sm leading-tight">
            เตงงง แบตมือถือจะหมดแล้ว แต่ลืมเอาสายชาร์จมา 😭
          </div>
          <span className="text-[8px] text-white/80 shrink-0">14:01</span>
        </div>

        {/* Message 2: Outgoing reply */}
        <div className="flex items-end justify-end gap-1.5 pl-6">
          <div className="text-right">
            <span className="text-[7px] text-white/90 block leading-none">อ่านแล้ว</span>
            <span className="text-[8px] text-white/80">14:02</span>
          </div>
          <div className="relative p-2 rounded-2xl rounded-br-none bg-[#06C755] text-white shadow-sm leading-tight">
            นี่พกตัวนี้ไว้ ชาร์จไร้สายแปะหลังเครื่อง จบเลย ⚡
          </div>
        </div>

        {/* Typing indicator bubble */}
        <div className="flex items-center gap-1 pl-6">
          <div className="px-2 py-1 rounded-full bg-white/90 text-slate-600 text-[8px] flex items-center gap-1 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce" />
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.2s]" />
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.4s]" />
          </div>
        </div>
      </div>

      {/* Bottom LINE Chat Keyboard Input Bar */}
      <div className="p-2 bg-white flex items-center gap-2 border-t border-slate-200 z-10">
        <div className="flex items-center gap-1.5 text-slate-400">
          <span className="text-sm font-bold leading-none">+</span>
          <Camera className="w-3.5 h-3.5" />
          <ImageIcon className="w-3.5 h-3.5" />
        </div>
        <div className="flex-1 py-1 px-2.5 rounded-full bg-slate-100 text-[9px] text-slate-400">
          พิมพ์ข้อความ...
        </div>
        <Mic className="w-3.5 h-3.5 text-slate-400" />
      </div>
    </div>
  );
}
