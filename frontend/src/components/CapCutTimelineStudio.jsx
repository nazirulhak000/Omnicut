import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  Scissors,
  Trash2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Sparkles,
  Layers,
  Volume2,
  Type,
  Smile,
  Music,
  Film,
  Sliders,
  Download,
  Share2,
  ChevronRight,
  Plus,
  FastForward,
  Rewind,
  Eye,
  Lock,
  Magnet,
  Zap,
  Check,
  Flame,
  ShoppingBag
} from 'lucide-react';
import { getRawVideos, getAllAssets, startRender, getRenderStatus, openFolder } from '../api';

export default function CapCutTimelineStudio({ onSwitchToSimpleStudio }) {
  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(3.4);
  const [totalDuration, setTotalDuration] = useState(18.0);
  const [activeTrackItem, setActiveTrackItem] = useState({ track: 'video', id: 'v1' });
  const [timelineZoom, setTimelineZoom] = useState(1.0);
  const [leftTab, setLeftTab] = useState('clips'); // 'clips', 'text', 'stickers', 'audio', 'luts'
  
  // Project settings
  const [projectName, setProjectName] = useState('TikTok_Esseger_สายชาร์จแม่เหล็ก');
  const [aspectRatio, setAspectRatio] = useState('9:16'); // '9:16', '16:9', '1:1'
  const [punchZoomScale, setPunchZoomScale] = useState(1.25);
  const [selectedFont, setSelectedFont] = useState('IBMPlex');
  const [selectedBadge, setSelectedBadge] = useState('badge_flash_sale_3d.png');
  const [selectedBGM, setSelectedBGM] = useState('tiktok_upbeat_bgm.wav');
  const [bgmVolume, setBgmVolume] = useState(25);
  const [voiceVolume, setVoiceVolume] = useState(100);
  const [sfxVolume, setSfxVolume] = useState(80);
  const [bilingual, setBilingual] = useState(true);

  // Mock Timeline Data (Loaded from Script/Pipeline)
  const [videoClips, setVideoClips] = useState([
    { id: 'v1', start: 0.0, end: 3.2, title: 'Hook: หยุดดูสายชาร์จพังง่าย', scale: 1.25, color: 'from-blue-600 to-indigo-700' },
    { id: 'v2', start: 3.2, end: 7.0, title: 'Pain: สายขาดง่าย เสียบยากในที่มืด', scale: 1.0, color: 'from-blue-500 to-cyan-600' },
    { id: 'v3', start: 7.0, end: 11.5, title: 'Feature: หัวแม่เหล็กดูดแรง ชาร์จไว', scale: 1.35, color: 'from-indigo-600 to-purple-700' },
    { id: 'v4', start: 11.5, end: 15.0, title: 'Deal: โปรพิเศษส่งฟรี มีรับประกัน', scale: 1.1, color: 'from-purple-600 to-pink-600' },
    { id: 'v5', start: 15.0, end: 18.0, title: 'CTA: จิ้มตะกร้าสีเหลืองด้านล่าง', scale: 1.25, color: 'from-rose-600 to-red-600' },
  ]);

  const [subtitleCues, setSubtitleCues] = useState([
    { id: 's1', start: 0.0, end: 3.2, th: 'เคยเป็นมั้ย? สายชาร์จพังง่ายขาดบ่อยมาก', en: 'Tired of broken charging cables?' },
    { id: 's2', start: 3.2, end: 7.0, th: 'จะเสียบในที่มืดก็ยาก หาขั้วชาร์จไม่เจอ', en: 'Hard to plug in the dark?' },
    { id: 's3', start: 7.0, end: 11.5, th: 'ตัวนี้หัวแม่เหล็กแรงดูดสูง เสียบปึ้งชาร์จเร็วทันที', en: 'Magnetic auto-snap, fast charging' },
    { id: 's4', start: 11.5, end: 15.0, th: 'ของแท้มีประกัน ส่งฟรีทั่วไทยวันนี้', en: '100% Authentic with warranty, free shipping' },
    { id: 's5', start: 15.0, end: 18.0, th: 'กดสั่งในตะกร้าสีเหลืองซ้ายล่างได้เลยครับ', en: 'Tap yellow basket bottom left now!' },
  ]);

  const [stickersTrack, setStickersTrack] = useState([
    { id: 'st1', start: 0.5, end: 7.0, name: '⚡ Flash Sale 3D', file: 'badge_flash_sale_3d.png' },
    { id: 'st2', start: 7.0, end: 14.5, name: '🚚 ส่งฟรีทั่วไทย', file: 'badge_free_shipping_3d.png' },
    { id: 'st3', start: 14.5, end: 18.0, name: '🛒 กดสั่งในตะกร้า', file: 'badge_yellow_cart_3d.png' },
  ]);

  const [sfxCues, setSfxCues] = useState([
    { id: 'sfx1', time: 0.0, type: 'whoosh', label: '💨 Whoosh' },
    { id: 'sfx2', time: 3.2, type: 'pop', label: '✨ Pop' },
    { id: 'sfx3', time: 7.0, type: 'magnet', label: '🧲 Magnet Clack' },
    { id: 'sfx4', time: 11.5, type: 'bell', label: '🔔 Bell Ding' },
    { id: 'sfx5', time: 15.0, type: 'cash', label: '💰 Cash Register' },
  ]);

  // Playback timer simulation
  useEffect(() => {
    let timer = null;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= totalDuration) {
            setIsPlaying(false);
            return 0.0;
          }
          return Math.min(totalDuration, prev + 0.1);
        });
      }, 100);
    }
    return () => clearInterval(timer);
  }, [isPlaying, totalDuration]);

  // Current active subtitle & sticker
  const activeSub = subtitleCues.find((c) => currentTime >= c.start && currentTime <= c.end);
  const activeSticker = stickersTrack.find((s) => currentTime >= s.start && currentTime <= s.end);
  const activeClip = videoClips.find((v) => currentTime >= v.start && currentTime <= v.end);

  const formatTimecode = (secs) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const ms = Math.floor((secs % 1) * 10);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${ms}`;
  };

  const handleTimelineClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, clickX / rect.width));
    setCurrentTime(Number((pct * totalDuration).toFixed(1)));
  };

  const handleSplitClip = () => {
    if (!activeClip) return;
    if (currentTime <= activeClip.start + 0.3 || currentTime >= activeClip.end - 0.3) {
      alert('กรุณาเลื่อนหัวอ่านให้อยู่ระหว่างคลิปเพื่อตัดแบ่ง');
      return;
    }
    const idx = videoClips.findIndex((v) => v.id === activeClip.id);
    if (idx === -1) return;

    const part1 = { ...activeClip, end: currentTime, title: `${activeClip.title} (ส่วน 1)` };
    const part2 = {
      id: `v_${Date.now()}`,
      start: currentTime,
      end: activeClip.end,
      title: `${activeClip.title} (ส่วน 2)`,
      scale: activeClip.scale === 1.25 ? 1.0 : 1.25,
      color: 'from-amber-600 to-orange-700'
    };

    const newClips = [...videoClips];
    newClips.splice(idx, 1, part1, part2);
    setVideoClips(newClips);
  };

  return (
    <div className="w-full h-full min-h-[880px] flex flex-col bg-[#0B0E14] text-slate-200 font-prompt select-none rounded-3xl border border-white/10 shadow-2xl overflow-hidden">
      {/* 1. TOP HEADER BAR (CapCut Topbar) */}
      <header className="h-14 bg-[#121620] border-b border-white/10 px-4 flex items-center justify-between z-30">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gradient-to-r from-[#FE2C55]/20 to-[#FE2C55]/5 border border-[#FE2C55]/40 shadow-sm">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FE2C55] animate-pulse" />
            <span className="text-xs font-black tracking-wider text-white uppercase">CapCut Timeline Pro Studio</span>
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-lg bg-black/40 border border-white/5 text-xs text-slate-300">
            <span className="text-slate-500">โปรเจกต์:</span>
            <span className="font-semibold text-white truncate max-w-[200px]">{projectName}</span>
          </div>
        </div>

        {/* Center Aspect Ratio */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-black/50 border border-white/5">
          {['9:16', '16:9', '1:1'].map((ratio) => (
            <button
              key={ratio}
              onClick={() => setAspectRatio(ratio)}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                aspectRatio === ratio
                  ? 'bg-gradient-to-r from-[#FE2C55] to-[#FF0050] text-white shadow-md'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {ratio === '9:16' ? '📱 9:16 TikTok' : ratio === '16:9' ? '🖥️ 16:9' : '⏹️ 1:1'}
            </button>
          ))}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          {onSwitchToSimpleStudio && (
            <button
              onClick={onSwitchToSimpleStudio}
              className="px-3 py-1.5 rounded-xl text-xs font-bold text-slate-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-all cursor-pointer"
            >
              🔄 กลับไปโหมด 1-Click Studio
            </button>
          )}

          <button
            onClick={() => alert('กำลังเชื่อมต่อไปยังเรนเดอร์เอนจิน FFmpeg Standalone เพื่อประกอบ MP4 คุณภาพสูง...')}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-black text-white bg-gradient-to-r from-emerald-500 to-teal-600 hover:brightness-110 shadow-lg shadow-emerald-500/25 border border-emerald-400/40 transition-all cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>เรนเดอร์ MP4 (Render)</span>
          </button>
        </div>
      </header>

      {/* 2. MIDDLE WORKSPACE (3 Columns: Left Media / Center Preview / Right Inspector) */}
      <div className="flex-1 grid grid-cols-12 gap-0 min-h-[480px] bg-[#0E121B] overflow-hidden">
        {/* LEFT COLUMN: Media & Assets Palette (3 cols) */}
        <div className="col-span-12 lg:col-span-3 border-r border-white/10 bg-[#121622] flex flex-col">
          {/* Asset Navigation Tabs */}
          <div className="flex items-center border-b border-white/10 bg-black/20 p-1.5 gap-1 overflow-x-auto scrollbar-none">
            {[
              { id: 'clips', label: '🎬 คลิป', icon: Film },
              { id: 'text', label: '💬 ซับ/ฟอนต์', icon: Type },
              { id: 'stickers', label: '🏷️ ป้าย 3D', icon: Smile },
              { id: 'audio', label: '🎵 เพลง/SFX', icon: Music },
              { id: 'luts', label: '🎨 โทนสี', icon: Sliders },
            ].map((tab) => {
              const Icon = tab.icon;
              const isSel = leftTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setLeftTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                    isSel
                      ? 'bg-[#FE2C55] text-white shadow-md shadow-[#FE2C55]/30'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Asset List Content */}
          <div className="flex-1 p-3.5 overflow-y-auto space-y-3">
            {leftTab === 'clips' && (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                  <span>🎞️ ชิ้นวิดีโอในไทม์ไลน์ ({videoClips.length} ช็อต)</span>
                  <span className="text-[11px] text-cyan-400 font-normal">Auto Punch-Zoom Active</span>
                </div>
                {videoClips.map((clip, idx) => (
                  <div
                    key={clip.id}
                    onClick={() => {
                      setActiveTrackItem({ track: 'video', id: clip.id });
                      setCurrentTime(clip.start);
                    }}
                    className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                      activeClip?.id === clip.id
                        ? 'bg-[#FE2C55]/15 border-[#FE2C55] ring-1 ring-[#FE2C55]'
                        : 'bg-black/30 border-white/5 hover:border-white/15'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="w-6 h-6 rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-xs font-black text-white">
                        {idx + 1}
                      </span>
                      <div>
                        <div className="text-xs font-bold text-white truncate max-w-[150px]">{clip.title}</div>
                        <div className="text-[10px] text-slate-400">
                          {clip.start.toFixed(1)}s - {clip.end.toFixed(1)}s (ซูม {clip.scale}x)
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-300 font-mono">
                      {(clip.end - clip.start).toFixed(1)}s
                    </span>
                  </div>
                ))}
              </div>
            )}

            {leftTab === 'text' && (
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-300">💬 สไตล์ซับไตเติลภาษาไทย & อังกฤษ</div>
                <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-bold text-white">🌐 ซับ 2 ภาษา Bilingual Stacked</div>
                    <div className="text-[10px] text-slate-400">บรรทัดบนไทย + ล่างอังกฤษ</div>
                  </div>
                  <button
                    onClick={() => setBilingual(!bilingual)}
                    className={`w-10 h-5 rounded-full relative transition-colors cursor-pointer ${
                      bilingual ? 'bg-cyan-500' : 'bg-slate-700'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform ${
                        bilingual ? 'left-5.5' : 'left-0.5'
                      }`}
                    />
                  </button>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-400">เลือกฟอนต์ซับไตเติล:</label>
                  {['IBMPlex', 'Kanit', 'Mitr', 'Prompt'].map((f) => (
                    <button
                      key={f}
                      onClick={() => setSelectedFont(f)}
                      className={`w-full p-2 rounded-xl text-xs font-bold text-left border transition-all cursor-pointer ${
                        selectedFont === f
                          ? 'bg-[#FE2C55]/20 border-[#FE2C55] text-white'
                          : 'bg-black/20 border-white/5 text-slate-300 hover:bg-black/40'
                      }`}
                    >
                      ฟอนต์ {f} (Modern Thai Sans)
                    </button>
                  ))}
                </div>
              </div>
            )}

            {leftTab === 'stickers' && (
              <div className="space-y-2.5">
                <div className="text-xs font-bold text-slate-300">🏷️ ป้าย 3D E-Commerce สากล (8 แบบ)</div>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'badge_flash_sale_3d.png', name: '⚡ Flash Sale' },
                    { id: 'badge_free_shipping_3d.png', name: '🚚 ส่งฟรีทั่วไทย' },
                    { id: 'badge_best_seller_3d.png', name: '⭐ สินค้าขายดี' },
                    { id: 'badge_yellow_cart_3d.png', name: '🛒 กดสั่งในตะกร้า' },
                    { id: 'badge_authentic_shield_3d.png', name: '🛡️ การันตีของแท้' },
                    { id: 'badge_special_gift_3d.png', name: '🎁 โปรโมชั่นพิเศษ' },
                    { id: 'badge_hot_deal_3d.png', name: '🔥 ดีลเด็ดมาแรง' },
                    { id: 'badge_cod_secure_3d.png', name: '💰 เก็บเงินปลายทาง' },
                  ].map((badge) => (
                    <button
                      key={badge.id}
                      onClick={() => setSelectedBadge(badge.id)}
                      className={`p-2 rounded-xl border text-center transition-all cursor-pointer ${
                        selectedBadge === badge.id
                          ? 'bg-amber-500/20 border-amber-400 text-amber-300 shadow-md'
                          : 'bg-black/30 border-white/5 text-slate-400 hover:text-white'
                      }`}
                    >
                      <div className="text-xs font-bold truncate">{badge.name}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {leftTab === 'audio' && (
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-300">🎵 เพลงประกอบ BGM & Sound Effects</div>
                <div className="space-y-1.5">
                  {['tiktok_upbeat_bgm.wav', 'bgm_brass_funk.wav', 'bgm_lofi_daily.wav', 'bgm_cyber_phonk.wav'].map(
                    (music) => (
                      <button
                        key={music}
                        onClick={() => setSelectedBGM(music)}
                        className={`w-full p-2.5 rounded-xl text-xs font-bold text-left border flex items-center justify-between transition-all cursor-pointer ${
                          selectedBGM === music
                            ? 'bg-[#FE2C55]/20 border-[#FE2C55] text-white'
                            : 'bg-black/20 border-white/5 text-slate-300'
                        }`}
                      >
                        <span className="truncate">{music.replace('.wav', '').replace('_', ' ')}</span>
                        {selectedBGM === music && <Check className="w-3.5 h-3.5 text-[#FE2C55]" />}
                      </button>
                    )
                  )}
                </div>
              </div>
            )}

            {leftTab === 'luts' && (
              <div className="space-y-2">
                <div className="text-xs font-bold text-slate-300">🎨 ฟิลเตอร์เกรดสี Color LUTs</div>
                {[
                  { name: '✨ Bright & Clean Product', desc: 'สีสด คมชัด วัตถุเด่น' },
                  { name: '🌸 Vibrant Beauty Skin', desc: 'ผิวอมชมพู สว่างนุ่มนวล' },
                  { name: '💻 Tech Cool Contrast', desc: 'มิติคมเข้ม สไตล์ Gadget' },
                  { name: '☕ Warm Cozy Lifestyle', desc: 'โทนอบอุ่น สบายตา' },
                ].map((lut, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-xl bg-black/30 border border-white/5 hover:border-white/15 cursor-pointer"
                  >
                    <div className="text-xs font-bold text-white">{lut.name}</div>
                    <div className="text-[10px] text-slate-400">{lut.desc}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* CENTER COLUMN: 9:16 Canvas Live Video Preview (6 cols) */}
        <div className="col-span-12 lg:col-span-6 bg-[#080A0F] flex flex-col items-center justify-between p-4 border-r border-white/10 relative overflow-hidden">
          {/* Canvas Wrapper */}
          <div className="flex-1 w-full flex items-center justify-center py-2">
            <div className="relative aspect-[9/16] h-[380px] sm:h-[440px] max-h-[460px] rounded-2xl bg-black border-2 border-white/15 shadow-2xl overflow-hidden group">
              {/* Simulated Video Feed with Punch-Zoom */}
              <div
                className="w-full h-full flex items-center justify-center transition-transform duration-300 relative"
                style={{
                  transform: `scale(${activeClip?.scale || 1.0})`,
                  backgroundImage: 'radial-gradient(circle, #1E293B 0%, #0F172A 100%)'
                }}
              >
                {/* Visual Video Content / Mock Camera Frame */}
                <div className="text-center p-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-orange-500 mx-auto flex items-center justify-center shadow-lg shadow-[#FE2C55]/30 mb-3">
                    <Film className="w-8 h-8 text-white" />
                  </div>
                  <div className="text-xs font-black text-white px-3 py-1 rounded-full bg-black/60 backdrop-blur-md inline-block border border-white/10">
                    {activeClip?.title || 'TikTok Video Scene'}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">Punch Zoom: {activeClip?.scale || 1.0}x Active</div>
                </div>

                {/* Overlaid 3D Sticker Badge (Upper Right Quadrant) */}
                {activeSticker && (
                  <div className="absolute top-4 right-4 animate-bounce duration-1000">
                    <div className="px-2.5 py-1 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 text-black font-black text-[10px] shadow-lg border border-white/40 flex items-center gap-1">
                      <span>{activeSticker.name}</span>
                    </div>
                  </div>
                )}

                {/* Overlaid Live Subtitles (Bottom Quadrant) */}
                {activeSub && (
                  <div className="absolute bottom-6 left-3 right-3 text-center pointer-events-none">
                    <div className="inline-block px-3 py-1.5 rounded-xl bg-black/80 backdrop-blur-md border border-white/20 shadow-xl">
                      <div className="text-sm sm:text-base font-black text-[#FFE600] tracking-wide drop-shadow-md">
                        {activeSub.th}
                      </div>
                      {bilingual && (
                        <div className="text-[10px] sm:text-xs font-semibold text-white/90 tracking-normal mt-0.5">
                          {activeSub.en}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Timecode Badge on Canvas */}
              <div className="absolute top-3 left-3 px-2 py-0.5 rounded-md bg-black/70 backdrop-blur-sm border border-white/10 text-[10px] font-mono text-cyan-300">
                {formatTimecode(currentTime)} / {formatTimecode(totalDuration)}
              </div>
            </div>
          </div>

          {/* Transport & Control Bar */}
          <div className="w-full max-w-md bg-[#121622] p-2.5 rounded-2xl border border-white/10 flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCurrentTime(Math.max(0, currentTime - 1.0))}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
                title="ย้อนหลัง 1 วิ"
              >
                <Rewind className="w-4 h-4" />
              </button>

              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`p-2.5 rounded-xl text-white font-bold transition-all shadow-md cursor-pointer ${
                  isPlaying
                    ? 'bg-amber-500 shadow-amber-500/30'
                    : 'bg-gradient-to-r from-[#FE2C55] to-[#FF0050] shadow-[#FE2C55]/30'
                }`}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-white" />}
              </button>

              <button
                onClick={() => setCurrentTime(Math.min(totalDuration, currentTime + 1.0))}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
                title="ไปข้างหน้า 1 วิ"
              >
                <FastForward className="w-4 h-4" />
              </button>
            </div>

            <div className="font-mono text-xs font-bold text-white px-3 py-1 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[#FE2C55]">{formatTimecode(currentTime)}</span>
              <span className="text-slate-500"> / {formatTimecode(totalDuration)}</span>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={handleSplitClip}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold bg-[#FE2C55]/15 text-[#FE2C55] hover:bg-[#FE2C55]/25 border border-[#FE2C55]/30 transition-all cursor-pointer"
                title="ตัดแบ่งคลิป ณ ตำแหน่งหัวอ่าน [S]"
              >
                <Scissors className="w-3.5 h-3.5" />
                <span>ตัด (Split)</span>
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Inspector / Properties (3 cols) */}
        <div className="col-span-12 lg:col-span-3 bg-[#121622] p-4 space-y-4 overflow-y-auto">
          <div className="flex items-center justify-between pb-2.5 border-b border-white/10">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" />
              <span>แผงควบคุมคุณสมบัติ (Inspector)</span>
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 font-bold">
              {activeClip?.title ? 'วิดีโอที่เลือก' : 'พารามิเตอร์'}
            </span>
          </div>

          {/* Punch-Zoom Scale Slider */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium">🔍 Dynamic Punch-Zoom:</span>
              <span className="font-mono font-bold text-amber-400">{activeClip?.scale || 1.25}x</span>
            </div>
            <div className="grid grid-cols-4 gap-1">
              {[1.0, 1.15, 1.25, 1.35].map((sc) => (
                <button
                  key={sc}
                  onClick={() => {
                    if (activeClip) {
                      const updated = videoClips.map((v) => (v.id === activeClip.id ? { ...v, scale: sc } : v));
                      setVideoClips(updated);
                    }
                  }}
                  className={`py-1 rounded-lg text-xs font-bold border transition-all cursor-pointer ${
                    activeClip?.scale === sc
                      ? 'bg-amber-500/20 border-amber-400 text-amber-300'
                      : 'bg-black/30 border-white/5 text-slate-400 hover:text-white'
                  }`}
                >
                  {sc}x
                </button>
              ))}
            </div>
          </div>

          {/* Audio Mixing Sliders */}
          <div className="space-y-3 pt-2 border-t border-white/10">
            <div className="text-xs font-bold text-slate-300">🎚️ มิกซ์ระดับเสียง (Audio Mixing)</div>

            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>🎙️ เสียงพากย์หลัก (Voiceover)</span>
                <span className="font-mono text-white">{voiceVolume}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="150"
                value={voiceVolume}
                onChange={(e) => setVoiceVolume(e.target.value)}
                className="w-full accent-[#FE2C55] h-1.5 bg-black/40 rounded-lg cursor-pointer"
              />
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>🎵 เพลงคลอ (BGM Auto-Ducking)</span>
                <span className="font-mono text-cyan-300">{bgmVolume}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={bgmVolume}
                onChange={(e) => setBgmVolume(e.target.value)}
                className="w-full accent-cyan-400 h-1.5 bg-black/40 rounded-lg cursor-pointer"
              />
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>🔊 ซาวด์เอฟเฟกต์ (SFX Cues)</span>
                <span className="font-mono text-amber-300">{sfxVolume}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="120"
                value={sfxVolume}
                onChange={(e) => setSfxVolume(e.target.value)}
                className="w-full accent-amber-400 h-1.5 bg-black/40 rounded-lg cursor-pointer"
              />
            </div>
          </div>

          {/* Quick AI Auto-Arrange Button */}
          <div className="pt-2 border-t border-white/10">
            <button
              onClick={() => alert('AI Auto-Arrange: จัดจังหวะคัตและซิงก์เสียงพากย์ + ซับไตเติลให้อัตโนมัติสมบูรณ์แบบ!')}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#FE2C55]/20 to-purple-600/20 border border-[#FE2C55]/40 text-white font-bold text-xs flex items-center justify-center gap-1.5 hover:brightness-125 transition-all cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#FE2C55]" />
              <span>จัดไทม์ไลน์ด้วย AI อัตโนมัติ</span>
            </button>
          </div>
        </div>
      </div>

      {/* 3. BOTTOM MULTI-TRACK TIMELINE (CapCut Multi-track) */}
      <div className="h-[280px] bg-[#0F121A] border-t border-white/10 flex flex-col">
        {/* Timeline Header & Toolbar */}
        <div className="h-10 bg-[#161B26] border-b border-white/10 px-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <button
                onClick={handleSplitClip}
                className="p-1.5 rounded-lg bg-black/40 hover:bg-white/10 text-slate-300 hover:text-white border border-white/5 transition-all cursor-pointer"
                title="ตัดแบ่งคลิป (Split)"
              >
                <Scissors className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => alert('ลบคลิปที่เลือก')}
                className="p-1.5 rounded-lg bg-black/40 hover:bg-red-500/20 text-slate-300 hover:text-red-400 border border-white/5 transition-all cursor-pointer"
                title="ลบชิ้นงาน"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="h-4 w-[1px] bg-white/10" />

            <div className="flex items-center gap-1 text-xs text-slate-400">
              <Magnet className="w-3.5 h-3.5 text-cyan-400" />
              <span>แม่เหล็กดูดขอบ (Snap): เปิด</span>
            </div>
          </div>

          {/* Timeline Zoom Slider */}
          <div className="flex items-center gap-2">
            <ZoomOut className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="range"
              min="0.8"
              max="2.0"
              step="0.1"
              value={timelineZoom}
              onChange={(e) => setTimelineZoom(parseFloat(e.target.value))}
              className="w-24 accent-[#FE2C55] h-1.5 bg-black/40 rounded-lg cursor-pointer"
            />
            <ZoomIn className="w-3.5 h-3.5 text-slate-400" />
          </div>
        </div>

        {/* Tracks Workspace with Draggable Playhead */}
        <div className="flex-1 flex overflow-x-auto overflow-y-auto relative bg-[#0A0D14]">
          {/* Left Track Headers Labels (Pinned) */}
          <div className="w-32 flex-shrink-0 bg-[#121622] border-r border-white/10 z-20 flex flex-col justify-between py-1 text-[11px] font-semibold text-slate-400 select-none">
            <div className="h-6 flex items-center px-2.5 text-[10px] text-slate-500">⏱️ ไม้บรรทัดเวลา</div>
            <div className="h-10 flex items-center px-2.5 gap-1.5 border-t border-white/5 text-slate-300">
              <Film className="w-3 h-3 text-blue-400" />
              <span>วิดีโอ 9:16</span>
            </div>
            <div className="h-9 flex items-center px-2.5 gap-1.5 border-t border-white/5 text-slate-300">
              <Type className="w-3 h-3 text-yellow-400" />
              <span>ซับไตเติล</span>
            </div>
            <div className="h-8 flex items-center px-2.5 gap-1.5 border-t border-white/5 text-slate-300">
              <Smile className="w-3 h-3 text-amber-400" />
              <span>ป้าย 3D</span>
            </div>
            <div className="h-8 flex items-center px-2.5 gap-1.5 border-t border-white/5 text-slate-300">
              <Volume2 className="w-3 h-3 text-rose-400" />
              <span>เสียงพากย์</span>
            </div>
            <div className="h-8 flex items-center px-2.5 gap-1.5 border-t border-white/5 text-slate-300">
              <Music className="w-3 h-3 text-cyan-400" />
              <span>เพลง BGM/SFX</span>
            </div>
          </div>

          {/* Right Scrollable Timeline Canvas */}
          <div
            className="flex-1 min-w-[700px] relative cursor-pointer"
            onClick={handleTimelineClick}
            style={{ width: `${100 * timelineZoom}%` }}
          >
            {/* 1. Time Ruler Header */}
            <div className="h-6 bg-[#0E121A] border-b border-white/10 flex items-center relative">
              {Array.from({ length: 10 }).map((_, i) => {
                const t = i * 2.0;
                const leftPct = (t / totalDuration) * 100;
                return (
                  <div
                    key={i}
                    className="absolute top-0 bottom-0 border-l border-white/10 flex items-center pl-1 text-[9px] font-mono text-slate-500"
                    style={{ left: `${leftPct}%` }}
                  >
                    {t.toFixed(0)}s
                  </div>
                );
              })}
            </div>

            {/* Playhead Needle (Red Indicator) */}
            <div
              className="absolute top-0 bottom-0 w-[2px] bg-[#FE2C55] z-30 pointer-events-none transition-all duration-75"
              style={{ left: `${(currentTime / totalDuration) * 100}%` }}
            >
              <div className="w-3.5 h-3.5 rounded-b-md bg-[#FE2C55] -ml-[6px] shadow-lg flex items-center justify-center">
                <div className="w-1 h-1 bg-white rounded-full" />
              </div>
            </div>

            {/* TRACK 1: Video & Cut Clips */}
            <div className="h-10 border-b border-white/5 relative p-0.5 flex items-center">
              {videoClips.map((clip) => {
                const left = (clip.start / totalDuration) * 100;
                const width = ((clip.end - clip.start) / totalDuration) * 100;
                const isSel = activeClip?.id === clip.id;
                return (
                  <div
                    key={clip.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveTrackItem({ track: 'video', id: clip.id });
                      setCurrentTime(clip.start);
                    }}
                    className={`absolute top-1 bottom-1 rounded-lg bg-gradient-to-r ${clip.color} border px-2 flex items-center justify-between text-xs font-bold text-white shadow-md overflow-hidden transition-all ${
                      isSel
                        ? 'ring-2 ring-white border-white scale-[1.01] z-10'
                        : 'border-white/20 hover:brightness-110'
                    }`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                  >
                    <span className="truncate text-[11px]">{clip.title}</span>
                    <span className="text-[9px] font-mono px-1 rounded bg-black/40">
                      {clip.scale}x
                    </span>
                  </div>
                );
              })}
            </div>

            {/* TRACK 2: Subtitle & Captions */}
            <div className="h-9 border-b border-white/5 relative p-0.5 flex items-center">
              {subtitleCues.map((sub) => {
                const left = (sub.start / totalDuration) * 100;
                const width = ((sub.end - sub.start) / totalDuration) * 100;
                const isSel = activeSub?.id === sub.id;
                return (
                  <div
                    key={sub.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setCurrentTime(sub.start);
                    }}
                    className={`absolute top-1 bottom-1 rounded-lg bg-yellow-500/20 border border-yellow-400/40 px-2 flex items-center text-xs font-semibold text-yellow-300 truncate shadow-sm ${
                      isSel ? 'ring-2 ring-yellow-400 bg-yellow-500/40' : 'hover:bg-yellow-500/30'
                    }`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                  >
                    <span className="truncate text-[10px]">💬 {sub.th}</span>
                  </div>
                );
              })}
            </div>

            {/* TRACK 3: 3D Promotional Stickers */}
            <div className="h-8 border-b border-white/5 relative p-0.5 flex items-center">
              {stickersTrack.map((st) => {
                const left = (st.start / totalDuration) * 100;
                const width = ((st.end - st.start) / totalDuration) * 100;
                const isSel = activeSticker?.id === st.id;
                return (
                  <div
                    key={st.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setCurrentTime(st.start);
                    }}
                    className={`absolute top-1 bottom-1 rounded-lg bg-amber-500/30 border border-amber-400/60 px-2 flex items-center text-[10px] font-bold text-amber-200 truncate ${
                      isSel ? 'ring-2 ring-amber-300 bg-amber-500/50' : 'hover:bg-amber-500/40'
                    }`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                  >
                    <span className="truncate">🏷️ {st.name}</span>
                  </div>
                );
              })}
            </div>

            {/* TRACK 4: Voiceover Waveform */}
            <div className="h-8 border-b border-white/5 relative p-0.5 flex items-center">
              <div className="w-full h-full rounded-lg bg-rose-500/20 border border-rose-500/30 px-2 flex items-center justify-between text-[10px] text-rose-300 font-mono">
                <span className="flex items-center gap-1 font-bold">🎙️ Voiceover (TikTok Pro AI)</span>
                <span className="tracking-widest text-rose-400"> ▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅ </span>
              </div>
            </div>

            {/* TRACK 5: BGM & SFX Cues */}
            <div className="h-8 relative p-0.5 flex items-center">
              <div className="w-full h-full rounded-lg bg-cyan-500/15 border border-cyan-500/30 px-2 flex items-center justify-between text-[10px] text-cyan-300 font-mono relative overflow-hidden">
                <span className="flex items-center gap-1 font-bold">🎵 {selectedBGM} (Ducked 25%)</span>
                
                {/* SFX Markers */}
                <div className="absolute inset-0 flex items-center pointer-events-none">
                  {sfxCues.map((sfx) => {
                    const left = (sfx.time / totalDuration) * 100;
                    return (
                      <div
                        key={sfx.id}
                        className="absolute top-1 bottom-1 px-1.5 rounded bg-emerald-500 text-black font-black text-[8px] flex items-center shadow"
                        style={{ left: `${left}%` }}
                      >
                        {sfx.label}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
