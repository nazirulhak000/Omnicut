import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Film, Sparkles, Clock, Lock, Unlock, Play, Pause, RotateCcw,
  AlertTriangle, ChevronRight, Video, Scissors, CheckCircle2, RotateCw,
  Eye, RefreshCw, X, Sliders, Check
} from 'lucide-react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { toMediaUrl, isSameVideo } from '../lib/mediaUrl';
import { formatTimecode } from '../lib/timelineMath';
import { getManualShotMap, saveManualShotMap, getMediaInfo } from '../api';

const ACTION_MAP = {
  turntable_spin: { label: 'หมุนสินค้า 360', color: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
  unboxing: { label: 'แกะกล่อง/อุปกรณ์', color: 'bg-purple-500/20 text-purple-300 border-purple-500/40' },
  port_connection: { label: 'พอร์ต/เสียบชาร์จ', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' },
  closeup: { label: 'โคลสอัพดีเทล', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
  hands_on: { label: 'จับถือใช้งาน', color: 'bg-blue-500/20 text-blue-300 border-blue-500/40' },
  cta_showcase: { label: 'ป้ายยา/โชว์สินค้า', color: 'bg-rose-500/20 text-rose-300 border-rose-500/40' },
  overview: { label: 'ภาพรวมสินค้า', color: 'bg-teal-500/20 text-teal-300 border-teal-500/40' },
};

const ROLE_BADGES = {
  hook: { label: 'Hook', color: 'bg-rose-500/20 text-rose-300 border-rose-500/30' },
  feature: { label: 'Feature', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
  cta: { label: 'CTA', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
};

function getFileName(p = '') {
  if (!p) return '';
  const clean = String(p).replace(/\\/g, '/');
  return clean.split('/').pop() || p;
}

function normalizePath(p = '') {
  return p ? String(p).replace(/\\/g, '/').trim() : '';
}

export default function ManualStoryboardModal({
  isOpen,
  onClose,
  productId,
  angle,
  product,
  onSaveSuccess,
  onOpenVoiceGen,
}) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveToast, setSaveToast] = useState(null);

  const [beatCues, setBeatCues] = useState([]);
  const [hasShotList, setHasShotList] = useState(false);
  const [totalDuration, setTotalDuration] = useState(0);
  const [sceneCatalogs, setSceneCatalogs] = useState({});

  // Active state
  const [selectedBeatIdx, setSelectedBeatIdx] = useState(0);
  const [shotPins, setShotPins] = useState({}); // { [beatIndex]: { beat_index, video_path, trim_start, trim_end } }
  const [activeVideoPath, setActiveVideoPath] = useState('');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('all');

  // Trimmer state for the currently active editing session
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  const videoRef = useRef(null);
  const angleId = angle?.angle_id || angle?.id;

  // Load data whenever modal opens
  useEffect(() => {
    if (!isOpen || !productId || !angleId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setSaveToast(null);

    getManualShotMap(productId, angleId)
      .then((res) => {
        if (cancelled) return;
        setBeatCues(res.beat_cues || []);
        setHasShotList(Boolean(res.has_shot_list));
        setTotalDuration(res.total_duration || 0);
        setSceneCatalogs(res.scene_catalogs || {});

        // Build pins dictionary: beat_index -> pin
        const pinsDict = {};
        (res.manual_shot_map || []).forEach((item) => {
          if (item && item.beat_index !== undefined) {
            pinsDict[Number(item.beat_index)] = {
              beat_index: Number(item.beat_index),
              video_path: normalizePath(item.video_path),
              trim_start: Number(item.trim_start) || 0,
              trim_end: Number(item.trim_end) || 0,
            };
          }
        });
        setShotPins(pinsDict);

        // Pick initial active video
        const pin0 = pinsDict[0];
        const rawCatalogKeys = Object.keys(res.scene_catalogs || {});
        const selectedVids = angle?.selected_videos || [];
        const fallbackVid = normalizePath(
          pin0?.video_path || selectedVids[0] || angle?.selected_video || rawCatalogKeys[0] || ''
        );
        setActiveVideoPath(fallbackVid);

        if (pin0) {
          setTrimStart(pin0.trim_start);
          setTrimEnd(pin0.trim_end);
        } else {
          const beat0 = (res.beat_cues || [])[0];
          const b0Dur = beat0 ? (beat0.planned_duration || Math.max(0.5, beat0.end - beat0.start)) : 2.5;
          setTrimStart(0);
          setTrimEnd(Math.round(b0Dur * 10) / 10);
        }

        setSelectedBeatIdx(0);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.friendlyMessage || err.message || 'ไม่สามารถโหลดข้อมูลสคริปต์และช็อตได้');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, productId, angleId]);

  // Available videos list
  const availableVideos = useMemo(() => {
    const list = new Map(); // path -> label
    const addPath = (p) => {
      if (!p) return;
      const clean = typeof p === 'string' ? normalizePath(p) : normalizePath(p.rel_path || p.path || '');
      if (clean && !list.has(clean)) {
        list.set(clean, getFileName(clean));
      }
    };

    (angle?.selected_videos || []).forEach(addPath);
    if (angle?.selected_video) addPath(angle.selected_video);
    (product?.videos || []).forEach(addPath);
    Object.keys(sceneCatalogs).forEach(addPath);
    Object.values(shotPins).forEach((pin) => {
      if (pin.video_path) addPath(pin.video_path);
    });

    return Array.from(list.keys());
  }, [angle, product, sceneCatalogs, shotPins]);

  // Load video media info when activeVideoPath changes
  useEffect(() => {
    if (!activeVideoPath) return;
    let cancelled = false;
    getMediaInfo(activeVideoPath)
      .then((info) => {
        if (cancelled) return;
        const dur = Number(info?.duration) || 0;
        setVideoDuration(dur);
      })
      .catch(() => {
        if (cancelled) return;
        setVideoDuration(60);
      });
    return () => {
      cancelled = true;
    };
  }, [activeVideoPath]);

  // When switching selectedBeatIdx, load the beat's existing pin or default range
  useEffect(() => {
    if (!beatCues.length) return;
    const beat = beatCues[selectedBeatIdx];
    const targetDur = beat ? (beat.planned_duration || Math.max(0.5, beat.end - beat.start)) : 2.5;
    const currentPin = shotPins[selectedBeatIdx];

    if (currentPin && currentPin.video_path) {
      const cleanPinVid = normalizePath(currentPin.video_path);
      setActiveVideoPath(cleanPinVid);
      setTrimStart(currentPin.trim_start);
      setTrimEnd(currentPin.trim_end);
      if (videoRef.current) {
        videoRef.current.currentTime = currentPin.trim_start;
      }
    } else {
      setTrimStart(0);
      setTrimEnd(Math.round(targetDur * 10) / 10);
      if (videoRef.current) {
        videoRef.current.currentTime = 0;
      }
    }
  }, [selectedBeatIdx]); // Only sync when beat index changes

  // Current beat info
  const currentBeat = beatCues[selectedBeatIdx] || null;
  const currentBeatTargetDur = currentBeat
    ? (currentBeat.planned_duration || Math.max(0.5, currentBeat.end - currentBeat.start))
    : 2.5;
  const selectedTrimDur = Math.max(0, trimEnd - trimStart);
  const isCurrentBeatPinned = Boolean(shotPins[selectedBeatIdx]);

  // Scenes of active video (robust multi-key matching)
  const activeCatalog = useMemo(() => {
    if (!activeVideoPath) return null;
    const cleanActive = normalizePath(activeVideoPath);
    if (sceneCatalogs[cleanActive]) return sceneCatalogs[cleanActive];
    if (sceneCatalogs[activeVideoPath]) return sceneCatalogs[activeVideoPath];
    const foundKey = Object.keys(sceneCatalogs).find(
      (k) => isSameVideo(k, activeVideoPath) || getFileName(k).toLowerCase() === getFileName(activeVideoPath).toLowerCase()
    );
    return foundKey ? sceneCatalogs[foundKey] : null;
  }, [sceneCatalogs, activeVideoPath]);

  const allScenes = activeCatalog?.scenes || [];
  const filteredScenes = useMemo(() => {
    if (selectedCategoryFilter === 'all') return allScenes;
    return allScenes.filter((s) => s.action_type === selectedCategoryFilter);
  }, [allScenes, selectedCategoryFilter]);

  // Handle video dropdown change
  const handleVideoChange = (newVid) => {
    const clean = normalizePath(newVid);
    setActiveVideoPath(clean);
    setTrimStart(0);
    setTrimEnd(Math.round(currentBeatTargetDur * 10) / 10);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
    }
  };

  // Handle selecting a scene from catalog
  const handleSelectScene = (scene) => {
    const sStart = Math.max(0, Number(scene.start) || 0);
    const sEnd = Math.max(sStart + 0.5, Number(scene.end) || (sStart + currentBeatTargetDur));
    const idealEnd = Math.min(sEnd, sStart + currentBeatTargetDur);

    setTrimStart(Math.round(sStart * 10) / 10);
    setTrimEnd(Math.round(idealEnd * 10) / 10);

    if (videoRef.current) {
      videoRef.current.currentTime = sStart;
    }
  };

  // Lock current trim to the active beat (or replace existing pin)
  const handleLockCurrentBeat = () => {
    if (!activeVideoPath) return;
    const s = Math.max(0, trimStart);
    const e = Math.max(s + 0.2, trimEnd);
    const cleanVid = normalizePath(activeVideoPath);

    setShotPins((prev) => ({
      ...prev,
      [selectedBeatIdx]: {
        beat_index: selectedBeatIdx,
        video_path: cleanVid,
        trim_start: Math.round(s * 100) / 100,
        trim_end: Math.round(e * 100) / 100,
      },
    }));

    // Auto-advance to next beat if available
    if (selectedBeatIdx < beatCues.length - 1) {
      setSelectedBeatIdx((idx) => idx + 1);
    }
  };

  // Unlock beat
  const handleUnlockBeat = (idx) => {
    setShotPins((prev) => {
      const next = { ...prev };
      delete next[idx];
      return next;
    });
    if (idx === selectedBeatIdx) {
      const beat = beatCues[idx];
      const targetDur = beat ? (beat.planned_duration || Math.max(0.5, beat.end - beat.start)) : 2.5;
      setTrimStart(0);
      setTrimEnd(Math.round(targetDur * 10) / 10);
      if (videoRef.current) {
        videoRef.current.currentTime = 0;
      }
    }
  };

  // Clear all pins
  const handleClearAllPins = () => {
    setShotPins({});
  };

  // Snap trimmer to beat duration
  const handleSnapToBeatDur = () => {
    const s = trimStart;
    const nextEnd = Math.min(videoDuration || 9999, s + currentBeatTargetDur);
    setTrimEnd(Math.round(nextEnd * 10) / 10);
  };

  // Video timeupdate handler to loop preview within [trimStart, trimEnd]
  const handleTimeUpdate = () => {
    const v = videoRef.current;
    if (!v) return;
    setCurrentTime(v.currentTime);
    if (v.currentTime >= trimEnd) {
      v.pause();
      setIsPlaying(false);
      v.currentTime = trimStart;
    }
  };

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (isPlaying) {
      v.pause();
      setIsPlaying(false);
    } else {
      if (v.currentTime < trimStart || v.currentTime >= trimEnd) {
        v.currentTime = trimStart;
      }
      v.play()
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false));
    }
  };

  // Save manual shot map
  const handleSave = async () => {
    if (!productId || !angleId) return;
    setSaving(true);
    setError(null);
    try {
      const pinArray = Object.values(shotPins).map((p) => ({
        beat_index: Number(p.beat_index),
        video_path: normalizePath(p.video_path),
        trim_start: Number(p.trim_start),
        trim_end: Number(p.trim_end),
      }));

      await saveManualShotMap(productId, angleId, pinArray);
      setSaveToast(`บันทึกแผนช็อตเรียบร้อยแล้ว (${pinArray.length} วรรค)`);
      setTimeout(() => setSaveToast(null), 3500);

      onSaveSuccess?.(pinArray);
    } catch (err) {
      setError(err.friendlyMessage || err.message || 'บันทึกแผนช็อตไม่สำเร็จ');
    } finally {
      setSaving(false);
    }
  };

  const pinnedCount = Object.keys(shotPins).length;
  const totalBeats = beatCues.length;

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2 text-white">
          <Scissors className="w-5 h-5 text-[#25F4EE]" />
          <span>วางแผนช็อตด้วยตนเอง (Manual Storyboard Mapper)</span>
        </div>
      }
      subtitle={
        angle?.angle_name
          ? `มุม: ${angle.angle_name} — ล็อกช็อตวิดีโอรายวรรคบทพูดด้วยความยาวเสียงจริง`
          : 'กำหนดช่วงเวลาวิดีโอรายวรรคบทพูด'
      }
      maxWidth="max-w-6xl"
    >
      <div className="space-y-4 p-1">
        {/* Loading state */}
        {loading && (
          <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
            <RefreshCw className="w-8 h-8 animate-spin text-[#25F4EE]" />
            <p className="text-sm font-medium">กำลังโหลดข้อมูลบทพูดและสารบัญฉาก...</p>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="p-3 bg-rose-500/15 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Save success toast */}
        {saveToast && (
          <div className="p-3 bg-emerald-500/15 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs flex items-center gap-2 font-bold animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-400" />
            <span>{saveToast}</span>
          </div>
        )}

        {/* Not loaded / No shot list state */}
        {!loading && !hasShotList && (
          <div className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/10 via-slate-900/60 to-slate-900/40 border border-amber-500/30 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center mx-auto text-amber-300">
              <Clock className="w-6 h-6" />
            </div>
            <div className="max-w-md mx-auto space-y-1.5">
              <h3 className="text-base font-bold text-white">ยังไม่มีข้อมูลเวลาเสียงพากย์จริง (TTS Beat Cues)</h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                ระบบจำเป็นต้องสร้างเสียงพากย์จริงก่อน เพื่อให้ได้ความยาววินาทีที่แน่นอน 100% ของแต่ละวรรคบทพูด
                ช่วยให้คุณเลือกช่วงตัดต่อได้พอดีกับเสียง ไม่หลุดจังหวะ
              </p>
            </div>
            <div className="pt-2 flex justify-center gap-3">
              <Button
                variant="primary"
                onClick={() => {
                  onClose();
                  onOpenVoiceGen?.();
                }}
              >
                สร้างเสียงพากย์ทันที
              </Button>
              <Button variant="ghost" onClick={onClose}>
                ปิดหน้าต่าง
              </Button>
            </div>
          </div>
        )}

        {/* Main Content Layout (2-Panel) */}
        {!loading && hasShotList && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* ── LEFT PANEL: Beat Cues List (5 cols) ── */}
            <div className="lg:col-span-5 flex flex-col space-y-2.5 max-h-[640px] overflow-hidden">
              <div className="flex items-center justify-between pb-1 border-b border-white/[0.08]">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
                  <Film className="w-3.5 h-3.5 text-[#25F4EE]" />
                  <span>วรรคบทพูด ({beatCues.length} วรรค / รวม {totalDuration.toFixed(1)}s)</span>
                </div>
                <span className="text-[11px] text-cyan-300 font-bold">
                  ล็อกแล้ว {pinnedCount}/{totalBeats}
                </span>
              </div>

              {/* Scrollable list of beats */}
              <div className="overflow-y-auto space-y-2 pr-1 custom-scrollbar flex-1">
                {beatCues.map((beat, idx) => {
                  const isSelected = idx === selectedBeatIdx;
                  const pin = shotPins[idx];
                  const dur = beat.planned_duration || Math.max(0.5, beat.end - beat.start);
                  const role = ROLE_BADGES[beat.role] || { label: 'Body', color: 'bg-slate-500/20 text-slate-300 border-slate-500/30' };

                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedBeatIdx(idx)}
                      className={`p-3 rounded-xl border transition-all cursor-pointer text-left ${
                        isSelected
                          ? 'bg-[#25F4EE]/10 border-[#25F4EE] ring-1 ring-[#25F4EE]/50 shadow-md'
                          : 'bg-white/[0.03] hover:bg-white/[0.06] border-white/[0.08]'
                      }`}
                    >
                      {/* Beat Header: Badge & Role & Timing */}
                      <div className="flex items-center justify-between gap-1.5 mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                            isSelected ? 'bg-[#25F4EE] text-black' : 'bg-white/10 text-white'
                          }`}>
                            วรรค {idx + 1}
                          </span>
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${role.color}`}>
                            {role.label}
                          </span>
                        </div>
                        <span className="text-[11px] text-amber-300 font-mono font-bold">
                          {dur.toFixed(1)}s ({beat.start.toFixed(1)}s - {beat.end.toFixed(1)}s)
                        </span>
                      </div>

                      {/* Script text */}
                      <p className="text-xs text-slate-200 line-clamp-2 leading-snug mb-2 font-medium">
                        {beat.text || '(ไม่มีข้อความ)'}
                      </p>

                      {/* Assignment status */}
                      <div className="flex items-center justify-between gap-1 pt-1.5 border-t border-white/[0.05]">
                        {pin ? (
                          <div className="flex items-center justify-between w-full">
                            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-300 font-bold bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded">
                              <Lock className="w-2.5 h-2.5 text-emerald-400 flex-shrink-0" />
                              <span className="truncate max-w-[130px]">{getFileName(pin.video_path)}</span>
                              <span className="font-mono text-emerald-200">[{pin.trim_start.toFixed(1)}-{pin.trim_end.toFixed(1)}s]</span>
                            </span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleUnlockBeat(idx);
                              }}
                              className="text-[10px] text-slate-400 hover:text-rose-300 underline cursor-pointer ml-2"
                            >
                              ปลดล็อก
                            </button>
                          </div>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] text-slate-400 bg-white/[0.04] border border-white/[0.08] px-2 py-0.5 rounded">
                            <Sparkles className="w-2.5 h-2.5 text-cyan-400" />
                            <span>AI เลือกให้อัตโนมัติ</span>
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── RIGHT PANEL: Scene Catalog & Trimmer (7 cols) ── */}
            <div className="lg:col-span-7 flex flex-col space-y-3">
              {/* Video Selector Dropdown / Tabs */}
              <div className="p-3 bg-white/[0.03] border border-white/[0.08] rounded-xl flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Video className="w-4 h-4 text-cyan-300 flex-shrink-0" />
                  <span className="text-xs font-bold text-white flex-shrink-0">คลิปดิบ:</span>
                  <select
                    value={activeVideoPath}
                    onChange={(e) => handleVideoChange(e.target.value)}
                    className="bg-black/60 border border-white/[0.15] text-xs text-cyan-200 rounded-lg px-2.5 py-1 focus:outline-none focus:border-[#25F4EE] max-w-[240px] truncate cursor-pointer font-medium"
                  >
                    {availableVideos.map((v) => (
                      <option key={v} value={v}>
                        {getFileName(v)}
                      </option>
                    ))}
                  </select>
                </div>

                {activeCatalog?.is_spin_footage && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                    <RotateCw className="w-3 h-3" />
                    <span>หมุน 360</span>
                  </span>
                )}
              </div>

              {/* Scene Catalog Gallery */}
              <div className="p-3 bg-white/[0.02] border border-white/[0.08] rounded-xl space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-white">
                    <Eye className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>สารบัญฉาก AI ({allScenes.length} ฉาก)</span>
                  </div>

                  {/* Filter tabs */}
                  <div className="flex items-center gap-1 overflow-x-auto">
                    <button
                      type="button"
                      onClick={() => setSelectedCategoryFilter('all')}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition-all ${
                        selectedCategoryFilter === 'all'
                          ? 'bg-[#25F4EE] text-black font-extrabold'
                          : 'bg-white/[0.06] text-slate-400 hover:text-white'
                      }`}
                    >
                      ทั้งหมด
                    </button>
                    {Object.keys(ACTION_MAP).map((act) => (
                      <button
                        key={act}
                        type="button"
                        onClick={() => setSelectedCategoryFilter(act)}
                        className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer whitespace-nowrap transition-all ${
                          selectedCategoryFilter === act
                            ? 'bg-cyan-500 text-black font-extrabold'
                            : 'bg-white/[0.06] text-slate-400 hover:text-white'
                        }`}
                      >
                        {ACTION_MAP[act].label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Scene Cards Carousel / Grid */}
                {filteredScenes.length > 0 ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-[190px] overflow-y-auto pr-1 custom-scrollbar">
                    {filteredScenes.map((scene, sIdx) => {
                      const sDur = Math.max(0, (scene.end || 0) - (scene.start || 0));
                      const actionInfo = ACTION_MAP[scene.action_type] || {
                        label: scene.action_type || 'ฉากทั่วไป',
                        color: 'bg-slate-500/20 text-slate-300 border-slate-500/40',
                      };

                      return (
                        <div
                          key={sIdx}
                          onClick={() => handleSelectScene(scene)}
                          className="p-2 rounded-lg bg-black/40 hover:bg-[#25F4EE]/10 border border-white/[0.08] hover:border-[#25F4EE]/60 transition-all cursor-pointer text-left flex flex-col justify-between group"
                        >
                          <div>
                            <div className="flex items-center justify-between gap-1 mb-1">
                              <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border truncate ${actionInfo.color}`}>
                                {actionInfo.label}
                              </span>
                              <span className="text-[9px] font-mono text-cyan-300 font-bold">
                                {sDur.toFixed(1)}s
                              </span>
                            </div>
                            <p className="text-[10px] text-slate-300 line-clamp-2 leading-tight">
                              {scene.visual_focus || scene.summary || `ฉาก ${sIdx + 1}`}
                            </p>
                          </div>

                          <div className="flex items-center justify-between pt-1.5 mt-1 border-t border-white/[0.05] text-[9px] text-slate-400 font-mono">
                            <span>{formatTimecode(scene.start)}</span>
                            <span className="text-[#25F4EE] opacity-0 group-hover:opacity-100 font-bold transition-opacity">
                              เลือกฉากนี้ ➔
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="py-6 text-center text-xs text-slate-400 bg-black/20 rounded-lg border border-dashed border-white/[0.08]">
                    {allScenes.length === 0
                      ? 'ยังไม่ได้สแกนสารบัญฉาก AI สำหรับคลิปนี้ แต่คุณสามารถเลื่อนแถบตัดต่อด้านล่างได้โดยตรง'
                      : 'ไม่พบฉากในหมวดหมู่ที่เลือก'}
                  </div>
                )}
              </div>

              {/* ── TRIM SCRUBBER & FINE TUNER ── */}
              <div className="p-3 bg-black/50 border border-white/[0.12] rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-[#25F4EE]" />
                    <span className="text-xs font-bold text-white">
                      ปรับช่วงตัดสำหรับวรรคที่ {selectedBeatIdx + 1}
                    </span>
                  </div>

                  {/* Target duration comparison gauge */}
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-400">
                      ต้องการ: <b className="text-amber-300 font-mono">{currentBeatTargetDur.toFixed(1)}s</b>
                    </span>
                    <span className="text-[11px] text-slate-400">|</span>
                    <span className="text-[11px] text-slate-400">
                      เลือกไว้: <b className={`font-mono ${
                        Math.abs(selectedTrimDur - currentBeatTargetDur) <= 0.3
                          ? 'text-emerald-400'
                          : selectedTrimDur > currentBeatTargetDur
                            ? 'text-cyan-300'
                            : 'text-amber-400'
                      }`}>
                        {selectedTrimDur.toFixed(1)}s
                      </b>
                    </span>
                    <button
                      type="button"
                      onClick={handleSnapToBeatDur}
                      className="px-2 py-0.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-[10px] font-bold cursor-pointer transition-all"
                      title="ปรับความยาวช่วงตัดให้พอดีกับความยาววรรคบทพูด"
                    >
                      พอดีวรรค
                    </button>
                  </div>
                </div>

                {/* Video Player Preview */}
                {activeVideoPath && (
                  <div className="relative rounded-lg overflow-hidden bg-black aspect-video max-h-[180px] flex items-center justify-center border border-white/[0.08]">
                    <video
                      key={activeVideoPath}
                      ref={videoRef}
                      src={toMediaUrl(activeVideoPath)}
                      className="w-full h-full object-contain"
                      onTimeUpdate={handleTimeUpdate}
                      onClick={togglePlay}
                    />

                    {/* Play/pause overlay button */}
                    <button
                      type="button"
                      onClick={togglePlay}
                      className="absolute inset-0 m-auto w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center border border-white/20 transition-all opacity-80 hover:opacity-100 cursor-pointer shadow-lg"
                    >
                      {isPlaying ? <Pause className="w-5 h-5 text-[#25F4EE]" /> : <Play className="w-5 h-5 ml-0.5 text-white" />}
                    </button>

                    {/* Timecode overlay */}
                    <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/70 text-[10px] font-mono text-cyan-300 border border-white/10">
                      {formatTimecode(currentTime)} / {formatTimecode(videoDuration)}
                    </div>
                  </div>
                )}

                {/* Time Range Inputs & Sliders */}
                <div className="space-y-2 pt-1">
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    {/* Start Input */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] text-slate-300">
                        <span>จุดเริ่ม (วินาที):</span>
                        <span className="font-mono text-cyan-300">{formatTimecode(trimStart)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max={Math.max(0, trimEnd - 0.2)}
                          value={trimStart}
                          onChange={(e) => {
                            const val = Math.max(0, Math.min(Number(e.target.value) || 0, trimEnd - 0.2));
                            setTrimStart(val);
                            if (videoRef.current) videoRef.current.currentTime = val;
                          }}
                          className="w-full bg-black/60 border border-white/[0.15] text-cyan-200 rounded px-2 py-1 font-mono text-xs focus:outline-none focus:border-[#25F4EE]"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const val = Math.max(0, trimStart - 0.5);
                            setTrimStart(val);
                            if (videoRef.current) videoRef.current.currentTime = val;
                          }}
                          className="px-2 py-1 rounded bg-white/[0.08] hover:bg-white/[0.15] text-[10px] text-white font-mono cursor-pointer"
                        >
                          -0.5s
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            const val = Math.min(trimEnd - 0.2, trimStart + 0.5);
                            setTrimStart(val);
                            if (videoRef.current) videoRef.current.currentTime = val;
                          }}
                          className="px-2 py-1 rounded bg-white/[0.08] hover:bg-white/[0.15] text-[10px] text-white font-mono cursor-pointer"
                        >
                          +0.5s
                        </button>
                      </div>
                    </div>

                    {/* End Input */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] text-slate-300">
                        <span>จุดจบ (วินาที):</span>
                        <span className="font-mono text-cyan-300">{formatTimecode(trimEnd)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          step="0.1"
                          min={trimStart + 0.2}
                          max={videoDuration || 9999}
                          value={trimEnd}
                          onChange={(e) => {
                            const val = Math.max(trimStart + 0.2, Number(e.target.value) || (trimStart + 0.2));
                            setTrimEnd(val);
                          }}
                          className="w-full bg-black/60 border border-white/[0.15] text-cyan-200 rounded px-2 py-1 font-mono text-xs focus:outline-none focus:border-[#25F4EE]"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const val = Math.max(trimStart + 0.2, trimEnd - 0.5);
                            setTrimEnd(val);
                          }}
                          className="px-2 py-1 rounded bg-white/[0.08] hover:bg-white/[0.15] text-[10px] text-white font-mono cursor-pointer"
                        >
                          -0.5s
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            const val = Math.min(videoDuration || 9999, trimEnd + 0.5);
                            setTrimEnd(val);
                          }}
                          className="px-2 py-1 rounded bg-white/[0.08] hover:bg-white/[0.15] text-[10px] text-white font-mono cursor-pointer"
                        >
                          +0.5s
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Lock / Update & Unlock button */}
                  <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.08]">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">
                        {isCurrentBeatPinned
                          ? 'วรรคนี้ถูกล็อกช็อตอยู่ — ปรับเปลี่ยนช่วงเวลาแล้วกดปุ่มเพื่ออัปเดต'
                          : 'เมื่อปรับเสร็จแล้ว กดปุ่มเพื่อยืนยันการล็อกช็อตนี้'}
                      </span>
                      {isCurrentBeatPinned && (
                        <button
                          type="button"
                          onClick={() => handleUnlockBeat(selectedBeatIdx)}
                          className="px-2.5 py-1 rounded-md bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 font-bold text-[11px] flex items-center gap-1 transition-all cursor-pointer"
                          title="ปลดล็อกวรรคนี้เพื่อให้ AI เลือกช็อตให้อัตโนมัติ"
                        >
                          <Unlock className="w-3 h-3" />
                          <span>ปลดล็อกวรรคนี้</span>
                        </button>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={handleLockCurrentBeat}
                      className="px-3.5 py-1.5 rounded-lg bg-[#25F4EE] hover:bg-[#20ded8] text-black font-extrabold text-xs shadow-md shadow-cyan-500/20 flex items-center gap-1.5 transition-all cursor-pointer active:scale-95"
                    >
                      <Lock className="w-3.5 h-3.5" />
                      <span>
                        {isCurrentBeatPinned
                          ? `อัปเดตช็อตวรรคที่ ${selectedBeatIdx + 1}`
                          : `ล็อกช็อตวรรคที่ ${selectedBeatIdx + 1}`}
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── MODAL FOOTER ── */}
        <div className="pt-3 border-t border-white/[0.08] flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-slate-400">
            {pinnedCount > 0 ? (
              <span className="text-cyan-300 font-bold">
                📌 กำหนดด้วยตนเอง {pinnedCount} วรรค (อีก {Math.max(0, totalBeats - pinnedCount)} วรรค AI จะจัดหาให้อัตโนมัติ)
              </span>
            ) : (
              <span>ยังไม่ได้ล็อกช็อตใด (AI จะตัดต่อให้อัตโนมัติทั้งหมด)</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {pinnedCount > 0 && (
              <Button variant="ghost" onClick={handleClearAllPins}>
                ล้างการล็อกทั้งหมด
              </Button>
            )}
            <Button variant="ghost" onClick={onClose}>
              ปิดหน้าต่าง
            </Button>
            <Button
              variant="primary"
              onClick={handleSave}
              loading={saving}
              disabled={!hasShotList || saving}
            >
              บันทึกแผนช็อต
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
