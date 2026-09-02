import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Film, MessageSquare, Music, Scissors, Waves } from 'lucide-react';
import TimelineClip from './TimelineClip';
import { CLIP_DRAG_TYPE } from './AssetPanel';
import { getAudioPeaks, MAX_DECODE_SECONDS } from '../../lib/audioPeaks';
import { formatTimecode } from '../../lib/timelineMath';

const RULER_H = 22;
const WAVE_COLUMNS = 1200;
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
      className="flex items-center gap-1.5 px-2 text-sm font-medium text-[#9C968F]"
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
  onDropClip,
  // Newer shell prop names. Both sets are accepted so the timeline keeps
  // working whichever shape the shell passes.
  onSelect,
  onClipChange,
  onCaptionChange,
  onBeginDrag,
  onEndDrag,
  onZoom,
  audioUrl,
  // Edge/body drags snap to these (clip boundaries, playhead, audio end).
  // Both default to "no snapping" so the timeline still works if a caller
  // doesn't wire them up.
  snapCandidates: snapPoints = [],
  snapFunction = (t) => t,
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
  const captionTrim = useRef(null);
  const bodyDrag = useRef(null);
  const [dropIndex, setDropIndex] = useState(null);
  const waveRef = useRef(null);
  const [waveInfo, setWaveInfo] = useState(null);

  const handleWheel = (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const dir = e.deltaY < 0 ? 1 : -1;
      onZoom?.(dir);
    }
  };

  // Real peaks for the audio track, decoded once per file (see audioPeaks.js)
  // and drawn into a fixed-column canvas that CSS stretches to the track
  // width -- zooming never re-decodes, and never allocates a 17000px canvas.
  useEffect(() => {
    let alive = true;
    if (!audioUrl) { setWaveInfo(null); return undefined; }
    getAudioPeaks(audioUrl, WAVE_COLUMNS).then((info) => { if (alive) setWaveInfo(info); });
    return () => { alive = false; };
  }, [audioUrl]);

  useEffect(() => {
    const canvas = waveRef.current;
    if (!canvas || !waveInfo?.peaks) return;
    const ctx = canvas.getContext('2d');
    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#8FBF9F';
    ctx.globalAlpha = 0.55;
    const mid = height / 2;
    for (let i = 0; i < WAVE_COLUMNS; i++) {
      const min = waveInfo.peaks[i * 2];
      const max = waveInfo.peaks[i * 2 + 1];
      const top = mid - max * mid;
      const bottom = mid - min * mid;
      ctx.fillRect(i, top, 1, Math.max(1, bottom - top));
    }
    ctx.globalAlpha = 1;
  }, [waveInfo]);

  // Dropping a clip from the media bin. The insert position is whichever
  // boundary the pointer is nearest, so a drop reads like where it landed.
  const indexFromX = (clientX) => {
    if (!laneRef.current) return segments.length;
    const t = (clientX - laneRef.current.getBoundingClientRect().left) / pxPerSec;
    let i = 0;
    while (i < segments.length && t > (segments[i].segStart + segments[i].segEnd) / 2) i += 1;
    return i;
  };
  const dragHasClip = (e) => Array.from(e.dataTransfer?.types || []).includes(CLIP_DRAG_TYPE);
  const onDragOverTrack = (e) => {
    if (!dragHasClip(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setDropIndex(indexFromX(e.clientX));
  };
  const onDropTrack = (e) => {
    if (!dragHasClip(e)) return;
    e.preventDefault();
    const at = indexFromX(e.clientX);
    setDropIndex(null);
    try {
      onDropClip?.(JSON.parse(e.dataTransfer.getData(CLIP_DRAG_TYPE)), at);
    } catch (err) { /* malformed payload -- nothing to insert */ }
  };

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

  const startTrim = (e, cue, edge) => {
    e.stopPropagation();
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
    captionTrim.current = {
      uid: cue._uid,
      edge,
      startX: e.clientX,
      start: cue.start,
      end: cue.end,
      moved: false,
    };
  };

  const moveTrim = (e) => {
    const d = captionTrim.current;
    if (!d) return;
    const delta = (e.clientX - d.startX) / pxPerSec;
    if (!d.moved && Math.abs(e.clientX - d.startX) < 3) return;
    if (!d.moved) { d.moved = true; dragBegin(); }

    if (d.edge === 'left') {
      const rawStart = Math.max(0, Math.min(d.end - 0.2, d.start + delta));
      const snapped = snapFunction(rawStart, snapPoints);
      shiftCaption(d.uid, { start: Math.round(snapped * 100) / 100 });
    } else {
      const rawEnd = Math.max(d.start + 0.2, d.end + delta);
      const snapped = snapFunction(rawEnd, snapPoints);
      shiftCaption(d.uid, { end: Math.round(snapped * 100) / 100 });
    }
  };

  const endTrim = (e) => {
    const d = captionTrim.current;
    captionTrim.current = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
    if (d?.moved) dragEnd();
  };

  const sfxMarkers = (cues || []).filter((c) => c.sfx);

  return (
    <div className="flex h-full flex-col bg-[#1C1B19]">
      <div onWheel={handleWheel} className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden">
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
                  <span className="absolute top-2 -translate-x-1/2 font-mono text-xs text-[#9C968F]">
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
              <div
                className="relative rounded bg-[#181716]"
                style={{ height: VIDEO_H }}
                onDragOver={onDragOverTrack}
                onDragLeave={() => setDropIndex(null)}
                onDrop={onDropTrack}
              >
                {dropIndex !== null && (
                  <div
                    className="pointer-events-none absolute top-0 z-40 h-full w-0.5 -translate-x-1/2 bg-[#D97757]"
                    style={{
                      left: (dropIndex >= segments.length
                        ? (segments.length ? segments[segments.length - 1].segEnd : 0)
                        : segments[dropIndex].segStart) * pxPerSec,
                    }}
                  />
                )}
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
                    snapCandidates={snapPoints}
                    snapFunction={snapFunction}
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
                  const w = Math.max(14, (cue.end - cue.start) * pxPerSec);
                  return (
                    <div
                      key={cue._uid}
                      onClick={() => selectCaption(cue._uid)}
                      title={`${cue.text} (${cue.start.toFixed(2)}s - ${cue.end.toFixed(2)}s)`}
                      className={`group absolute top-1 h-[calc(100%-8px)] touch-none select-none rounded text-left text-xs leading-[18px] transition-colors duration-150 flex items-center ${
                        selected
                          ? 'bg-[#33251F] text-[#EDE9E3] ring-2 ring-[#D97757]'
                          : 'bg-[#282724] text-[#C9C3BB] ring-1 ring-[#4A4742] hover:ring-[#6B6660]'
                      }`}
                      style={{ left: cue.start * pxPerSec, width: w }}
                    >
                      {/* Left Trim Handle */}
                      <div
                        onPointerDown={(e) => startTrim(e, cue, 'left')}
                        onPointerMove={moveTrim}
                        onPointerUp={endTrim}
                        onPointerCancel={endTrim}
                        title="ลากเพื่อยืด/หดเวลาเริ่มต้น"
                        className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-l hover:bg-[#D97757] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
                      >
                        <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
                      </div>

                      {/* Middle Body (Drag to shift entire cue) */}
                      <div
                        onPointerDown={(e) => {
                          try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
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
                          const rawStart = d.start + shift;
                          const snappedStart = snapFunction(rawStart, snapPoints);
                          const correction = snappedStart - rawStart;
                          shiftCaption(cue._uid, {
                            start: Math.round((d.start + shift + correction) * 100) / 100,
                            end: Math.round((d.end + shift + correction) * 100) / 100,
                          });
                        }}
                        onPointerUp={(e) => {
                          const d = captionDrag.current;
                          captionDrag.current = null;
                          try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
                          if (d?.moved) dragEnd();
                        }}
                        onPointerCancel={(e) => {
                          const d = captionDrag.current;
                          captionDrag.current = null;
                          try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
                          if (d?.moved) dragEnd();
                        }}
                        className="flex-1 min-w-0 h-full flex items-center px-1 overflow-hidden cursor-grab active:cursor-grabbing"
                      >
                        <span className="truncate">{cue.text}</span>
                      </div>

                      {/* Right Trim Handle */}
                      <div
                        onPointerDown={(e) => startTrim(e, cue, 'right')}
                        onPointerMove={moveTrim}
                        onPointerUp={endTrim}
                        onPointerCancel={endTrim}
                        title="ลากเพื่อยืด/หดเวลาสิ้นสุด"
                        className="h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-r hover:bg-[#D97757] bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100"
                      >
                        <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
                      </div>
                    </div>
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
                    {waveInfo?.peaks && (
                      <canvas
                        ref={waveRef}
                        width={WAVE_COLUMNS}
                        height={AUDIO_H}
                        className="pointer-events-none absolute inset-0 h-full w-full"
                      />
                    )}
                    <span className="relative truncate text-xs text-[#8FBF9F] drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)]">
                      เสียงพากย์ + BGM{bgmLabel ? ` · ${bgmLabel}` : ' · ค่าเริ่มต้นของช่อง'}
                      {waveInfo?.truncated ? ` · รูปคลื่นแสดง ${MAX_DECODE_SECONDS} วิแรก` : ''}
                    </span>
                  </div>
                )}
                {sfxMarkers.map((cue) => (
                  <button
                    key={`sfx-${cue._uid}`}
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSeek?.(cue.start);
                      selectCaption(cue._uid);
                    }}
                    title={`⚡ SFX: ${cue.sfx} (คลิกเพื่อกระโดดไปที่จังหวะนี้)`}
                    className="group/sfx absolute top-0.5 z-20 flex -translate-x-1/2 cursor-pointer items-center gap-0.5 rounded-full border border-black/40 bg-[#D97757] px-1.5 py-0.5 shadow-lg transition-all hover:scale-110 hover:bg-[#25F4EE] hover:z-30"
                    style={{ left: cue.start * pxPerSec }}
                  >
                    <span className="text-[9px] font-mono font-extrabold uppercase text-black leading-none">{cue.sfx}</span>
                  </button>
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
