import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Film, Play, Share2, Download, Image as ImageIcon, Copy, Check,
  RefreshCw, CheckSquare, Square, X, AlertTriangle, ChevronLeft,
  ChevronRight, Loader2, CheckCircle2,
} from 'lucide-react';
import api from '../../api.js';
import { toMediaUrl } from '../../lib/mediaUrl.js';
import { getCoverVariant } from '../../lib/coverVariant.js';
import {
  getCachedVideoFile,
  prefetchVideoFile,
  resolveVideoFilename,
  sharePreparedFileSync,
  triggerBrowserDownload,
} from '../../lib/saveToDevice.js';
import { useBackToClose } from '../../hooks/useBackToClose.js';
import { CoverSheet } from './CoverSheet.jsx';

const CLIP_FILTERS = Object.freeze([
  { id: 'ready', label: 'พร้อมโพสต์' },
  { id: 'unbound_cover', label: 'ปกยังไม่ยืนยัน' },
  { id: 'qc_rejected', label: 'QC ปัดตก' },
  { id: 'posted', label: 'โพสต์แล้ว' },
]);

function isClipPosted(item) {
  return Boolean(
    item?.is_posted ||
    item?.export_status === 'posted' ||
    item?.angle_status === 'posted',
  );
}

function isClipQcRejected(item) {
  return Boolean(
    item?.is_qc_rejected ||
    item?.angle_status === 'qc_rejected' ||
    item?.qc_note,
  );
}

function isClipCoverBound(item) {
  return Boolean(
    item?.cover_revision ||
    item?.cover_binding_revision ||
    item?.cover_3x4_path,
  );
}

function filterClipsByTab(clips = [], filterId = 'ready') {
  const list = Array.isArray(clips) ? clips : [];
  return list.filter((item) => {
    if (!item || item.is_duplicate_copy) return false;
    const posted = isClipPosted(item);
    const rejected = isClipQcRejected(item);
    const coverBound = isClipCoverBound(item);

    switch (filterId) {
      case 'posted':
        return posted;
      case 'qc_rejected':
        return !posted && rejected;
      case 'unbound_cover':
        return !posted && !rejected && !coverBound;
      case 'ready':
      default:
        return !posted && !rejected;
    }
  });
}

function clipKey(item, idx = 0) {
  return item?.export_id || item?.rel_path || item?.path || item?.name || `clip-${idx}`;
}

function buildCaptionText(item) {
  const caption = String(item?.tiktok_caption || item?.hook_title || '').trim();
  const hashtags = String(item?.tiktok_hashtags || '').trim();
  if (caption && hashtags) return `${caption}\n\n${hashtags}`;
  return caption || hashtags || '';
}

/**
 * MobileClipLibrary — Mobile-first 3-column WebP clip gallery & vertical viewer (Phase 5.1).
 *
 * Strictly omits any price display (`price_deal` etc. never rendered per Rule 2.1).
 * Zero horizontal overflow at 360px (`overflow-x-hidden`, 3-column grid).
 */
