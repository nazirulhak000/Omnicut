import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause } from 'lucide-react';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';
import { toMediaUrl } from '../../../lib/mediaUrl';
import { shiftTrimWindow, resizeTrimWindow } from '../../../lib/timelineMath';

/**
 * Right-click a clip -> "ปรับช่วงตัด" -> this modal. Replaces the old
 * Alt+drag-on-the-timeline gesture: that was undiscoverable and its ghost
 * overlay was too small to read anything from. Here the preview is full
 * size and the filmstrip scrub bar spans the whole modal width, mirroring
 * CapCut mobile's own trim UI.
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
  srcDur,      // full source-file duration in seconds
  filmstripUrl,
}) {
  const [draft, setDraft] = useState(null);
  const [barWidth, setBarWidth] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const dragRef = useRef(null);
  const barRef = useRef(null);
  const videoRef = useRef(null);
  // onTimeUpdate needs the live trim_end without re-binding the listener
  // every drag frame -- a ref mirrors `draft` so the closure always reads
  // the latest bound without recreating the <video> element's handler.
  const draftRef = useRef(null);
  draftRef.current = draft;

  // Minimum on-screen width for the green box, in px -- wide enough to fit
  // both edge handles (10px each) plus a real grabbable middle area. Without
  // this a short clip inside a long source file renders a box so thin the
  // two edge handles cover it entirely, making "drag the whole box to shift"
  // physically impossible to hit (found via manual browser testing).
  const MIN_BOX_PX = 32;

  // Reset the draft only when the modal opens or targets a different clip --
  // never on every render, or mid-drag state would be clobbered by parent
  // re-renders triggered elsewhere in the app.
  useEffect(() => {
    if (isOpen && clip) {
      setDraft({
        trim_start: clip.trim_start || 0,
        trim_end: clip.trim_end ?? srcDur ?? 0,
      });
    } else if (!isOpen) {
      setDraft(null);
    }
  }, [isOpen, clip?.id, srcDur]);

  useEffect(() => {
    if (isOpen) videoRef.current?.pause();
    setIsPlaying(false);
  }, [isOpen]);

  // Measure the scrub bar's real pixel width once it's mounted and visible,
  // so the green box's minimum-width clamp (MIN_BOX_PX) can be applied in
  // the same pixel space the drag math already uses. Depends on `draft` too
  // (not just `isOpen`): the component early-returns a bar-less <Modal>
  // shell until `draft` is set (see the render guard below), so barRef isn't
  // mounted yet on the same tick `isOpen` first flips true.
  useEffect(() => {
    if (!isOpen || !draft) return;
    const el = barRef.current;
    if (!el) return;
    setBarWidth(el.getBoundingClientRect().width);
    const observer = new ResizeObserver((entries) => {
      setBarWidth(entries[0].contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [isOpen, draft === null]);

  useEffect(() => {
    if (!draft || !videoRef.current) return;
    const mode = dragRef.current?.mode;
    videoRef.current.currentTime = mode === 'end' ? draft.trim_end : draft.trim_start;
  }, [draft]);

  if (!isOpen || !clip || !draft) return <Modal isOpen={isOpen} onClose={onClose} title="ปรับช่วงตัด" />;

  const pxPerSourceSecond = (barWidth || 1) / (srcDur || 1);

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
    if (!d) return;
    const deltaSource = (e.clientX - d.startX) / pxPerSourceSecond;
    const patch = d.mode === 'shift'
      ? shiftTrimWindow(d.startDraft, deltaSource, srcDur)
      : resizeTrimWindow(d.mode, d.startDraft, deltaSource, srcDur);
    setDraft(patch);
  };

  const endDrag = (e) => {
    if (!dragRef.current) return;
    dragRef.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch { /* already released */ }
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

  // Pixel-space, not percent: the box needs a real MIN_BOX_PX floor so its
  // two edge handles (10px each) never cover the entire box, leaving no
  // grabbable middle area to shift with. Widening from its own center keeps
  // the box's true position on the filmstrip visually honest rather than
  // just growing off one side.
  const rawLeftPx = (draft.trim_start / (srcDur || 1)) * barWidth;
  const rawWidthPx = ((draft.trim_end - draft.trim_start) / (srcDur || 1)) * barWidth;
  const windowWidthPx = Math.max(MIN_BOX_PX, rawWidthPx);
  const windowLeftPx = Math.max(0, Math.min(barWidth - windowWidthPx, rawLeftPx - (windowWidthPx - rawWidthPx) / 2));

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

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>{draft.trim_start.toFixed(2)}s</span>
            <span>{draft.trim_end.toFixed(2)}s</span>
          </div>
          <div
            ref={barRef}
            className="relative h-16 rounded-lg bg-black overflow-hidden select-none touch-none"
            style={filmstripUrl ? {
              backgroundImage: `url("${filmstripUrl}")`,
              backgroundSize: '100% 100%',
              backgroundRepeat: 'no-repeat',
            } : undefined}
          >
            <div
              className="absolute top-0 h-full ring-2 ring-emerald-400 bg-white/10 cursor-grab active:cursor-grabbing touch-none"
              style={{ left: windowLeftPx, width: windowWidthPx }}
              onPointerDown={startDrag('shift')}
              onPointerMove={moveDrag}
              onPointerUp={endDrag}
              onPointerCancel={endDrag}
            >
              <div
                className="absolute top-0 left-0 h-full w-2.5 cursor-ew-resize touch-none bg-emerald-400"
                onPointerDown={startDrag('start')}
                onPointerMove={moveDrag}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
              />
              <div
                className="absolute top-0 right-0 h-full w-2.5 cursor-ew-resize touch-none bg-emerald-400"
                onPointerDown={startDrag('end')}
                onPointerMove={moveDrag}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
              />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.08]">
          <Button variant="secondary" onClick={onClose}>ยกเลิก</Button>
          <Button variant="primary" onClick={handleConfirm}>ยืนยัน</Button>
        </div>
      </div>
    </Modal>
  );
}
