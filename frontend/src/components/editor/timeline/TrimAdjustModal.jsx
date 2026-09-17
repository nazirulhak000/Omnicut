import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Play, Pause, Loader2, RotateCcw, GripHorizontal, ZoomIn, ZoomOut, Sliders } from 'lucide-react';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';
import { toMediaUrl } from '../../../lib/mediaUrl';
import { getMediaInfo, filmstripUrlFor } from '../../../api';
import { shiftTrimWindow, resizeTrimWindow, formatTimecode } from '../../../lib/timelineMath';

const FILMSTRIP_FRAMES = 48;
const MIN_BOX_PX = 32;

/**
 * TrimAdjustModal — Single-Track Smart Trimmer (เส้นเดียว สมูท เลื่อนไว ชัดเจน ไม่แคบ)
 *
 * Solves the narrow-box problem completely:
 *  1. Floating "เลื่อนช็อต" (Move Shot) Pill attached above the trim box — always grabbable, never blocked by edge handles!
 *  2. Zoom Toggle: "🌐 ทั้งคลิป (1x)" vs "🔍 โฟกัสช็อตนี้" — expands narrow shots to wide, comfortable editing size.
 *  3. Smooth Position Slider underneath — drag the slider thumb to glide across the entire video effortlessly.
 *  4. Mouse Wheel Scroll on track — roll mouse wheel up/down to glide the shot forward/backward smoothly.
 *  5. Quick Nudge Buttons (-1s, -0.1s, +0.1s, +1s) & Tap-to-jump on the filmstrip.
 */
