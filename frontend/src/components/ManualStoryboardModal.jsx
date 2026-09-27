import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  Film, Sparkles, Clock, Lock, Unlock, Play, Pause, RotateCcw,
  AlertTriangle, ChevronRight, Video, Scissors, CheckCircle2, RotateCw,
  Eye, RefreshCw, X, Sliders, Check, Share2, FastForward, Image as ImageIcon,
  ZoomIn, ZoomOut, Maximize2, Move, Compass, ArrowLeft, ArrowRight
} from 'lucide-react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { toMediaUrl, isSameVideo } from '../lib/mediaUrl';
import { formatTimecode } from '../lib/timelineMath';
import { getManualShotMap, saveManualShotMap, syncManualShotMap, getMediaInfo } from '../api';

// ── In-Memory Thumbnail Cache for Scene Thumbnails ──────────────────────
const sceneThumbnailCache = new Map();
const MAX_CONCURRENT_CAPTURES = 2;
let activeCapturesCount = 0;
const captureQueue = [];

function processCaptureQueue() {
  while (activeCapturesCount < MAX_CONCURRENT_CAPTURES && captureQueue.length > 0) {
    const task = captureQueue.shift();
    if (task) {
      activeCapturesCount++;
      let finished = false;
      const done = () => {
        if (!finished) {
          finished = true;
          activeCapturesCount = Math.max(0, activeCapturesCount - 1);
          processCaptureQueue();
        }
      };
      try {
        task(done);
      } catch (_) {
        done();
      }
    }
  }
}

function requestSceneThumbnail(task) {
  captureQueue.push(task);
  processCaptureQueue();
}

/**
 * SceneThumbnail: renders a lightweight frame preview of the video at scene.start
 */
