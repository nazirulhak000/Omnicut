import React, { useState, useEffect, useRef } from 'react';
import { 
  Settings, Folder, Volume2, HardDrive, CheckCircle2, Music, Type, 
  Search, Play, Pause, Download, Trash2, Upload, Sparkles, Image, 
  Film, Palette, AlertTriangle, X, Check, RefreshCw, Layers
} from 'lucide-react';
import { openFolder, getAllAssets, uploadAsset, deleteFile } from '../api';

export default function SystemAssets({ status }) {
  const [activeAssetTab, setActiveAssetTab] = useState('sfx'); // 'sfx' | 'music' | 'fonts' | 'stickers' | 'luts' | 'system'
  const [assetData, setAssetData] = useState({ sfx: [], music: [], fonts: [], stickers: [], luts: [], counts: {} });
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentlyPlayingAudio, setCurrentlyPlayingAudio] = useState(null);
  const [customFontText, setCustomFontText] = useState('🔥 อย่าเพิ่งเลื่อนผ่าน! โปรโมชั่นลด 50% วันนี้');
  const [uploadingAsset, setUploadingAsset] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const audioRef = useRef(null);
  const fileUploadRef = useRef(null);

  const fetchAssets = async () => {
    setLoading(true);
    try {
      const data = await getAllAssets();
      setAssetData(data);
    } catch (err) {
      console.error('Failed to fetch assets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, []);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleOpen = (target) => {
    openFolder(target);
  };

  const playAudio = (url, name) => {
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
  };

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
      alert('อัปโหลดล้มเหลว: ' + (err.response?.data?.detail || err.message));
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
      showToast(`ลบไฟล์ ${deleteTarget.name} เรียบร้อยแล้ว`);
      setDeleteTarget(null);
      fetchAssets();
    } catch (err) {
      alert('ไม่สามารถลบไฟล์ได้: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  // Filtered lists based on search
  const filteredSFX = (assetData.sfx || []).filter(sf => 
    sf.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredMusic = (assetData.music || []).filter(m => 
    m.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredFonts = (assetData.fonts || []).filter(f => 
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredStickers = (assetData.stickers || []).filter(s => 
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const assetCategories = [
    { id: 'sfx', label: '🔊 SFX Soundboard', count: assetData.counts?.sfx || assetData.sfx?.length || 0, color: 'from-[#FE2C55] to-rose-600' },
    { id: 'music', label: '🎵 BGM เพลงประกอบ', count: assetData.counts?.music || assetData.music?.length || 0, color: 'from-purple-500 to-indigo-600' },
    { id: 'fonts', label: '🎨 ฟอนต์ตัวหนังสือ', count: assetData.counts?.fonts || assetData.fonts?.length || 0, color: 'from-[#25F4EE] to-teal-600' },
    { id: 'stickers', label: '🏷️ สติกเกอร์ & ป้ายเซลล์', count: assetData.counts?.stickers || assetData.stickers?.length || 0, color: 'from-amber-500 to-orange-600' },
    { id: 'luts', label: '🎬 โทนสี LUTs', count: assetData.counts?.luts || assetData.luts?.length || 0, color: 'from-blue-500 to-cyan-600' },
    { id: 'system', label: '⚙️ ระบบ & ไดเรกทอรี', count: 5, color: 'from-slate-700 to-slate-900' },
  ];

  return (
    <div className="space-y-6 relative">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-2xl bg-emerald-500/90 text-white font-bold text-xs backdrop-blur-md shadow-2xl animate-bounce">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 sm:p-6 glass-panel border border-white/10 shadow-2xl">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#FE2C55] via-[#FF0050] to-[#25F4EE] flex items-center justify-center shadow-lg shadow-[#FE2C55]/30 flex-shrink-0">
            <Layers className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-black font-kanit text-white flex items-center gap-2">
              คลังทรัพยากร & ระบบตัดต่อ (System & Assets Hub)
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 font-prompt mt-0.5">
              ศูนย์รวมเสียงเอฟเฟกต์ SFX • เพลง BGM • ฟอนต์สไตล์ TikTok • ป้ายสติกเกอร์ • โทนสี LUTs และการเชื่อมต่อ CapCut
            </p>
          </div>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          <button
            onClick={() => fileUploadRef.current?.click()}
            disabled={uploadingAsset}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:opacity-90 text-white text-xs font-bold shadow-lg shadow-[#FE2C55]/25 transition-all cursor-pointer"
          >
            <Upload className="w-4 h-4" />
            <span>{uploadingAsset ? 'กำลังเพิ่มไฟล์...' : 'เพิ่มทรัพยากรใหม่'}</span>
          </button>
          <button
            onClick={() => handleOpen('assets')}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold border border-slate-700 transition-colors cursor-pointer"
          >
            <Folder className="w-4 h-4 text-[#25F4EE]" />
            <span className="hidden sm:inline">เปิดโฟลเดอร์ Assets</span>
          </button>
          <button
            onClick={fetchAssets}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
            title="รีเฟรชข้อมูล"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <input
            ref={fileUploadRef}
            type="file"
            onChange={handleAssetUpload}
            className="hidden"
          />
        </div>
      </div>

      {/* Categorized Nav Pills */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {assetCategories.map((tab) => {
          const isActive = activeAssetTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveAssetTab(tab.id)}
              className={`p-3.5 rounded-2xl border text-left transition-all relative cursor-pointer ${
                isActive
                  ? 'bg-gradient-to-br from-[#212838] to-[#181F2C] border-[#25F4EE]/50 shadow-xl ring-1 ring-[#25F4EE]/30'
                  : 'bg-black/30 border-white/5 hover:border-white/15 hover:bg-black/50'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white truncate">{tab.label}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold font-mono ${
                  isActive ? 'bg-[#25F4EE] text-slate-950' : 'bg-slate-800 text-slate-400'
                }`}>
                  {tab.count}
                </span>
              </div>
              <div className={`h-1 w-full mt-2.5 rounded-full bg-gradient-to-r ${tab.color} opacity-${isActive ? '100' : '40'}`} />
            </button>
          );
        })}
      </div>

      {/* Search Bar for Assets */}
      {activeAssetTab !== 'system' && (
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`ค้นหาในหมวด ${activeAssetTab.toUpperCase()} (เช่น pop, whoosh, bold, deal)...`}
            className="w-full pl-11 pr-4 py-3 rounded-2xl bg-[#121622] border border-white/10 text-slate-100 text-xs sm:text-sm focus:outline-none focus:border-[#25F4EE] transition-colors"
          />
        </div>
      )}

      {/* TAB CONTENT: 1. SFX SOUNDBOARD */}
      {activeAssetTab === 'sfx' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>🔊 แตะที่ปุ่มเพื่อทดลองฟังเสียงสดทันที ({filteredSFX.length} ไฟล์)</span>
            <span className="text-[11px] text-[#25F4EE]">Auto-sync กับไทม์ไลน์วิดีโอ</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {filteredSFX.map((sf, idx) => {
              const isPlaying = currentlyPlayingAudio === sf.name;
              return (
                <div
                  key={idx}
                  className={`p-3 rounded-2xl border transition-all flex items-center justify-between gap-2.5 ${
                    isPlaying 
                      ? 'bg-gradient-to-r from-[#FE2C55]/25 to-rose-900/30 border-[#FE2C55] shadow-lg shadow-[#FE2C55]/20 ring-1 ring-[#FE2C55]' 
                      : 'bg-black/35 border-white/5 hover:border-white/20 hover:bg-black/55'
                  }`}
                >
                  <button
                    onClick={() => playAudio(sf.audio_url, sf.name)}
                    className="flex items-center gap-2.5 flex-1 min-w-0 text-left cursor-pointer group"
                  >
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all flex-shrink-0 ${
                      isPlaying 
                        ? 'bg-[#FE2C55] text-white animate-bounce' 
                        : 'bg-[#232A3B] text-[#25F4EE] group-hover:bg-[#25F4EE] group-hover:text-black'
                    }`}>
                      {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-white truncate group-hover:text-[#25F4EE] transition-colors">
                        {sf.name.replace(/\.(wav|mp3)$/i, '')}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] text-slate-400 font-mono">{sf.size_mb} MB</span>
                        {sf.category && sf.category !== 'misc' && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-[#25F4EE]/10 text-[#25F4EE] font-bold">
                            {sf.category}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>

                  <div className="flex items-center gap-1">
                    <a
                      href={sf.audio_url}
                      download={sf.name}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                      title="ดาวน์โหลด SFX"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                    <button
                      onClick={() => setDeleteTarget(sf)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                      title="ลบเสียงนี้"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB CONTENT: 2. BGM MUSIC HUB */}
      {activeAssetTab === 'music' && (
        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-gradient-to-r from-purple-900/30 to-indigo-900/20 border border-purple-500/30 flex items-center justify-between text-xs text-purple-200">
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              เพลง BGM ทั้งหมดถูกปรับระดับเสียงและ Auto-Ducking (-16dB) ให้พอดีกับเสียงพูดอัตโนมัติ
            </span>
            <button
              onClick={() => handleOpen('music')}
              className="px-3 py-1.5 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 font-bold border border-purple-500/30 cursor-pointer"
            >
              เปิดโฟลเดอร์เพลง
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredMusic.map((m, idx) => {
              const isPlaying = currentlyPlayingAudio === m.name;
              return (
                <div
                  key={idx}
                  className={`p-4 rounded-2xl border transition-all flex flex-col justify-between space-y-3 ${
                    isPlaying
                      ? 'bg-gradient-to-b from-[#212838] to-[#181F2C] border-purple-500 shadow-xl ring-1 ring-purple-500'
                      : 'bg-black/35 border-white/5 hover:border-white/15'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        isPlaying ? 'bg-purple-500 text-white' : 'bg-slate-800 text-purple-400'
                      }`}>
                        <Music className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white truncate max-w-[190px]" title={m.name}>
                          {m.name.replace(/\.(wav|mp3)$/i, '')}
                        </div>
                        <span className="text-[11px] text-slate-400 font-mono">{m.size_mb} MB • High Quality</span>
                      </div>
                    </div>

                    <button
                      onClick={() => setDeleteTarget(m)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 cursor-pointer"
                      title="ลบเพลงนี้"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                    <button
                      onClick={() => playAudio(m.audio_url, m.name)}
                      className={`flex-1 py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer ${
                        isPlaying 
                          ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30' 
                          : 'bg-[#232A3B] hover:bg-[#323B52] text-white'
                      }`}
                    >
                      {isPlaying ? (
                        <>
                          <Pause className="w-3.5 h-3.5" />
                          <span>หยุดเล่นเพลง</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 fill-current" />
                          <span>ทดลองฟังเพลง (Play)</span>
                        </>
                      )}
                    </button>

                    <a
                      href={m.audio_url}
                      download={m.name}
                      className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
                      title="ดาวน์โหลดไฟล์เพลง"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB CONTENT: 3. FONTS & TYPOGRAPHY LAB */}
      {activeAssetTab === 'fonts' && (
        <div className="space-y-4">
          {/* Live Text Customizer */}
          <div className="p-4 rounded-2xl glass-panel border border-[#25F4EE]/30 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-300 font-bold">
              <span className="flex items-center gap-2 text-[#25F4EE]">
                <Type className="w-4 h-4" />
                ทดสอบพิมพ์ข้อความตัวอย่างเพื่อดูการแสดงผลฟอนต์จริงสดๆ:
              </span>
              <span className="text-[11px] text-slate-400 font-normal">
                ฟอนต์ทั้งหมดถูกแพ็กรวมใน CapCut และ FFmpeg อัตโนมัติ
              </span>
            </div>
            <input
              type="text"
              value={customFontText}
              onChange={(e) => setCustomFontText(e.target.value)}
              placeholder="พิมพ์ข้อความทดสอบฟอนต์ที่นี่..."
              className="w-full py-2.5 px-3.5 rounded-xl bg-[#121622] border border-white/10 text-white text-sm focus:outline-none focus:border-[#25F4EE]"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredFonts.map((f, idx) => {
              const fontStem = f.name.replace(/\.(ttf|otf)$/i, '');
              return (
                <div
                  key={idx}
                  className="p-4 rounded-2xl glass-card border border-white/5 hover:border-[#25F4EE]/40 transition-all space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-[#25F4EE]">{fontStem}</div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">{f.size_mb} MB • TrueType Font</div>
                    </div>
                    <button
                      onClick={() => setDeleteTarget(f)}
                      className="p-1 text-slate-500 hover:text-red-400 cursor-pointer"
                      title="ลบฟอนต์นี้"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="p-3 bg-black/60 rounded-xl border border-white/5 min-h-[60px] flex items-center justify-center text-center">
                    <p className="text-base font-bold text-white leading-relaxed break-words">
                      {customFontText || fontStem}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB CONTENT: 4. STICKERS & BADGES */}
      {activeAssetTab === 'stickers' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>🏷️ สติกเกอร์ ป้ายลดราคา และไอคอนกระตุ้นยอดขาย ({filteredStickers.length} ภาพ)</span>
            <button
              onClick={() => handleOpen('stickers')}
              className="text-[#25F4EE] hover:underline font-bold"
            >
              เปิดโฟลเดอร์ Stickers
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
            {filteredStickers.map((st, idx) => (
              <div
                key={idx}
                className="p-3 rounded-2xl glass-card border border-white/5 hover:border-amber-500/40 flex flex-col items-center justify-between text-center group"
              >
                <div className="w-full aspect-square p-2 bg-black/40 rounded-xl flex items-center justify-center mb-2 overflow-hidden border border-white/5 group-hover:scale-105 transition-transform">
                  <img
                    src={st.img_url}
                    alt={st.name}
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
                <div className="w-full">
                  <div className="text-[11px] font-bold text-white truncate" title={st.name}>
                    {st.name}
                  </div>
                  <div className="flex items-center justify-between mt-2 pt-1 border-t border-white/5">
                    <a
                      href={st.img_url}
                      download={st.name}
                      className="text-[10px] text-amber-400 hover:underline flex items-center gap-1 font-bold"
                    >
                      <Download className="w-3 h-3" />
                      ดาวน์โหลด
                    </a>
                    <button
                      onClick={() => setDeleteTarget(st)}
                      className="p-1 text-slate-500 hover:text-red-400 cursor-pointer"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB CONTENT: 5. LUTS COLOR PRESETS */}
      {activeAssetTab === 'luts' && (
        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-gradient-to-r from-blue-900/30 to-cyan-900/20 border border-cyan-500/30 text-xs text-cyan-200 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Palette className="w-4 h-4 text-cyan-400" />
              พรีเซ็ตสี 3D LUTs (.cube) ยอดนิยมสำหรับแต่งคลิปวิดีโอสินค้า สกินแคร์ และแกดเจ็ต
            </span>
            <button
              onClick={() => handleOpen('luts')}
              className="px-3 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 font-bold border border-cyan-500/30 cursor-pointer"
            >
              เปิดโฟลเดอร์ LUTs
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {(assetData.luts || []).map((lut, idx) => (
              <div
                key={idx}
                className="p-4 rounded-2xl glass-card border border-white/5 hover:border-cyan-500/40 space-y-3"
              >
                <div className="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
                  <Palette className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-bold text-white truncate" title={lut.name}>
                    {lut.name.replace('.cube', '')}
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">3D Color LUT Cube ({lut.size_mb} MB)</div>
                </div>
                <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                  <span
                    className="text-[10px] text-amber-400 font-bold"
                    title="เลือกได้ในขั้นตอนที่ 3 ของหน้า 'สินค้า → คลิป' — ไม่ auto-apply เพราะวัดแล้วทำให้เรนเดอร์ช้าลง ~90% บนเครื่องนี้ (ไม่มีการ์ดจอช่วย)"
                  >
                    ⚠️ เลือกเองที่หน้าตัดคลิป (ช้าลง ~90%)
                  </span>
                  <button
                    onClick={() => setDeleteTarget(lut)}
                    className="p-1 text-slate-500 hover:text-red-400 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB CONTENT: 6. SYSTEM DIRECTORIES & CAPCUT MANAGER */}
      {activeAssetTab === 'system' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Storage Directory Explorer */}
          <div className="glass-card p-5 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
              <Folder className="w-4 h-4 text-[#25F4EE]" />
              ไดเรกทอรีจัดเก็บไฟล์ในเครื่องคอมพิวเตอร์
            </h3>

            <div className="space-y-2.5 text-xs">
              {[
                { title: '00_Inbox (พักไฟล์จากมือถือ)', desc: 'ไฟล์ที่อัปโหลดไร้สายมาจะถูกเก็บที่นี่', key: 'inbox', path: status?.directories?.inbox },
                { title: '01_Raw (ฟุตเทจจัดเก็บถาวร)', desc: 'คลิปสินค้าต้นฉบับคุณภาพสูง', key: 'raw', path: status?.directories?.raw },
                { title: '02_Assets (SFX / เพลง / ฟอนต์)', desc: 'คลังของแต่งคลิปและเสียงประกอบทั้งหมด', key: 'assets', path: status?.directories?.assets },
                { title: '04_Exports (วิดีโอพร้อมโพสต์)', desc: 'ไฟล์ .MP4 9:16 ที่ตัดต่อเสร็จแล้ว', key: 'exports', path: status?.directories?.exports },
                { title: 'CapCut PC Projects Draft', desc: 'โฟลเดอร์โปรเจกต์ของแอป CapCut Desktop', key: 'capcut', path: status?.directories?.capcut }
              ].map((dir, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-black/40 border border-white/5 gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="font-bold text-white truncate">{dir.title}</div>
                    <div className="text-[11px] text-slate-400 truncate">{dir.desc}</div>
                    <div className="text-[10px] text-slate-500 font-mono truncate mt-0.5">{dir.path}</div>
                  </div>
                  <button
                    onClick={() => handleOpen(dir.key)}
                    className="px-3 py-1.5 rounded-lg bg-[#232A3B] hover:bg-[#323B52] text-white text-xs font-bold transition-colors cursor-pointer flex-shrink-0"
                  >
                    เปิด
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={() => handleOpen('root')}
              className="w-full py-3 rounded-xl bg-[#232A3B] hover:bg-[#323B52] border border-white/10 text-white text-xs font-bold transition-all shadow-md cursor-pointer flex items-center justify-center gap-2"
            >
              <Folder className="w-4 h-4 text-[#25F4EE]" />
              เปิดโฟลเดอร์หลักโปรเจกต์ (Project Root Folder)
            </button>
          </div>

          {/* System Health & CapCut Integration Info */}
          <div className="glass-card p-5 space-y-4 flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-2 border-b border-white/10">
                <Settings className="w-4 h-4 text-[#FE2C55]" />
                สถานะระบบและการเชื่อมต่อ CapCut
              </h3>

              <div className="space-y-3 mt-3 text-xs">
                <div
                  className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 flex items-center justify-between"
                  title="เครื่องนี้ไม่มีการ์ดจอ CUDA (AMD Radeon integrated) — render ทั้งหมดใช้ libx264 บน CPU ล้วน"
                >
                  <span className="font-bold flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    FFmpeg Video Engine
                  </span>
                  <span className="text-[11px] font-mono font-bold bg-amber-500/20 px-2 py-0.5 rounded">
                    CPU Encode (libx264, ไม่มีการ์ดจอช่วย)
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-300 flex items-center justify-between">
                  <span className="font-bold flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    CapCut PC Draft Sync
                  </span>
                  <span className="text-[11px] font-mono font-bold bg-teal-500/20 px-2 py-0.5 rounded">
                    {status?.capcut_synced ? 'Synced' : 'Configured'}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 flex items-center justify-between">
                  <span className="font-bold flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    Local Wi-Fi Mobile Sync
                  </span>
                  <span className="text-[11px] font-mono font-bold bg-blue-500/20 px-2 py-0.5 rounded">
                    {status?.local_ip || '127.0.0.1'}:5173
                  </span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-black/50 border border-white/10 space-y-2 text-xs text-slate-300">
              <div className="font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#25F4EE]" />
                สเปกวิดีโอมาตรฐาน TikTok Auto-Cutter:
              </div>
              <ul className="space-y-1 text-slate-400 text-[11px] list-disc list-inside">
                <li>ขนาดหน้าจอ: <b>1080 x 1920 (9:16 Vertical Video)</b></li>
                <li>เฟรมเรต: <b>30 FPS H.264 High Profile</b></li>
                <li>จังหวะการตัดต่อ: <b>1.5 - 2.5 วินาทีต่อ 1 ช็อต (Dynamic Fast-Paced Cut)</b></li>
                <li>ฟอนต์คำบรรยาย: <b>Kanit-Black / Mitr พร้อมขอบดำและเอฟเฟกต์ Pop</b></li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* DELETE ASSET CONFIRMATION MODAL */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-sm p-6 glass-panel border border-red-500/40 shadow-2xl rounded-3xl text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-red-500/20 text-red-400 flex items-center justify-center mx-auto border border-red-500/30">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-white">ยืนยันการลบทรัพยากรนี้?</h3>
              <p className="text-xs text-slate-300 font-mono break-all bg-black/40 p-2.5 rounded-xl border border-white/5 mt-2">
                {deleteTarget.name}
              </p>
              <p className="text-[11px] text-slate-400 pt-1">
                ไฟล์จะถูกลบออกจากโฟลเดอร์ Assets ในเครื่อง
              </p>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition-colors cursor-pointer"
              >
                ยกเลิก
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="flex-1 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold shadow-lg shadow-red-600/30 transition-all cursor-pointer"
              >
                {deleting ? 'กำลังลบ...' : 'ยืนยันลบไฟล์'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