export default function TrimAdjustModal({
  isOpen,
  onClose,
  onConfirm,   // (clipId, patch) => void
  clip,        // real clip object: { id, trim_start, trim_end, source_path, ... }
}) {
  const [draft, setDraft] = useState(null);
  const [barWidth, setBarWidth] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [trueDuration, setTrueDuration] = useState(null);
  const [filmstripUrl, setFilmstripUrl] = useState(null);
  const [isZoomFocus, setIsZoomFocus] = useState(false);

  const dragRef = useRef(null);
  const barRef = useRef(null);
  const videoRef = useRef(null);
  const draftRef = useRef(null);
  draftRef.current = draft;

  // Video seeking throttle
  const seekThrottleRef = useRef({ last: 0, timer: null });

  const seekVideo = useCallback((targetTime) => {
    const v = videoRef.current;
    if (!v) return;
    const clamped = Math.max(0, Math.min(trueDuration || 9999, targetTime));
    const state = seekThrottleRef.current;
    const THROTTLE_MS = 35;

    if (state.timer) {
      clearTimeout(state.timer);
      state.timer = null;
    }

    const elapsed = performance.now() - state.last;
    const doSeek = (t) => {
      if ('fastSeek' in v) {
        try { v.fastSeek(t); } catch (_) { v.currentTime = t; }
      } else {
        v.currentTime = t;
      }
      setCurrentTime(t);
    };

    if (elapsed >= THROTTLE_MS) {
      doSeek(clamped);
      state.last = performance.now();
    } else {
      state.timer = setTimeout(() => {
        doSeek(clamped);
        state.last = performance.now();
        state.timer = null;
      }, THROTTLE_MS - elapsed);
    }
  }, [trueDuration]);

  // Initialize draft and fetch media info
  useEffect(() => {
    if (isOpen && clip) {
      setDraft({
        trim_start: clip.trim_start || 0,
        trim_end: clip.trim_end ?? 0,
      });
      setCurrentTime(clip.trim_start || 0);
      setIsZoomFocus(false);
    } else if (!isOpen) {
      setDraft(null);
      setTrueDuration(null);
      setFilmstripUrl(null);
      setIsPlaying(false);
      setIsZoomFocus(false);
    }
  }, [isOpen, clip?.id]);

  useEffect(() => {
    if (!isOpen || !clip?.source_path) return;
    let cancelled = false;
    (async () => {
      try {
        const info = await getMediaInfo(clip.source_path);
        const duration = Number(info?.duration) || 0;
        if (cancelled || !duration) return;
        setTrueDuration(duration);
        setDraft((prev) => ({
          trim_start: prev?.trim_start ?? (clip.trim_start || 0),
          trim_end: (prev?.trim_end && prev.trim_end > 0) ? prev.trim_end : (clip.trim_end ?? duration),
        }));
        setFilmstripUrl(filmstripUrlFor(clip.source_path, FILMSTRIP_FRAMES));
      } catch (err) {
        // Fallback if media info fails
      }
    })();
    return () => { cancelled = true; };
  }, [isOpen, clip?.id, clip?.source_path]);

  // Track bar width
  useEffect(() => {
    if (!isOpen || !barRef.current) return;
    const el = barRef.current;
    setBarWidth(el.getBoundingClientRect().width);
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        setBarWidth(entries[0].contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [isOpen, draft !== null]);

  // Calculate active view window (Full vs Focus Zoom)
  const clipSpan = draft ? Math.max(0.1, (draft.trim_end - draft.trim_start)) : 1.0;
  const focusSpan = Math.max(8.0, clipSpan * 4.5);
  const viewStart = (isZoomFocus && trueDuration)
    ? Math.max(0, Math.min(trueDuration - focusSpan, draft.trim_start - (focusSpan - clipSpan) / 2))
    : 0;
  const viewEnd = (isZoomFocus && trueDuration)
    ? Math.min(trueDuration, viewStart + focusSpan)
    : (trueDuration || 1);
  const viewSpan = Math.max(0.1, viewEnd - viewStart);

  const pxPerSecond = (barWidth > 0 && viewSpan > 0) ? barWidth / viewSpan : 1;

  // Drag handling
  const startDrag = (mode) => (e) => {
    e.preventDefault();
    e.stopPropagation();
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (_) {}
    videoRef.current?.pause();
    setIsPlaying(false);
    dragRef.current = { mode, startX: e.clientX, startDraft: { ...draft } };
  };

  const moveDrag = (e) => {
    const d = dragRef.current;
    if (!d || !trueDuration || !barWidth) return;
    const deltaSource = (e.clientX - d.startX) / pxPerSecond;
    const patch = d.mode === 'shift'
      ? shiftTrimWindow(d.startDraft, deltaSource, trueDuration)
      : resizeTrimWindow(d.mode, d.startDraft, deltaSource, trueDuration);

    setDraft(patch);
    const seekTarget = d.mode === 'end' ? patch.trim_end : patch.trim_start;
    seekVideo(seekTarget);
  };

  const endDrag = (e) => {
    if (!dragRef.current) return;
    dragRef.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (_) {}
  };

  // Jump to clicked position on track
  const handleTrackClick = (e) => {
    if (!barRef.current || !barWidth || !trueDuration || !draft) return;
    const rect = barRef.current.getBoundingClientRect();
    const clickRatio = Math.max(0, Math.min(1, (e.clientX - rect.left) / barWidth));
    const clickTime = viewStart + clickRatio * viewSpan;
    const span = draft.trim_end - draft.trim_start;

    videoRef.current?.pause();
    setIsPlaying(false);

    const patch = shiftTrimWindow(draft, clickTime - span / 2 - draft.trim_start, trueDuration);
    setDraft(patch);
    seekVideo(patch.trim_start);
  };

  // Mouse wheel scrolling on track
  const handleWheel = (e) => {
    e.preventDefault();
    const step = e.deltaY > 0 ? 0.25 : -0.25;
    handleNudge(step);
  };

  // Quick Nudge Buttons
  const handleNudge = useCallback((delta) => {
    const d = draftRef.current;
    if (!d || !trueDuration) return;
    const patch = shiftTrimWindow(d, delta, trueDuration);
    setDraft(patch);
    seekVideo(patch.trim_start);
  }, [trueDuration, seekVideo]);

  // Slider change for instant smooth sliding
  const handleSliderChange = (newStart) => {
    if (!draft || !trueDuration) return;
    const span = draft.trim_end - draft.trim_start;
    const maxStart = Math.max(0, trueDuration - span);
    const clampedStart = Math.min(maxStart, Math.max(0, newStart));
    const patch = {
      trim_start: Math.round(clampedStart * 100) / 100,
      trim_end: Math.round((clampedStart + span) * 100) / 100,
    };
    setDraft(patch);
    seekVideo(patch.trim_start);
  };

  const handleReset = () => {
    if (!clip || !trueDuration) return;
    const patch = {
      trim_start: clip.trim_start || 0,
      trim_end: clip.trim_end ?? trueDuration,
    };
    setDraft(patch);
    seekVideo(patch.trim_start);
  };

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    const d = draftRef.current;
    if (!v || !d) return;
    if (isPlaying) {
      v.pause();
      setIsPlaying(false);
      return;
    }
    if (v.currentTime < d.trim_start || v.currentTime >= d.trim_end) {
      v.currentTime = d.trim_start;
      setCurrentTime(d.trim_start);
    }
    v.play().catch(() => {});
    setIsPlaying(true);
  }, [isPlaying]);

  // Intercept Spacebar and Arrow Keys when modal is open
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      const el = e.target;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) {
        return;
      }

      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        e.stopPropagation();
        togglePlay();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        e.stopPropagation();
        handleNudge(e.shiftKey ? -1.0 : -0.1);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        e.stopPropagation();
        handleNudge(e.shiftKey ? 1.0 : 0.1);
      }
    };

    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [isOpen, togglePlay, handleNudge]);

  const handleTimeUpdate = () => {
    const v = videoRef.current;
    const d = draftRef.current;
    if (!v || !d) return;
    setCurrentTime(v.currentTime);
    if (v.currentTime >= d.trim_end) {
      v.pause();
      v.currentTime = d.trim_start;
      setCurrentTime(d.trim_start);
      setIsPlaying(false);
    }
  };

  const handleConfirm = () => {
    onConfirm?.(clip.id, draft);
    onClose?.();
  };

  if (!isOpen || !clip || !draft) {
    return <Modal isOpen={isOpen} onClose={onClose} title="ปรับช่วงตัด" />;
  }

  // Visual layout math for the single track
  const durationReady = trueDuration && trueDuration > 0 && barWidth > 0;
  const rawLeftPx = durationReady ? ((draft.trim_start - viewStart) / viewSpan) * barWidth : 0;
  const rawWidthPx = durationReady ? ((draft.trim_end - draft.trim_start) / viewSpan) * barWidth : 0;
  const windowWidthPx = Math.max(MIN_BOX_PX, rawWidthPx);
  const windowLeftPx = Math.max(0, Math.min(barWidth - windowWidthPx, rawLeftPx));

  const playheadPx = durationReady ? Math.max(0, Math.min(barWidth, ((currentTime - viewStart) / viewSpan) * barWidth)) : 0;
  const maxSliderStart = trueDuration ? Math.max(0, trueDuration - clipSpan) : 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="ปรับช่วงตัด" maxWidth="max-w-2xl">
      <div className="space-y-4">
        {/* Video Preview Container */}
        <div className="relative rounded-2xl overflow-hidden bg-slate-950 border border-white/10 h-[360px] sm:h-[400px] w-full flex items-center justify-center group shadow-2xl">
          <video
            ref={videoRef}
            src={toMediaUrl(clip.source_path)}
            className="max-w-full max-h-full object-contain"
            playsInline
            onTimeUpdate={handleTimeUpdate}
            onPause={() => setIsPlaying(false)}
            onClick={togglePlay}
          />
          <button
            type="button"
            onClick={togglePlay}
            aria-label={isPlaying ? 'หยุดชั่วคราว' : 'เล่นช่วงที่เลือก'}
            className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/25 transition-all cursor-pointer"
          >
            <span className={`flex items-center justify-center w-15 h-15 rounded-full bg-black/65 backdrop-blur-md border border-white/20 shadow-xl transition-all transform hover:scale-105 ${isPlaying ? 'opacity-0 group-hover:opacity-100' : 'opacity-90'}`}>
              {isPlaying ? (
                <Pause className="w-7 h-7 text-white" />
              ) : (
                <Play className="w-7 h-7 text-white ml-1 fill-white" />
              )}
            </span>
          </button>

          {/* Badge: Current Playback Time */}
          <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-md px-2.5 py-1 rounded-lg border border-white/10 text-xs font-mono text-emerald-400 flex items-center gap-1.5 shadow-md">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>{formatTimecode(currentTime)}</span>
          </div>

          {/* Reset Button */}
          <button
            type="button"
            onClick={handleReset}
            title="รีเซ็ตช่วงตัดเป็นค่าเดิม"
            className="absolute top-3 right-3 bg-black/60 hover:bg-black/80 backdrop-blur-md px-2.5 py-1 rounded-lg border border-white/10 text-xs text-slate-300 hover:text-white flex items-center gap-1 transition-all cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>คืนค่าเดิม</span>
          </button>
        </div>

        {/* Single-Track Trimmer Controls */}
        <div className="bg-slate-900/95 border border-white/10 rounded-2xl p-4 space-y-3.5 shadow-xl">
          {/* Header Stats & Zoom Toggle */}
          <div className="flex items-center justify-between text-xs px-1 select-none">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 font-medium">จุดเริ่ม:</span>
              <span className="font-mono text-white bg-slate-800 px-2 py-0.5 rounded-md border border-white/5">
                {draft.trim_start.toFixed(2)}s
              </span>
            </div>

            {/* Central Duration Badge & Zoom Mode */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/30 px-3 py-0.5 rounded-full text-emerald-400 font-semibold text-xs shadow-inner">
                <span>ความยาวช็อต:</span>
                <span className="font-mono">{clipSpan.toFixed(2)}s</span>
              </div>

              {/* Zoom Focus Toggle */}
              <button
                type="button"
                onClick={() => setIsZoomFocus(!isZoomFocus)}
                className={`px-2.5 py-0.5 rounded-full border text-[11px] font-medium transition-all flex items-center gap-1 cursor-pointer ${
                  isZoomFocus
                    ? 'bg-amber-400 text-slate-950 border-amber-300 shadow-md font-semibold'
                    : 'bg-slate-800 text-slate-300 border-white/10 hover:text-white hover:bg-slate-700'
                }`}
                title={isZoomFocus ? 'สลับเป็นมุมมองทั้งคลิป 1x' : 'ขยายซูมเฉพาะช่วงช็อตนี้เพื่อให้เลื่อนและปรับขอบง่ายขึ้น'}
              >
                {isZoomFocus ? <ZoomOut className="w-3 h-3" /> : <ZoomIn className="w-3 h-3" />}
                <span>{isZoomFocus ? 'ซูมขยายอยู่' : 'ซูมขยายช็อต'}</span>
              </button>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 font-medium">จุดจบ:</span>
              <span className="font-mono text-white bg-slate-800 px-2 py-0.5 rounded-md border border-white/5">
                {draft.trim_end.toFixed(2)}s
              </span>
            </div>
          </div>

          {/* The Single Filmstrip Scrubber Track */}
          <div className="pt-6"> {/* Extra top padding for the floating Move Pill */}
            <div
              ref={barRef}
              onClick={handleTrackClick}
              onWheel={handleWheel}
              className="relative h-18 rounded-xl bg-slate-950 overflow-visible select-none touch-none cursor-pointer border border-white/10 shadow-inner"
              style={durationReady && filmstripUrl ? {
                backgroundImage: `url("${filmstripUrl}")`,
                backgroundSize: '100% 100%',
                backgroundRepeat: 'no-repeat',
              } : undefined}
            >
              {!durationReady && (
                <div className="absolute inset-0 flex items-center justify-center gap-2 text-xs text-slate-400 bg-slate-950 rounded-xl">
                  <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                  <span>กำลังโหลดฟิล์มสตริป...</span>
                </div>
              )}

              {durationReady && (
                <>
                  {/* Dimmed Outside Areas (Left & Right) */}
                  <div
                    className="pointer-events-none absolute inset-y-0 left-0 bg-black/75 backdrop-blur-[1px] transition-[width] duration-75 ease-out rounded-l-xl"
                    style={{ width: windowLeftPx }}
                  />
                  <div
                    className="pointer-events-none absolute inset-y-0 right-0 bg-black/75 backdrop-blur-[1px] transition-[width] duration-75 ease-out rounded-r-xl"
                    style={{ width: Math.max(0, barWidth - windowLeftPx - windowWidthPx) }}
                  />

                  {/* Highlighted Selected Trim Window */}
                  <div
                    className="absolute top-0 h-full border-2 border-emerald-400 bg-emerald-400/10 rounded-lg shadow-lg flex items-center justify-between touch-none transition-[left,width] duration-75 ease-out"
                    style={{ left: windowLeftPx, width: windowWidthPx }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {/* Floating "เลื่อนช็อต" Pill (Always easy to grab, never blocked by edge handles!) */}
                    <div
                      className="absolute -top-7 left-1/2 -translate-x-1/2 h-6 px-3 bg-emerald-400 hover:bg-emerald-300 active:bg-emerald-200 text-slate-950 font-bold text-[11px] rounded-full shadow-xl flex items-center justify-center gap-1 cursor-grab active:cursor-grabbing border border-white/40 whitespace-nowrap select-none transition-transform active:scale-95 z-30"
                      onPointerDown={startDrag('shift')}
                      onPointerMove={moveDrag}
                      onPointerUp={endDrag}
                      onPointerCancel={endDrag}
                      title="กดค้างแล้วลากปุ่มนี้เพื่อเลื่อนตำแหน่งช็อตไปซ้าย/ขวา"
                    >
                      <GripHorizontal className="w-3.5 h-3.5" />
                      <span>เลื่อนช็อต</span>
                    </div>

                    {/* Left Trim Handle */}
                    <div
                      className="h-full w-3 bg-emerald-400 hover:bg-emerald-300 active:bg-emerald-200 cursor-ew-resize touch-none rounded-l-md flex items-center justify-center transition-colors shadow-md before:absolute before:-inset-x-2.5 before:inset-y-0 before:content-[''] z-20"
                      onPointerDown={startDrag('start')}
                      onPointerMove={moveDrag}
                      onPointerUp={endDrag}
                      onPointerCancel={endDrag}
                      title="ลากเพื่อปรับจุดเริ่มต้น"
                    >
                      <span className="h-3 w-0.5 rounded-full bg-slate-950 pointer-events-none" />
                    </div>

                    {/* Center Grabbable Shift Area */}
                    <div
                      className="flex-1 h-full cursor-grab active:cursor-grabbing flex items-center justify-center touch-none z-10"
                      onPointerDown={startDrag('shift')}
                      onPointerMove={moveDrag}
                      onPointerUp={endDrag}
                      onPointerCancel={endDrag}
                      title="ลากเพื่อเลื่อนทั้งช่วง"
                    />

                    {/* Right Trim Handle */}
                    <div
                      className="h-full w-3 bg-emerald-400 hover:bg-emerald-300 active:bg-emerald-200 cursor-ew-resize touch-none rounded-r-md flex items-center justify-center transition-colors shadow-md before:absolute before:-inset-x-2.5 before:inset-y-0 before:content-[''] z-20"
                      onPointerDown={startDrag('end')}
                      onPointerMove={moveDrag}
                      onPointerUp={endDrag}
                      onPointerCancel={endDrag}
                      title="ลากเพื่อปรับจุดสิ้นสุด"
                    >
                      <span className="h-3 w-0.5 rounded-full bg-slate-950 pointer-events-none" />
                    </div>
                  </div>

                  {/* Playhead Needle */}
                  <div
                    className="pointer-events-none absolute top-0 bottom-0 w-0.5 bg-white shadow-xl z-20 transition-[left] duration-75 ease-out"
                    style={{ left: playheadPx }}
                  >
                    <div className="w-2.5 h-2.5 -ml-1 -mt-0.5 bg-white rounded-full shadow-md border border-slate-900" />
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Quick Slider: Drag to slide the shot across the entire video */}
          {durationReady && maxSliderStart > 0 && (
            <div className="pt-1 px-1 flex items-center gap-3">
              <span className="text-[11px] text-slate-400 flex items-center gap-1 shrink-0 select-none">
                <Sliders className="w-3 h-3 text-emerald-400" />
                <span>แถบเลื่อน:</span>
              </span>
              <input
                type="range"
                min={0}
                max={maxSliderStart}
                step={0.05}
                value={draft.trim_start}
                onChange={(e) => handleSliderChange(parseFloat(e.target.value))}
                className="w-full accent-emerald-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer transition-all"
                title="ลากแถบเลื่อนนี้เพื่อเลื่อนช็อตข้ามวิดีโอได้อย่างรวดเร็ว"
              />
              <span className="text-[11px] font-mono text-slate-300 shrink-0 w-12 text-right">
                {draft.trim_start.toFixed(1)}s
              </span>
            </div>
          )}

          {/* Micro-Adjustment & Quick Nudge Row */}
          <div className="flex items-center justify-between pt-1 border-t border-white/5 text-xs">
            {/* Backward Nudge */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => handleNudge(-1.0)}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-white/5 transition-all cursor-pointer font-mono text-[11px]"
                title="ขยับย้อนหลัง 1 วินาที"
              >
                -1.0s
              </button>
              <button
                type="button"
                onClick={() => handleNudge(-0.1)}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-emerald-400 hover:text-emerald-300 rounded-lg border border-white/5 transition-all cursor-pointer font-mono text-[11px] font-medium"
                title="ขยับย้อนหลัง 0.1 วินาที"
              >
                -0.1s
              </button>
            </div>

            {/* Hint / File Span Info */}
            <div className="text-slate-400 text-[11px] text-center select-none">
              💡 ลากปุ่ม <span className="text-emerald-400 font-semibold">"เลื่อนช็อต"</span> หรือแตะแถบฟิล์มเพื่อย้ายทันที
            </div>

            {/* Forward Nudge */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => handleNudge(0.1)}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-emerald-400 hover:text-emerald-300 rounded-lg border border-white/5 transition-all cursor-pointer font-mono text-[11px] font-medium"
                title="ขยับไปข้างหน้า 0.1 วินาที"
              >
                +0.1s
              </button>
              <button
                type="button"
                onClick={() => handleNudge(1.0)}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-white/5 transition-all cursor-pointer font-mono text-[11px]"
                title="ขยับไปข้างหน้า 1 วินาที"
              >
                +1.0s
              </button>
            </div>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-white/[0.08]">
          <Button variant="secondary" onClick={onClose}>ยกเลิก</Button>
          <Button variant="primary" onClick={handleConfirm}>ยืนยัน</Button>
        </div>
      </div>
    </Modal>
  );
}