const SceneThumbnail = React.memo(function SceneThumbnail({ videoPath, startTime, isHovered, hoverProgress }) {
  const cacheKey = `${videoPath}#${Math.round(startTime * 2) / 2}`;
  const [thumbSrc, setThumbSrc] = useState(sceneThumbnailCache.get(cacheKey) || null);
  const [isCapturing, setIsCapturing] = useState(false);
  const containerRef = useRef(null);
  const videoRef = useRef(null);
  const hoverVideoRef = useRef(null);
  const releaseCaptureRef = useRef(null);

  const finishCapture = useCallback(() => {
    if (releaseCaptureRef.current) {
      releaseCaptureRef.current();
      releaseCaptureRef.current = null;
    }
    setIsCapturing(false);
  }, []);

  useEffect(() => {
    if (thumbSrc || !videoPath) return;
    let isMounted = true;
    let timeoutId = null;

    requestSceneThumbnail((done) => {
      if (!isMounted) {
        done();
        return;
      }
      releaseCaptureRef.current = done;
      setIsCapturing(true);

      // Safety timeout: release queue slot after 4 seconds even if video stalls
      timeoutId = setTimeout(() => {
        if (isMounted) {
          finishCapture();
        }
      }, 4000);
    });

    return () => {
      isMounted = false;
      if (timeoutId) clearTimeout(timeoutId);
      if (releaseCaptureRef.current) {
        releaseCaptureRef.current();
        releaseCaptureRef.current = null;
      }
    };
  }, [videoPath, startTime, thumbSrc, finishCapture]);

  const handleCaptureLoaded = useCallback(() => {
    const v = videoRef.current;
    if (!v || !v.videoWidth || !v.videoHeight) {
      finishCapture();
      return;
    }
    try {
      const canvas = document.createElement('canvas');
      const w = 108;
      const h = 192; // 9:16 portrait thumbnail
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(v, 0, 0, w, h);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.65);
        if (dataUrl && dataUrl.length > 100) {
          sceneThumbnailCache.set(cacheKey, dataUrl);
          setThumbSrc(dataUrl);
        }
      }
    } catch (_) {
      // Ignore cross-origin fallback
    } finally {
      finishCapture();
    }
  }, [cacheKey, finishCapture]);

  const handleCaptureError = useCallback(() => {
    finishCapture();
  }, [finishCapture]);

  return (
    <div ref={containerRef} className="relative w-full h-full overflow-hidden bg-black flex items-center justify-center">
      {/* Live hover scrubbing video layer */}
      {isHovered ? (
        <video
          ref={hoverVideoRef}
          src={`${toMediaUrl(videoPath)}#t=${(startTime + (hoverProgress || 0)).toFixed(1)}`}
          preload="auto"
          muted
          playsInline
          className="w-full h-full object-cover pointer-events-none"
        />
      ) : thumbSrc ? (
        <img
          src={thumbSrc}
          alt=""
          loading="lazy"
          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105 pointer-events-none"
        />
      ) : isCapturing ? (
        <>
          <video
            ref={videoRef}
            src={`${toMediaUrl(videoPath)}#t=${Math.max(0.1, Number(startTime) || 0).toFixed(1)}`}
            preload="metadata"
            muted
            playsInline
            onLoadedData={handleCaptureLoaded}
            onSeeked={handleCaptureLoaded}
            onError={handleCaptureError}
            className="hidden"
          />
          <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        </>
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-slate-900/60 text-slate-600">
          <ImageIcon className="w-5 h-5 opacity-40" />
        </div>
      )}
    </div>
  );
});

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

  // Timeline Zoom & Pan state (1x to 8x, defaults to 8x for high precision)
  const [zoomLevel, setZoomLevel] = useState(8);
  const [panOffset, setPanOffset] = useState(0); // Viewport start time in seconds

  const [hoveredSceneIdx, setHoveredSceneIdx] = useState(null);
  const [hoverProgress, setHoverProgress] = useState(0);

  const videoRef = useRef(null);
  const angleId = angle?.angle_id || angle?.id;

  // Sync across all angles state
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [selectedSyncAngleIds, setSelectedSyncAngleIds] = useState(new Set());
  const [syncOverwritePolicy, setSyncOverwritePolicy] = useState('overwrite_all');
  const [syncing, setSyncing] = useState(false);


  // Load data whenever modal opens
  useEffect(() => {
    if (!isOpen || !productId || !angleId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setSaveToast(null);

    getManualShotMap(productId, angleId, angle?.batch || 1)
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

  // Available videos list (Strict Deduplication by filename/identity)
  const availableVideos = useMemo(() => {
    const list = [];
    const seenNames = new Set();
    const seenPaths = new Set();

    const addPath = (p) => {
      if (!p) return;
      const clean = typeof p === 'string' ? normalizePath(p) : normalizePath(p.rel_path || p.path || '');
      if (!clean) return;

      const fileName = getFileName(clean).toLowerCase();
      const normPath = clean.toLowerCase();

      // Skip if already in list by exact path or filename
      if (seenPaths.has(normPath) || seenNames.has(fileName)) return;

      // Also double check with isSameVideo against existing entries
      if (list.some((existing) => isSameVideo(existing, clean))) return;

      seenPaths.add(normPath);
      seenNames.add(fileName);
      list.push(clean);
    };

    (angle?.selected_videos || []).forEach(addPath);
    if (angle?.selected_video) addPath(angle.selected_video);
    (product?.videos || []).forEach(addPath);
    Object.keys(sceneCatalogs).forEach(addPath);
    Object.values(shotPins).forEach((pin) => {
      if (pin.video_path) addPath(pin.video_path);
    });

    return list;
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

  // Helper to ensure zoomed viewport centers on a target timestamp
  const panToTime = useCallback((targetTime, dur = videoDuration, zoom = zoomLevel) => {
    if (!dur || zoom <= 1) {
      setPanOffset(0);
      return;
    }
    const viewSpan = dur / zoom;
    const idealPan = Math.max(0, Math.min(dur - viewSpan, targetTime - viewSpan * 0.3));
    setPanOffset(idealPan);
  }, [videoDuration, zoomLevel]);

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
      panToTime(currentPin.trim_start);
    } else {
      setTrimStart(0);
      setTrimEnd(Math.round(targetDur * 10) / 10);
      if (videoRef.current) {
        videoRef.current.currentTime = 0;
      }
      panToTime(0);
    }
  }, [selectedBeatIdx, panToTime]); // Only sync when beat index changes

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
    setPanOffset(0);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
    }
  };

  // Handle selecting a scene from catalog (previews scene in player & auto-pans viewport)
  const handleSelectScene = (scene) => {
    const sStart = Math.max(0, Number(scene.start) || 0);
    const sEnd = Math.max(sStart + 0.5, Number(scene.end) || (sStart + currentBeatTargetDur));
    const idealEnd = Math.min(sEnd, sStart + currentBeatTargetDur);

    setTrimStart(Math.round(sStart * 10) / 10);
    setTrimEnd(Math.round(idealEnd * 10) / 10);

    // Auto-Pan timeline view to ensure selected scene is visible and centered
    panToTime(sStart);

    if (videoRef.current) {
      videoRef.current.currentTime = sStart;
      videoRef.current.play?.().catch(() => {});
      setIsPlaying(true);
    }
  };

  // One-Click Fast Assign: locks scene to current beat with auto-fitted duration and auto-advances
  const handleQuickAssignScene = (scene, e) => {
    e?.stopPropagation?.();
    if (!activeVideoPath) return;

    const sStart = Math.max(0, Number(scene.start) || 0);
    const sEnd = Math.max(sStart + 0.5, Number(scene.end) || (sStart + currentBeatTargetDur));
    const idealEnd = Math.min(sEnd, sStart + currentBeatTargetDur);
    const cleanVid = normalizePath(activeVideoPath);

    const roundedStart = Math.round(sStart * 100) / 100;
    const roundedEnd = Math.round(idealEnd * 100) / 100;

    // 1. Lock shot to current beat
    setShotPins((prev) => ({
      ...prev,
      [selectedBeatIdx]: {
        beat_index: selectedBeatIdx,
        video_path: cleanVid,
        trim_start: roundedStart,
        trim_end: roundedEnd,
      },
    }));

    // 2. Set current trim preview state & pan viewport to scene
    setTrimStart(roundedStart);
    setTrimEnd(roundedEnd);
    panToTime(roundedStart);

    if (videoRef.current) {
      videoRef.current.currentTime = roundedStart;
    }

    // 3. Show micro toast
    setSaveToast(`✓ ล็อกช็อตใส่วรรคที่ ${selectedBeatIdx + 1} เรียบร้อยแล้ว`);
    setTimeout(() => setSaveToast(null), 2000);

    // 4. Auto-advance to next beat if available
    if (selectedBeatIdx < beatCues.length - 1) {
      setSelectedBeatIdx((idx) => idx + 1);
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

  // Nudge trim range by deltaSec (used by keyboard arrow keys or buttons)
  const nudgeTrimWindow = useCallback((deltaSec) => {
    if (!videoDuration) return;
    const span = trimEnd - trimStart;
    const newStart = Math.max(0, Math.min(videoDuration - span, trimStart + deltaSec));
    const newEnd = Math.min(videoDuration, newStart + span);
    const roundedStart = Math.round(newStart * 100) / 100;
    const roundedEnd = Math.round(newEnd * 100) / 100;

    setTrimStart(roundedStart);
    setTrimEnd(roundedEnd);
    panToTime(roundedStart);
    if (videoRef.current) {
      videoRef.current.currentTime = roundedStart;
    }
  }, [videoDuration, trimStart, trimEnd, panToTime]);

  // Global keyboard shortcuts for arrow keys when modal is open
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      // Do not trigger if typing in an input or textarea or select
      const activeTag = document.activeElement?.tagName?.toLowerCase();
      if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') return;

      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        // Move by 0.5s (~15 frames at 30fps) by default, or 2.0s (~60 frames) with Shift
        const step = e.shiftKey ? 2.0 : 0.5;
        const dir = e.key === 'ArrowRight' ? 1 : -1;
        nudgeTrimWindow(dir * step);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, nudgeTrimWindow]);

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

      await saveManualShotMap(productId, angleId, pinArray, angle?.batch || 1);
      setSaveToast(`บันทึกแผนช็อตเรียบร้อยแล้ว (${pinArray.length} วรรค)`);
      setTimeout(() => setSaveToast(null), 3500);

      onSaveSuccess?.(pinArray);
    } catch (err) {
      setError(err.friendlyMessage || err.message || 'บันทึกแผนช็อตไม่สำเร็จ');
    } finally {
      setSaving(false);
    }
  };

  const handleOpenSyncModal = () => {
    const currentBatch = angle?.batch || 1;
    const otherIds = (product?.angles || [])
      .filter(a => (a.angle_id || a.id) !== angleId || (a.batch || 1) !== currentBatch)
      .map(a => a.angle_id || a.id);
    setSelectedSyncAngleIds(new Set(otherIds));
    setSyncModalOpen(true);
  };

  const handleToggleSyncAngleId = (targetId) => {
    setSelectedSyncAngleIds(prev => {
      const next = new Set(prev);
      if (next.has(targetId)) next.delete(targetId);
      else next.add(targetId);
      return next;
    });
  };

  const handleSelectAllSyncAngles = () => {
    const currentBatch = angle?.batch || 1;
    const otherIds = (product?.angles || [])
      .filter(a => (a.angle_id || a.id) !== angleId || (a.batch || 1) !== currentBatch)
      .map(a => a.angle_id || a.id);
    setSelectedSyncAngleIds(new Set(otherIds));
  };

  const handleDeselectAllSyncAngles = () => {
    setSelectedSyncAngleIds(new Set());
  };

  const handleConfirmSync = async () => {
    if (!productId || !angleId || selectedSyncAngleIds.size === 0) return;
    setSyncing(true);
    try {
      // Auto-save current pins first
      const pinArray = Object.values(shotPins).map((p) => ({
        beat_index: Number(p.beat_index),
        video_path: normalizePath(p.video_path),
        trim_start: Number(p.trim_start),
        trim_end: Number(p.trim_end),
      }));
      await saveManualShotMap(productId, angleId, pinArray, angle?.batch || 1);

      const payload = {
        target_angle_ids: Array.from(selectedSyncAngleIds),
        overwrite_policy: syncOverwritePolicy,
        batch: angle?.batch || 1,
      };
      const res = await syncManualShotMap(productId, angleId, payload);
      setSyncModalOpen(false);
      onSaveSuccess?.(pinArray);
      setSaveToast(`🎉 ปรับใช้ชุดช็อตนี้กับอีก ${res.synced_count} สคริปต์เรียบร้อยแล้ว!`);
      setTimeout(() => setSaveToast(null), 4000);
    } catch (err) {
      console.error('Failed to sync storyboard:', err);
      setError('ไม่สามารถปรับใช้กับสคริปต์อื่นได้: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSyncing(false);
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
      maxWidth="max-w-7xl"
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

        {/* Main Content Layout (Focused 2-Column Studio Layout: Left Beat Cues 5 cols | Right 9:16 Video Player & Timeline 7 cols) */}
        {!loading && hasShotList && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch min-h-[620px]">
            {/* ── COL 1 (LEFT): Beat Cues List (5 cols) ── */}
            <div className="lg:col-span-5 flex flex-col space-y-3 max-h-[680px] overflow-hidden bg-white/[0.02] p-3.5 rounded-2xl border border-white/[0.08]">
              <div className="flex items-center justify-between pb-2.5 border-b border-white/[0.08]">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                  <Film className="w-4 h-4 text-[#25F4EE]" />
                  <span>วรรคบทพูด ({beatCues.length} วรรค)</span>
                </div>
                <span className="text-xs text-cyan-300 font-extrabold px-2 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-500/30">
                  ล็อกแล้ว {pinnedCount}/{totalBeats}
                </span>
              </div>

              {/* Scrollable list of beats */}
              <div className="overflow-y-auto space-y-2.5 pr-1.5 custom-scrollbar flex-1">
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
                          ? 'bg-[#25F4EE]/10 border-[#25F4EE] ring-1 ring-[#25F4EE]/50 shadow-lg'
                          : 'bg-white/[0.03] hover:bg-white/[0.06] border-white/[0.08]'
                      }`}
                    >
                      {/* Beat Header: Badge & Role & Timing */}
                      <div className="flex items-center justify-between gap-1.5 mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className={`px-2.5 py-0.5 rounded text-[11px] font-extrabold ${
                            isSelected ? 'bg-[#25F4EE] text-black shadow-sm' : 'bg-white/10 text-white'
                          }`}>
                            วรรค {idx + 1}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[9.5px] font-bold border ${role.color}`}>
                            {role.label}
                          </span>
                        </div>
                        <span className="text-xs text-amber-300 font-mono font-extrabold">
                          {dur.toFixed(1)}s
                        </span>
                      </div>

                      {/* Script text */}
                      <p className="text-xs text-slate-200 line-clamp-3 leading-relaxed mb-2.5 font-medium">
                        {beat.text || '(ไม่มีข้อความ)'}
                      </p>

                      {/* Assignment status */}
                      <div className="flex items-center justify-between gap-1 pt-2 border-t border-white/[0.06]">
                        {pin ? (
                          <div className="flex items-center justify-between w-full">
                            <span className="inline-flex items-center gap-1.5 text-[10.5px] text-emerald-300 font-bold bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 rounded-lg truncate max-w-[260px]">
                              <Lock className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                              <span className="truncate">{getFileName(pin.video_path)}</span>
                              <span className="font-mono text-emerald-200 flex-shrink-0">[{pin.trim_start.toFixed(1)}-{pin.trim_end.toFixed(1)}s]</span>
                            </span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleUnlockBeat(idx);
                              }}
                              className="text-[11px] text-slate-400 hover:text-rose-300 underline cursor-pointer ml-1.5 flex-shrink-0 font-medium"
                            >
                              ปลด
                            </button>
                          </div>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-[10.5px] text-slate-400 bg-white/[0.04] border border-white/[0.08] px-2.5 py-0.5 rounded-lg">
                            <Sparkles className="w-3 h-3 text-cyan-400" />
                            <span>AI เลือกให้อัตโนมัติ</span>
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── COL 2 (RIGHT): 9:16 Video Player & Pro Scrubber Studio (7 cols) ── */}
            <div className="lg:col-span-7 flex flex-col space-y-3 bg-black/50 p-4 rounded-2xl border border-white/[0.12] justify-between shadow-2xl">
              {/* Top Controls: Dropdown & Target Duration Gauge */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <Video className="w-4 h-4 text-cyan-300 flex-shrink-0" />
                    <select
                      value={activeVideoPath}
                      onChange={(e) => handleVideoChange(e.target.value)}
                      className="bg-black/70 border border-white/[0.15] text-xs text-cyan-200 rounded-xl px-3 py-1.5 focus:outline-none focus:border-[#25F4EE] w-full truncate cursor-pointer font-medium shadow-inner"
                    >
                      {availableVideos.map((v) => (
                        <option key={v} value={v}>
                          {getFileName(v)}
                        </option>
                      ))}
                    </select>
                  </div>
                  {activeCatalog?.is_spin_footage && (
                    <span className="px-2.5 py-1 rounded-xl text-[10.5px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 flex-shrink-0">
                      <RotateCw className="w-3.5 h-3.5" />
                      <span>360</span>
                    </span>
                  )}
                </div>

                {/* Target Duration vs Selected Trim Bar */}
                <div className="flex items-center justify-between text-xs bg-white/[0.03] px-3 py-1.5 rounded-xl border border-white/[0.07]">
                  <span className="text-slate-300 font-medium">
                    ความยาวที่ต้องการ: <b className="text-amber-300 font-mono font-extrabold ml-1">{currentBeatTargetDur.toFixed(1)}s</b>
                  </span>
                  <div className="flex items-center gap-2.5">
                    <span className="text-slate-300 font-medium">
                      ตัดไว้: <b className={`font-mono font-extrabold ml-1 ${
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
                      className="px-2 py-0.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-[10px] font-extrabold cursor-pointer transition-all active:scale-95 shadow-sm"
                    >
                      ปรับให้พอดี
                    </button>
                  </div>
                </div>
              </div>

              {/* 9:16 Video Player Container (Enlarged True 9:16 Aspect Ratio) */}
              <div className="flex-1 flex items-center justify-center my-1.5">
                {activeVideoPath && (
                  <div className="relative rounded-2xl overflow-hidden bg-black aspect-[9/16] h-[370px] max-h-[390px] border border-white/[0.18] shadow-2xl flex items-center justify-center group/vid">
                    <video
                      key={activeVideoPath}
                      ref={videoRef}
                      src={toMediaUrl(activeVideoPath)}
                      className="w-full h-full object-contain"
                      onTimeUpdate={handleTimeUpdate}
                      onClick={togglePlay}
                    />

                    {/* Play/Pause Button */}
                    <button
                      type="button"
                      onClick={togglePlay}
                      className="absolute inset-0 m-auto w-13 h-13 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center border border-white/20 transition-all opacity-80 group-hover/vid:opacity-100 hover:scale-105 cursor-pointer shadow-2xl active:scale-90 z-10"
                    >
                      {isPlaying ? <Pause className="w-6 h-6 text-[#25F4EE]" /> : <Play className="w-6 h-6 ml-0.5 text-white" />}
                    </button>

                    {/* Timecode overlay */}
                    <div className="absolute bottom-2.5 left-2.5 px-2.5 py-1 rounded-lg bg-black/80 backdrop-blur-md text-[10px] font-mono text-cyan-300 border border-white/10 z-10 font-bold">
                      {formatTimecode(currentTime)} / {formatTimecode(videoDuration)}
                    </div>

                    {/* 9:16 Badge */}
                    <div className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded-lg bg-black/75 backdrop-blur-md text-[9px] font-mono text-slate-300 border border-white/10 z-10 font-semibold">
                      9:16 TikTok
                    </div>
                  </div>
                )}
              </div>

              {/* ── Interactive Scrubber & Trimmer Controls (Expanded Width) ── */}
              <div className="space-y-2.5 pt-2 border-t border-white/[0.08]">
                {/* Zoom & Pan Toolbar */}
                <div className="flex items-center justify-between gap-1 pb-0.5 text-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 font-semibold flex items-center gap-1 text-[11px]">
                      <ZoomIn className="w-3.5 h-3.5 text-[#25F4EE]" />
                      ซูม:
                    </span>
                    {[1, 2, 4, 8].map((z) => (
                      <button
                        key={z}
                        type="button"
                        onClick={() => {
                          setZoomLevel(z);
                          if (z === 1) {
                            setPanOffset(0);
                          } else {
                            const viewSpan = videoDuration / z;
                            const idealStart = Math.max(0, Math.min(videoDuration - viewSpan, trimStart - viewSpan * 0.25));
                            setPanOffset(idealStart);
                          }
                        }}
                        className={`px-2 py-0.5 rounded-lg font-mono font-bold text-[11px] transition-all cursor-pointer ${
                          zoomLevel === z
                            ? 'bg-[#25F4EE] text-black shadow-md'
                            : 'bg-white/[0.08] hover:bg-white/[0.15] text-slate-300'
                        }`}
                      >
                        {z}x
                      </button>
                    ))}
                  </div>

                  <div className="flex items-center gap-1.5">
                    {/* Focus Selection Button */}
                    <button
                      type="button"
                      onClick={() => {
                        if (!videoDuration) return;
                        const selDur = Math.max(0.5, trimEnd - trimStart);
                        const targetZoom = Math.min(8, Math.max(1, Math.round(videoDuration / (selDur * 2))));
                        setZoomLevel(targetZoom);
                        const viewSpan = videoDuration / targetZoom;
                        const center = (trimStart + trimEnd) / 2;
                        const newPan = Math.max(0, Math.min(videoDuration - viewSpan, center - viewSpan / 2));
                        setPanOffset(newPan);
                      }}
                      className="px-2 py-1 rounded-lg bg-white/[0.08] hover:bg-[#25F4EE]/20 hover:text-[#25F4EE] text-slate-300 font-bold text-[11px] transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
                      title="ซูมและโฟกัสตรงช่วงที่กำลังตัดต่อ"
                    >
                      <Maximize2 className="w-3 h-3" />
                      <span>โฟกัสช่วงตัด</span>
                    </button>

                    {zoomLevel > 1 && (
                      <button
                        type="button"
                        onClick={() => {
                          setZoomLevel(1);
                          setPanOffset(0);
                        }}
                        className="px-2 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 font-bold text-[11px] transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
                        title="รีเซ็ตการซูมเป็น 1x (เต็มคลิป)"
                      >
                        <ZoomOut className="w-3 h-3" />
                        <span>รีเซ็ต</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* ── PRO INTEGRATED DUAL-DECK SCRUBBER ── */}
                <div className="space-y-1.5 pt-0.5">
                  {/* Deck 1: Global Navigator (Always shows 100% of video overview + interactive viewport lens) */}
                  {videoDuration > 0 && (
                    <div className="space-y-0.5">
                      <div className="flex items-center justify-between text-[9.5px] text-slate-400 font-mono px-0.5">
                        <span className="flex items-center gap-1 text-slate-400 font-medium">
                          <Compass className="w-3 h-3 text-cyan-400" />
                          <span>ภาพรวมคลิปเต็ม (Navigator)</span>
                        </span>
                        <span className="font-bold">{formatTimecode(videoDuration)}</span>
                      </div>
                      <div
                        className="relative w-full h-4.5 bg-slate-950/90 rounded-lg border border-white/10 overflow-hidden cursor-pointer select-none group/nav"
                        onClick={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          const clickRatio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                          const clickTime = clickRatio * videoDuration;
                          const viewSpan = videoDuration / zoomLevel;
                          const maxPan = Math.max(0, videoDuration - viewSpan);
                          const newPan = Math.max(0, Math.min(maxPan, clickTime - viewSpan / 2));
                          setPanOffset(newPan);
                        }}
                        title="คลิกที่แถบหรือลากกรอบสีขาวเพื่อเลื่อนดูตำแหน่งต่างๆ ในคลิป"
                      >
                        {/* Trim Range Indicator on Navigator */}
                        <div
                          className="absolute top-0 bottom-0 bg-cyan-400/50 pointer-events-none rounded transition-all"
                          style={{
                            left: `${(trimStart / videoDuration) * 100}%`,
                            width: `${Math.max(1, ((trimEnd - trimStart) / videoDuration) * 100)}%`,
                          }}
                        />

                        {/* Current Playhead on Navigator */}
                        <div
                          className="absolute top-0 bottom-0 w-0.5 bg-amber-400 pointer-events-none z-10"
                          style={{ left: `${(currentTime / videoDuration) * 100}%` }}
                        />

                        {/* Viewport Lens Box on Navigator (Draggable Window) */}
                        {zoomLevel > 1 && (
                          <div
                            className="absolute top-0 bottom-0 bg-white/20 border border-white/90 rounded cursor-grab active:cursor-grabbing pointer-events-auto shadow-md shadow-white/20 transition-colors hover:bg-white/30"
                            style={{
                              left: `${(panOffset / videoDuration) * 100}%`,
                              width: `${(1 / zoomLevel) * 100}%`,
                            }}
                            onPointerDown={(e) => {
                              e.stopPropagation();
                              const startX = e.clientX;
                              const initialPan = panOffset;
                              const parentWidth = e.currentTarget.parentElement?.getBoundingClientRect().width || 1;
                              const viewSpan = videoDuration / zoomLevel;
                              const maxPan = Math.max(0, videoDuration - viewSpan);

                              const onPointerMove = (moveEvt) => {
                                const dx = moveEvt.clientX - startX;
                                const dt = (dx / parentWidth) * videoDuration;
                                const newPan = Math.max(0, Math.min(maxPan, initialPan + dt));
                                setPanOffset(newPan);
                              };
                              const onPointerUp = () => {
                                window.removeEventListener('pointermove', onPointerMove);
                                window.removeEventListener('pointerup', onPointerUp);
                              };
                              window.addEventListener('pointermove', onPointerMove);
                              window.addEventListener('pointerup', onPointerUp);
                            }}
                          >
                            <div className="w-full h-full flex items-center justify-center opacity-60">
                              <div className="w-1.5 h-2 bg-white/80 rounded-full" />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Deck 2: Precision Zoomed Timeline Scrubber */}
                  <div
                    className="relative w-full h-11 bg-slate-950 rounded-xl border border-cyan-500/25 hover:border-cyan-500/40 transition-colors overflow-hidden select-none p-1"
                    onWheel={(e) => {
                      if (zoomLevel <= 1 || !videoDuration) return;
                      e.preventDefault();
                      const viewSpan = videoDuration / zoomLevel;
                      const maxPan = Math.max(0, videoDuration - viewSpan);
                      const deltaSec = (e.deltaY > 0 ? 1 : -1) * (viewSpan * 0.08);
                      setPanOffset((p) => Math.max(0, Math.min(maxPan, p + deltaSec)));
                    }}
                  >
                    {(() => {
                      const viewSpan = videoDuration > 0 ? videoDuration / zoomLevel : 1;
                      const maxPan = Math.max(0, videoDuration - viewSpan);
                      const clampedPan = Math.max(0, Math.min(maxPan, panOffset));
                      const viewStart = clampedPan;
                      const viewEnd = clampedPan + viewSpan;

                      const timeToPct = (t) => {
                        if (viewSpan <= 0) return 0;
                        return ((t - viewStart) / viewSpan) * 100;
                      };

                      const trimLeftPct = timeToPct(trimStart);
                      const trimRightPct = timeToPct(trimEnd);
                      const playheadPct = timeToPct(currentTime);

                      return (
                        <div
                          className="relative w-full h-full rounded-lg cursor-pointer overflow-hidden bg-black/60"
                          onClick={(e) => {
                            if (!videoDuration) return;
                            const rect = e.currentTarget.getBoundingClientRect();
                            const clickX = e.clientX - rect.left;
                            const pct = Math.max(0, Math.min(1, clickX / rect.width));
                            const targetTime = viewStart + pct * viewSpan;
                            if (videoRef.current) videoRef.current.currentTime = Math.max(0, Math.min(videoDuration, targetTime));
                          }}
                        >
                          {/* Active Trim Window (Shift Range with Auto-Pan at Boundaries) */}
                          {videoDuration > 0 && (
                            <div
                              className="absolute top-0 bottom-0 bg-gradient-to-r from-cyan-500/40 via-cyan-400/30 to-cyan-500/40 border-y-2 border-cyan-400 cursor-grab active:cursor-grabbing z-20 group/range transition-shadow"
                              style={{
                                left: `${Math.max(0, trimLeftPct)}%`,
                                width: `${Math.max(0.5, Math.min(100, trimRightPct) - Math.max(0, trimLeftPct))}%`,
                              }}
                              title="คลิกลากตรงกลางเพื่อเลื่อนช่วงตัดต่อ (เมื่อลากชนขอบ ไทม์ไลน์จะเลื่อนตามอัตโนมัติ)"
                              onPointerDown={(e) => {
                                e.stopPropagation();
                                const startX = e.clientX;
                                const initialStart = trimStart;
                                const initialEnd = trimEnd;
                                const spanDur = initialEnd - initialStart;
                                const trackEl = e.currentTarget.parentElement;
                                if (!trackEl) return;

                                let currentDx = 0;
                                let animFrameId = null;

                                const updateDrag = () => {
                                  const rect = trackEl.getBoundingClientRect();
                                  const parentWidth = rect.width || 1;
                                  const dt = (currentDx / parentWidth) * viewSpan;
                                  let newStart = Math.max(0, Math.min(videoDuration - spanDur, initialStart + dt));
                                  let newEnd = newStart + spanDur;

                                  // Auto-pan viewport if dragged near or beyond edges
                                  setPanOffset((curPan) => {
                                    let nextPan = curPan;
                                    const edgeMargin = viewSpan * 0.05;
                                    if (newStart < curPan + edgeMargin) {
                                      nextPan = Math.max(0, newStart - edgeMargin);
                                    } else if (newEnd > curPan + viewSpan - edgeMargin) {
                                      nextPan = Math.min(maxPan, newEnd - viewSpan + edgeMargin);
                                    }
                                    return nextPan;
                                  });

                                  setTrimStart(Math.round(newStart * 10) / 10);
                                  setTrimEnd(Math.round(newEnd * 10) / 10);
                                  if (videoRef.current) videoRef.current.currentTime = newStart;
                                };

                                const onPointerMove = (moveEvt) => {
                                  currentDx = moveEvt.clientX - startX;
                                  if (!animFrameId) {
                                    animFrameId = requestAnimationFrame(() => {
                                      updateDrag();
                                      animFrameId = null;
                                    });
                                  }
                                };

                                const onPointerUp = () => {
                                  if (animFrameId) cancelAnimationFrame(animFrameId);
                                  window.removeEventListener('pointermove', onPointerMove);
                                  window.removeEventListener('pointerup', onPointerUp);
                                };

                                window.addEventListener('pointermove', onPointerMove);
                                window.addEventListener('pointerup', onPointerUp);
                              }}
                            >
                              <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-40 group-hover/range:opacity-90 transition-opacity">
                                <Move className="w-3.5 h-3.5 text-cyan-200 drop-shadow" />
                              </div>
                            </div>
                          )}

                          {/* Playhead */}
                          {videoDuration > 0 && playheadPct >= 0 && playheadPct <= 100 && (
                            <div
                              className="absolute top-0 bottom-0 w-0.5 bg-amber-400 shadow-sm shadow-amber-400/80 z-25 pointer-events-none transition-all"
                              style={{ left: `${playheadPct}%` }}
                            />
                          )}

                          {/* Left Trim Handle */}
                          {videoDuration > 0 && trimLeftPct >= -2 && trimLeftPct <= 102 && (
                            <div
                              className="absolute top-0 bottom-0 w-5 -ml-2.5 flex items-center justify-center cursor-ew-resize z-30 group/handle touch-none"
                              style={{ left: `${Math.max(0, Math.min(100, trimLeftPct))}%` }}
                              title="ลากเพื่อปรับเวลาเริ่มต้น"
                              onPointerDown={(e) => {
                                e.stopPropagation();
                                const startX = e.clientX;
                                const initialTrim = trimStart;
                                const trackEl = e.currentTarget.parentElement;
                                if (!trackEl) return;

                                const onPointerMove = (moveEvt) => {
                                  const rect = trackEl.getBoundingClientRect();
                                  const parentWidth = rect.width || 1;
                                  const dx = moveEvt.clientX - startX;
                                  const dt = (dx / parentWidth) * viewSpan;
                                  const newStart = Math.max(0, Math.min(trimEnd - 0.2, initialTrim + dt));

                                  if (newStart < panOffset) {
                                    setPanOffset(Math.max(0, newStart));
                                  }

                                  setTrimStart(Math.round(newStart * 10) / 10);
                                  if (videoRef.current) videoRef.current.currentTime = newStart;
                                };

                                const onPointerUp = () => {
                                  window.removeEventListener('pointermove', onPointerMove);
                                  window.removeEventListener('pointerup', onPointerUp);
                                };

                                window.addEventListener('pointermove', onPointerMove);
                                window.addEventListener('pointerup', onPointerUp);
                              }}
                            >
                              <div className="w-2.5 h-8 bg-[#25F4EE] rounded-sm shadow-lg group-hover/handle:scale-110 transition-transform border border-black/60 flex items-center justify-center">
                                <div className="w-0.5 h-3.5 bg-black/40 rounded-full" />
                              </div>
                            </div>
                          )}

                          {/* Right Trim Handle */}
                          {videoDuration > 0 && trimRightPct >= -2 && trimRightPct <= 102 && (
                            <div
                              className="absolute top-0 bottom-0 w-5 -ml-2.5 flex items-center justify-center cursor-ew-resize z-30 group/handle touch-none"
                              style={{ left: `${Math.max(0, Math.min(100, trimRightPct))}%` }}
                              title="ลากเพื่อปรับเวลาสิ้นสุด"
                              onPointerDown={(e) => {
                                e.stopPropagation();
                                const startX = e.clientX;
                                const initialTrim = trimEnd;
                                const trackEl = e.currentTarget.parentElement;
                                if (!trackEl) return;

                                const onPointerMove = (moveEvt) => {
                                  const rect = trackEl.getBoundingClientRect();
                                  const parentWidth = rect.width || 1;
                                  const dx = moveEvt.clientX - startX;
                                  const dt = (dx / parentWidth) * viewSpan;
                                  const newEnd = Math.max(trimStart + 0.2, Math.min(videoDuration, initialTrim + dt));

                                  if (newEnd > panOffset + viewSpan) {
                                    setPanOffset(Math.min(maxPan, newEnd - viewSpan));
                                  }

                                  setTrimEnd(Math.round(newEnd * 10) / 10);
                                  if (videoRef.current) videoRef.current.currentTime = newEnd;
                                };

                                const onPointerUp = () => {
                                  window.removeEventListener('pointermove', onPointerMove);
                                  window.removeEventListener('pointerup', onPointerUp);
                                };

                                window.addEventListener('pointermove', onPointerMove);
                                window.addEventListener('pointerup', onPointerUp);
                              }}
                            >
                              <div className="w-2.5 h-8 bg-[#25F4EE] rounded-sm shadow-lg group-hover/handle:scale-110 transition-transform border border-black/60 flex items-center justify-center">
                                <div className="w-0.5 h-3.5 bg-black/40 rounded-full" />
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                </div>

                {/* Numeric Fine-tune Row & Lock Button */}
                <div className="flex items-center justify-between gap-2 pt-1 text-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] text-slate-400 font-medium">เริ่ม:</span>
                    <span className="font-mono text-cyan-300 text-xs font-bold">{formatTimecode(trimStart)}</span>
                    <button
                      type="button"
                      onClick={() => {
                        const val = Math.max(0, trimStart - 0.5);
                        setTrimStart(val);
                        if (videoRef.current) videoRef.current.currentTime = val;
                      }}
                      className="px-2 py-0.5 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-[10px] text-white font-mono cursor-pointer transition-all active:scale-95"
                    >
                      -0.5
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        const val = Math.min(trimEnd - 0.2, trimStart + 0.5);
                        setTrimStart(val);
                        if (videoRef.current) videoRef.current.currentTime = val;
                      }}
                      className="px-2 py-0.5 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-[10px] text-white font-mono cursor-pointer transition-all active:scale-95"
                    >
                      +0.5
                    </button>
                  </div>

                  {/* Nudge Entire Range Buttons */}
                  <div className="flex items-center gap-1 bg-white/[0.04] p-1 rounded-xl border border-white/10" title="คีย์ลัด: กด ← หรือ → บนคีย์บอร์ด">
                    <button
                      type="button"
                      onClick={() => nudgeTrimWindow(-0.5)}
                      className="p-1.5 rounded-lg bg-white/[0.08] hover:bg-cyan-500/25 hover:text-cyan-300 text-slate-200 transition-all cursor-pointer flex items-center justify-center active:scale-95 shadow-sm"
                      title="เลื่อนถอยหลัง 0.5s (~15 เฟรม) (คีย์ลัด: ←)"
                    >
                      <ArrowLeft className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => nudgeTrimWindow(0.5)}
                      className="p-1.5 rounded-lg bg-white/[0.08] hover:bg-cyan-500/25 hover:text-cyan-300 text-slate-200 transition-all cursor-pointer flex items-center justify-center active:scale-95 shadow-sm"
                      title="เลื่อนไปข้างหน้า 0.5s (~15 เฟรม) (คีย์ลัด: →)"
                    >
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] text-slate-400 font-medium">จบ:</span>
                    <span className="font-mono text-cyan-300 text-xs font-bold">{formatTimecode(trimEnd)}</span>
                    <button
                      type="button"
                      onClick={() => {
                        const val = Math.max(trimStart + 0.2, trimEnd - 0.5);
                        setTrimEnd(val);
                      }}
                      className="px-2 py-0.5 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-[10px] text-white font-mono cursor-pointer transition-all active:scale-95"
                    >
                      -0.5
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        const val = Math.min(videoDuration || 9999, trimEnd + 0.5);
                        setTrimEnd(val);
                      }}
                      className="px-2 py-0.5 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-[10px] text-white font-mono cursor-pointer transition-all active:scale-95"
                    >
                      +0.5
                    </button>
                  </div>
                </div>

                {/* Lock Action Button */}
                <div className="pt-2.5 flex items-center justify-between gap-2 border-t border-white/[0.08]">
                  {isCurrentBeatPinned ? (
                    <button
                      type="button"
                      onClick={() => handleUnlockBeat(selectedBeatIdx)}
                      className="px-3 py-1.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
                    >
                      <Unlock className="w-3.5 h-3.5" />
                      <span>ปลดล็อกช็อตนี้</span>
                    </button>
                  ) : (
                    <span className="text-xs text-slate-400 font-medium">เลือกช่วงเวลาที่ต้องการ แล้วกดปุ่มยืนยัน</span>
                  )}

                  <button
                    type="button"
                    onClick={handleLockCurrentBeat}
                    className="px-4 py-2 rounded-xl bg-[#25F4EE] hover:bg-[#20ded8] text-black font-black text-xs shadow-lg shadow-cyan-500/25 flex items-center gap-2 transition-all cursor-pointer active:scale-95 ml-auto"
                  >
                    <Lock className="w-4 h-4" />
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
            {pinnedCount > 0 && (
              <button
                type="button"
                onClick={handleOpenSyncModal}
                className="py-1.5 px-3 rounded-xl bg-gradient-to-r from-cyan-600/80 to-blue-600/80 hover:brightness-110 border border-cyan-400/40 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-cyan-500/20 cursor-pointer active:scale-95 transition-all"
                title="คัดลอกและปรับใช้ชุดช็อตนี้กับสคริปต์มุมอื่นๆ ทั้งหมดของสินค้านี้"
              >
                <Share2 className="w-3.5 h-3.5 text-cyan-200" />
                <span>ปรับใช้กับทุกสคริปต์</span>
              </button>
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

        {/* ── SYNC ACROSS ALL ANGLES POPUP MODAL ── */}
        {syncModalOpen && (
          <div
            className="fixed inset-0 z-[90] flex items-center justify-center p-3 sm:p-5 bg-black/85 backdrop-blur-sm animate-in fade-in duration-150"
            onClick={() => setSyncModalOpen(false)}
          >
            <div
              className="relative w-full max-w-xl bg-[#0D121D] border border-cyan-500/30 rounded-2xl shadow-2xl shadow-black/80 overflow-hidden flex flex-col max-h-[85vh]"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.08] bg-[#0E1524]">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center justify-center">
                    <Share2 className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">ปรับใช้ชุดช็อตกับสคริปต์อื่น</h3>
                    <p className="text-[11px] text-slate-400">
                      ต้นทาง: <span className="text-cyan-300 font-semibold">{angle?.angle_name || 'สคริปต์ปัจจุบัน'}</span> ({pinnedCount} ช็อต)
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSyncModalOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 text-xs">
                {/* Policy Notice */}
                <div className="p-3 rounded-xl bg-cyan-950/30 border border-cyan-500/20 text-slate-300 space-y-1 text-[11px] leading-relaxed">
                  <div className="font-bold text-cyan-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Smart Role Mapping</span>
                  </div>
                  <p>
                    ระบบจะแมพช็อตเปิดตัว (Hook) และช็อตปิดท้าย (CTA) ให้ตรงบทบาทเสมอ หากสคริปต์ปลายทางยาวกว่า (เช่น 60 วิ มี 8 วรรค) ระบบจะขยายและสลับวนช็อตกลางพร้อมเลื่อนช่วงตัดไม่ให้ภาพซ้ำจุดเดิม
                  </p>
                </div>

                {/* Overwrite policy */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                    การจัดการสคริปต์ที่เคยจัดช็อตไว้แล้ว:
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setSyncOverwritePolicy('overwrite_all')}
                      className={`p-2.5 rounded-xl border text-left cursor-pointer transition-all ${
                        syncOverwritePolicy === 'overwrite_all'
                          ? 'bg-cyan-500/15 border-cyan-400 text-white shadow-sm'
                          : 'bg-black/30 border-white/10 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <div className="font-bold text-xs text-white">เขียนทับทั้งหมด</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">อัปเดตสคริปต์ที่เลือกให้ใช้ชุดช็อตนี้ใหม่ทั้งหมด</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSyncOverwritePolicy('skip_existing')}
                      className={`p-2.5 rounded-xl border text-left cursor-pointer transition-all ${
                        syncOverwritePolicy === 'skip_existing'
                          ? 'bg-cyan-500/15 border-cyan-400 text-white shadow-sm'
                          : 'bg-black/30 border-white/10 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <div className="font-bold text-xs text-white">ข้ามสคริปต์ที่มีช็อตแล้ว</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">เฉพาะสคริปต์ที่ยังไม่เคยล็อกช็อตเท่านั้น</div>
                    </button>
                  </div>
                </div>

                {/* Target Angle Selector */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      เลือกสคริปต์ปลายทาง ({selectedSyncAngleIds.size}/{(product?.angles || []).length - 1}):
                    </label>
                    <div className="flex items-center gap-2 text-[11px]">
                      <button
                        type="button"
                        onClick={handleSelectAllSyncAngles}
                        className="text-cyan-400 hover:underline cursor-pointer"
                      >
                        เลือกทั้งหมด
                      </button>
                      <span className="text-slate-600">|</span>
                      <button
                        type="button"
                        onClick={handleDeselectAllSyncAngles}
                        className="text-slate-400 hover:underline cursor-pointer"
                      >
                        ยกเลิก
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                    {(product?.angles || [])
                      .filter(a => (a.angle_id || a.id) !== angleId)
                      .map((ang, aIdx) => {
                        const targetId = ang.angle_id || ang.id;
                        const isSelected = selectedSyncAngleIds.has(targetId);
                        const linesCount = (ang.script_lines || []).length;
                        const existingPinsCount = (ang.manual_shot_map || []).length;

                        return (
                          <div
                            key={targetId}
                            onClick={() => handleToggleSyncAngleId(targetId)}
                            className={`p-2.5 rounded-xl border flex items-center justify-between gap-3 cursor-pointer transition-all ${
                              isSelected
                                ? 'bg-cyan-950/20 border-cyan-500/40 text-white'
                                : 'bg-black/20 border-white/[0.06] text-slate-400 hover:border-white/20'
                            }`}
                          >
                            <div className="flex items-center gap-2.5 min-w-0">
                              <div
                                className={`w-4 h-4 rounded flex items-center justify-center border transition-all ${
                                  isSelected
                                    ? 'bg-cyan-500 border-cyan-400 text-black'
                                    : 'border-white/30 bg-black/40'
                                }`}
                              >
                                {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                              </div>
                              <span className="font-bold text-xs truncate">
                                {ang.angle_name || `มุมมองที่ ${aIdx + 1}`}
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 flex-shrink-0 text-[11px]">
                              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                                {linesCount} วรรค
                              </span>
                              {existingPinsCount > 0 && (
                                <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px] font-semibold">
                                  มีแล้ว {existingPinsCount} ช็อต
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="px-5 py-3 border-t border-white/[0.08] bg-[#0E1524] flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setSyncModalOpen(false)}
                  className="py-1.5 px-3 rounded-lg text-slate-400 hover:text-white text-xs font-medium cursor-pointer"
                >
                  ยกเลิก
                </button>
                <button
                  type="button"
                  onClick={handleConfirmSync}
                  disabled={syncing || selectedSyncAngleIds.size === 0}
                  className="py-2 px-5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 hover:brightness-110 disabled:opacity-50 text-black font-black text-xs flex items-center gap-1.5 shadow-md shadow-cyan-500/25 cursor-pointer active:scale-95 transition-all"
                >
                  {syncing ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                      <span>กำลังปรับใช้...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                      <span>ยืนยันปรับใช้ ({selectedSyncAngleIds.size} สคริปต์)</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
