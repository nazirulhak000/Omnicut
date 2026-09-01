import React, { useMemo, useRef } from 'react';
import { Film, MessageSquare, Music, Scissors, Waves } from 'lucide-react';
import TimelineClip from './TimelineClip';
import { formatTimecode } from '../../lib/timelineMath';

const RULER_H = 22;
const VIDEO_H = 60;
const CAPTION_H = 30;
const AUDIO_H = 30;
const GUTTER = 92;        // left label column
const TRACK_GAP = 4;

/** Tick spacing that keeps labels readable at any zoom. */
function tickStep(pxPerSec) {
  for (const step of [1, 2, 5, 10, 15, 30, 60]) {
    if (step * pxPerSec >= 56) return step;
  }
  return 120;
}

function TrackLabel({ icon: Icon, children }) {
  return (
    <div
      className="flex items-center gap-1.5 px-2 text-[10px] font-medium text-[#9C968F]"
      style={{ width: GUTTER }}
    >
      <Icon className="h-3 w-3 flex-shrink-0" />
      <span className="truncate">{children}</span>
    </div>
  );
}

export default function Timeline({
  segments,
  totalDuration,
  audioDuration,
  cues,
  bgmLabel,
  filmstrips,
  pxPerSec,
  playhead,
  selection,
  onSeek,
  onSelectClip,
  onSelectCaption,
  onTrim,
  onTrimBegin,
  onTrimEnd,
  onToggleTransition,
  onCaptionShift,
  onReorder,
  onReorderSilent,
  // Newer shell prop names. Both sets are accepted so the timeline keeps
  // working whichever shape the shell passes.
  onSelect,
  onClipChange,
  onCaptionChange,
  onBeginDrag,
  onEndDrag,
}) {
  const selectClip = (id) => (onSelectClip ? onSelectClip(id) : onSelect?.({ type: 'clip', id }));
  const selectCaption = (uid) => (onSelectCaption ? onSelectCaption(uid) : onSelect?.({ type: 'caption', id: uid }));
  const trimClip = (id, patch) => (onTrim ? onTrim(id, patch) : onClipChange?.(id, patch, true));
  const shiftCaption = (uid, patch) => (onCaptionShift ? onCaptionShift(uid, patch) : onCaptionChange?.(uid, patch, true));
  const dragBegin = () => (onTrimBegin || onBeginDrag)?.();
  const dragEnd = () => (onTrimEnd || onEndDrag)?.();
  const toggleTransition = (id) => {
    if (onToggleTransition) { onToggleTransition(id); return; }
    const seg = segments.find((sg) => sg.clip.id === id);
    const current = seg?.clip.transition_in || 'cut';
    onClipChange?.(id, { transition_in: current !== 'cut' ? 'cut' : 'fade' });
  };
  const reorder = (id, dir, silent) => {
    if (silent && onReorderSilent) { onReorderSilent(id, dir); return true; }
    if (onReorder) { onReorder(id, dir); return true; }
    return false;
  };
  const laneRef = useRef(null);
  const scrubbing = useRef(false);
  const captionDrag = useRef(null);
  const bodyDrag = useRef(null);

  // Dragging a clip body reorders it. The clip reports pointer positions; the
  // decision lives here because only the timeline knows where the other clips
  // are. Each crossing is one swap, and the whole gesture is one undo step.
  const onBodyDragStart = () => { bodyDrag.current = true; dragBegin(); };
  const onBodyDragMove = (clipId, clientX) => {
    if (!bodyDrag.current || !laneRef.current) return false;
    const t = (clientX - laneRef.current.getBoundingClientRect().left) / pxPerSec;
    const myIdx = segments.findIndex((s) => s.clip.id === clipId);
    const overIdx = segments.findIndex((s) => t >= s.segStart && t < s.segEnd);
    if (myIdx === -1 || overIdx === -1 || overIdx === myIdx) return false;
    return reorder(clipId, overIdx > myIdx ? 1 : -1, true);
  };
  const onBodyDragEnd = () => {
    if (!bodyDrag.current) return;
    bodyDrag.current = false;
    dragEnd();
  };

  const contentWidth = Math.max(audioDuration || 0, totalDuration, 1) * pxPerSec + 240;
  const step = tickStep(pxPerSec);
  const ticks = useMemo(() => {
    const span = Math.max(totalDuration, audioDuration || 0);
    const out = [];
    for (let t = 0; t <= span + step; t += step) out.push(t);
    return out;
  }, [totalDuration, audioDuration, step]);

  const timeFromEvent = (e) => {
    const lane = laneRef.current;
    if (!lane) return 0;
    const rect = lane.getBoundingClientRect();
    return Math.max(0, (e.clientX - rect.left) / pxPerSec);
  };

  const startScrub = (e) => {
    scrubbing.current = true;
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* scrub still works */ }
    onSeek(timeFromEvent(e));
  };
  const moveScrub = (e) => { if (scrubbing.current) onSeek(timeFromEvent(e)); };
  const endScrub = (e) => {
    scrubbing.current = false;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
  };

  const sfxMarkers = (cues || []).filter((c) => c.sfx);

  return (
    <div className="flex h-full flex-col bg-[#1C1B19]">
      <div className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden">
        <div style={{ width: contentWidth, minWidth: '100%' }} className="relative">

          {/* Ruler: click or drag to scrub */}
          <div className="sticky top-0 z-20 flex bg-[#1C1B19]">
            <div style={{ width: GUTTER }} className="flex-shrink-0" />
            <div
              onPointerDown={startScrub}
              onPointerMove={moveScrub}
              onPointerUp={endScrub}
              onPointerCancel={endScrub}
              className="relative flex-1 cursor-text touch-none border-b border-[#363430]"
              style={{ height: RULER_H }}
              title="คลิกหรือลากเพื่อเลื่อนหัวอ่าน"
            >
              {ticks.map((t) => (
                <div key={t} className="absolute top-0 h-full" style={{ left: t * pxPerSec }}>
                  <span className="absolute top-0 h-2 w-px bg-[#4A4742]" />
                  <span className="absolute top-2 -translate-x-1/2 font-mono text-[9px] text-[#6B6660]">
                    {formatTimecode(t)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Track lanes */}
          <div className="flex" style={{ paddingTop: TRACK_GAP }}>
            <div className="flex flex-shrink-0 flex-col gap-1">
              <div style={{ height: VIDEO_H }} className="flex items-center">
                <TrackLabel icon={Film}>วิดีโอ</TrackLabel>
              </div>
              <div style={{ height: CAPTION_H }} className="flex items-center">
                <TrackLabel icon={MessageSquare}>คำบรรยาย</TrackLabel>
              </div>
              <div style={{ height: AUDIO_H }} className="flex items-center">
                <TrackLabel icon={Music}>เสียง</TrackLabel>
              </div>
            </div>

            <div ref={laneRef} className="relative flex-1">
              {/* video track */}
              <div className="relative rounded bg-[#181716]" style={{ height: VIDEO_H }}>
                {segments.map((seg) => (
                  <TimelineClip
                    key={seg.clip.id}
                    seg={seg}
                    pxPerSec={pxPerSec}
                    isSelected={selection?.type === 'clip' && selection.id === seg.clip.id}
                    filmstrip={filmstrips?.[seg.clip.id]}
                    onSelect={selectClip}
                    onTrim={trimClip}
                    onTrimBegin={dragBegin}
                    onTrimEnd={dragEnd}
                    onReorder={(id, dir) => reorder(id, dir, false)}
                    onBodyDragStart={onBodyDragStart}
                    onBodyDragMove={onBodyDragMove}
                    onBodyDragEnd={onBodyDragEnd}
                  />
                ))}

                {segments.slice(1).map((seg) => {
                  const isFade = (seg.clip.transition_in || 'cut') !== 'cut';
                  return (
                    <button
                      key={`tr-${seg.clip.id}`}
                      onClick={(e) => { e.stopPropagation(); toggleTransition(seg.clip.id); }}
                      title={isFade
                        ? `${seg.clip.transition_in} ${seg.overlap.toFixed(1)} วิ — คลิกเปลี่ยนเป็นตัดตรง (เลือกแบบอื่นที่แผงขวา)`
                        : 'ตัดตรง — คลิกเปลี่ยนเป็นรอยต่อแบบจาง'}
                      className={`absolute top-1/2 z-20 flex h-5 w-5 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded border transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
                        isFade
                          ? 'border-[#D97757] bg-[#33251F] text-[#E89274]'
                          : 'border-[#4A4742] bg-[#232220] text-[#9C968F] hover:text-[#EDE9E3]'
                      }`}
                      style={{ left: seg.segStart * pxPerSec }}
                    >
                      {isFade ? <Waves className="h-3 w-3" /> : <Scissors className="h-3 w-3" />}
                    </button>
                  );
                })}
              </div>

              {/* caption track */}
              <div className="relative mt-1 rounded bg-[#181716]" style={{ height: CAPTION_H }}>
                {(cues || []).map((cue) => {
                  const selected = selection?.type === 'caption' && selection.id === cue._uid;
                  const w = Math.max(10, (cue.end - cue.start) * pxPerSec);
                  return (
                    <button
                      key={cue._uid}
                      onClick={() => selectCaption(cue._uid)}
                      onPointerDown={(e) => {
                        try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* drag still works */ }
                        captionDrag.current = {
                          uid: cue._uid, startX: e.clientX, start: cue.start, end: cue.end, moved: false,
                        };
                      }}
                      onPointerMove={(e) => {
                        const d = captionDrag.current;
                        if (!d || d.uid !== cue._uid) return;
                        const delta = (e.clientX - d.startX) / pxPerSec;
                        if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
                        if (!d.moved) { d.moved = true; dragBegin(); }
                        const shift = Math.max(-d.start, delta);
                        shiftCaption(cue._uid, {
                          start: Math.round((d.start + shift) * 100) / 100,
                          end: Math.round((d.end + shift) * 100) / 100,
                        });
                      }}
                      onPointerUp={(e) => {
                        const d = captionDrag.current;
                        captionDrag.current = null;
                        try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* fine */ }
                        if (d?.moved) dragEnd();
                      }}
                      title={cue.text}
                      className={`absolute top-1 h-[calc(100%-8px)] touch-none overflow-hidden rounded px-1.5 text-left text-[9px] leading-[18px] transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757] ${
                        selected
                          ? 'bg-[#33251F] text-[#EDE9E3] ring-2 ring-[#D97757]'
                          : 'bg-[#282724] text-[#C9C3BB] ring-1 ring-[#4A4742] hover:ring-[#6B6660]'
                      }`}
                      style={{ left: cue.start * pxPerSec, width: w }}
                    >
                      <span className="block truncate">{cue.text}</span>
                    </button>
                  );
                })}
              </div>

              {/* audio track */}
              <div className="relative mt-1 rounded bg-[#181716]" style={{ height: AUDIO_H }}>
                {audioDuration > 0 && (
                  <div
                    className="absolute top-1 flex h-[calc(100%-8px)] items-center overflow-hidden rounded bg-[#242A26] px-2 ring-1 ring-[#33463A]"
                    style={{ left: 0, width: audioDuration * pxPerSec }}
                    title="เสียงพากย์ + BGM ของทั้งคลิป (เปลี่ยนเพลงได้ที่แผงขวา)"
                  >
                    <span className="truncate text-[9px] text-[#8FBF9F]">
                      เสียงพากย์ + BGM{bgmLabel ? ` · ${bgmLabel}` : ' · ค่าเริ่มต้นของช่อง'}
                    </span>
                  </div>
                )}
                {sfxMarkers.map((cue) => (
                  <span
                    key={`sfx-${cue._uid}`}
                    title={`SFX: ${cue.sfx}`}
                    className="absolute top-0 h-full w-px bg-[#D97757]/70"
                    style={{ left: cue.start * pxPerSec }}
                  >
                    <span className="absolute -left-[3px] top-0 h-1.5 w-1.5 rounded-full bg-[#D97757]" />
                  </span>
                ))}
              </div>

              {/* the render is cut at the voiceover length, so show where that is */}
              {audioDuration > 0 && (
                <div
                  className="pointer-events-none absolute bottom-0 top-0 border-l border-dashed border-[#6B6660]"
                  style={{ left: audioDuration * pxPerSec }}
                  title="ความยาวเสียงพากย์ — เรนเดอร์จะตัดที่เส้นนี้"
                />
              )}

              {/* playhead */}
              <div
                className="pointer-events-none absolute z-30"
                style={{ left: playhead * pxPerSec, top: -RULER_H - TRACK_GAP, bottom: 0 }}
              >
                <div className="absolute bottom-0 left-0 top-0 w-0.5 -translate-x-1/2 bg-[#D97757]" />
                <div className="absolute top-0 h-2.5 w-2.5 -translate-x-1/2 rotate-45 bg-[#D97757]" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
