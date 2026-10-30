import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  Folder, Volume2, Square, Music, Type,
  Search, Play, Pause, Download, Trash2, Upload, Sparkles, Image as ImageIcon,
  Film, Palette, AlertTriangle, X, Check, RefreshCw, Layers, Sliders,
  CheckCircle2, HardDrive, Cpu, Smartphone, Copy, ExternalLink,
  Columns, LayoutGrid, List, ChevronRight, Eye, VolumeX, ShieldCheck, Tag, Info, RotateCcw, Star
} from 'lucide-react';
import { openFolder, getAllAssets, uploadAsset, deleteFile, starAsset } from '../api';
import { Modal, Toast, Button, Badge, Input, ConfirmModal, PageHeader } from './ui';
import PaginationControls from './PaginationControls';
import { useDebounce, useToast } from '../hooks';

export default function MediaAssetsHub({ status }) {
  // ── Tab & View State ──
  const [activeAssetTab, setActiveAssetTab] = useState('sfx'); // 'sfx' | 'music' | 'fonts' | 'stickers' | 'luts' | 'effects' | 'system'
  const [viewMode, setViewMode] = useState(() => {
    try {
      return localStorage.getItem('omnicut_assets_view_mode') || 'grid';
    } catch {
      return 'grid';
    }
  }); // 'grid' (default) | 'split'

  useEffect(() => {
    try {
      localStorage.setItem('omnicut_assets_view_mode', viewMode);
    } catch {}
  }, [viewMode]);
  const [assetData, setAssetData] = useState({ sfx: [], music: [], fonts: [], stickers: [], luts: [], effects: [], counts: {} });
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sfxCategory, setSfxCategory] = useState('all'); // Sub-category filter for SFX
  const debouncedSearch = useDebounce(searchQuery, 250);

  // ── Selected Asset for Workbench Inspector ──
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [checkerboardBg, setCheckerboardBg] = useState(true); // For 3D stickers/badges
  const [fontSizePreview, setFontSizePreview] = useState(32);
  const [customFontText, setCustomFontText] = useState('อย่าเพิ่งเลื่อนผ่าน! ซื้อ 1 แถม 1 เฉพาะวันนี้');
  const [copiedPath, setCopiedPath] = useState(false);
  const [previewEffect, setPreviewEffect] = useState(null);

  // ── Audio Player State ──
  const [currentlyPlayingAudio, setCurrentlyPlayingAudio] = useState(null);
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const audioRef = useRef(null);

  // ── Upload & Delete State ──
  const [uploadingAsset, setUploadingAsset] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const fileUploadRef = useRef(null);
  const { toastMessage, toastType, toastDuration, showToast, hideToast } = useToast();

  // ── Fetch Assets ──
  const fetchAssets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAllAssets();
      setAssetData(data || { sfx: [], music: [], fonts: [], stickers: [], luts: [], effects: [], counts: {} });
    } catch (err) {
      console.error('Failed to fetch assets:', err);
      showToast('ไม่สามารถดึงข้อมูล Assets ได้', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  // ── Open Folder Utility ──
  const handleOpen = useCallback((target) => {
    openFolder(target);
  }, []);

  // ── Copy to Clipboard Utility ──
  const handleCopy = useCallback((text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  }, []);

  // ── Star / Favorite Toggle (marks an asset as usable-in-editing) ──
  const handleToggleStar = useCallback((item, e) => {
    if (e) e.stopPropagation();
    const nextStarred = !item.starred;
    setAssetData((prev) => {
      const patchList = (list) => (list || []).map((it) => (it.id === item.id ? { ...it, starred: nextStarred } : it));
      return { ...prev, sfx: patchList(prev.sfx), music: patchList(prev.music), effects: patchList(prev.effects) };
    });
    setSelectedAsset((prev) => (prev && prev.id === item.id ? { ...prev, starred: nextStarred } : prev));
    starAsset(item.id, nextStarred).catch((err) => {
      console.error('Failed to toggle star:', err);
      showToast('ติดดาวไม่สำเร็จ', 'error');
      setAssetData((prev) => {
        const revertList = (list) => (list || []).map((it) => (it.id === item.id ? { ...it, starred: item.starred } : it));
        return { ...prev, sfx: revertList(prev.sfx), music: revertList(prev.music), effects: revertList(prev.effects) };
      });
      setSelectedAsset((prev) => (prev && prev.id === item.id ? { ...prev, starred: item.starred } : prev));
    });
  }, [showToast]);

  // ── Audio Controller ──
  const playAudio = useCallback((itemOrUrl, explicitName = null, durationSec = null) => {
    let url = '';
    let trackName = '';

    if (typeof itemOrUrl === 'string') {
      url = itemOrUrl;
      trackName = explicitName || itemOrUrl;
    } else if (itemOrUrl && typeof itemOrUrl === 'object') {
      url = itemOrUrl.audio_url || itemOrUrl.url || '';
      if (!url && (itemOrUrl.rel_path || itemOrUrl.path)) {
        const p = String(itemOrUrl.rel_path || itemOrUrl.path).replace(/\\/g, '/');
        url = p.startsWith('/api/media/') ? p : `/api/media/${p}`;
      }
      trackName = explicitName || itemOrUrl.name || url;
    }

    if (!url) {
      console.warn('Cannot play audio: missing URL for', itemOrUrl);
      return;
    }

    if (currentlyPlayingAudio === trackName) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setCurrentlyPlayingAudio(null);
      setAudioProgress(0);
      setAudioCurrentTime(0);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }

    const audio = new Audio(url);
    audio.volume = 1.0; // Clear audible volume for user preview
    audioRef.current = audio;
    setCurrentlyPlayingAudio(trackName);
    setAudioDuration(durationSec || 0);

    audio.ontimeupdate = () => {
      if (audio.duration) {
        setAudioProgress((audio.currentTime / audio.duration) * 100);
        setAudioCurrentTime(audio.currentTime);
        setAudioDuration(audio.duration);
      }
    };

    audio.onended = () => {
      setCurrentlyPlayingAudio(null);
      setAudioProgress(0);
      setAudioCurrentTime(0);
    };

    audio.play().catch(e => {
      console.error('Audio play error on url:', url, e);
      setCurrentlyPlayingAudio(null);
    });
  }, [currentlyPlayingAudio]);

  // Stop audio when switching tabs
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setCurrentlyPlayingAudio(null);
      setAudioProgress(0);
    }
    setSelectedAsset(null);
  }, [activeAssetTab]);

  // ── Upload Asset ──
  const handleAssetUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingAsset(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('asset_type', activeAssetTab === 'system' ? 'sfx' : activeAssetTab);

    try {
      const res = await uploadAsset(formData);
      showToast(res.message || 'เพิ่มทรัพยากรสำเร็จ');
      fetchAssets();
    } catch (err) {
      showToast('อัปโหลดล้มเหลว: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setUploadingAsset(false);
      e.target.value = '';
    }
  };

  // ── Delete Asset ──
  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteFile(deleteTarget.path);
      showToast(`ลบไฟล์ ${deleteTarget.name} เรียบร้อยแล้ว`);
      if (selectedAsset?.name === deleteTarget.name) {
        setSelectedAsset(null);
      }
      setDeleteTarget(null);
      fetchAssets();
    } catch (err) {
      showToast('ลบไฟล์ไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setDeleting(false);
    }
  };

  // ── Search & Filter Logic ──
  const filterList = useCallback((list) => {
    if (!debouncedSearch) return list || [];
    const q = debouncedSearch.toLowerCase().trim();
    return (list || []).filter(item =>
      (item.name && item.name.toLowerCase().includes(q)) ||
      (item.label && item.label.toLowerCase().includes(q)) ||
      (item.label_th && item.label_th.toLowerCase().includes(q)) ||
      (item.category && item.category.toLowerCase().includes(q)) ||
      (item.family && item.family.toLowerCase().includes(q))
    );
  }, [debouncedSearch]);

  // SFX Sub-category counts & list
  const sfxCategoryList = useMemo(() => {
    const rawList = assetData.sfx || [];
    const counts = {};
    rawList.forEach((item) => {
      const cat = item.category || 'misc';
      counts[cat] = (counts[cat] || 0) + 1;
    });
    const starredCount = rawList.filter((item) => item.starred).length;
    return [
      { id: 'all', label: 'ทั้งหมด', count: rawList.length },
      { id: 'starred', label: '⭐ ติดดาว', count: starredCount },
      { id: 'thai', label: 'เสียงไทย / ตลก', count: counts['thai'] || 0 },
      { id: 'game', label: 'เกม', count: counts['game'] || 0 },
      { id: 'meme', label: 'มีม', count: counts['meme'] || 0 },
      { id: 'reaction', label: 'รีแอ็กชัน', count: counts['reaction'] || 0 },
      { id: 'notification', label: 'แจ้งเตือน / UI', count: counts['notification'] || 0 },
      { id: 'music', label: 'ท่อนเพลง', count: counts['music'] || 0 },
      { id: 'horror', label: 'สยองขวัญ', count: counts['horror'] || 0 },
      { id: 'anime', label: 'อนิเมะ', count: counts['anime'] || 0 },
      { id: 'transition', label: 'เปลี่ยนฉาก / Whoosh', count: counts['transition'] || 0 },
      { id: 'other', label: 'อื่นๆ', count: counts['other'] || 0 },
      { id: 'misc', label: 'เสียงระบบเดิม', count: counts['misc'] || 0 },
    ].filter(c => c.id === 'all' || c.count > 0);
  }, [assetData.sfx]);

  const filteredSFX = useMemo(() => {
    let list = assetData.sfx || [];
    if (sfxCategory === 'starred') {
      list = list.filter((item) => item.starred);
    } else if (sfxCategory !== 'all') {
      list = list.filter((item) => (item.category || 'misc') === sfxCategory);
    }
    return filterList(list);
  }, [assetData.sfx, sfxCategory, filterList]);
  const filteredMusic = useMemo(() => filterList(assetData.music), [assetData.music, filterList]);
  const filteredFonts = useMemo(() => filterList(assetData.fonts), [assetData.fonts, filterList]);
  const filteredStickers = useMemo(() => filterList(assetData.stickers), [assetData.stickers, filterList]);
  const filteredLuts = useMemo(() => filterList(assetData.luts), [assetData.luts, filterList]);

  // Effects Sub-category counts & list (mirrors sfxCategoryList)
  const effectsCategoryList = useMemo(() => {
    const rawList = assetData.effects || [];
    const counts = {};
    rawList.forEach((item) => {
      const cat = item.category || 'other';
      counts[cat] = (counts[cat] || 0) + 1;
    });
    const starredCount = rawList.filter((item) => item.starred).length;
    return [
      { id: 'all', label: 'ทั้งหมด', count: rawList.length },
      { id: 'starred', label: '⭐ ติดดาว', count: starredCount },
      { id: 'checkmark', label: 'ถูกต้อง/ข้อดี', count: counts['checkmark'] || 0 },
      { id: 'warning', label: 'ข้อเสีย/บั๊ก', count: counts['warning'] || 0 },
      { id: 'notification', label: 'แจ้งเตือน/UI', count: counts['notification'] || 0 },
      { id: 'money', label: 'ราคา/คุ้มราคา', count: counts['money'] || 0 },
      { id: 'rating', label: 'รีวิว/ดาว', count: counts['rating'] || 0 },
      { id: 'arrow', label: 'ชี้/คลิก UI', count: counts['arrow'] || 0 },
      { id: 'celebration', label: 'ปิดคลิป/CTA', count: counts['celebration'] || 0 },
      { id: 'other', label: 'อื่นๆ', count: counts['other'] || 0 },
    ].filter(c => c.id === 'all' || c.count > 0);
  }, [assetData.effects]);
  const [effectsCategory, setEffectsCategory] = useState('all');

  const filteredEffects = useMemo(() => {
    let list = assetData.effects || [];
    if (effectsCategory === 'starred') {
      list = list.filter((item) => item.starred);
    } else if (effectsCategory !== 'all') {
      list = list.filter((item) => (item.category || 'other') === effectsCategory);
    }
    return filterList(list);
  }, [assetData.effects, effectsCategory, filterList]);

  // Current list based on active tab
  const currentItems = useMemo(() => {
    switch (activeAssetTab) {
      case 'sfx': return filteredSFX;
      case 'music': return filteredMusic;
      case 'fonts': return filteredFonts;
      case 'stickers': return filteredStickers;
      case 'luts': return filteredLuts;
      case 'effects': return filteredEffects;
      default: return [];
    }
  }, [activeAssetTab, filteredSFX, filteredMusic, filteredFonts, filteredStickers, filteredLuts, filteredEffects]);

  // Stock asset libraries (SFX/music/fonts/stickers/LUTs/effects) can each
  // grow into the hundreds. Only one tab's list is ever on screen at a time,
  // so one shared window works for all of them -- reset to page 1 whenever
  // the tab or search changes.
  const [assetPage, setAssetPage] = useState(1);
  const [assetPageSize, setAssetPageSize] = useState(20);
  useEffect(() => {
    setAssetPage(1);
  }, [activeAssetTab, debouncedSearch]);
  const visibleCurrentItems = useMemo(
    () => currentItems.slice((assetPage - 1) * assetPageSize, assetPage * assetPageSize),
    [currentItems, assetPage, assetPageSize]
  );
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(currentItems.length / assetPageSize));
    setAssetPage((page) => Math.min(page, totalPages));
  }, [currentItems.length, assetPageSize]);

  const renderAssetPagination = () => (
    <PaginationControls
      page={assetPage}
      pageSize={assetPageSize}
      totalItems={currentItems.length}
      onPageChange={setAssetPage}
      onPageSizeChange={(size) => {
        setAssetPageSize(size);
        setAssetPage(1);
      }}
      itemLabel="ไฟล์"
      disabled={loading}
    />
  );

  // Auto-select first item if none selected in split mode
  useEffect(() => {
    if (viewMode === 'split' && currentItems.length > 0 && !selectedAsset) {
      setSelectedAsset(currentItems[0]);
    }
  }, [viewMode, currentItems, selectedAsset]);

  // ── Category Definitions ──
  const assetCategories = useMemo(() => [
    {
      id: 'sfx',
      label: 'เสียง SFX',
      sublabel: 'Whoosh, Pop, Ding',
      icon: Volume2,
      count: assetData.counts?.sfx || assetData.sfx?.length || 0,
      color: 'text-[#25F4EE]',
      borderColor: 'border-[#25F4EE]/40',
      activeBg: 'bg-[#25F4EE]/10'
    },
    {
      id: 'music',
      label: 'เพลง BGM',
      sublabel: 'TikTok Trends & Lo-Fi',
      icon: Music,
      count: assetData.counts?.music || assetData.music?.length || 0,
      color: 'text-[#FE2C55]',
      borderColor: 'border-[#FE2C55]/40',
      activeBg: 'bg-[#FE2C55]/10'
    },
    {
      id: 'fonts',
      label: 'ฟอนต์วิดีโอ',
      sublabel: 'Kanit, Prompt, Bai Jam',
      icon: Type,
      count: assetData.counts?.fonts || assetData.fonts?.length || 0,
      color: 'text-purple-400',
      borderColor: 'border-purple-500/40',
      activeBg: 'bg-purple-500/10'
    },
    {
      id: 'stickers',
      label: 'ป้าย 3D Badges',
      sublabel: 'Universal 6 Badges',
      icon: ImageIcon,
      count: assetData.counts?.stickers || assetData.stickers?.length || 0,
      color: 'text-amber-400',
      borderColor: 'border-amber-500/40',
      activeBg: 'bg-amber-500/10'
    },
    {
      id: 'luts',
      label: 'โทนสี LUTs',
      sublabel: '3D Color Cube .cube',
      icon: Film,
      count: assetData.counts?.luts || assetData.luts?.length || 0,
      color: 'text-emerald-400',
      borderColor: 'border-emerald-500/40',
      activeBg: 'bg-emerald-500/10'
    },
    {
      id: 'effects',
      label: 'วิดีโอเอฟเฟกต์',
      sublabel: 'Checkmark, Arrow, CTA',
      icon: Sparkles,
      count: assetData.counts?.effects || assetData.effects?.length || 0,
      color: 'text-fuchsia-400',
      borderColor: 'border-fuchsia-500/40',
      activeBg: 'bg-fuchsia-500/10'
    },
    {
      id: 'system',
      label: 'ไดเรกทอรีระบบ',
      sublabel: 'โฟลเดอร์ & CapCut Drafts',
      icon: Folder,
      count: 6,
      color: 'text-cyan-400',
      borderColor: 'border-cyan-500/40',
      activeBg: 'bg-cyan-500/10'
    },
  ], [assetData]);

  // System Core Directories
  const systemDirectories = useMemo(() => [
    {
      id: 'inbox',
      name: '00_Inbox',
      desc: 'ไฟล์ดิบและวิดีโอที่ sync จากมือถือผ่าน Wi-Fi/QR',
      path: status?.directories?.inbox || '00_Inbox',
      icon: Smartphone,
      color: 'text-[#25F4EE]'
    },
    {
      id: 'raw',
      name: '01_Raw',
      desc: 'วัตถุดิบต้นฉบับแยกตามโฟลเดอร์สินค้า YYYYMMDD',
      path: status?.directories?.raw || '01_Raw',
      icon: Folder,
      color: 'text-blue-400'
    },
    {
      id: 'assets',
      name: '02_Assets',
      desc: 'มีเดียส่วนกลาง (SFX, เพลง BGM, ฟอนต์, สติกเกอร์, LUTs)',
      path: status?.directories?.assets || '02_Assets',
      icon: Layers,
      color: 'text-purple-400'
    },
    {
      id: 'projects',
      name: '03_Projects',
      desc: 'ไฟล์โปรเจกต์ สคริปต์ brief และดราฟต์งานอัตโนมัติ',
      path: status?.directories?.projects || '03_Projects',
      icon: Folder,
      color: 'text-amber-400'
    },
    {
      id: 'exports',
      name: '04_Exports',
      desc: 'วิดีโอ 9:16 ที่ตัดต่อเสร็จแล้ว (Ready_to_post / Posted)',
      path: status?.directories?.exports || '04_Exports',
      icon: CheckCircle2,
      color: 'text-emerald-400'
    },
    {
      id: 'capcut',
      name: 'CapCut Drafts',
      desc: 'โฟลเดอร์โปรเจกต์ของ CapCut PC (draft_content.json)',
      path: status?.directories?.capcut || 'CapCut Drafts',
      icon: HardDrive,
      color: 'text-pink-400'
    },
  ], [status]);

  // Format seconds to mm:ss
  const formatSec = (sec) => {
    if (!sec || isNaN(sec)) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="space-y-4 sm:space-y-5 animate-fadeIn pb-24 md:pb-12 max-w-[2200px] mx-auto">
      {/* ── 1. Command Bar Header (shared PageHeader) ── */}
      <PageHeader
        icon={Layers}
        eyebrow="Media Assets & System Hub"
        title="คลังทรัพยากรสื่อ & ระบบตัดต่อ"
        actions={
          <>
            {/* View Mode Toggle (Desktop) */}
            <div className="hidden lg:flex items-center p-0.5 rounded-xl bg-black/40 border border-white/[0.08]">
              <button
                type="button"
                onClick={() => setViewMode('split')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === 'split'
                    ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="โหมดสตูดิโอผ่าครึ่ง (Split Workbench)"
              >
                <Columns className="w-3.5 h-3.5" />
                <span>Studio Split</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('grid')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  viewMode === 'grid'
                    ? 'bg-[#25F4EE]/15 text-[#25F4EE] border border-[#25F4EE]/30 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="โหมดแกลเลอรีเต็มจอ (Full Grid)"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span>Grid Gallery</span>
              </button>
            </div>

            {/* Upload Button */}
            {activeAssetTab !== 'system' && (
              <label
                className={`relative flex items-center justify-center gap-2 flex-1 sm:flex-initial px-3.5 sm:px-4 py-2 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold shadow-lg shadow-[#FE2C55]/20 transition-all cursor-pointer active:scale-95 ${
                  uploadingAsset ? 'opacity-50 pointer-events-none' : ''
                }`}
              >
                <input
                  ref={fileUploadRef}
                  type="file"
                  accept="video/*,audio/*,image/*,image/heic,image/heif,.heic,.HEIC,.heif,.HEIF,.mov,.MOV,.mp4,.MP4,.ttf,.otf,.cube"
                  onChange={handleAssetUpload}
                  disabled={uploadingAsset}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                />
                <Upload className="w-4 h-4 text-white pointer-events-none flex-shrink-0" />
                <span className="pointer-events-none whitespace-nowrap">{uploadingAsset ? 'กำลังเพิ่มไฟล์...' : 'เพิ่มทรัพยากรใหม่'}</span>
              </label>
            )}

            {/* Open Folder Button */}
            <button
              type="button"
              onClick={() => handleOpen(activeAssetTab === 'system' ? 'root' : 'assets')}
              className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 text-xs font-bold border border-white/[0.08] transition-all cursor-pointer active:scale-95 flex-shrink-0"
              title="เปิดโฟลเดอร์ Assets"
            >
              <Folder className="w-3.5 h-3.5 text-[#25F4EE]" />
              <span className="hidden xs:inline">เปิดโฟลเดอร์</span>
            </button>

            {/* Refresh Button */}
            <button
              type="button"
              onClick={fetchAssets}
              className="p-2 min-w-[36px] min-h-[36px] rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white border border-white/[0.08] transition-colors cursor-pointer flex items-center justify-center active:scale-95 flex-shrink-0"
              title="รีเฟรชข้อมูล"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#25F4EE]' : ''}`} />
            </button>
          </>
        }
        secondRow={
          <>
            {/* Description */}
            <p className="text-xs text-slate-400 leading-relaxed break-words pt-2 border-t border-white/[0.06]">
              ศูนย์รวมเสียงเอฟเฟกต์ SFX • เพลง BGM • ฟอนต์สไตล์ TikTok • ป้าย 3D Badges • โทนสี LUTs และโฟลเดอร์ CapCut
            </p>

            {/* Responsive Category Nav Pills (iPhone 15 PM Touch Snap + Desktop Grid) */}
            <div className="w-full max-w-full overflow-x-auto no-scrollbar snap-x flex gap-2 pb-1 sm:grid sm:grid-cols-3 lg:grid-cols-6 sm:overflow-visible pt-2 border-t border-white/[0.06]">
              {assetCategories.map((cat) => {
                const Icon = cat.icon;
                const isActive = activeAssetTab === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setActiveAssetTab(cat.id)}
                    className={`flex-shrink-0 snap-start min-w-[150px] sm:min-w-0 p-3 sm:p-3.5 rounded-2xl border text-left transition-all relative cursor-pointer active:scale-95 ${
                      isActive
                        ? `${cat.activeBg} ${cat.borderColor} shadow-lg ring-1 ${cat.borderColor}`
                        : 'bg-[#080B11]/80 border-white/[0.06] hover:border-white/[0.15] hover:bg-white/[0.02]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1.5">
                      <div className="flex items-center gap-2 min-w-0">
                        <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? cat.color : 'text-slate-400'}`} />
                        <span className={`text-xs font-bold truncate ${isActive ? 'text-white' : 'text-slate-300'}`}>
                          {cat.label}
                        </span>
                      </div>
                      <span className={`text-[11px] px-2 py-0.5 rounded-full font-mono font-bold flex-shrink-0 ${
                        isActive
                          ? 'bg-white text-slate-950 shadow-sm'
                          : 'bg-white/[0.06] text-slate-400 border border-white/[0.08]'
                      }`}>
                        {cat.count}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 truncate mt-1">
                      {cat.sublabel}
                    </div>
                    <div className={`h-1 w-full mt-2 rounded-full transition-all ${
                      isActive ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE]' : 'bg-white/[0.04]'
                    }`} />
                  </button>
                );
              })}
            </div>

            {/* Search Bar for Assets */}
            {activeAssetTab !== 'system' && (
              <div className="space-y-3 pt-2 border-t border-white/[0.06]">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={`ค้นหาในหมวด ${activeAssetTab.toUpperCase()} (เช่น whoosh, upbeat, bold, sale, cube)...`}
                    className="w-full pl-11 pr-4 py-2.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-xs sm:text-sm focus:outline-none focus:border-[#25F4EE]/50 transition-colors shadow-inner"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Sub-category Quick Filter Pills for SFX */}
                {activeAssetTab === 'sfx' && sfxCategoryList.length > 1 && (
                  <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-0.5 pt-0.5">
                    {sfxCategoryList.map((sc) => {
                      const isActive = sfxCategory === sc.id;
                      return (
                        <button
                          key={sc.id}
                          type="button"
                          onClick={() => setSfxCategory(sc.id)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer flex-shrink-0 ${
                            isActive
                              ? 'bg-[#25F4EE] text-slate-950 shadow-md shadow-[#25F4EE]/20'
                              : 'bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 border border-white/[0.08]'
                          }`}
                        >
                          <span>{sc.label}</span>
                          <span
                            className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                              isActive ? 'bg-slate-950/20 text-slate-950' : 'bg-white/[0.08] text-slate-400'
                            }`}
                          >
                            {sc.count}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Sub-category Quick Filter Pills for Effects */}
                {activeAssetTab === 'effects' && effectsCategoryList.length > 1 && (
                  <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-0.5 pt-0.5">
                    {effectsCategoryList.map((sc) => {
                      const isActive = effectsCategory === sc.id;
                      return (
                        <button
                          key={sc.id}
                          type="button"
                          onClick={() => setEffectsCategory(sc.id)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer flex-shrink-0 ${
                            isActive
                              ? 'bg-fuchsia-400 text-slate-950 shadow-md shadow-fuchsia-400/20'
                              : 'bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 border border-white/[0.08]'
                          }`}
                        >
                          <span>{sc.label}</span>
                          <span
                            className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                              isActive ? 'bg-slate-950/20 text-slate-950' : 'bg-white/[0.08] text-slate-400'
                            }`}
                          >
                            {sc.count}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </>
        }
      />

      {/* ── 4. MAIN CONTENT AREA (Split Studio Workbench vs Classic Grid) ── */}

      {/* ── SYSTEM STORAGE TAB (Full Width Grid) ── */}
      {activeAssetTab === 'system' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5 animate-fadeIn">
          {/* Storage Directory Explorer (7 cols) */}
          <div className="lg:col-span-7 glass-panel rounded-2xl p-4 sm:p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center gap-2">
                <Folder className="w-4 h-4 text-[#25F4EE]" />
                <h3 className="text-sm sm:text-base font-bold text-white">
                  ไดเรกทอรีจัดเก็บไฟล์ในเครื่องคอมพิวเตอร์
                </h3>
              </div>
              <button
                type="button"
                onClick={() => handleOpen('root')}
                className="px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-white text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
              >
                <Folder className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>เปิดโฟลเดอร์โปรเจกต์</span>
              </button>
            </div>

            <div className="space-y-2.5 text-xs">
              {systemDirectories.map((dir) => {
                const DirIcon = dir.icon;
                return (
                  <div
                    key={dir.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-xl bg-black/40 border border-white/[0.06] hover:border-white/[0.15] transition-all gap-3 group"
                  >
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <DirIcon className={`w-4 h-4 ${dir.color} flex-shrink-0`} />
                        <span className="font-bold text-white text-xs sm:text-sm">{dir.name}</span>
                      </div>
                      <p className="text-[11px] text-slate-400">{dir.desc}</p>
                      <p className="text-[10px] text-slate-500 font-mono truncate">{dir.path}</p>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center flex-shrink-0">
                      <button
                        type="button"
                        onClick={() => handleCopy(dir.path)}
                        className="p-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-white transition-colors cursor-pointer"
                        title="คัดลอกที่อยู่โฟลเดอร์"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOpen(dir.id)}
                        className="px-3 py-1.5 rounded-lg bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/30 text-[#25F4EE] hover:text-white text-xs font-bold transition-all cursor-pointer active:scale-95"
                      >
                        เปิดโฟลเดอร์
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Engine Health & Standards (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Audio Mix Standards Card (Rule 5) */}
            <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-xl space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-white/[0.08]">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">
                  มาตรฐานระดับเสียงวิดีโอ (Audio Mix Standard)
                </h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                ตามกฎเหล็กข้อ 5 ของโปรเจกต์ ระดับเสียงทุกคลิปจะถูกควบคุมอัตโนมัติให้ได้สัดส่วนที่ชัดเจนที่สุด:
              </p>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-[10px] text-slate-400 block">เสียงพากย์หลัก (Voice)</span>
                  <span className="text-sm font-bold font-mono text-[#25F4EE] mt-0.5 block">100% (1.0)</span>
                  <span className="text-[10px] text-slate-500">Edge-TTS +15%</span>
                </div>
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-[10px] text-slate-400 block">เสียงเอฟเฟกต์ (SFX)</span>
                  <span className="text-sm font-bold font-mono text-amber-300 mt-0.5 block">28% (0.28)</span>
                  <span className="text-[10px] text-slate-500">Whoosh / Ding</span>
                </div>
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-[10px] text-slate-400 block">เพลงประกอบ (BGM)</span>
                  <span className="text-sm font-bold font-mono text-[#FE2C55] mt-0.5 block">12% (0.12)</span>
                  <span className="text-[10px] text-slate-500">ไม่กลบเสียงพูด</span>
                </div>
              </div>
            </div>

            {/* Video Engine & Subprocess Card */}
            <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-xl space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-white/[0.08]">
                <Cpu className="w-4 h-4 text-[#25F4EE]" />
                <h3 className="text-sm font-bold text-white">
                  สถานะ Video Engine & Subprocess
                </h3>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-slate-300 font-bold flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    FFmpeg Video Engine
                  </span>
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                    CPU Encode (libx264)
                  </span>
                </div>
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-slate-300 font-bold flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    TTS Engine
                  </span>
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30">
                    Edge-TTS (Premwadee/Niwat)
                  </span>
                </div>
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-slate-300 font-bold flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Subtitle Engine
                  </span>
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30">
                    pythainlp + ASS libass
                  </span>
                </div>
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                  <span className="text-slate-300 font-bold flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Background Removal
                  </span>
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                    Rembg (U2Net)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : viewMode === 'split' ? (
        /* ── STUDIO SPLIT WORKBENCH (Desktop: 2 columns, Mobile: Top list + Bottom Inspector) ── */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5 items-start">
          {/* Left Column: Asset Catalog List (lg:col-span-5) */}
          <div className="lg:col-span-5 space-y-2.5 glass-panel rounded-2xl p-3 sm:p-4 shadow-xl">
            <div className="flex items-center justify-between px-1 pb-2 border-b border-white/[0.08] text-xs font-bold text-slate-300">
              <span>รายการในหมวด ({currentItems.length} ไฟล์)</span>
              <span className="text-[11px] text-slate-400">แตะเพื่อดูรายละเอียด</span>
            </div>

            {currentItems.length === 0 ? (
              <div className="text-center py-12 text-slate-500 space-y-2">
                <AlertTriangle className="w-8 h-8 mx-auto text-slate-600" />
                <p className="text-xs">ไม่พบไฟล์ในหมวดนี้</p>
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    className="text-xs text-[#25F4EE] underline cursor-pointer"
                  >
                    ล้างการค้นหา
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-2 max-h-[650px] overflow-y-auto pr-1 no-scrollbar">
                {visibleCurrentItems.map((item, idx) => {
                  const isSelected = selectedAsset?.name === item.name;
                  const isPlaying = currentlyPlayingAudio === item.name;

                  return (
                    <div
                      key={item.name || idx}
                      onClick={() => setSelectedAsset(item)}
                      className={`p-2.5 sm:p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-2.5 group ${
                        isSelected
                          ? 'border-[#25F4EE] bg-[#25F4EE]/10 shadow-md ring-1 ring-[#25F4EE]/30'
                          : 'glass-tile hover:border-white/[0.25]'
                      }`}
                    >
                      {/* Left thumbnail / icon / audio play */}
                      <div className="flex items-center gap-2.5 min-w-0">
                        {activeAssetTab === 'sfx' || activeAssetTab === 'music' ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              playAudio(item, item.name);
                            }}
                            className={`w-11 h-11 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center transition-all flex-shrink-0 cursor-pointer ${
                              isPlaying
                                ? 'bg-[#25F4EE] text-slate-950 scale-95 shadow-md shadow-[#25F4EE]/30'
                                : 'bg-white/[0.06] text-slate-300 hover:bg-[#25F4EE]/20 hover:text-[#25F4EE]'
                            }`}
                          >
                            {isPlaying ? (
                              <Pause className="w-4 h-4 fill-current" />
                            ) : (
                              <Play className="w-4 h-4 fill-current ml-0.5" />
                            )}
                          </button>
                        ) : activeAssetTab === 'stickers' ? (
                          <div className="w-10 h-10 rounded-lg bg-black/60 border border-white/[0.08] flex items-center justify-center p-1 flex-shrink-0">
                            <img
                              src={item.img_url || item.url || (item.rel_path ? `/api/media/${item.rel_path}` : '')}
                              alt=""
                              className="max-w-full max-h-full object-contain"
                            />
                          </div>
                        ) : activeAssetTab === 'fonts' ? (
                          <div className="w-9 h-9 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-300 flex items-center justify-center font-bold text-xs flex-shrink-0">
                            Aa
                          </div>
                        ) : activeAssetTab === 'effects' ? (
                          <div className="w-10 h-10 rounded-lg bg-white border border-white/[0.08] flex items-center justify-center p-0.5 flex-shrink-0 overflow-hidden">
                            <video
                              src={item.video_url || (item.rel_path ? `/api/media/${item.rel_path}` : '')}
                              className="max-w-full max-h-full object-contain"
                              style={{ mixBlendMode: 'multiply' }}
                              autoPlay
                              loop
                              muted
                              playsInline
                            />
                          </div>
                        ) : (
                          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center justify-center flex-shrink-0">
                            <Film className="w-4 h-4" />
                          </div>
                        )}

                        {/* Title & metadata */}
                        <div className="min-w-0">
                          <div className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                            {item.label || item.name}
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono truncate mt-0.5">
                            {item.category || item.family || item.size_mb ? `${item.size_mb} MB` : item.name}
                          </div>
                        </div>
                      </div>

                      {/* Right actions */}
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {isPlaying && (
                          <span className="flex h-2 w-2 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#25F4EE] opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#25F4EE]"></span>
                          </span>
                        )}
                        {(activeAssetTab === 'sfx' || activeAssetTab === 'music' || activeAssetTab === 'effects') && (
                          <button
                            type="button"
                            onClick={(e) => handleToggleStar(item, e)}
                            className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                              item.starred
                                ? 'text-amber-400 hover:text-amber-300'
                                : 'text-slate-600 hover:text-amber-400 opacity-0 group-hover:opacity-100'
                            }`}
                            title={item.starred ? 'เอาดาวออก' : 'ติดดาว (ใช้ในตัดต่อ)'}
                          >
                            <Star className={`w-4 h-4 ${item.starred ? 'fill-current' : ''}`} />
                          </button>
                        )}
                        <ChevronRight className={`w-4 h-4 transition-transform ${isSelected ? 'text-[#25F4EE] translate-x-0.5' : 'text-slate-600'}`} />
                      </div>
                    </div>
                  );
                })}
                {renderAssetPagination()}
              </div>
            )}
          </div>

          {/* Right Column: Interactive Workbench Detail Inspector (lg:col-span-7) */}
          <div className="lg:col-span-7 sticky top-4">
            {selectedAsset ? (
              <div className="glass-panel rounded-2xl p-4 sm:p-5 shadow-xl space-y-4 animate-fadeIn">
                {/* Inspector Header */}
                <div className="flex items-start justify-between gap-3 pb-3 border-b border-white/[0.08]">
                  <div className="min-w-0">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/[0.08] text-[#25F4EE] border border-white/[0.1] font-mono">
                      {activeAssetTab.toUpperCase()} INSPECTOR
                    </span>
                    <h3 className="text-base sm:text-lg font-bold text-white truncate mt-1">
                      {selectedAsset.label || selectedAsset.name}
                    </h3>
                    <p className="text-xs text-slate-400 font-mono truncate mt-0.5">
                      {selectedAsset.path || selectedAsset.url || selectedAsset.name}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {(activeAssetTab === 'sfx' || activeAssetTab === 'music' || activeAssetTab === 'effects') && (
                      <button
                        type="button"
                        onClick={(e) => handleToggleStar(selectedAsset, e)}
                        className={`p-2 rounded-xl transition-colors cursor-pointer ${
                          selectedAsset.starred
                            ? 'text-amber-400 bg-amber-500/10 hover:bg-amber-500/20'
                            : 'text-slate-400 hover:text-amber-400 hover:bg-amber-500/10'
                        }`}
                        title={selectedAsset.starred ? 'เอาดาวออก' : 'ติดดาว (ใช้ในตัดต่อ)'}
                      >
                        <Star className={`w-4 h-4 ${selectedAsset.starred ? 'fill-current' : ''}`} />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(selectedAsset)}
                      className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                      title="ลบไฟล์ทรัพยากรนี้"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* ── WORKBENCH VIEW: AUDIO (SFX / MUSIC) ── */}
                {(activeAssetTab === 'sfx' || activeAssetTab === 'music') && (
                  <div className="space-y-4">
                    {/* Simulated Waveform / Audio Player Card */}
                    <div className="p-4 sm:p-5 rounded-2xl bg-black/60 border border-white/[0.08] text-center space-y-4 relative overflow-hidden">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                        <span>{formatSec(audioCurrentTime)}</span>
                        <span className="text-[11px] text-[#25F4EE] font-bold">
                          {activeAssetTab === 'sfx' ? 'มาตรฐาน SFX: 28%' : 'มาตรฐาน BGM: 12%'}
                        </span>
                        <span>{formatSec(audioDuration)}</span>
                      </div>

                      {/* Animated Audio Wave Bars */}
                      <div className="flex items-center justify-center gap-1 sm:gap-1.5 h-16 py-2">
                        {Array.from({ length: 28 }).map((_, i) => {
                          const isPlayingThis = currentlyPlayingAudio === selectedAsset.name;
                          const heightPct = isPlayingThis
                            ? Math.max(15, Math.sin(i * 0.5 + audioCurrentTime * 5) * 85 + 15)
                            : (Math.sin(i * 0.4) * 30 + 35);
                          return (
                            <div
                              key={i}
                              style={{ height: `${heightPct}%` }}
                              className={`w-1 sm:w-1.5 rounded-full transition-all duration-75 ${
                                isPlayingThis
                                  ? 'bg-gradient-to-t from-[#FE2C55] to-[#25F4EE]'
                                  : 'bg-white/[0.12]'
                              }`}
                            />
                          );
                        })}
                      </div>

                      {/* Audio Progress Bar */}
                      <div className="w-full bg-white/[0.08] h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] h-full transition-all duration-100"
                          style={{ width: `${audioProgress}%` }}
                        />
                      </div>

                      {/* Player Controls */}
                      <div className="flex items-center justify-center gap-3 pt-1">
                        <button
                          type="button"
                          onClick={() => playAudio(selectedAsset, selectedAsset.name)}
                          className="min-h-[44px] px-6 py-2.5 rounded-2xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-slate-950 font-bold text-xs flex items-center gap-2 shadow-lg shadow-[#25F4EE]/20 hover:brightness-110 active:scale-95 transition-all cursor-pointer"
                        >
                          {currentlyPlayingAudio === selectedAsset.name ? (
                            <>
                              <Pause className="w-4 h-4 fill-current" />
                              <span>หยุดเล่น</span>
                            </>
                          ) : (
                            <>
                              <Play className="w-4 h-4 fill-current ml-0.5" />
                              <span>ทดลองฟังเสียง</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Audio Technical Details Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">หมวดหมู่</span>
                        <span className="text-white font-bold truncate block mt-0.5">
                          {selectedAsset.category || (activeAssetTab === 'sfx' ? 'Sound Effect' : 'Background Music')}
                        </span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">ขนาดไฟล์</span>
                        <span className="text-cyan-300 font-mono font-bold block mt-0.5">
                          {selectedAsset.size || (selectedAsset.size_mb ? `${selectedAsset.size_mb} MB` : 'Audio Track')}
                        </span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">อัตราเสียงมาตรฐาน</span>
                        <span className="text-amber-300 font-mono font-bold block mt-0.5">
                          {activeAssetTab === 'sfx' ? '0.28 (28%)' : '0.12 (12%)'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── WORKBENCH VIEW: FONTS PLAYGROUND ── */}
                {activeAssetTab === 'fonts' && (
                  <div className="space-y-4">
                    {/* Live Font Tester Box */}
                    <div className="p-4 rounded-2xl bg-black/50 border border-white/[0.08] space-y-3">
                      <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                        <span className="">ทดสอบพิมพ์ข้อความสด</span>
                        <span className="text-slate-500 text-[11px]">ขนาด: {fontSizePreview}px</span>
                      </div>
                      <input
                        type="text"
                        value={customFontText}
                        onChange={(e) => setCustomFontText(e.target.value)}
                        placeholder="พิมพ์ข้อความทดสอบฟอนต์..."
                        className="w-full p-2.5 rounded-xl bg-black/60 border border-white/[0.12] text-white text-xs sm:text-sm focus:outline-none focus:border-[#25F4EE]"
                      />

                      {/* Font Size Slider */}
                      <div className="flex items-center gap-3 pt-1">
                        <span className="text-[10px] text-slate-500 font-mono">18px</span>
                        <input
                          type="range"
                          min="18"
                          max="56"
                          value={fontSizePreview}
                          onChange={(e) => setFontSizePreview(Number(e.target.value))}
                          className="flex-1 accent-[#25F4EE] h-1.5 bg-white/[0.1] rounded-lg cursor-pointer"
                        />
                        <span className="text-[10px] text-slate-500 font-mono">56px</span>
                      </div>
                    </div>

                    {/* Live Rendered Canvas / Subtitle Display */}
                    <div className="p-6 rounded-2xl bg-gradient-to-b from-black to-slate-950 border border-white/[0.1] text-center shadow-inner min-h-[140px] flex flex-col items-center justify-center">
                      <div
                        style={{
                          fontSize: `${fontSizePreview}px`,
                          fontFamily: selectedAsset.family || selectedAsset.name,
                          textShadow: '0 2px 10px rgba(0,0,0,0.8), 0 0 20px rgba(37,244,238,0.3)'
                        }}
                        className="font-bold text-[#FFE600] tracking-wide break-words max-w-full leading-tight"
                      >
                        {customFontText || 'ทดสอบข้อความซับไตเติล'}
                      </div>
                      <span className="text-[10px] text-slate-500 mt-3 font-mono">
                        {selectedAsset.family || selectedAsset.name} • สไตล์ซับไตเติล TikTok (Micro-Burst)
                      </span>
                    </div>

                    {/* Font Specs */}
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">Font Family</span>
                        <span className="text-white font-mono font-bold block mt-0.5">{selectedAsset.family || selectedAsset.name}</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">ฟอร์แมตไฟล์</span>
                        <span className="text-[#25F4EE] font-mono font-bold block mt-0.5">TrueType / OpenType (.ttf/.otf)</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── WORKBENCH VIEW: 3D BADGES & STICKERS ── */}
                {activeAssetTab === 'stickers' && (
                  <div className="space-y-4">
                    {/* Background Toggle (Checkerboard vs Dark) */}
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">ตรวจสอบพื้นหลังโปร่งใส (Alpha Transparency)</span>
                      <button
                        type="button"
                        onClick={() => setCheckerboardBg(!checkerboardBg)}
                        className="px-2.5 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-xs font-bold text-slate-300 transition-colors cursor-pointer"
                      >
                        {checkerboardBg ? 'ดูบนพื้นหลังทึบ' : 'ดูบนตารางโปร่งใส'}
                      </button>
                    </div>

                    {/* Sticker Display Area */}
                    <div
                      className={`w-full h-56 rounded-2xl border border-white/[0.1] flex items-center justify-center p-6 shadow-inner relative ${
                        checkerboardBg
                          ? 'bg-[linear-gradient(45deg,#161B26_25%,transparent_25%),linear-gradient(-45deg,#161B26_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#161B26_75%),linear-gradient(-45deg,transparent_75%,#161B26_75%)] bg-[size:20px_20px] bg-[#0A0D14]'
                          : 'bg-black'
                      }`}
                    >
                      <img
                        src={selectedAsset.img_url || selectedAsset.url || (selectedAsset.rel_path ? `/api/media/${selectedAsset.rel_path}` : '')}
                        alt={selectedAsset.name}
                        className="max-w-full max-h-full object-contain drop-shadow-2xl transition-transform hover:scale-105"
                      />
                    </div>

                    {/* Rule 4 Compliance Banner */}
                    <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200/90 leading-relaxed">
                      <span className="font-bold block text-amber-300 mb-0.5">
                        มาตรฐานป้าย 3D Universal Badges (กฎเหล็กข้อ 4 & 6)
                      </span>
                      ป้ายสติกเกอร์ต้องเป็นป้ายอเนกประสงค์ (PROS, CONS, WARNING, PRO TIP, SCORE, VERDICT) ขอบขาว Die-cut ห้ามระบุชื่อสินค้าเฉพาะเจาะจง เพื่อให้ใช้ซ้ำได้กับทุกคลิป
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">ชื่อไฟล์</span>
                        <span className="text-white font-mono font-bold block truncate mt-0.5">{selectedAsset.name}</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">ชนิดไฟล์</span>
                        <span className="text-emerald-300  block mt-0.5">PNG โปร่งใส (Transparent)</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── WORKBENCH VIEW: LUTS COLOR PRESETS ── */}
                {activeAssetTab === 'luts' && (
                  <div className="space-y-4">
                    {/* Color Swatch Card */}
                    <div className="p-6 rounded-2xl bg-gradient-to-r from-amber-600 via-rose-600 to-indigo-700 border border-white/[0.1] shadow-2xl text-center space-y-2">
                      <Palette className="w-8 h-8 mx-auto text-white drop-shadow" />
                      <h4 className="text-lg font-bold text-white drop-shadow">
                        {selectedAsset.name.replace('.cube', '')}
                      </h4>
                      <p className="text-xs text-white/80 font-mono">
                        3D Color Lookup Table (.cube)
                      </p>
                    </div>

                    <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-300 space-y-1.5 leading-relaxed">
                      <span className="font-bold text-[#25F4EE] block">การใช้งานในขั้นตอนตัดต่อ:</span>
                      <p>
                        LUTs จะถูกโหลดผ่าน FFmpeg `lut3d` filter ในระหว่างกระบวนการเรนเดอร์ สามารถเลือกใช้เพื่อยกระดับโทนสีให้คลิปดูพรีเมียม สไตล์ภาพยนตร์ (Cinematic Grade)
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">ขนาดไฟล์ LUT</span>
                        <span className="text-cyan-300 font-mono font-bold block mt-0.5">
                          {selectedAsset.size_mb ? `${selectedAsset.size_mb} MB` : 'Standard 33x33x33'}
                        </span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">ความเข้ากันได้</span>
                        <span className="text-emerald-300 font-mono font-bold block mt-0.5">FFmpeg / CapCut PC</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── WORKBENCH VIEW: VIDEO EFFECTS (transparent overlay) ── */}
                {activeAssetTab === 'effects' && (
                  <div className="space-y-4">
                    <div className="w-full h-56 rounded-2xl border border-white/[0.1] flex items-center justify-center p-6 shadow-inner relative bg-[linear-gradient(45deg,#e2e8f0_25%,transparent_25%),linear-gradient(-45deg,#e2e8f0_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#e2e8f0_75%),linear-gradient(-45deg,transparent_75%,#e2e8f0_75%)] bg-[size:20px_20px] bg-white">
                      <video
                        src={selectedAsset.video_url || (selectedAsset.rel_path ? `/api/media/${selectedAsset.rel_path}` : '')}
                        className="max-w-full max-h-full object-contain drop-shadow-2xl"
                        style={{ mixBlendMode: 'multiply' }}
                        autoPlay
                        loop
                        muted
                        playsInline
                        controls
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">หมวดหมู่</span>
                        <span className="text-white font-bold truncate block mt-0.5">{selectedAsset.category || 'Effect'}</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-black/40 border border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 block">ชนิดไฟล์</span>
                        <span className="text-fuchsia-300  block mt-0.5">WebM VP9 โปร่งใส (Alpha)</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Workbench Footer: Copy Path & Quick Action */}
                <div className="flex items-center gap-2 pt-3 border-t border-white/[0.08]">
                  <button
                    type="button"
                    onClick={() => handleCopy(selectedAsset.path || selectedAsset.url || selectedAsset.name)}
                    className="flex-1 py-2.5 px-3 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-xs font-bold text-slate-200 flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    <span>{copiedPath ? 'คัดลอกที่อยู่แล้ว' : 'คัดลอกที่อยู่ไฟล์'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpen('assets')}
                    className="px-4 py-2.5 rounded-xl bg-[#25F4EE]/15 hover:bg-[#25F4EE]/25 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <Folder className="w-3.5 h-3.5" />
                    <span>เปิดโฟลเดอร์</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-8 text-center text-slate-500 space-y-2">
                <Layers className="w-8 h-8 mx-auto text-slate-600" />
                <p className="text-xs">เลือกไฟล์จากรายการฝั่งซ้ายเพื่อตรวจดูรายละเอียด</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ── CLASSIC GRID GALLERY VIEW ── */
        <div className="space-y-4 animate-fadeIn">
          {/* SFX Grid */}
          {activeAssetTab === 'sfx' && (
            <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2.5 sm:gap-3">
              {visibleCurrentItems.map((sfx) => {
                const isPlaying = currentlyPlayingAudio === sfx.name;
                return (
                  <div
                    key={sfx.name}
                    className={`p-3.5 rounded-2xl border transition-all flex items-center justify-between group glass-card ${
                      isPlaying
                        ? 'border-[#25F4EE] bg-[#25F4EE]/10 shadow-lg shadow-[#25F4EE]/10'
                        : 'border-white/[0.06] hover:border-white/[0.15]'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0 pr-2">
                      <button
                        type="button"
                        onClick={() => playAudio(sfx, sfx.name)}
                        className={`w-11 h-11 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center transition-all cursor-pointer flex-shrink-0 active:scale-95 ${
                          isPlaying
                            ? 'bg-[#25F4EE] text-slate-950 scale-95 shadow-md shadow-[#25F4EE]/30'
                            : 'bg-white/[0.06] text-slate-300 hover:bg-[#25F4EE]/20 hover:text-[#25F4EE]'
                        }`}
                      >
                        {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
                      </button>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-slate-200 truncate group-hover:text-white transition-colors">
                          {sfx.label || sfx.name}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {sfx.category || 'Sound Effect'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        type="button"
                        onClick={(e) => handleToggleStar(sfx, e)}
                        className={`p-1.5 rounded-lg transition-all cursor-pointer ${
                          sfx.starred ? 'text-amber-400 hover:text-amber-300' : 'text-slate-500 opacity-0 group-hover:opacity-100 hover:text-amber-400'
                        }`}
                        title={sfx.starred ? 'เอาดาวออก' : 'ติดดาว (ใช้ในตัดต่อ)'}
                      >
                        <Star className={`w-3.5 h-3.5 ${sfx.starred ? 'fill-current' : ''}`} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(sfx)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
                        title="ลบไฟล์เสียง"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Music Grid */}
          {activeAssetTab === 'music' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {visibleCurrentItems.map((bgm) => {
                const isPlaying = currentlyPlayingAudio === bgm.name;
                return (
                  <div
                    key={bgm.name}
                    className={`p-4 rounded-2xl border transition-all flex items-center justify-between group glass-card ${
                      isPlaying
                        ? 'border-[#FE2C55] bg-[#FE2C55]/10 shadow-lg shadow-[#FE2C55]/10'
                        : 'border-white/[0.06] hover:border-white/[0.15]'
                    }`}
                  >
                    <div className="flex items-center gap-3.5 min-w-0 pr-2">
                      <button
                        type="button"
                        onClick={() => playAudio(bgm, bgm.name)}
                        className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all cursor-pointer flex-shrink-0 active:scale-95 ${
                          isPlaying
                            ? 'bg-[#FE2C55] text-white scale-95 shadow-md shadow-[#FE2C55]/30'
                            : 'bg-white/[0.06] text-slate-300 hover:bg-[#FE2C55]/20 hover:text-[#FE2C55]'
                        }`}
                      >
                        {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-0.5" />}
                      </button>
                      <div className="min-w-0">
                        <div className="text-xs sm:text-sm font-bold text-slate-200 truncate">
                          {bgm.name}
                        </div>
                        <div className="text-xs text-slate-400 font-mono mt-0.5">
                          {bgm.size || 'Audio Track'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        type="button"
                        onClick={(e) => handleToggleStar(bgm, e)}
                        className={`p-2 rounded-xl transition-all cursor-pointer ${
                          bgm.starred ? 'text-amber-400 hover:text-amber-300' : 'text-slate-500 opacity-0 group-hover:opacity-100 hover:text-amber-400'
                        }`}
                        title={bgm.starred ? 'เอาดาวออก' : 'ติดดาว (ใช้ในตัดต่อ)'}
                      >
                        <Star className={`w-4 h-4 ${bgm.starred ? 'fill-current' : ''}`} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(bgm)}
                        className="opacity-0 group-hover:opacity-100 p-2 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Fonts Grid */}
          {activeAssetTab === 'fonts' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {visibleCurrentItems.map((font) => (
                <div key={font.name} className="p-4 rounded-2xl border border-white/[0.06] glass-card space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-bold text-white text-sm">{font.name}</span>
                    <span className="font-mono text-[11px]">{font.family || 'TrueType Font'}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-black/50 border border-white/[0.04] text-lg sm:text-xl text-[#25F4EE] font-bold truncate">
                    {customFontText}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Stickers Grid */}
          {activeAssetTab === 'stickers' && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {visibleCurrentItems.map((sticker) => (
                <div key={sticker.name} className="p-3 rounded-2xl border border-white/[0.06] glass-card flex flex-col items-center justify-center text-center group relative space-y-2">
                  <div className="w-20 h-20 flex items-center justify-center p-2 rounded-xl bg-black/40">
                    <img
                      src={sticker.img_url || sticker.url || (sticker.rel_path ? `/api/media/${sticker.rel_path}` : '')}
                      alt={sticker.name}
                      className="max-w-full max-h-full object-contain drop-shadow-md"
                    />
                  </div>
                  <span className="text-xs font-bold text-slate-300 truncate w-full px-1">{sticker.name}</span>
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(sticker)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-black/60 text-slate-400 hover:text-red-400 transition-all cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* LUTs Grid */}
          {activeAssetTab === 'luts' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {visibleCurrentItems.map((lut) => (
                <div key={lut.name} className="p-4 rounded-2xl border border-white/[0.06] glass-card flex items-center justify-between group">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500/20 to-pink-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                      <Film className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white truncate max-w-[140px]">{lut.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">3D LUT (.cube)</div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(lut)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Effects Grid */}
          {activeAssetTab === 'effects' && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {visibleCurrentItems.map((fx) => (
                <div key={fx.id} className="p-3 rounded-2xl border border-white/[0.06] glass-card flex flex-col items-center justify-center text-center group relative space-y-2">
                  <div
                    onClick={() => setPreviewEffect(fx)}
                    className="w-20 h-20 flex items-center justify-center rounded-xl bg-[linear-gradient(45deg,#e2e8f0_25%,transparent_25%),linear-gradient(-45deg,#e2e8f0_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#e2e8f0_75%),linear-gradient(-45deg,transparent_75%,#e2e8f0_75%)] bg-[size:14px_14px] bg-white cursor-pointer"
                    title="คลิกดูพรีวิวขนาดใหญ่"
                  >
                    <video
                      src={fx.video_url || (fx.rel_path ? `/api/media/${fx.rel_path}` : '')}
                      className="max-w-full max-h-full object-contain"
                      style={{ mixBlendMode: 'multiply' }}
                      autoPlay
                      loop
                      muted
                      playsInline
                    />
                  </div>
                  <span className="text-xs font-bold text-slate-300 truncate w-full px-1">{fx.label || fx.name}</span>
                  <button
                    type="button"
                    onClick={(e) => handleToggleStar(fx, e)}
                    className={`absolute top-2 left-2 p-1.5 rounded-lg bg-black/60 transition-all cursor-pointer ${
                      fx.starred ? 'text-amber-400' : 'text-slate-400 opacity-0 group-hover:opacity-100 hover:text-amber-400'
                    }`}
                    title={fx.starred ? 'เอาดาวออก' : 'ติดดาว (ใช้ในตัดต่อ)'}
                  >
                    <Star className={`w-3.5 h-3.5 ${fx.starred ? 'fill-current' : ''}`} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(fx)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-black/60 text-slate-400 hover:text-red-400 transition-all cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {renderAssetPagination()}
        </div>
      )}

      {/* ── Effect Big Preview Modal ── */}
      {(() => {
        const livePreview = previewEffect
          ? (assetData.effects || []).find((e) => e.id === previewEffect.id) || previewEffect
          : null;
        return (
          <Modal
            isOpen={!!livePreview}
            onClose={() => setPreviewEffect(null)}
            title={livePreview?.label || livePreview?.name}
            subtitle={livePreview?.category}
            maxWidth="max-w-lg"
          >
            {livePreview && (
              <div className="space-y-3">
                <div className="w-full aspect-square rounded-2xl border border-white/[0.1] flex items-center justify-center p-6 shadow-inner bg-[linear-gradient(45deg,#e2e8f0_25%,transparent_25%),linear-gradient(-45deg,#e2e8f0_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#e2e8f0_75%),linear-gradient(-45deg,transparent_75%,#e2e8f0_75%)] bg-[size:24px_24px] bg-white">
                  <video
                    src={livePreview.video_url || (livePreview.rel_path ? `/api/media/${livePreview.rel_path}` : '')}
                    className="max-w-full max-h-full object-contain"
                    style={{ mixBlendMode: 'multiply' }}
                    autoPlay
                    loop
                    muted
                    playsInline
                    controls
                  />
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    try { navigator.vibrate?.(10); } catch {}
                    handleToggleStar(livePreview, e);
                  }}
                  className={`w-full py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
                    livePreview.starred
                      ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                      : 'bg-white/[0.06] text-slate-200 hover:bg-white/[0.12]'
                  }`}
                >
                  <Star className={`w-3.5 h-3.5 ${livePreview.starred ? 'fill-current' : ''}`} />
                  <span>{livePreview.starred ? 'ยกเลิกการติดดาว' : 'ติดดาวสำหรับตัดต่อ'}</span>
                </button>
              </div>
            )}
          </Modal>
        );
      })()}

      {/* ── Asset Delete Confirmation Modal ── */}
      <ConfirmModal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="ยืนยันการลบทรัพยากรนี้ถาวร?"
        description="ไฟล์จะถูกลบออกจากโฟลเดอร์ Assets ในเครื่อง"
        itemName={deleteTarget?.name}
        dangerNote="การกระทำนี้ไม่สามารถย้อนกลับได้"
        confirmText="ยืนยันลบไฟล์"
        loading={deleting}
        variant="danger"
      />

      {/* ── Sticky Mobile Audio Mini-Player Bar ── */}
      {currentlyPlayingAudio && (
        <div className="fixed bottom-[calc(var(--nav-h,4rem)+env(safe-area-inset-bottom,0px)+0.75rem)] md:bottom-6 left-1/2 -translate-x-1/2 z-40 max-w-md w-[calc(100%-2rem)] p-3 rounded-2xl glass-panel shadow-2xl flex items-center justify-between gap-3 animate-fadeIn">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-[#25F4EE]/20 text-[#25F4EE] flex items-center justify-center flex-shrink-0 animate-pulse">
              <Volume2 className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-xs font-bold text-white truncate max-w-[200px]">{currentlyPlayingAudio}</div>
              <div className="text-[10px] text-[#25F4EE] font-mono">กำลังทดลองฟังเสียง...</div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current.currentTime = 0;
              }
              setCurrentlyPlayingAudio(null);
            }}
            className="px-3.5 py-1.5 rounded-xl bg-white/[0.08] hover:bg-white/[0.15] text-xs font-bold text-white flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>หยุดเล่น</span>
          </button>
        </div>
      )}

      {/* Toast */}
      {toastMessage && (
        <Toast
          message={toastMessage.message}
          type={toastMessage.type}
          onClose={hideToast}
          duration={toastDuration}
        />
      )}
    </div>
  );
}