export function MobileClipLibrary({
  initialClips = null,
  refreshTrigger = 0,
  onSelectClipsChange,
}) {
  const [fetchedClips, setFetchedClips] = useState([]);
  const [coverOverrides, setCoverOverrides] = useState({});
  const [loading, setLoading] = useState(!Array.isArray(initialClips));
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('ready');

  // Multi-select state (long-press or toggle button)
  const [multiSelectMode, setMultiSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const longPressTimerRef = useRef(null);

  // Full-screen viewer state
  const [viewerClipId, setViewerClipId] = useState(null);
  const [coverSheetOpen, setCoverSheetOpen] = useState(false);

  // Save/share prefetch state inside viewer
  const [preparedByClip, setPreparedByClip] = useState({});
  const [prefetching, setPrefetching] = useState(false);
  const [prefetchProgress, setPrefetchProgress] = useState(null);
  const [copyFeedback, setCopyFeedback] = useState('');
  const [shareFeedback, setShareFeedback] = useState('');
  const abortControllerRef = useRef(null);

  const fetchClips = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/exports', {
        params: { scope: 'ready', limit: 24, lite: 1 },
      });
      const data = response?.data;
      const items = Array.isArray(data)
        ? data
        : Array.isArray(data?.exports)
          ? data.exports
          : Array.isArray(data?.items)
            ? data.items
            : [];
      setFetchedClips(items);
    } catch (err) {
      setError(err?.friendlyMessage || err?.message || 'โหลดรายการคลิปไม่สำเร็จ');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (Array.isArray(initialClips)) return undefined;
    let cancelled = false;
    Promise.resolve().then(async () => {
      if (cancelled) return;
      await fetchClips();
    });
    return () => {
      cancelled = true;
    };
  }, [initialClips, refreshTrigger, fetchClips]);

  const clips = useMemo(() => {
    const base = Array.isArray(initialClips) ? initialClips : fetchedClips;
    return base.map((item, idx) => {
      const key = clipKey(item, idx);
      return coverOverrides[key] ? { ...item, ...coverOverrides[key] } : item;
    });
  }, [initialClips, fetchedClips, coverOverrides]);

  const filteredClips = useMemo(
    () => filterClipsByTab(clips, activeFilter),
    [clips, activeFilter],
  );

  const countsByFilter = useMemo(() => {
    const counts = {};
    for (const f of CLIP_FILTERS) {
      counts[f.id] = filterClipsByTab(clips, f.id).length;
    }
    return counts;
  }, [clips]);

  const viewerIndex = useMemo(() => {
    if (!viewerClipId) return -1;
    return filteredClips.findIndex((c, idx) => clipKey(c, idx) === viewerClipId);
  }, [filteredClips, viewerClipId]);

  const activeClip = useMemo(() => {
    if (viewerIndex >= 0 && filteredClips[viewerIndex]) {
      return filteredClips[viewerIndex];
    }
    if (!viewerClipId) return null;
    return clips.find((c, idx) => clipKey(c, idx) === viewerClipId) || null;
  }, [filteredClips, viewerIndex, viewerClipId, clips]);

  const activeClipId = activeClip ? clipKey(activeClip) : '';

  const preparedFile = useMemo(() => {
    if (!activeClip) return null;
    if (preparedByClip[activeClipId]) return preparedByClip[activeClipId];
    const rawVideoPath = activeClip.rel_path || activeClip.path || activeClip.video_url || '';
    const mediaUrl = toMediaUrl(rawVideoPath);
    const filename = resolveVideoFilename(mediaUrl, activeClip.name);
    return getCachedVideoFile(mediaUrl, filename);
  }, [activeClip, activeClipId, preparedByClip]);

  const closeViewer = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setViewerClipId(null);
    setPrefetching(false);
    setPrefetchProgress(null);
    setCopyFeedback('');
    setShareFeedback('');
  };

  useBackToClose(Boolean(activeClip && !coverSheetOpen), closeViewer);

  const toggleSelectId = useCallback((id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      onSelectClipsChange?.(Array.from(next));
      return next;
    });
  }, [onSelectClipsChange]);

  const handleToggleMultiSelectMode = () => {
    setMultiSelectMode((prev) => {
      const next = !prev;
      if (!next) {
        setSelectedIds(new Set());
        onSelectClipsChange?.([]);
      }
      return next;
    });
  };

  const clearLongPressTimer = () => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
  };

  const handleCardPointerDown = (id) => {
    clearLongPressTimer();
    longPressTimerRef.current = setTimeout(() => {
      setMultiSelectMode(true);
      toggleSelectId(id);
    }, 450);
  };

  const handleCardClick = (item, idx) => {
    const id = clipKey(item, idx);
    if (multiSelectMode) {
      toggleSelectId(id);
      return;
    }
    setPrefetchProgress(null);
    setCopyFeedback('');
    setShareFeedback('');
    setViewerClipId(id);
  };

  const handlePrepareFile = async () => {
    if (!activeClip || prefetching) return;
    const rawVideoPath = activeClip.rel_path || activeClip.path || activeClip.video_url || '';
    const mediaUrl = toMediaUrl(rawVideoPath);
    if (!mediaUrl) {
      setShareFeedback('ไม่พบลิงก์ไฟล์วิดีโอ');
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setPrefetching(true);
    setShareFeedback('');
    setPrefetchProgress({ loaded: 0, total: 0, percent: 0 });

    try {
      const filename = resolveVideoFilename(mediaUrl, activeClip.name);
      const file = await prefetchVideoFile(mediaUrl, {
        filename,
        signal: controller.signal,
        onProgress: (prog) => setPrefetchProgress(prog),
      });
      setPreparedByClip((prev) => ({ ...prev, [activeClipId]: file }));
      setShareFeedback('เตรียมไฟล์พร้อมแล้ว แตะปุ่มอีกครั้งเพื่อบันทึกหรือแชร์');
    } catch (err) {
      if (err?.name !== 'AbortError') {
        setShareFeedback(err?.message || 'เตรียมไฟล์ไม่สำเร็จ กรุณาลองใหม่');
      }
    } finally {
      setPrefetching(false);
    }
  };

  // CRITICAL: Synchronous handler for iOS Safari user activation when preparedFile is ready
  const handleSharePreparedFile = (e) => {
    e?.stopPropagation();
    if (!activeClip || !preparedFile) return;
    const rawVideoPath = activeClip.rel_path || activeClip.path || activeClip.video_url || '';
    const mediaUrl = toMediaUrl(rawVideoPath);
    const captionText = buildCaptionText(activeClip);

    sharePreparedFileSync(preparedFile, {
      title: activeClip.hook_title || activeClip.product_name || 'คลิปรีวิว',
      text: captionText,
      fallbackDownloadUrl: mediaUrl,
    })
      .then((res) => {
        if (res?.cancelled) return;
        if (res?.method === 'share') {
          setShareFeedback('เปิดเมนูแชร์เรียบร้อย');
        } else {
          setShareFeedback('เริ่มดาวน์โหลดไฟล์ลงเครื่องแล้ว');
        }
      })
      .catch((err) => {
        setShareFeedback(err?.message || 'ไม่สามารถแชร์ไฟล์ได้');
      });
  };

  const handleCopyCaption = async () => {
    if (!activeClip) return;
    const text = buildCaptionText(activeClip);
    if (!text) {
      setCopyFeedback('ไม่มีข้อความแคปชันสำหรับคลิปนี้');
      return;
    }
    try {
      if (!navigator?.clipboard?.writeText) {
        throw new Error('Clipboard API unavailable');
      }
      await navigator.clipboard.writeText(text);
      setCopyFeedback('คัดลอกแคปชันเรียบร้อยแล้ว');
    } catch {
      setCopyFeedback('คัดลอกอัตโนมัติไม่สำเร็จ กรุณาคัดลอกด้วยตนเอง');
    }
  };

  const handleCoverUpdated = useCallback((updatedClip) => {
    const key = clipKey(updatedClip);
    if (!key) return;
    setCoverOverrides((prev) => ({
      ...prev,
      [key]: updatedClip,
    }));
  }, []);

  const stepViewer = (delta) => {
    if (viewerIndex < 0) return;
    const nextIdx = viewerIndex + delta;
    if (nextIdx >= 0 && nextIdx < filteredClips.length) {
      setPrefetchProgress(null);
      setCopyFeedback('');
      setShareFeedback('');
      setViewerClipId(clipKey(filteredClips[nextIdx], nextIdx));
    }
  };

  return (
    <div className="w-full max-w-full overflow-x-hidden bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Action & Filter Bar */}
      <div className="px-3 pt-3 pb-2 space-y-2.5 border-b border-slate-800/80 bg-slate-950/95 sticky top-0 z-20">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Film className="w-5 h-5 text-cyan-400 shrink-0" />
            <h1 className="text-base font-bold text-white truncate">
              คลังคลิปพร้อมโพสต์
            </h1>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={handleToggleMultiSelectMode}
              className={`min-h-11 px-3 inline-flex items-center gap-1.5 rounded-xl text-xs font-medium border transition ${
                multiSelectMode
                  ? 'bg-cyan-500/20 border-cyan-400 text-cyan-200'
                  : 'bg-slate-900 border-slate-800 text-slate-200 hover:bg-slate-800'
              }`}
            >
              {multiSelectMode ? (
                <CheckSquare className="w-4 h-4 text-cyan-400" />
              ) : (
                <Square className="w-4 h-4 text-slate-400" />
              )}
              <span>{multiSelectMode ? `เลือกแล้ว (${selectedIds.size})` : 'เลือกหลายรายการ'}</span>
            </button>

            <button
              type="button"
              onClick={fetchClips}
              disabled={loading}
              aria-label="รีเฟรชคลังคลิป"
              className="min-w-11 min-h-11 inline-flex items-center justify-center rounded-xl bg-slate-900 border border-slate-800 text-slate-200 hover:bg-slate-800 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* 4 Filter Chips (>=44px height, zero horizontal page overflow) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5" role="tablist" aria-label="ตัวกรองคลังคลิป">
          {CLIP_FILTERS.map((filter) => {
            const active = activeFilter === filter.id;
            const count = countsByFilter[filter.id] ?? 0;
            return (
              <button
                key={filter.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setActiveFilter(filter.id)}
                className={`min-h-11 px-2.5 py-1.5 rounded-xl text-xs font-semibold flex items-center justify-between gap-1 border transition ${
                  active
                    ? 'bg-cyan-500/20 border-cyan-400 text-cyan-200 shadow-sm'
                    : 'bg-slate-900/90 border-slate-800 text-slate-300 hover:bg-slate-800/80'
                }`}
              >
                <span className="truncate">{filter.label}</span>
                <span
                  className={`px-1.5 py-0.5 rounded-full text-[11px] font-bold shrink-0 ${
                    active ? 'bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="mx-3 mt-3 p-3 rounded-2xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          <span className="flex-1">{error}</span>
        </div>
      )}

      {/* 3-Column WebP Grid */}
      <div className="p-2 flex-1">
        {loading ? (
          <div className="grid grid-cols-3 gap-1.5">
            {[0, 1, 2, 3, 4, 5].map((n) => (
              <div
                key={n}
                className="aspect-[9/16] rounded-xl bg-slate-900 animate-pulse border border-slate-800"
              />
            ))}
          </div>
        ) : filteredClips.length === 0 ? (
          <div className="py-12 px-4 text-center space-y-2">
            <Film className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-sm font-medium text-slate-300">ไม่มีคลิปในหมวดนี้</p>
            <p className="text-xs text-slate-500">
              ลองสลับตัวกรองด้านบน หรือกดรีเฟรชเพื่อโหลดข้อมูลล่าสุด
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-1.5" data-testid="mobile-clip-grid">
            {filteredClips.map((item, idx) => {
              const id = clipKey(item, idx);
              const isSelected = selectedIds.has(id);
              const cover9x16 = getCoverVariant(item, '9:16');
              // Prefer lightweight .webp thumbnail first
              const thumbUrl = toMediaUrl(item.thumbnail_url || cover9x16.url || cover9x16.path);
              const coverBound = isClipCoverBound(item);
              const titleText = item.hook_title || item.angle_name || item.product_name || item.name || 'คลิป';

              return (
                <button
                  key={id}
                  type="button"
                  onPointerDown={() => handleCardPointerDown(id)}
                  onPointerUp={clearLongPressTimer}
                  onPointerLeave={clearLongPressTimer}
                  onPointerCancel={clearLongPressTimer}
                  onClick={() => handleCardClick(item, idx)}
                  className={`group relative aspect-[9/16] w-full rounded-xl overflow-hidden bg-slate-900 border text-left focus:outline-none transition ${
                    isSelected
                      ? 'border-cyan-400 ring-2 ring-cyan-400/70'
                      : 'border-slate-800 hover:border-slate-600'
                  }`}
                >
                  {thumbUrl ? (
                    <img
                      src={thumbUrl}
                      alt={titleText}
                      loading="lazy"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-slate-900 text-slate-600">
                      <Play className="w-6 h-6" />
                    </div>
                  )}

                  {/* Top status indicator */}
                  <div className="absolute top-1.5 inset-x-1.5 flex items-center justify-between gap-1 pointer-events-none">
                    {coverBound ? (
                      <span className="px-1.5 py-0.5 rounded bg-emerald-500/85 text-[10px] font-semibold text-slate-950 truncate">
                        ปกพร้อม
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/85 text-[10px] font-semibold text-slate-950 truncate">
                        รอเลือกปก
                      </span>
                    )}

                    {multiSelectMode && (
                      <span
                        className={`w-5 h-5 rounded-md flex items-center justify-center ${
                          isSelected ? 'bg-cyan-400 text-slate-950' : 'bg-black/60 text-white border border-white/40'
                        }`}
                      >
                        {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                      </span>
                    )}
                  </div>

                  {/* Bottom title overlay (strictly no price badge per Rule 2.1) */}
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/55 to-transparent p-1.5 pointer-events-none">
                    <p className="text-[11px] font-medium text-white line-clamp-2 leading-tight">
                      {titleText}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Full-Screen Vertical Viewer */}
      {activeClip && (
        <div
          className="fixed inset-0 z-40 bg-black flex flex-col justify-between overflow-hidden"
          role="dialog"
          aria-modal="true"
          aria-label="ดูคลิปเต็มจอ"
        >
          {/* Viewer Top Bar */}
          <div className="flex items-center justify-between gap-2 px-3 py-2.5 bg-gradient-to-b from-black/90 to-transparent z-10">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-white truncate">
                {activeClip.hook_title || activeClip.product_name || activeClip.name}
              </p>
              <p className="text-xs text-slate-300 truncate">
                {activeClip.product_name || activeClip.project_name || ''}
              </p>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {viewerIndex > 0 && (
                <button
                  type="button"
                  onClick={() => stepViewer(-1)}
                  aria-label="คลิปก่อนหน้า"
                  className="min-w-11 min-h-11 inline-flex items-center justify-center rounded-full bg-slate-900/80 text-white border border-slate-700"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
              )}
              {viewerIndex >= 0 && viewerIndex < filteredClips.length - 1 && (
                <button
                  type="button"
                  onClick={() => stepViewer(1)}
                  aria-label="คลิปถัดไป"
                  className="min-w-11 min-h-11 inline-flex items-center justify-center rounded-full bg-slate-900/80 text-white border border-slate-700"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              )}
              <button
                type="button"
                onClick={closeViewer}
                aria-label="ปิดหน้าต่างดูคลิป"
                className="min-w-11 min-h-11 inline-flex items-center justify-center rounded-full bg-slate-900/90 text-white border border-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Video Player (`preload="none"`, `playsInline`, `controls`) */}
          <div className="flex-1 min-h-0 flex items-center justify-center bg-black px-2">
            <video
              key={activeClipId}
              src={toMediaUrl(activeClip.rel_path || activeClip.path || activeClip.video_url)}
              poster={toMediaUrl(
                activeClip.thumbnail_url ||
                getCoverVariant(activeClip, '9:16').url ||
                getCoverVariant(activeClip, '9:16').path,
              )}
              preload="none"
              playsInline
              controls
              className="max-h-full max-w-full aspect-[9/16] rounded-2xl bg-slate-950"
            />
          </div>

          {/* Viewer Bottom Action Controls (all buttons >= 44px) */}
          <div
            className="px-3 pt-2.5 pb-3 bg-slate-950/95 border-t border-slate-800 space-y-2"
            style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 8px) + 12px)' }}
          >
            {/* Feedback / Progress Bar */}
            {prefetching && prefetchProgress && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs text-cyan-300">
                  <span>กำลังโหลดไฟล์แบบแบ่งส่วน...</span>
                  <span>{prefetchProgress.percent}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-cyan-400 transition-all duration-150"
                    style={{ width: `${prefetchProgress.percent}%` }}
                  />
                </div>
              </div>
            )}

            {(shareFeedback || copyFeedback) && (
              <div className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-emerald-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="truncate">{shareFeedback || copyFeedback}</span>
              </div>
            )}

            {/* Primary Save / Share Action */}
            <div className="flex items-center gap-2">
              {preparedFile ? (
                <button
                  type="button"
                  onClick={handleSharePreparedFile}
                  className="flex-1 min-h-11 px-4 rounded-2xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-bold text-sm inline-flex items-center justify-center gap-2 shadow-lg transition active:scale-[0.99]"
                >
                  <Share2 className="w-4 h-4" />
                  <span>บันทึกหรือแชร์วิดีโอ</span>
                </button>
              ) : (
                <button
                  type="button"
                  disabled={prefetching}
                  onClick={handlePrepareFile}
                  className="flex-1 min-h-11 px-4 rounded-2xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/60 text-cyan-200 font-semibold text-sm inline-flex items-center justify-center gap-2 transition disabled:opacity-60"
                >
                  {prefetching ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>กำลังเตรียมไฟล์ ({prefetchProgress?.percent ?? 0}%)</span>
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      <span>เตรียมไฟล์ไว้แชร์</span>
                    </>
                  )}
                </button>
              )}

              <button
                type="button"
                onClick={() => {
                  const rawVideoPath = activeClip.rel_path || activeClip.path || activeClip.video_url || '';
                  const mediaUrl = toMediaUrl(rawVideoPath);
                  triggerBrowserDownload(mediaUrl, activeClip.name);
                  setShareFeedback('เริ่มดาวน์โหลดวิดีโอลงเครื่องแล้ว');
                }}
                aria-label="ดาวน์โหลดไฟล์โดยตรง"
                className="min-w-11 min-h-11 px-3 rounded-2xl bg-slate-900 border border-slate-700 text-slate-200 inline-flex items-center justify-center"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>

            {/* Secondary Actions: CoverSheet & Copy Caption */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setCoverSheetOpen(true)}
                className="min-h-11 px-3 rounded-2xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-white inline-flex items-center justify-center gap-1.5 transition"
              >
                <ImageIcon className="w-4 h-4 text-amber-400" />
                <span>เลือกปกคลิป</span>
              </button>

              <button
                type="button"
                onClick={handleCopyCaption}
                className="min-h-11 px-3 rounded-2xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-white inline-flex items-center justify-center gap-1.5 transition"
              >
                <Copy className="w-4 h-4 text-cyan-400" />
                <span>คัดลอกแคปชัน</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cover Binding Bottom Sheet */}
      <CoverSheet
        open={Boolean(activeClip && coverSheetOpen)}
        clip={activeClip}
        onClose={() => setCoverSheetOpen(false)}
        onCoverUpdated={handleCoverUpdated}
      />
    </div>
  );
}

export default MobileClipLibrary;
