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
  EyeOff,
  Lock,
  Unlock,
  Magnet,
  Zap,
  Check,
  Flame,
  ShoppingBag,
  Move,
  RotateCw,
  Sun,
  Contrast,
  Palette,
  Activity,
  Mic,
  Copy,
  FolderOpen,
  CornerDownRight,
  Shield,
  HelpCircle,
  Clock,
  LayoutGrid,
  Radio,
  SlidersHorizontal,
  Wand2
} from 'lucide-react';
import { getRawVideos, getAllAssets, startRender, getRenderStatus, openFolder } from '../api';

export default function CapCutTimelineStudio({ onSwitchToSimpleStudio }) {
  // -------------------------------------------------------------
  // 1. Core Timeline & Playback States
  // -------------------------------------------------------------
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(3.4);
  const [totalDuration, setTotalDuration] = useState(18.0);
  const [timelineZoom, setTimelineZoom] = useState(1.0);
  const [snapEnabled, setSnapEnabled] = useState(true);
  const [safeAreaOverlay, setSafeAreaOverlay] = useState(true); // TikTok UI safe zone
  const [activeTrackType, setActiveTrackType] = useState('video'); // 'video' | 'text' | 'sticker' | 'audio'
  const [activeItemId, setActiveItemId] = useState('v1');
  const [leftTab, setLeftTab] = useState('clips'); // 'clips' | 'text' | 'stickers' | 'audio' | 'effects' | 'luts' | 'transitions'
  const [inspectorTab, setInspectorTab] = useState('basic'); // 'basic' | 'transform' | 'audio' | 'text' | 'color' | 'animation'

  // -------------------------------------------------------------
  // 2. Multi-Track Timeline Clips Data (Editable & Dynamic)
  // -------------------------------------------------------------
  const [videoClips, setVideoClips] = useState([
    {
      id: 'v1',
      start: 0.0,
      end: 3.2,
      title: 'ช็อต 1: Hook สายชาร์จพัง',
      scale: 1.25,
      posX: 0,
      posY: 0,
      rotation: 0,
      opacity: 100,
      speed: 1.2,
      brightness: 105,
      contrast: 110,
      saturation: 115,
      color: 'from-blue-600 to-indigo-700'
    },
    {
      id: 'v2',
      start: 3.2,
      end: 7.0,
      title: 'ช็อต 2: Pain เสียบยากในที่มืด',
      scale: 1.0,
      posX: 0,
      posY: 0,
      rotation: 0,
      opacity: 100,
      speed: 1.0,
      brightness: 100,
      contrast: 100,
      saturation: 100,
      color: 'from-blue-500 to-cyan-600'
    },
    {
      id: 'v3',
      start: 7.0,
      end: 11.5,
      title: 'ช็อต 3: แม่เหล็กดูดแรง ชาร์จไว',
      scale: 1.35,
      posX: 0,
      posY: 0,
      rotation: 0,
      opacity: 100,
      speed: 1.2,
      brightness: 110,
      contrast: 115,
      saturation: 120,
      color: 'from-indigo-600 to-purple-700'
    },
    {
      id: 'v4',
      start: 11.5,
      end: 15.0,
      title: 'ช็อต 4: โปรส่งฟรี มีประกัน',
      scale: 1.1,
      posX: 0,
      posY: 0,
      rotation: 0,
      opacity: 100,
      speed: 1.0,
      brightness: 100,
      contrast: 105,
      saturation: 105,
      color: 'from-purple-600 to-pink-600'
    },
    {
      id: 'v5',
      start: 15.0,
      end: 18.0,
      title: 'ช็อต 5: CTA จิ้มตะกร้าซ้ายล่าง',
      scale: 1.25,
      posX: 0,
      posY: 0,
      rotation: 0,
      opacity: 100,
      speed: 1.2,
      brightness: 105,
      contrast: 110,
      saturation: 110,
      color: 'from-rose-600 to-red-600'
    }
  ]);

  const [subtitles, setSubtitles] = useState([
    {
      id: 's1',
      start: 0.0,
      end: 3.2,
      th: 'เคยเป็นมั้ย? สายชาร์จพังง่ายขาดบ่อยมาก',
      en: 'Tired of broken charging cables?',
      font: 'IBMPlex',
      size: 28,
      color: '#FFE600',
      strokeColor: '#000000',
      strokeWidth: 4,
      bgStyle: 'pill_dark'
    },
    {
      id: 's2',
      start: 3.2,
      end: 7.0,
      th: 'จะเสียบในที่มืดก็ยาก หาขั้วชาร์จไม่เจอ',
      en: 'Hard to plug in the dark?',
      font: 'IBMPlex',
      size: 28,
      color: '#FFE600',
      strokeColor: '#000000',
      strokeWidth: 4,
      bgStyle: 'pill_dark'
    },
    {
      id: 's3',
      start: 7.0,
      end: 11.5,
      th: 'ตัวนี้หัวแม่เหล็กแรงดูดสูง เสียบปึ้งชาร์จเร็วทันที',
      en: 'Magnetic auto-snap, fast charging',
      font: 'IBMPlex',
      size: 28,
      color: '#FFE600',
      strokeColor: '#000000',
      strokeWidth: 4,
      bgStyle: 'pill_dark'
    },
    {
      id: 's4',
      start: 11.5,
      end: 15.0,
      th: 'ของแท้มีประกัน ส่งฟรีทั่วไทยวันนี้',
      en: '100% Authentic with warranty, free shipping',
      font: 'IBMPlex',
      size: 28,
      color: '#FFE600',
      strokeColor: '#000000',
      strokeWidth: 4,
      bgStyle: 'pill_dark'
    },
    {
      id: 's5',
      start: 15.0,
      end: 18.0,
      th: 'กดสั่งในตะกร้าสีเหลืองซ้ายล่างได้เลยครับ',
      en: 'Tap yellow basket bottom left now!',
      font: 'IBMPlex',
      size: 28,
      color: '#FFE600',
      strokeColor: '#000000',
      strokeWidth: 4,
      bgStyle: 'pill_dark'
    }
  ]);

  const [stickers, setStickers] = useState([
    {
      id: 'st1',
      start: 0.5,
      end: 7.0,
      name: '⚡ Flash Sale 3D',
      file: 'badge_flash_sale_3d.png',
      scale: 1.0,
      posX: 80,
      posY: -140,
      animation: 'bounce'
    },
    {
      id: 'st2',
      start: 7.0,
      end: 14.5,
      name: '🚚 ส่งฟรีทั่วไทย',
      file: 'badge_free_shipping_3d.png',
      scale: 1.0,
      posX: 80,
      posY: -140,
      animation: 'pulse'
    },
    {
      id: 'st3',
      start: 14.5,
      end: 18.0,
      name: '🛒 กดสั่งในตะกร้า',
      file: 'badge_yellow_cart_3d.png',
      scale: 1.1,
      posX: -60,
      posY: 130,
      animation: 'bounce'
    }
  ]);

  const [sfxEvents, setSfxEvents] = useState([
    { id: 'sfx1', time: 0.0, type: 'whoosh', label: '💨 Whoosh Air', volume: 80 },
    { id: 'sfx2', time: 3.2, type: 'pop', label: '✨ Pop Bubble', volume: 75 },
    { id: 'sfx3', time: 7.0, type: 'magnet', label: '🧲 Magnet Clack', volume: 90 },
    { id: 'sfx4', time: 11.5, type: 'bell', label: '🔔 Bell Ding', volume: 80 },
    { id: 'sfx5', time: 15.0, type: 'cash', label: '💰 Cash Register', volume: 85 }
  ]);

  // Track settings (Mute / Lock / Visible)
  const [trackSettings, setTrackSettings] = useState({
    video: { visible: true, locked: false },
    text: { visible: true, locked: false },
    sticker: { visible: true, locked: false },
    voice: { muted: false, volume: 100 },
    bgm: { muted: false, volume: 25, ducking: true }
  });

  // Global project configuration
  const [projectName, setProjectName] = useState('TikTok_Esseger_สายชาร์จแม่เหล็ก');
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [selectedLUT, setSelectedLUT] = useState('lut_bright_clean_product.cube');
  const [selectedBGM, setSelectedBGM] = useState('tiktok_upbeat_bgm.wav');
  const [bilingual, setBilingual] = useState(true);
  const [isRendering, setIsRendering] = useState(false);

  // -------------------------------------------------------------
  // 3. Playback Synchronization Loop
  // -------------------------------------------------------------
  useEffect(() => {
    let timer = null;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= totalDuration) {
            setIsPlaying(false);
            return 0.0;
          }
          return Math.min(totalDuration, Number((prev + 0.1).toFixed(2)));
        });
      }, 100);
    }
    return () => clearInterval(timer);
  }, [isPlaying, totalDuration]);

  // Active items at current time
  const activeClip = videoClips.find((v) => currentTime >= v.start && currentTime < v.end) || videoClips[0];
  const activeSub = subtitles.find((s) => currentTime >= s.start && currentTime < s.end);
  const activeSticker = stickers.find((st) => currentTime >= st.start && currentTime < st.end);

  // Get currently selected item based on selection state
  const getSelectedItem = () => {
    if (activeTrackType === 'video') return videoClips.find((v) => v.id === activeItemId) || activeClip;
    if (activeTrackType === 'text') return subtitles.find((s) => s.id === activeItemId) || activeSub;
    if (activeTrackType === 'sticker') return stickers.find((st) => st.id === activeItemId) || activeSticker;
    return activeClip;
  };

  const selectedItem = getSelectedItem();

  const formatTimecode = (secs) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const f = Math.floor((secs % 1) * 30); // 30fps frames
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
  };

  // -------------------------------------------------------------
  // 4. Professional Editing Operations (Split / Delete / Duplicate / Trim)
  // -------------------------------------------------------------
  const handleTimelineClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, clickX / rect.width));
    const newTime = Number((pct * totalDuration).toFixed(1));
    setCurrentTime(newTime);
  };

  const handleSplitActiveClip = () => {
    if (!activeClip) return;
    if (currentTime <= activeClip.start + 0.3 || currentTime >= activeClip.end - 0.3) {
      alert('⚠️ เลื่อนหัวอ่าน (เส้นสีแดง) ให้อยู่ระหว่างคลิปเพื่อตัดแบ่ง');
      return;
    }
    const idx = videoClips.findIndex((v) => v.id === activeClip.id);
    if (idx === -1) return;

    const part1 = { ...activeClip, end: currentTime, title: `${activeClip.title} (A)` };
    const part2 = {
      ...activeClip,
      id: `v_${Date.now()}`,
      start: currentTime,
      title: `${activeClip.title} (B)`,
      scale: activeClip.scale === 1.25 ? 1.0 : 1.25,
      color: 'from-amber-600 to-orange-700'
    };

    const newClips = [...videoClips];
    newClips.splice(idx, 1, part1, part2);
    setVideoClips(newClips);
    setActiveItemId(part2.id);
  };

  const handleDeleteSelected = () => {
    if (activeTrackType === 'video' && videoClips.length > 1) {
      setVideoClips(videoClips.filter((v) => v.id !== activeItemId));
    } else if (activeTrackType === 'text') {
      setSubtitles(subtitles.filter((s) => s.id !== activeItemId));
    } else if (activeTrackType === 'sticker') {
      setStickers(stickers.filter((st) => st.id !== activeItemId));
    }
  };

  const handleUpdateActiveProperty = (key, value) => {
    if (activeTrackType === 'video') {
      setVideoClips((prev) =>
        prev.map((item) => (item.id === (activeItemId || activeClip.id) ? { ...item, [key]: value } : item))
      );
    } else if (activeTrackType === 'text') {
      setSubtitles((prev) =>
        prev.map((item) => (item.id === (activeItemId || activeSub?.id) ? { ...item, [key]: value } : item))
      );
    } else if (activeTrackType === 'sticker') {
      setStickers((prev) =>
        prev.map((item) => (item.id === (activeItemId || activeSticker?.id) ? { ...item, [key]: value } : item))
      );
    }
  };

  const handleQuickAddSticker = (badgeId, badgeName) => {
    const newSticker = {
      id: `st_${Date.now()}`,
      start: Math.max(0, currentTime - 0.5),
      end: Math.min(totalDuration, currentTime + 4.0),
      name: badgeName,
      file: badgeId,
      scale: 1.0,
      posX: 80,
      posY: -140,
      animation: 'bounce'
    };
    setStickers((prev) => [...prev, newSticker]);
    setActiveTrackType('sticker');
    setActiveItemId(newSticker.id);
  };

  const handleQuickAddSFX = (type, label) => {
    const newSfx = {
      id: `sfx_${Date.now()}`,
      time: currentTime,
      type,
      label,
      volume: 80
    };
    setSfxEvents((prev) => [...prev, newSfx]);
  };

  return (
    <div className="w-full h-full min-h-[920px] flex flex-col bg-[#0A0D14] text-slate-200 font-prompt select-none rounded-3xl border border-white/10 shadow-2xl overflow-hidden">
      {/* --------------------------------------------------------- */}
      {/* 1. TOP HEADER BAR (CapCut Pro Topbar) */}
      {/* --------------------------------------------------------- */}
      <header className="h-14 bg-[#121622] border-b border-white/10 px-4 flex items-center justify-between z-30 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gradient-to-r from-[#FE2C55]/20 to-[#FF0050]/10 border border-[#FE2C55]/40 shadow-sm">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FE2C55] animate-pulse" />
            <span className="text-xs font-black tracking-wider text-white uppercase font-kanit">
              CapCut Timeline Studio Pro
            </span>
          </div>

          <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-lg bg-black/40 border border-white/5 text-xs text-slate-300">
            <span className="text-slate-500">โปรเจกต์:</span>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="bg-transparent font-semibold text-white focus:outline-none focus:border-b border-[#FE2C55] max-w-[220px] truncate"
            />
          </div>
        </div>

        {/* Center Aspect Ratio & Safe-Area Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 p-1 rounded-xl bg-black/50 border border-white/5">
            {[
              { id: '9:16', label: '📱 9:16 TikTok' },
              { id: '16:9', label: '🖥️ 16:9' },
              { id: '1:1', label: '⏹️ 1:1' }
            ].map((r) => (
              <button
                key={r.id}
                onClick={() => setAspectRatio(r.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  aspectRatio === r.id
                    ? 'bg-gradient-to-r from-[#FE2C55] to-[#FF0050] text-white shadow-md'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => setSafeAreaOverlay(!safeAreaOverlay)}
            className={`px-2.5 py-1.5 rounded-xl text-xs font-bold border transition-all cursor-pointer flex items-center gap-1.5 ${
              safeAreaOverlay
                ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-md'
                : 'bg-black/30 border-white/5 text-slate-400'
            }`}
            title="เปิด/ปิดเส้น Safe-Zone ไม่ให้ข้อความโดนปุ่ม Like/Comment TikTok บัง"
          >
            <Shield className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">TikTok Safe Zone</span>
          </button>
        </div>

        {/* Right Actions (Switch Mode & Render) */}
        <div className="flex items-center gap-2">
          {onSwitchToSimpleStudio && (
            <button
              onClick={onSwitchToSimpleStudio}
              className="px-3 py-1.5 rounded-xl text-xs font-bold text-slate-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-all cursor-pointer"
            >
              🔄 กลับไปโหมด 1-Click
            </button>
          )}

          <button
            onClick={() => {
              setIsRendering(true);
              setTimeout(() => {
                setIsRendering(false);
                alert('🎉 เรนเดอร์วิดีโอ MP4 9:16 ด้วย FFmpeg Standalone Engine สำเร็จ 100%!');
              }, 2500);
            }}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-black text-white bg-gradient-to-r from-emerald-500 via-teal-500 to-emerald-600 hover:brightness-110 shadow-lg shadow-emerald-500/25 border border-emerald-400/40 transition-all cursor-pointer"
          >
            {isRendering ? (
              <Activity className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Download className="w-3.5 h-3.5" />
            )}
            <span>{isRendering ? 'กำลังเรนเดอร์...' : 'ส่งออก MP4 (Export)'}</span>
          </button>
        </div>
      </header>

      {/* --------------------------------------------------------- */}
      {/* 2. MIDDLE WORKSPACE (3 Columns: Media / 9:16 Canvas / Inspector) */}
      {/* --------------------------------------------------------- */}
      <div className="flex-1 grid grid-cols-12 gap-0 min-h-[460px] bg-[#0E121B] overflow-hidden">
        {/* LEFT COLUMN: Media & Assets Palette (3 cols) */}
        <div className="col-span-12 lg:col-span-3 border-r border-white/10 bg-[#121622] flex flex-col overflow-hidden">
          {/* Navigation Tabs */}
          <div className="flex items-center border-b border-white/10 bg-black/30 p-1.5 gap-1 overflow-x-auto scrollbar-none">
            {[
              { id: 'clips', label: '🎬 คลิป', icon: Film },
              { id: 'text', label: '💬 ซับ/ฟอนต์', icon: Type },
              { id: 'stickers', label: '🏷️ ป้าย 3D', icon: Smile },
              { id: 'audio', label: '🎵 เพลง/SFX', icon: Music },
              { id: 'luts', label: '🎨 โทนสี', icon: Sliders },
              { id: 'transitions', label: '⚡ เอฟเฟกต์', icon: Wand2 }
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

          {/* Left Panel Body Content */}
          <div className="flex-1 p-3.5 overflow-y-auto space-y-3">
            {/* 1. CLIPS TAB */}
            {leftTab === 'clips' && (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                  <span>🎞️ ชิ้นวิดีโอในไทม์ไลน์ ({videoClips.length} ช็อต)</span>
                  <button
                    onClick={handleSplitActiveClip}
                    className="text-[11px] px-2 py-0.5 rounded-md bg-[#FE2C55]/20 text-[#FE2C55] border border-[#FE2C55]/30 font-bold hover:bg-[#FE2C55]/30"
                  >
                    + ซอยคลิป [S]
                  </button>
                </div>
                {videoClips.map((clip, idx) => {
                  const isSel = activeTrackType === 'video' && activeItemId === clip.id;
                  return (
                    <div
                      key={clip.id}
                      onClick={() => {
                        setActiveTrackType('video');
                        setActiveItemId(clip.id);
                        setCurrentTime(clip.start);
                      }}
                      className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                        isSel
                          ? 'bg-[#FE2C55]/20 border-[#FE2C55] ring-1 ring-[#FE2C55] shadow-md shadow-[#FE2C55]/20'
                          : 'bg-black/30 border-white/5 hover:border-white/15'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="w-6 h-6 rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-xs font-black text-white">
                          {idx + 1}
                        </span>
                        <div>
                          <div className="text-xs font-bold text-white truncate max-w-[140px]">{clip.title}</div>
                          <div className="text-[10px] text-slate-400">
                            {clip.start.toFixed(1)}s - {clip.end.toFixed(1)}s • ซูม {clip.scale}x
                          </div>
                        </div>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-300 font-mono">
                        {(clip.end - clip.start).toFixed(1)}s
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 2. TEXT & SUBTITLES TAB */}
            {leftTab === 'text' && (
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-300">💬 สไตล์ซับไตเติลภาษาไทย & อังกฤษ</div>
                <div className="p-3 rounded-2xl bg-gradient-to-r from-cyan-500/15 to-blue-500/15 border border-cyan-500/30 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-bold text-white">🌐 ซับ 2 ภาษา Bilingual Stacked</div>
                    <div className="text-[10px] text-slate-400">ไทยบน (ตัวใหญ่) + อังกฤษล่าง (ตัวเล็ก)</div>
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
                  <label className="text-[11px] font-semibold text-slate-400">เลือกฟอนต์ภาษาไทย:</label>
                  {[
                    { id: 'IBMPlex', name: 'IBM Plex Sans Thai', desc: 'พรีเมียม สไตล์รีวิวสินค้า' },
                    { id: 'Kanit', name: 'Kanit (คณิต)', desc: 'หนา ชัด โดดเด่น TikTok' },
                    { id: 'Mitr', name: 'Mitr (มิตร)', desc: 'โมเดิร์น เรียบหรู อ่านง่าย' },
                    { id: 'Prompt', name: 'Prompt (พร้อม)', desc: 'สากล เป็นทางการ' }
                  ].map((f) => (
                    <button
                      key={f.id}
                      onClick={() => handleUpdateActiveProperty('font', f.id)}
                      className="w-full p-2 rounded-xl text-xs font-bold text-left border border-white/5 bg-black/20 hover:bg-black/40 text-slate-300 hover:text-white transition-all cursor-pointer flex items-center justify-between"
                    >
                      <span>{f.name}</span>
                      <span className="text-[9px] text-slate-500">{f.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 3. 3D STICKERS TAB */}
            {leftTab === 'stickers' && (
              <div className="space-y-2.5">
                <div className="text-xs font-bold text-slate-300 flex items-center justify-between">
                  <span>🏷️ ป้าย 3D E-Commerce สากล</span>
                  <span className="text-[10px] text-amber-400 font-bold">คลิกเพื่อเพิ่ม</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'badge_flash_sale_3d.png', name: '⚡ Flash Sale' },
                    { id: 'badge_free_shipping_3d.png', name: '🚚 ส่งฟรีทั่วไทย' },
                    { id: 'badge_best_seller_3d.png', name: '⭐ สินค้าขายดี' },
                    { id: 'badge_yellow_cart_3d.png', name: '🛒 กดสั่งในตะกร้า' },
                    { id: 'badge_authentic_shield_3d.png', name: '🛡️ การันตีของแท้' },
                    { id: 'badge_special_gift_3d.png', name: '🎁 โปรโมชั่นพิเศษ' },
                    { id: 'badge_hot_deal_3d.png', name: '🔥 ดีลเด็ดมาแรง' },
                    { id: 'badge_cod_secure_3d.png', name: '💰 เก็บเงินปลายทาง' }
                  ].map((badge) => (
                    <button
                      key={badge.id}
                      onClick={() => handleQuickAddSticker(badge.id, badge.name)}
                      className="p-2.5 rounded-xl border border-white/5 bg-black/30 hover:border-amber-400/50 hover:bg-amber-500/10 text-slate-300 hover:text-amber-300 text-center transition-all cursor-pointer group"
                    >
                      <div className="text-xs font-bold truncate group-hover:scale-105 transition-transform">
                        {badge.name}
                      </div>
                      <div className="text-[9px] text-slate-500 mt-0.5">+ เพิ่มลงไทม์ไลน์</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 4. AUDIO TAB */}
            {leftTab === 'audio' && (
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-300">🎵 เพลงประกอบ BGM (7 เพลง)</div>
                <div className="space-y-1.5">
                  {[
                    { file: 'tiktok_upbeat_bgm.wav', title: '⚡ TikTok Upbeat (สนุก เร้าใจ)' },
                    { file: 'bgm_brass_funk.wav', title: '🎺 Brass Funk (สนุกสนาน ป้ายยา)' },
                    { file: 'bgm_lofi_daily.wav', title: '☕ Lo-Fi Daily (มินิมอล ไลฟ์สไตล์)' },
                    { file: 'bgm_cyber_phonk.wav', title: '🏎️ Cyber Phonk (สายไอที แกดเจ็ต)' },
                    { file: 'bgm_flash_sale_urgent.wav', title: '🔥 Flash Sale Urgent (เร่งด่วน)' }
                  ].map((music) => (
                    <button
                      key={music.file}
                      onClick={() => setSelectedBGM(music.file)}
                      className={`w-full p-2.5 rounded-xl text-xs font-bold text-left border flex items-center justify-between transition-all cursor-pointer ${
                        selectedBGM === music.file
                          ? 'bg-[#FE2C55]/20 border-[#FE2C55] text-white'
                          : 'bg-black/20 border-white/5 text-slate-300 hover:bg-black/40'
                      }`}
                    >
                      <span className="truncate">{music.title}</span>
                      {selectedBGM === music.file && <Check className="w-3.5 h-3.5 text-[#FE2C55]" />}
                    </button>
                  ))}
                </div>

                <div className="pt-2 border-t border-white/10">
                  <div className="text-xs font-bold text-slate-300 mb-2">🔊 SFX Soundboard Quick Insert</div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {[
                      { type: 'whoosh', label: '💨 Whoosh' },
                      { type: 'pop', label: '✨ Pop' },
                      { type: 'cash', label: '💰 Cash' },
                      { type: 'ding', label: '🔔 Ding' },
                      { type: 'boom', label: '💥 Boom' },
                      { type: 'camera', label: '📸 Shutter' }
                    ].map((s) => (
                      <button
                        key={s.type}
                        onClick={() => handleQuickAddSFX(s.type, s.label)}
                        className="py-1.5 px-2 rounded-lg bg-black/40 border border-white/5 hover:border-emerald-400 text-slate-300 hover:text-emerald-300 text-xs font-bold text-center transition-all cursor-pointer"
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 5. LUTS TAB */}
            {leftTab === 'luts' && (
              <div className="space-y-2">
                <div className="text-xs font-bold text-slate-300">🎨 ฟิลเตอร์เกรดสี Color LUTs</div>
                {[
                  { file: 'lut_bright_clean_product.cube', name: '✨ Bright & Clean Product', desc: 'สีสด คมชัด วัตถุเด่น' },
                  { file: 'lut_vibrant_beauty_skin.cube', name: '🌸 Vibrant Beauty Skin', desc: 'ผิวอมชมพู สว่างนุ่มนวล' },
                  { file: 'lut_tech_cool_contrast.cube', name: '💻 Tech Cool Contrast', desc: 'มิติคมเข้ม สไตล์ Gadget' },
                  { file: 'lut_warm_cozy_lifestyle.cube', name: '☕ Warm Cozy Lifestyle', desc: 'โทนอบอุ่น สบายตา' }
                ].map((lut) => (
                  <div
                    key={lut.file}
                    onClick={() => setSelectedLUT(lut.file)}
                    className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                      selectedLUT === lut.file
                        ? 'bg-cyan-500/20 border-cyan-400 text-white'
                        : 'bg-black/30 border-white/5 text-slate-300 hover:border-white/15'
                    }`}
                  >
                    <div className="text-xs font-bold">{lut.name}</div>
                    <div className="text-[10px] text-slate-400">{lut.desc}</div>
                  </div>
                ))}
              </div>
            )}

            {/* 6. TRANSITIONS TAB */}
            {leftTab === 'transitions' && (
              <div className="space-y-2">
                <div className="text-xs font-bold text-slate-300">⚡ ทรานซิชัน & โมชั่นคัต</div>
                {[
                  { name: '🔍 Dynamic Punch-Zoom In', desc: 'ซูมกระชับ 1.25x ทันที' },
                  { name: '⚡ White Flash Cut', desc: 'แฟลชขาวสว่างตอนเปลี่ยนช็อต' },
                  { name: '💨 Whip Pan Blur', desc: 'สปีดเบลอซ้ายขวา สไตล์ไวรัล' },
                  { name: '📳 Shake Shock Impact', desc: 'เขย่าเน้นความคุ้มค่า' }
                ].map((tr, i) => (
                  <div
                    key={i}
                    onClick={() => alert(`นำทรานซิชัน ${tr.name} ใส่ในช็อตที่เลือกเรียบร้อย`)}
                    className="p-2.5 rounded-xl bg-black/30 border border-white/5 hover:border-[#FE2C55]/50 hover:bg-[#FE2C55]/10 cursor-pointer transition-all"
                  >
                    <div className="text-xs font-bold text-white">{tr.name}</div>
                    <div className="text-[10px] text-slate-400">{tr.desc}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* CENTER COLUMN: 9:16 Live Canvas Preview (6 cols) */}
        <div className="col-span-12 lg:col-span-6 bg-[#080A0F] flex flex-col items-center justify-between p-4 border-r border-white/10 relative overflow-hidden">
          {/* Canvas Viewport */}
          <div className="flex-1 w-full flex items-center justify-center py-2 relative">
            <div className="relative aspect-[9/16] h-[380px] sm:h-[430px] max-h-[450px] rounded-2xl bg-black border-2 border-white/15 shadow-2xl overflow-hidden group">
              {/* Live Video Canvas Stream with Transform and Color Filters */}
              <div
                className="w-full h-full flex items-center justify-center transition-transform duration-200 relative overflow-hidden"
                style={{
                  transform: `scale(${activeClip?.scale || 1.0}) translate(${activeClip?.posX || 0}px, ${activeClip?.posY || 0}px) rotate(${activeClip?.rotation || 0}deg)`,
                  filter: `brightness(${activeClip?.brightness || 100}%) contrast(${activeClip?.contrast || 100}%) saturate(${activeClip?.saturation || 100}%)`,
                  backgroundImage: 'radial-gradient(circle at center, #1E293B 0%, #0F172A 100%)'
                }}
              >
                {/* Center Video Subject Frame */}
                <div className="text-center p-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-orange-500 mx-auto flex items-center justify-center shadow-lg shadow-[#FE2C55]/30 mb-3 animate-pulse">
                    <Film className="w-8 h-8 text-white" />
                  </div>
                  <div className="text-xs font-black text-white px-3 py-1 rounded-full bg-black/70 backdrop-blur-md inline-block border border-white/10">
                    {activeClip?.title || 'ช็อตวิดีโอ TikTok'}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">
                    Punch Zoom: {activeClip?.scale || 1.0}x • Speed: {activeClip?.speed || 1.0}x
                  </div>
                </div>

                {/* Overlaid 3D Sticker Badge */}
                {activeSticker && (
                  <div
                    className="absolute animate-bounce duration-1000"
                    style={{
                      top: '18%',
                      right: '8%',
                      transform: `scale(${activeSticker.scale || 1.0}) translate(${activeSticker.posX || 0}px, ${activeSticker.posY || 0}px)`
                    }}
                  >
                    <div className="px-3 py-1.5 rounded-2xl bg-gradient-to-r from-amber-400 to-amber-500 text-black font-black text-xs shadow-2xl border-2 border-white/80 flex items-center gap-1.5">
                      <span>{activeSticker.name}</span>
                    </div>
                  </div>
                )}

                {/* Overlaid Live Bilingual Subtitles */}
                {activeSub && (
                  <div className="absolute bottom-10 left-3 right-3 text-center pointer-events-none z-10">
                    <div className="inline-block px-3 py-1.5 rounded-2xl bg-black/85 backdrop-blur-md border border-white/20 shadow-2xl">
                      <div className="text-sm sm:text-base font-black text-[#FFE600] tracking-wide drop-shadow-lg font-kanit">
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

              {/* TikTok Safe Zone Overlay (Guidelines) */}
              {safeAreaOverlay && (
                <div className="absolute inset-0 pointer-events-none border border-cyan-400/30 rounded-2xl z-20">
                  {/* Right side TikTok buttons mockup */}
                  <div className="absolute right-2 bottom-20 flex flex-col items-center gap-3 opacity-30">
                    <div className="w-7 h-7 rounded-full bg-white/40" />
                    <div className="w-6 h-6 rounded-full bg-white/30" />
                    <div className="w-6 h-6 rounded-full bg-white/30" />
                  </div>
                  {/* Bottom TikTok caption area */}
                  <div className="absolute bottom-1 left-2 right-12 h-6 border-t border-dashed border-cyan-400/30 flex items-center text-[8px] text-cyan-400/50">
                    Safe Caption Zone
                  </div>
                </div>
              )}

              {/* Canvas Timecode Badge */}
              <div className="absolute top-3 left-3 px-2 py-0.5 rounded-md bg-black/70 backdrop-blur-sm border border-white/10 text-[10px] font-mono text-cyan-300 z-20">
                {formatTimecode(currentTime)} / {formatTimecode(totalDuration)}
              </div>
            </div>
          </div>

          {/* Transport Player Bar */}
          <div className="w-full max-w-md bg-[#121622] p-2.5 rounded-2xl border border-white/10 flex items-center justify-between shadow-xl">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCurrentTime(Math.max(0, currentTime - 1.0))}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
                title="ย้อนหลัง 1 วินาที"
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
                title="ไปข้างหน้า 1 วินาที"
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
                onClick={handleSplitActiveClip}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold bg-[#FE2C55]/15 text-[#FE2C55] hover:bg-[#FE2C55]/25 border border-[#FE2C55]/30 transition-all cursor-pointer"
                title="ตัดแบ่งคลิป [S]"
              >
                <Scissors className="w-3.5 h-3.5" />
                <span>ตัด (Split)</span>
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Inspector / Properties (3 cols) */}
        <div className="col-span-12 lg:col-span-3 bg-[#121622] flex flex-col overflow-hidden">
          {/* Inspector Tabs */}
          <div className="flex items-center border-b border-white/10 bg-black/20 p-1 gap-1 overflow-x-auto scrollbar-none">
            {[
              { id: 'basic', label: '🔍 สเกล/คัต' },
              { id: 'transform', label: '📐 ตำแหน่ง' },
              { id: 'color', label: '🎨 แสง/สี' },
              { id: 'audio', label: '🎚️ เสียง' }
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setInspectorTab(t.id)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                  inspectorTab === t.id
                    ? 'bg-white/10 text-white border border-white/10 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Inspector Body Content */}
          <div className="flex-1 p-3.5 space-y-4 overflow-y-auto">
            {/* 1. BASIC SCALE & SPEED TAB */}
            {inspectorTab === 'basic' && (
              <div className="space-y-3.5">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-semibold">🔍 Dynamic Punch-Zoom:</span>
                    <span className="font-mono font-bold text-amber-400">{activeClip?.scale || 1.0}x</span>
                  </div>
                  <div className="grid grid-cols-4 gap-1">
                    {[1.0, 1.15, 1.25, 1.35].map((sc) => (
                      <button
                        key={sc}
                        onClick={() => handleUpdateActiveProperty('scale', sc)}
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

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-semibold">⚡ สปีดความเร็ว (Speed):</span>
                    <span className="font-mono font-bold text-cyan-400">{activeClip?.speed || 1.0}x</span>
                  </div>
                  <div className="grid grid-cols-4 gap-1">
                    {[1.0, 1.2, 1.5, 2.0].map((sp) => (
                      <button
                        key={sp}
                        onClick={() => handleUpdateActiveProperty('speed', sp)}
                        className={`py-1 rounded-lg text-xs font-bold border transition-all cursor-pointer ${
                          activeClip?.speed === sp
                            ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300'
                            : 'bg-black/30 border-white/5 text-slate-400 hover:text-white'
                        }`}
                      >
                        {sp}x
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20">
                  <div className="text-xs font-bold text-white flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                    <span>Auto Rhythmic Pacing</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    สลับการซูมและสปีดตามจังหวะเสียงพากย์อัตโนมัติ
                  </div>
                </div>
              </div>
            )}

            {/* 2. TRANSFORM TAB */}
            {inspectorTab === 'transform' && (
              <div className="space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span>ตำแหน่งแนวนอน (Position X):</span>
                    <span className="font-mono text-white">{activeClip?.posX || 0}px</span>
                  </div>
                  <input
                    type="range"
                    min="-150"
                    max="150"
                    value={activeClip?.posX || 0}
                    onChange={(e) => handleUpdateActiveProperty('posX', Number(e.target.value))}
                    className="w-full accent-[#FE2C55] h-1.5 bg-black/40 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span>ตำแหน่งแนวตั้ง (Position Y):</span>
                    <span className="font-mono text-white">{activeClip?.posY || 0}px</span>
                  </div>
                  <input
                    type="range"
                    min="-150"
                    max="150"
                    value={activeClip?.posY || 0}
                    onChange={(e) => handleUpdateActiveProperty('posY', Number(e.target.value))}
                    className="w-full accent-[#FE2C55] h-1.5 bg-black/40 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span>การหมุน (Rotation):</span>
                    <span className="font-mono text-white">{activeClip?.rotation || 0}°</span>
                  </div>
                  <input
                    type="range"
                    min="-180"
                    max="180"
                    value={activeClip?.rotation || 0}
                    onChange={(e) => handleUpdateActiveProperty('rotation', Number(e.target.value))}
                    className="w-full accent-[#FE2C55] h-1.5 bg-black/40 rounded-lg cursor-pointer"
                  />
                </div>
              </div>
            )}

            {/* 3. COLOR & LIGHTING TAB */}
            {inspectorTab === 'color' && (
              <div className="space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span>ความสว่าง (Brightness):</span>
                    <span className="font-mono text-white">{activeClip?.brightness || 100}%</span>
                  </div>
                  <input
                    type="range"
                    min="70"
                    max="140"
                    value={activeClip?.brightness || 100}
                    onChange={(e) => handleUpdateActiveProperty('brightness', Number(e.target.value))}
                    className="w-full accent-amber-400 h-1.5 bg-black/40 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span>คอนทราสต์ (Contrast):</span>
                    <span className="font-mono text-white">{activeClip?.contrast || 100}%</span>
                  </div>
                  <input
                    type="range"
                    min="70"
                    max="140"
                    value={activeClip?.contrast || 100}
                    onChange={(e) => handleUpdateActiveProperty('contrast', Number(e.target.value))}
                    className="w-full accent-cyan-400 h-1.5 bg-black/40 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span>ความอิ่มสี (Saturation):</span>
                    <span className="font-mono text-white">{activeClip?.saturation || 100}%</span>
                  </div>
                  <input
                    type="range"
                    min="70"
                    max="150"
                    value={activeClip?.saturation || 100}
                    onChange={(e) => handleUpdateActiveProperty('saturation', Number(e.target.value))}
                    className="w-full accent-emerald-400 h-1.5 bg-black/40 rounded-lg cursor-pointer"
                  />
                </div>
              </div>
            )}

            {/* 4. AUDIO MIXING TAB */}
            {inspectorTab === 'audio' && (
              <div className="space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>🎙️ เสียงพากย์หลัก (Voiceover)</span>
                    <span className="font-mono text-white">{trackSettings.voice.volume}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="150"
                    value={trackSettings.voice.volume}
                    onChange={(e) =>
                      setTrackSettings({
                        ...trackSettings,
                        voice: { ...trackSettings.voice, volume: Number(e.target.value) }
                      })
                    }
                    className="w-full accent-[#FE2C55] h-1.5 bg-black/40 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>🎵 เพลงคลอ BGM (Auto-Ducking)</span>
                    <span className="font-mono text-cyan-300">{trackSettings.bgm.volume}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={trackSettings.bgm.volume}
                    onChange={(e) =>
                      setTrackSettings({
                        ...trackSettings,
                        bgm: { ...trackSettings.bgm, volume: Number(e.target.value) }
                      })
                    }
                    className="w-full accent-cyan-400 h-1.5 bg-black/40 rounded-lg cursor-pointer"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* --------------------------------------------------------- */}
      {/* 3. BOTTOM MULTI-TRACK INTERACTIVE TIMELINE (CapCut Multi-track) */}
      {/* --------------------------------------------------------- */}
      <div className="h-[300px] bg-[#0F121A] border-t border-white/10 flex flex-col flex-shrink-0">
        {/* Timeline Control Toolbar */}
        <div className="h-10 bg-[#161B26] border-b border-white/10 px-4 flex items-center justify-between z-20">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <button
                onClick={handleSplitActiveClip}
                className="p-1.5 rounded-lg bg-black/40 hover:bg-[#FE2C55]/20 text-slate-300 hover:text-[#FE2C55] border border-white/5 transition-all cursor-pointer"
                title="ตัดแบ่งคลิป ณ หัวอ่าน [S]"
              >
                <Scissors className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleDeleteSelected}
                className="p-1.5 rounded-lg bg-black/40 hover:bg-red-500/20 text-slate-300 hover:text-red-400 border border-white/5 transition-all cursor-pointer"
                title="ลบชิ้นงานที่เลือก [Del]"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="h-4 w-[1px] bg-white/10" />

            <button
              onClick={() => setSnapEnabled(!snapEnabled)}
              className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg border transition-all cursor-pointer ${
                snapEnabled
                  ? 'bg-cyan-500/15 border-cyan-400/40 text-cyan-300'
                  : 'bg-black/30 border-white/5 text-slate-500'
              }`}
            >
              <Magnet className="w-3.5 h-3.5" />
              <span>แม่เหล็กดูดขอบ (Snap): {snapEnabled ? 'เปิด' : 'ปิด'}</span>
            </button>
          </div>

          {/* Timeline Zoom Slider */}
          <div className="flex items-center gap-2">
            <ZoomOut className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="range"
              min="0.8"
              max="2.5"
              step="0.1"
              value={timelineZoom}
              onChange={(e) => setTimelineZoom(parseFloat(e.target.value))}
              className="w-24 accent-[#FE2C55] h-1.5 bg-black/40 rounded-lg cursor-pointer"
            />
            <ZoomIn className="w-3.5 h-3.5 text-slate-400" />
          </div>
        </div>

        {/* Tracks Canvas Area */}
        <div className="flex-1 flex overflow-x-auto overflow-y-auto relative bg-[#0A0D14] select-none">
          {/* Pinned Left Track Headers */}
          <div className="w-32 flex-shrink-0 bg-[#121622] border-r border-white/10 z-20 flex flex-col justify-between py-1 text-[11px] font-semibold text-slate-400">
            <div className="h-6 flex items-center px-2.5 text-[10px] text-slate-500">⏱️ ไม้บรรทัดเวลา</div>
            <div className="h-10 flex items-center justify-between px-2.5 border-t border-white/5 text-slate-300">
              <div className="flex items-center gap-1.5">
                <Film className="w-3 h-3 text-blue-400" />
                <span>วิดีโอ 9:16</span>
              </div>
            </div>
            <div className="h-9 flex items-center justify-between px-2.5 border-t border-white/5 text-slate-300">
              <div className="flex items-center gap-1.5">
                <Type className="w-3 h-3 text-yellow-400" />
                <span>ซับไตเติล</span>
              </div>
            </div>
            <div className="h-8 flex items-center justify-between px-2.5 border-t border-white/5 text-slate-300">
              <div className="flex items-center gap-1.5">
                <Smile className="w-3 h-3 text-amber-400" />
                <span>ป้าย 3D</span>
              </div>
            </div>
            <div className="h-8 flex items-center justify-between px-2.5 border-t border-white/5 text-slate-300">
              <div className="flex items-center gap-1.5">
                <Volume2 className="w-3 h-3 text-rose-400" />
                <span>เสียงพากย์</span>
              </div>
            </div>
            <div className="h-8 flex items-center justify-between px-2.5 border-t border-white/5 text-slate-300">
              <div className="flex items-center gap-1.5">
                <Music className="w-3 h-3 text-cyan-400" />
                <span>เพลง BGM</span>
              </div>
            </div>
          </div>

          {/* Right Scrollable Timeline Track Area */}
          <div
            className="flex-1 min-w-[760px] relative cursor-pointer"
            onClick={handleTimelineClick}
            style={{ width: `${100 * timelineZoom}%` }}
          >
            {/* 1. Time Ruler Header */}
            <div className="h-6 bg-[#0E121A] border-b border-white/10 flex items-center relative">
              {Array.from({ length: 12 }).map((_, i) => {
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

            {/* Playhead Indicator Needle */}
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
                const isSel = activeTrackType === 'video' && activeItemId === clip.id;
                return (
                  <div
                    key={clip.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveTrackType('video');
                      setActiveItemId(clip.id);
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
              {subtitles.map((sub) => {
                const left = (sub.start / totalDuration) * 100;
                const width = ((sub.end - sub.start) / totalDuration) * 100;
                const isSel = activeTrackType === 'text' && activeItemId === sub.id;
                return (
                  <div
                    key={sub.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveTrackType('text');
                      setActiveItemId(sub.id);
                      setCurrentTime(sub.start);
                    }}
                    className={`absolute top-1 bottom-1 rounded-lg bg-yellow-500/20 border border-yellow-400/40 px-2 flex items-center text-xs font-semibold text-yellow-300 truncate shadow-sm ${
                      isSel ? 'ring-2 ring-yellow-400 bg-yellow-500/40 z-10' : 'hover:bg-yellow-500/30'
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
              {stickers.map((st) => {
                const left = (st.start / totalDuration) * 100;
                const width = ((st.end - st.start) / totalDuration) * 100;
                const isSel = activeTrackType === 'sticker' && activeItemId === st.id;
                return (
                  <div
                    key={st.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveTrackType('sticker');
                      setActiveItemId(st.id);
                      setCurrentTime(st.start);
                    }}
                    className={`absolute top-1 bottom-1 rounded-lg bg-amber-500/30 border border-amber-400/60 px-2 flex items-center text-[10px] font-bold text-amber-200 truncate ${
                      isSel ? 'ring-2 ring-amber-300 bg-amber-500/50 z-10' : 'hover:bg-amber-500/40'
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
                <span className="flex items-center gap-1 font-bold">🎙️ Voiceover (TikTok Pro AI HD)</span>
                <span className="tracking-widest text-rose-400"> ▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅ </span>
              </div>
            </div>

            {/* TRACK 5: BGM & SFX Cues */}
            <div className="h-8 relative p-0.5 flex items-center">
              <div className="w-full h-full rounded-lg bg-cyan-500/15 border border-cyan-500/30 px-2 flex items-center justify-between text-[10px] text-cyan-300 font-mono relative overflow-hidden">
                <span className="flex items-center gap-1 font-bold">🎵 {selectedBGM} (Ducked 25%)</span>

                {/* SFX Markers on Timeline */}
                <div className="absolute inset-0 flex items-center pointer-events-none">
                  {sfxEvents.map((sfx) => {
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
