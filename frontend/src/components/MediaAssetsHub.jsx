import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { 
  Folder, Volume2, Music, Type, 
  Search, Play, Pause, Download, Trash2, Upload, Sparkles, Image, 
  Film, Palette, AlertTriangle, X, Check, RefreshCw, Layers
} from 'lucide-react';
import { openFolder, getAllAssets, uploadAsset, deleteFile } from '../api';
import { Modal, Toast, Button, Badge, Input, ConfirmModal } from './ui';
import { useDebounce, useToast } from '../hooks';

export default function MediaAssetsHub() {
  const [activeAssetTab, setActiveAssetTab] = useState('sfx'); // 'sfx' | 'music' | 'fonts' | 'stickers' | 'luts'
  const [assetData, setAssetData] = useState({ sfx: [], music: [], fonts: [], stickers: [], luts: [], counts: {} });
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 250);
  const [currentlyPlayingAudio, setCurrentlyPlayingAudio] = useState(null);
  const [customFontText, setCustomFontText] = useState('อย่าเพิ่งเลื่อนผ่าน! โปรโมชั่นลด 50% วันนี้');
  const [uploadingAsset, setUploadingAsset] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const { toastMessage, showToast, hideToast } = useToast();
  const audioRef = useRef(null);
  const fileUploadRef = useRef(null);

  const fetchAssets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAllAssets();
      setAssetData(data);
    } catch (err) {
      console.error('Failed to fetch assets:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const handleOpen = useCallback((target) => {
    openFolder(target);
  }, []);

  const playAudio = useCallback((url, name) => {
    if (currentlyPlayingAudio === name) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setCurrentlyPlayingAudio(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }

    const audio = new Audio(url);
    audioRef.current = audio;
    setCurrentlyPlayingAudio(name);

    audio.play().catch(e => console.error(e));
    audio.onended = () => {
      setCurrentlyPlayingAudio(null);
    };
  }, [currentlyPlayingAudio]);

  const handleAssetUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingAsset(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('asset_type', activeAssetTab);

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

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteFile(deleteTarget.path);
      showToast(`ลบไฟล์ ${deleteTarget.name} เรียบร้อย`);
      setDeleteTarget(null);
      fetchAssets();
    } catch (err) {
      showToast('ลบไฟล์ไม่สำเร็จ: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setDeleting(false);
    }
  };

  // Filter items by search query
  const filterList = (list) => {
    if (!debouncedSearch) return list;
    const q = debouncedSearch.toLowerCase();
    return (list || []).filter(item => 
      (item.name && item.name.toLowerCase().includes(q)) ||
      (item.label && item.label.toLowerCase().includes(q)) ||
      (item.category && item.category.toLowerCase().includes(q))
    );
  };

  const filteredSFX = useMemo(() => filterList(assetData.sfx), [assetData.sfx, debouncedSearch]);
  const filteredMusic = useMemo(() => filterList(assetData.music), [assetData.music, debouncedSearch]);
  const filteredFonts = useMemo(() => filterList(assetData.fonts), [assetData.fonts, debouncedSearch]);
  const filteredStickers = useMemo(() => filterList(assetData.stickers), [assetData.stickers, debouncedSearch]);
  const filteredLuts = useMemo(() => filterList(assetData.luts), [assetData.luts, debouncedSearch]);

  const assetCategories = [
    { id: 'sfx', label: 'เสียง SFX', icon: Volume2, count: assetData.counts?.sfx || 0 },
    { id: 'music', label: 'เพลง BGM', icon: Music, count: assetData.counts?.music || 0 },
    { id: 'fonts', label: 'ฟอนต์วิดีโอ', icon: Type, count: assetData.counts?.fonts || 0 },
    { id: 'stickers', label: 'ป้าย 3D Badges', icon: Image, count: assetData.counts?.stickers || 0 },
    { id: 'luts', label: 'โทนสี LUTs', icon: Film, count: assetData.counts?.luts || 0 },
  ];

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* ── Header Bar ── */}
      <div className="glass-panel p-5 sm:p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 rounded-3xl border border-white/[0.08]">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] flex items-center justify-center text-white shadow-lg shadow-[#FE2C55]/20 flex-shrink-0">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold font-kanit text-white flex items-center gap-2">
              คลังทรัพยากรสื่อ (Media Assets Hub)
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              ศูนย์รวมเสียงเอฟเฟกต์ SFX • เพลง BGM • ฟอนต์สไตล์ TikTok • ป้ายสติกเกอร์ 3D และโทนสี LUTs
            </p>
          </div>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          <label
            className={`relative flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white text-xs font-bold shadow-lg shadow-[#FE2C55]/20 transition-all cursor-pointer ${
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
            <Upload className="w-4 h-4 text-white pointer-events-none" />
            <span className="pointer-events-none">{uploadingAsset ? 'กำลังเพิ่มไฟล์...' : 'เพิ่มทรัพยากรใหม่'}</span>
          </label>
          <button
            onClick={() => handleOpen('assets')}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 text-xs font-bold border border-white/[0.08] transition-colors cursor-pointer"
          >
            <Folder className="w-4 h-4 text-[#25F4EE]" />
            <span className="hidden sm:inline">เปิดโฟลเดอร์ Assets</span>
          </button>
          <button
            onClick={fetchAssets}
            className="p-2.5 min-w-[36px] min-h-[36px] rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white border border-white/[0.08] transition-colors cursor-pointer flex items-center justify-center"
            title="รีเฟรชข้อมูล"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#25F4EE]' : ''}`} />
          </button>
        </div>
      </div>

      {/* Categorized Nav Pills */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
        {assetCategories.map((tab) => {
          const isActive = activeAssetTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveAssetTab(tab.id)}
              className={`p-3.5 rounded-2xl border text-left transition-all relative cursor-pointer glass-card ${
                isActive
                  ? 'border-[#25F4EE]/50 bg-[#25F4EE]/10 shadow-md ring-1 ring-[#25F4EE]/30'
                  : 'border-white/[0.06] hover:border-white/[0.15]'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-xs font-bold truncate ${isActive ? 'text-white' : 'text-slate-400'}`}>{tab.label}</span>
                <span className={`text-sm px-2 py-0.5 rounded-full font-bold font-mono ${
                  isActive ? 'bg-[#25F4EE] text-slate-950 shadow-sm' : 'bg-white/[0.05] border border-white/[0.08] text-slate-400'
                }`}>
                  {tab.count}
                </span>
              </div>
              <div className={`h-1 w-full mt-2.5 rounded-full ${isActive ? 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE]' : 'bg-white/[0.08]'}`} />
            </button>
          );
        })}
      </div>

      {/* Search Bar for Assets */}
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={`ค้นหาในหมวด ${activeAssetTab.toUpperCase()} (เช่น pop, whoosh, bold, deal)...`}
          className="w-full pl-11 pr-4 py-2.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-xs sm:text-sm focus:outline-none focus:border-[#25F4EE]/50 transition-colors shadow-inner"
        />
      </div>

      {/* ── 1. SFX SOUNDBOARD ── */}
      {activeAssetTab === 'sfx' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1 font-semibold">
            <span>แตะที่ปุ่มเพื่อทดลองฟังเสียงสดทันที ({filteredSFX.length} ไฟล์)</span>
            <span className="text-sm text-[#25F4EE] font-bold">Auto-sync กับไทม์ไลน์วิดีโอ</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {filteredSFX.map((sfx) => {
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
                      onClick={() => playAudio(sfx.url, sfx.name)}
                      className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all cursor-pointer flex-shrink-0 ${
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

                  <button
                    onClick={() => setDeleteTarget(sfx)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
                    title="ลบไฟล์เสียง"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── 2. BGM MUSIC ── */}
      {activeAssetTab === 'music' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredMusic.map((bgm) => {
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
                      onClick={() => playAudio(bgm.url, bgm.name)}
                      className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all cursor-pointer flex-shrink-0 ${
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

                  <button
                    onClick={() => setDeleteTarget(bgm)}
                    className="opacity-0 group-hover:opacity-100 p-2 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── 3. FONTS ── */}
      {activeAssetTab === 'fonts' && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-2xl bg-black/40 border border-white/[0.08] flex items-center gap-3">
            <span className="text-xs text-slate-400 font-bold whitespace-nowrap">ทดสอบพิมพ์ข้อความ:</span>
            <input
              type="text"
              value={customFontText}
              onChange={(e) => setCustomFontText(e.target.value)}
              className="flex-1 bg-transparent text-sm text-white focus:outline-none placeholder-slate-600 font-kanit"
              placeholder="พิมพ์ข้อความทดสอบฟอนต์ที่นี่..."
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredFonts.map((font) => (
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
        </div>
      )}

      {/* ── 4. STICKERS & BADGES ── */}
      {activeAssetTab === 'stickers' && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {filteredStickers.map((sticker) => (
            <div key={sticker.name} className="p-3 rounded-2xl border border-white/[0.06] glass-card flex flex-col items-center justify-center text-center group relative space-y-2">
              <div className="w-20 h-20 flex items-center justify-center p-2 rounded-xl bg-black/40">
                <img src={sticker.url} alt={sticker.name} className="max-w-full max-h-full object-contain drop-shadow-md" />
              </div>
              <span className="text-xs font-bold text-slate-300 truncate w-full px-1">{sticker.name}</span>
              <button
                onClick={() => setDeleteTarget(sticker)}
                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-black/60 text-slate-400 hover:text-red-400 transition-all cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── 5. LUTS ── */}
      {activeAssetTab === 'luts' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {filteredLuts.map((lut) => (
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
                onClick={() => setDeleteTarget(lut)}
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

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

      {toastMessage && (
        <Toast
          message={toastMessage.message}
          type={toastMessage.type}
          onClose={hideToast}
        />
      )}
    </div>
  );
}
