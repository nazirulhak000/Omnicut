import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, Loader2 } from 'lucide-react';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';
import { toMediaUrl } from '../../../lib/mediaUrl';
import { getMediaInfo, filmstripUrlFor } from '../../../api';
import { shiftTrimWindow, resizeTrimWindow } from '../../../lib/timelineMath';

const DETAIL_FRAMES = 24;
const OVERVIEW_FRAMES = 40;

// How much source-time the detail bar shows on either side of the current
// trim window -- a multiple of the window's own span, floored at a fixed
// number of seconds so a very short (near-zero) clip still gets a browsable
// amount of context. Sized to keep the green box a comfortable fraction of
// the bar (roughly 1/5th) rather than either filling it (old bug: box ==
// whole bar, nothing to grab) or shrinking to a near-invisible sliver (using
// the true full source length verbatim -- a 300s file would put a 3s clip
// at ~1% width).
const ZOOM_PAD_MULTIPLIER = 2;
const ZOOM_PAD_FLOOR_SECONDS = 8;

/**
 * Right-click a clip (or double-click it) -> "ปรับช่วงตัด" -> this modal.
 * Replaces the old Alt+drag-on-the-timeline gesture: that was undiscoverable
 * and its ghost overlay was too small to read anything from.
 *
 * Two scrub bars, because "see the whole raw file" and "nudge a cut point by
 * 0.1s" fight each other on one fixed-width strip:
 *  - Overview (thin, top): the *entire* source file, always. Tap anywhere to
 *    re-center the detail bar there -- pure navigation, does not move the
 *    actual trim range. Shows both where the detail bar is currently zoomed
 *    (dim outline) and where the real trim range sits (bright box), which
 *    can be two different places once you've panned away to look around.
 *  - Detail (tall, below): a zoomed-in window around wherever the overview
 *    last pointed it. This is where trim_start/trim_end actually get
 *    dragged/resized/jumped -- same interactions as before.
 *
 * All dragging operates on local draft state only -- the real clip is
 * never touched until "ยืนยัน" (Confirm) commits it as a single patch.
 * "ยกเลิก" (Cancel) just closes; there is nothing to revert.
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
  // True ffprobe duration of the raw source file, and the zoomed sub-range
  // (in absolute source seconds) the detail bar currently shows -- both null
  // until the media-info fetch below resolves.
  const [trueDuration, setTrueDuration] = useState(null);
  const [zoomWindow, setZoomWindow] = useState(null);
  const [detailUrl, setDetailUrl] = useState(null);
  const [overviewUrl, setOverviewUrl] = useState(null);
  const dragRef = useRef(null);
  const barRef = useRef(null);
  const videoRef = useRef(null);
  // onTimeUpdate needs the live trim_end without re-binding the listener
  // every drag frame -- a ref mirrors `draft` so the closure always reads
  // the latest bound without recreating the <video> element's handler.
  const draftRef = useRef(null);
  draftRef.current = draft;
  // Last edge-pan timestamp -- see maybePanZoom below.
  const panThrottleRef = useRef(0);

  // Minimum on-screen width for the green box, in px -- wide enough to fit
  // both edge handles (10px each) plus a real grabbable middle area. Without
  // this a short clip inside the zoomed window renders a box so thin the two
  // edge handles cover it entirely, making "drag the whole box to shift"
  // physically impossible to hit (found via manual browser testing).
  const MIN_BOX_PX = 32;

  // Reset the draft only when the modal opens or targets a different clip --
  // never on every render, or mid-drag state would be clobbered by parent
  // re-renders triggered elsewhere in the app.
  useEffect(() => {
    if (isOpen && clip) {
      setDraft({
        trim_start: clip.trim_start || 0,
        trim_end: clip.trim_end ?? 0,
      });
    } else if (!isOpen) {
      setDraft(null);
      setTrueDuration(null);
      setZoomWindow(null);
      setDetailUrl(null);
      setOverviewUrl(null);
    }
  }, [isOpen, clip?.id]);

  useEffect(() => {
    if (isOpen) videoRef.current?.pause();
    setIsPlaying(false);
  }, [isOpen]);

  // Fetch the real source duration and the full-file overview strip once;
  // compute the initial detail zoom window around the clip's current trim
  // range and fetch its scoped filmstrip. Runs once per clip, keyed off
  // clip.id -- re-navigating the overview afterward is handled by
  // navigateOverview() below, not by this effect re-running.
  useEffect(() => {
    if (!isOpen || !clip?.source_path) return;
    let cancelled = false;
    (async () => {
      try {
        const info = await getMediaInfo(clip.source_path);
        const duration = Number(info?.duration) || 0;
        if (cancelled || !duration) return;
        const start = clip.trim_start || 0;
        const end = clip.trim_end ?? duration;
        const span = Math.max(0, end - start);
        const pad = Math.max(span * ZOOM_PAD_MULTIPLIER, ZOOM_PAD_FLOOR_SECONDS);
        const zStart = Math.max(0, start - pad);
        const zEnd = Math.min(duration, end + pad);
        setTrueDuration(duration);
        setZoomWindow({ start: zStart, end: zEnd });
        setDraft((prev) => (prev ? { trim_start: prev.trim_start, trim_end: prev.trim_end ?? duration } : prev));
        setDetailUrl(filmstripUrlFor(clip.source_path, DETAIL_FRAMES, zStart, zEnd));
        setOverviewUrl(filmstripUrlFor(clip.source_path, OVERVIEW_FRAMES));
      } catch (err) {
        // No zoom data -- the bar below just stays in its loading state
        // rather than rendering with bogus math.
      }
    })();
    return () => { cancelled = true; };
  }, [isOpen, clip?.id, clip?.source_path]);

  // Measure the detail bar's real pixel width once it's mounted and visible,
  // so the green box's minimum-width clamp (MIN_BOX_PX) can be applied in
  // the same pixel space the drag math already uses.
  useEffect(() => {
    if (!isOpen || !draft || !zoomWindow) return;
    const el = barRef.current;
    if (!el) return;
    setBarWidth(el.getBoundingClientRect().width);
    const observer = new ResizeObserver((entries) => {
      setBarWidth(entries[0].contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [isOpen, draft === null, zoomWindow === null]);

  // Throttled with a trailing edge, not a straight assignment on every
  // `draft` change: dragging fires this effect at raw pointermove frequency
  // (60+/s), and each `<video>.currentTime =` is a real network seek on a
  // streamed multi-minute source file -- doing that dozens of times a
  // second is what made the drag feel slow/stuttery, not the drag math
  // itself (the box's own CSS position updates every event, uncapped, and
  // stays smooth on their own). Capping actual seeks to ~11/s keeps the
  // preview visibly tracking the drag while leaving the video pipeline room
  // to keep up; the trailing timeout guarantees the final position (after
  // the pointer stops) always lands on the exact value, never a skipped one.
  const seekThrottleRef = useRef({ last: 0, timer: null });
  useEffect(() => {
    if (!draft || !videoRef.current) return;
    const mode = dragRef.current?.mode;
    const target = mode === 'end' ? draft.trim_end : draft.trim_start;
    const v = videoRef.current;
    const state = seekThrottleRef.current;
    const SEEK_THROTTLE_MS = 90;

    if (state.timer) {
      clearTimeout(state.timer);
      state.timer = null;
    }
    const elapsed = performance.now() - state.last;
    if (elapsed >= SEEK_THROTTLE_MS) {
      v.currentTime = target;
      state.last = performance.now();
    } else {
      state.timer = setTimeout(() => {
        v.currentTime = target;
        state.last = performance.now();
        state.timer = null;
      }, SEEK_THROTTLE_MS - elapsed);
    }
    return () => {
      if (state.timer) {
        clearTimeout(state.timer);
        state.timer = null;
      }
    };
  }, [draft]);

  const zoomReady = isOpen && !!clip && !!draft && !!zoomWindow && !!trueDuration && barWidth > 0;

  if (!isOpen || !clip || !draft) return <Modal isOpen={isOpen} onClose={onClose} title="ปรับช่วงตัด" />;

  const zoomSpan = zoomWindow ? (zoomWindow.end - zoomWindow.start) || 1 : 1;
  const pxPerSourceSecond = (barWidth || 1) / zoomSpan;

  // Pure navigation for the overview strip: re-center the detail bar's zoom
  // window on `centerTime`, keeping the same span it already has (panning,
  // not re-zooming). Does not touch trim_start/trim_end -- the detail bar's
  // own drag/jump interactions are what actually move the trim range.
  const navigateOverview = (centerTime) => {
    if (!trueDuration || !clip?.source_path) return;
    const half = zoomSpan / 2;
    const zStart = Math.max(0, Math.min(trueDuration - zoomSpan, centerTime - half));
    const zEnd = Math.min(trueDuration, zStart + zoomSpan);
    setZoomWindow({ start: zStart, end: zEnd });
    setDetailUrl(filmstripUrlFor(clip.source_path, DETAIL_FRAMES, zStart, zEnd));
  };

  const handleOverviewClick = (e) => {
    if (!trueDuration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const t = ((e.clientX - rect.left) / rect.width) * trueDuration;
    navigateOverview(t);
  };

  // Clamp for a one-off jump (tap on the detail bar): the click coordinate
  // is itself always inside the bar, so the resulting window is already
  // within zoomWindow -- this is just a safety net.
  const clampToZoom = (patch) => {
    if (!zoomWindow) return patch;
    const span = patch.trim_end - patch.trim_start;
    if (patch.trim_start < zoomWindow.start) {
      return { trim_start: zoomWindow.start, trim_end: Math.round((zoomWindow.start + span) * 100) / 100 };
    }
    if (patch.trim_end > zoomWindow.end) {
      return { trim_start: Math.round((zoomWindow.end - span) * 100) / 100, trim_end: zoomWindow.end };
    }
    return patch;
  };

  // While actively dragging (shift or either edge), once the target value
  // crosses EDGE_FRACTION into the current zoom window's edge, re-pin the
  // window so that point sits exactly back at the margin line -- "drag to
  // the edge and it keeps sliding" instead of hard-stopping there.
  //
  // This re-pin runs on every qualifying drag tick, not throttled: it moves
  // the window by *exactly* however far the drag has crossed the margin, so
  // the box's on-screen position (relative to the window) never overshoots
  // and snaps backward -- a fixed step tried first here did overshoot
  // whenever the drag moved less than the step within one throttle tick,
  // which read as "the box jumped the opposite way" even though the trim
  // value only ever moved forward. What IS throttled is the filmstrip
  // image refetch below: panning the window is free (just re-centers where
  // existing state points), but a new image is a real backend ffmpeg call,
  // so that keeps its own cadence and briefly shows the previous frame
  // strip while the window keeps tracking the drag underneath it.
  const EDGE_FRACTION = 0.15;
  const FILMSTRIP_REFETCH_MS = 220;

  const maybePanZoom = (patch) => {
    if (!zoomWindow || !trueDuration || !clip?.source_path) return;
    const margin = zoomSpan * EDGE_FRACTION;
    let zStart = zoomWindow.start;
    let zEnd = zoomWindow.end;
    if (patch.trim_start < zoomWindow.start + margin && zoomWindow.start > 0) {
      zStart = Math.max(0, patch.trim_start - margin);
      zEnd = zStart + zoomSpan;
    } else if (patch.trim_end > zoomWindow.end - margin && zoomWindow.end < trueDuration) {
      zEnd = Math.min(trueDuration, patch.trim_end + margin);
      zStart = zEnd - zoomSpan;
    } else {
      return;
    }
    setZoomWindow({ start: zStart, end: zEnd });
    const now = performance.now();
    if (now - panThrottleRef.current >= FILMSTRIP_REFETCH_MS) {
      panThrottleRef.current = now;
      setDetailUrl(filmstripUrlFor(clip.source_path, DETAIL_FRAMES, zStart, zEnd));
    }
  };

  const startDrag = (mode) => (e) => {
    e.preventDefault();
    e.stopPropagation();
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag still works */ }
    videoRef.current?.pause();
    setIsPlaying(false);
    dragRef.current = { mode, startX: e.clientX, startDraft: { ...draft } };
  };

  const moveDrag = (e) => {
    const d = dragRef.current;
    if (!d || !zoomReady) return;
    const deltaSource = (e.clientX - d.startX) / pxPerSourceSecond;
    const patch = d.mode === 'shift'
      ? shiftTrimWindow(d.startDraft, deltaSource, trueDuration)
      : resizeTrimWindow(d.mode, d.startDraft, deltaSource, trueDuration);
    // Not clamped to zoomWindow here -- the drag target is free to go
    // anywhere in the source file; maybePanZoom keeps the visible window
    // chasing it instead of capping the drag at the window's edge.
    setDraft(patch);
    maybePanZoom(patch);
  };

  const endDrag = (e) => {
    if (!dragRef.current) return;
    dragRef.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch { /* already released */ }
  };

  // Tap anywhere on the detail filmstrip (outside the green box, which stops
  // this click via startDrag's stopPropagation) to jump the whole selection
  // window there, centered on the tap -- same span, just recentered. Without
  // this the only way to move the window was dragging it from inside itself,
  // which is invisible as an affordance on a bar that looks like a scrubber.
  const jumpTo = (e) => {
    if (!barRef.current || !barWidth || !zoomReady) return;
    const rect = barRef.current.getBoundingClientRect();
    const clickSourceTime = zoomWindow.start + ((e.clientX - rect.left) / barWidth) * zoomSpan;
    const span = draft.trim_end - draft.trim_start;
    videoRef.current?.pause();
    setIsPlaying(false);
    const patch = shiftTrimWindow(draft, clickSourceTime - span / 2 - draft.trim_start, trueDuration);
    setDraft(clampToZoom(patch));
  };

  const handleConfirm = () => {
    onConfirm?.(clip.id, draft);
    onClose?.();
  };

  // Plays only the selected window (trim_start..trim_end), then stops --
  // never leaks past the green box's own edges, and never loops.
  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (isPlaying) {
      v.pause();
      setIsPlaying(false);
      return;
    }
    if (v.currentTime < draft.trim_start || v.currentTime >= draft.trim_end) {
      v.currentTime = draft.trim_start;
    }
    v.play();
    setIsPlaying(true);
  };

  const handleTimeUpdate = () => {
    const v = videoRef.current;
    const d = draftRef.current;
    if (!v || !d) return;
    if (v.currentTime >= d.trim_end) {
      v.pause();
      v.currentTime = d.trim_start;
      setIsPlaying(false);
    }
  };

  // Pixel-space, not percent, relative to the zoomed window's own start --
  // the box needs a real MIN_BOX_PX floor so its two edge handles (10px
  // each) never cover the entire box, leaving no grabbable middle area to
  // shift with. Widening from its own center keeps the box's true position
  // on the filmstrip visually honest rather than just growing off one side.
  const rawLeftPx = zoomReady ? ((draft.trim_start - zoomWindow.start) / zoomSpan) * barWidth : 0;
  const rawWidthPx = zoomReady ? ((draft.trim_end - draft.trim_start) / zoomSpan) * barWidth : 0;
  const windowWidthPx = Math.max(MIN_BOX_PX, rawWidthPx);
  const windowLeftPx = Math.max(0, Math.min(barWidth - windowWidthPx, rawLeftPx - (windowWidthPx - rawWidthPx) / 2));

  // The actual trim range can fall entirely outside the current zoom window
  // after panning the overview elsewhere -- render no box in that case (it
  // has nothing to sit on) rather than pin it to a misleading edge.
  // While a drag is in progress the box must keep rendering (pinned to the
  // bar's edge by windowLeftPx's own clamp) even on the few throttled ticks
  // where the pan hasn't caught up yet -- if this div unmounted mid-drag,
  // the pointer capture and its move/up handlers would go with it.
  const trimInView = zoomReady && (
    !!dragRef.current || (draft.trim_end > zoomWindow.start && draft.trim_start < zoomWindow.end)
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="ปรับช่วงตัด" maxWidth="max-w-2xl">
      <div className="space-y-4">
        <div className="relative rounded-xl overflow-hidden bg-black aspect-video flex items-center justify-center group">
          <video
            ref={videoRef}
            src={toMediaUrl(clip.source_path)}
            className="max-w-full max-h-full"
            playsInline
            onTimeUpdate={handleTimeUpdate}
            onPause={() => setIsPlaying(false)}
            onClick={togglePlay}
          />
          <button
            type="button"
            onClick={togglePlay}
            aria-label={isPlaying ? 'หยุดชั่วคราว' : 'เล่นช่วงที่เลือก'}
            className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/20 transition-colors cursor-pointer"
          >
            <span className={`flex items-center justify-center w-14 h-14 rounded-full bg-black/60 backdrop-blur-sm border border-white/20 transition-opacity ${isPlaying ? 'opacity-0 group-hover:opacity-100' : 'opacity-90'}`}>
              {isPlaying ? <Pause className="w-6 h-6 text-white" /> : <Play className="w-6 h-6 text-white ml-0.5" />}
            </span>
          </button>
        </div>

        <div className="space-y-2">
          {/* Overview -- whole file, always. Tap to pan the detail bar. */}
          <div
            className="relative h-7 rounded-md bg-black overflow-hidden select-none touch-none cursor-pointer"
            style={trueDuration && overviewUrl ? {
              backgroundImage: `url("${overviewUrl}")`,
              backgroundSize: '100% 100%',
              backgroundRepeat: 'no-repeat',
            } : undefined}
            onClick={handleOverviewClick}
            title="แตะเพื่อเลื่อนกล้องซูมด้านล่างไปตรงนี้"
          >
            {!trueDuration && (
              <div className="absolute inset-0 flex items-center justify-center text-[10px] text-slate-600">
                กำลังโหลด...
              </div>
            )}
            {trueDuration && zoomWindow && (
              <div
                className="pointer-events-none absolute inset-y-0 border border-white/50"
                style={{
                  left: `${(zoomWindow.start / trueDuration) * 100}%`,
                  width: `${Math.max(1.5, ((zoomWindow.end - zoomWindow.start) / trueDuration) * 100)}%`,
                }}
              />
            )}
            {trueDuration && (
              <div
                className="pointer-events-none absolute inset-y-0 ring-2 ring-emerald-400"
                style={{
                  left: `${Math.max(0, (draft.trim_start / trueDuration) * 100)}%`,
                  width: `${Math.max(0.6, ((draft.trim_end - draft.trim_start) / trueDuration) * 100)}%`,
                }}
              />
            )}
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>{draft.trim_start.toFixed(2)}s</span>
            <span>{draft.trim_end.toFixed(2)}s</span>
          </div>
          <div
            ref={barRef}
            className="relative h-16 rounded-lg bg-black overflow-hidden select-none touch-none cursor-pointer"
            style={zoomReady && detailUrl ? {
              backgroundImage: `url("${detailUrl}")`,
              backgroundSize: '100% 100%',
              backgroundRepeat: 'no-repeat',
            } : undefined}
            onClick={jumpTo}
          >
            {!zoomReady && (
              <div className="absolute inset-0 flex items-center justify-center gap-2 text-xs text-slate-500">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                กำลังโหลดฟิล์มสตริป...
              </div>
            )}
            {zoomReady && trimInView && (
              <>
                {/* Dim everything outside the selected window instead of
                    relying on a faint fill inside it -- against a busy
                    filmstrip a tinted middle was unreadable as "this whole
                    span is selected", and it read as two disconnected edge
                    markers instead of one box. */}
                <div className="pointer-events-none absolute inset-y-0 left-0 bg-black/60 transition-[width] duration-100 ease-out" style={{ width: windowLeftPx }} />
                <div className="pointer-events-none absolute inset-y-0 right-0 bg-black/60 transition-[width] duration-100 ease-out" style={{ width: barWidth - windowLeftPx - windowWidthPx }} />
                <div
                  className="absolute top-0 h-full border-2 border-emerald-400 cursor-grab active:cursor-grabbing touch-none flex items-center justify-center transition-[left,width] duration-100 ease-out"
                  style={{ left: windowLeftPx, width: windowWidthPx }}
                  onPointerDown={startDrag('shift')}
                  onPointerMove={moveDrag}
                  onPointerUp={endDrag}
                  onPointerCancel={endDrag}
                  onClick={(e) => e.stopPropagation()}
                >
                  {windowWidthPx > 40 && (
                    <div className="pointer-events-none flex gap-0.5 opacity-70">
                      <span className="h-4 w-0.5 rounded-full bg-emerald-400" />
                      <span className="h-4 w-0.5 rounded-full bg-emerald-400" />
                    </div>
                  )}
                  <div
                    className="absolute top-0 left-0 h-full w-3 sm:w-2.5 cursor-ew-resize touch-none bg-emerald-400 before:absolute before:-inset-x-2.5 before:inset-y-0 before:content-['']"
                    onPointerDown={startDrag('start')}
                    onPointerMove={moveDrag}
                    onPointerUp={endDrag}
                    onPointerCancel={endDrag}
                  />
                  <div
                    className="absolute top-0 right-0 h-full w-3 sm:w-2.5 cursor-ew-resize touch-none bg-emerald-400 before:absolute before:-inset-x-2.5 before:inset-y-0 before:content-['']"
                    onPointerDown={startDrag('end')}
                    onPointerMove={moveDrag}
                    onPointerUp={endDrag}
                    onPointerCancel={endDrag}
                  />
                </div>
              </>
            )}
            {zoomReady && !trimInView && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-[11px] text-slate-500 bg-black/40">
                ช่วงที่เลือกอยู่นอกมุมมองนี้ — แตะแถบด้านบนเพื่อเลื่อนมาดู
              </div>
            )}
          </div>
          <p className="text-[11px] text-slate-500">
            {zoomReady && zoomWindow
              ? `ซูมช่วง ${zoomWindow.start.toFixed(1)}s–${zoomWindow.end.toFixed(1)}s จากทั้งไฟล์ ${trueDuration.toFixed(1)}s (แถบบน) · `
              : ''}
            ลากกลางกรอบเพื่อเลื่อนทั้งช่วง · ลากขอบซ้าย/ขวาเพื่อยืดหด · แตะจุดอื่นบนแถบเพื่อกระโดดมาที่นั่น
          </p>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.08]">
          <Button variant="secondary" onClick={onClose}>ยกเลิก</Button>
          <Button variant="primary" onClick={handleConfirm}>ยืนยัน</Button>
        </div>
      </div>
    </Modal>
  );
}
