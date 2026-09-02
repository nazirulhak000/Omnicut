import React, { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { Play, Pause, Eye } from 'lucide-react';
import { toMediaUrl } from '../lib/mediaUrl';
import {
  buildSegments, totalDuration as totalDurationOf, getDrawPlan as planAt
} from '../lib/timelineMath';

const CANVAS_W = 540;
const CANVAS_H = 960;
// How far a clip's decoded currentTime may drift from the wall-clock-derived
// target before we force a reseek. Hidden <video> elements were measured
// decoding at ~3-7x real time in this environment (Chromium doesn't pace
// paint/compositor work the same way for off-screen media) -- an
// independent clock plus periodic resync keeps playback at real speed
// regardless of how fast the browser is willing to decode.
const RESYNC_THRESHOLD = 0.15;

/**
 * CSS filter that approximates video_editor.py's per-clip `eq`. ffmpeg's
 * brightness is an additive offset (-0.3..0.3) while canvas brightness is a
 * multiplier, so it is mapped to 1 + b -- close enough to judge a grade by,
 * and the rendered file is still the source of truth.
 */
function clipFilter(clip) {
  if (!clip) return 'none';
  const parts = [];
  const b = clip.brightness ?? 0;
  const c = clip.contrast ?? 1;
  const sat = clip.saturation ?? 1;
  if (Math.abs(b) > 1e-3) parts.push(`brightness(${(1 + b).toFixed(3)})`);
  if (Math.abs(c - 1) > 1e-3) parts.push(`contrast(${c.toFixed(3)})`);
  if (Math.abs(sat - 1) > 1e-3) parts.push(`saturate(${sat.toFixed(3)})`);
  return parts.length ? parts.join(' ') : 'none';
}

function drawVideoFrame(ctx, video, clip) {
  if (!video || !video.videoWidth) return;
  const vw = video.videoWidth, vh = video.videoHeight;
  const vRatio = vw / vh, cRatio = CANVAS_W / CANVAS_H;
  let sx, sy, sw, sh;
  if (vRatio > cRatio) {
    sh = vh; sw = vh * cRatio; sy = 0; sx = (vw - sw) / 2;
  } else {
    sw = vw; sh = vw / cRatio; sx = 0; sy = (vh - sh) / 2;
  }

  // Zoom crops into that cover-fit rect; pan slides it across the room the
  // zoom left, the same -1..1 mapping frame_geometry() uses in video_editor.py.
  const zoom = Math.min(3, Math.max(1, clip?.zoom || 1));
  if (zoom > 1.001) {
    const zw = sw / zoom, zh = sh / zoom;
    const roomX = sw - zw, roomY = sh - zh;
    const panX = Math.min(1, Math.max(-1, clip?.pan_x || 0));
    const panY = Math.min(1, Math.max(-1, clip?.pan_y || 0));
    sx += (roomX / 2) * (1 + panX);
    sy += (roomY / 2) * (1 + panY);
    sw = zw; sh = zh;
  }
  ctx.drawImage(video, sx, sy, sw, sh, 0, 0, CANVAS_W, CANVAS_H);
}

// Mirrors the .ass style the renderer burns: CAPTION_POSITIONS in
// subtitle_engine.py puts the block at the bottom (margin 420 of 1920),
// centre, or top (margin 260). Same fractions here so the preview does not
// promise a placement the file will not have.
const CAPTION_Y = { bottom: 1 - 420 / 1920, middle: 0.5, top: 260 / 1920 };

function drawCaption(ctx, cues, t, style = {}) {
  const cue = cues.find(c => t >= c.start && t < c.end);
  if (!cue || !cue.text) return;
  const scale = Math.min(2, Math.max(0.5, style.captionScale ?? 1));
  const fontSize = Math.round(CANVAS_W * 0.075 * scale);
  ctx.font = `900 ${fontSize}px Kanit, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineWidth = fontSize * 0.18;
  ctx.strokeStyle = 'rgba(0,0,0,0.85)';
  ctx.fillStyle = style.captionColor || '#fff';
  const x = CANVAS_W / 2;
  const y = CANVAS_H * (CAPTION_Y[style.captionPosition] ?? CAPTION_Y.bottom);
  ctx.strokeText(cue.text, x, y, CANVAS_W * 0.92);
  ctx.fillText(cue.text, x, y, CANVAS_W * 0.92);
}

/**
 * Plays `clips` back-to-back as one continuous sequence in a single canvas
 * (approximate preview -- real output only comes from Apply's ffmpeg
 * render, per this project's "accurate render, willing to wait" choice).
 * Segment timing math (fade eats FADE_DURATION of overlap) mirrors
 * video_editor.py's has_fade branch so what plays here lines up with what
 * Apply produces.
 *
 * The global playhead is driven by an independent performance.now() clock,
 * not by trusting a <video> element's own playback rate -- see
 * RESYNC_THRESHOLD's comment for why.
 */
function SequencePlayer({ clips, cues = [], compact = false, onPlayhead, onDurations, captionStyle = {} }, ref) {
  const canvasRef = useRef(null);
  const videoElsRef = useRef({});
  const rafRef = useRef(null);
  const clockRef = useRef({ startWall: 0, startT: 0 });

  const [durations, setDurations] = useState({});
  const [metadataReady, setMetadataReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playhead, setPlayhead] = useState(0);
  const playheadRef = useRef(0);

  const captionKey = `${captionStyle.captionPosition}:${captionStyle.captionColor}:${captionStyle.captionScale}`;
  const clipKey = clips.map(c => `${c.id}:${c.source_path}:${c.trim_start}:${c.trim_end}:${c.transition_in}:${c.transition_duration}:${c.brightness}:${c.contrast}:${c.saturation}:${c.zoom}:${c.pan_x}:${c.pan_y}`).join('|');

  // Load real duration for every clip up front -- segment timing needs it
  // (a clip with trim_end === null trims to "the source's own end").
  useEffect(() => {
    setMetadataReady(false);
    setIsPlaying(false);
    setPlayhead(0);
    let cancelled = false;

    const waits = clips.map(c => new Promise((resolve) => {
      const v = videoElsRef.current[c.id];
      if (!v) return resolve();
      if (v.readyState >= 1) return resolve();
      const onLoaded = () => { v.removeEventListener('loadedmetadata', onLoaded); resolve(); };
      v.addEventListener('loadedmetadata', onLoaded);
    }));

    Promise.all(waits).then(() => {
      if (cancelled) return;
      const d = {};
      clips.forEach(c => { d[c.id] = videoElsRef.current[c.id]?.duration || 0; });
      setDurations(d);
      setMetadataReady(true);
      onDurations?.(d);
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clipKey]);

  const segments = useMemo(
    () => (metadataReady ? buildSegments(clips, durations) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [clipKey, metadataReady, durations]
  );

  const totalDuration = totalDurationOf(segments);
  playheadRef.current = playhead;

  const getDrawPlan = (t) => planAt(segments, t);

  const renderAt = (t) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!ctx || !segments.length) return;
    const plan = getDrawPlan(t);
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    plan.forEach(({ seg, alpha }) => {
      const video = videoElsRef.current[seg.clip.id];
      if (!video) return;
      ctx.globalAlpha = alpha;
      ctx.filter = clipFilter(seg.clip);
      drawVideoFrame(ctx, video, seg.clip);
    });
    ctx.globalAlpha = 1;
    ctx.filter = 'none';
    drawCaption(ctx, cues, t, captionStyle);
  };

  useEffect(() => {
    renderAt(playhead);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segments, captionKey]);

  useEffect(() => {
    if (!isPlaying || segments.length === 0) return;

    const tick = () => {
      const t = clockRef.current.startT + (performance.now() - clockRef.current.startWall) / 1000;

      if (t >= totalDuration) {
        Object.values(videoElsRef.current).forEach(v => v?.pause());
        setPlayhead(totalDuration);
      onPlayhead?.(totalDuration);
        renderAt(totalDuration);
        setIsPlaying(false);
        return;
      }

      const plan = getDrawPlan(t);
      const neededIds = new Set(plan.map(p => p.seg.clip.id));

      plan.forEach(({ seg, localTime }) => {
        const v = videoElsRef.current[seg.clip.id];
        if (!v) return;
        if (v.paused) {
          v.currentTime = localTime;
          v.play().catch(() => {});
        } else if (Math.abs(v.currentTime - localTime) > RESYNC_THRESHOLD) {
          v.currentTime = localTime;
        }
      });

      Object.entries(videoElsRef.current).forEach(([id, v]) => {
        if (v && !v.paused && !neededIds.has(id)) v.pause();
      });

      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
        plan.forEach(({ seg, alpha }) => {
          const video = videoElsRef.current[seg.clip.id];
          if (!video) return;
          ctx.globalAlpha = alpha;
          ctx.filter = clipFilter(seg.clip);
          drawVideoFrame(ctx, video, seg.clip);
        });
        ctx.globalAlpha = 1;
        ctx.filter = 'none';
        drawCaption(ctx, cues, t, captionStyle);
      }

      setPlayhead(t);
      onPlayhead?.(t);
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, segments, cues, totalDuration]);

  const togglePlay = () => {
    if (!segments.length) return;
    if (isPlaying) {
      Object.values(videoElsRef.current).forEach(v => v?.pause());
      setIsPlaying(false);
    } else {
      const startT = playhead >= totalDuration ? 0 : playhead;
      clockRef.current = { startWall: performance.now(), startT };
      setPlayhead(startT);
      onPlayhead?.(startT);
      setIsPlaying(true);
    }
  };

  const seekTo = (t) => {
    const maxDur = totalDuration || 999999;
    const clamped = Math.max(0, Math.min(maxDur, t));
    Object.values(videoElsRef.current).forEach(v => v?.pause());
    setPlayhead(clamped);
    playheadRef.current = clamped;
    onPlayhead?.(clamped);
    clockRef.current = { startWall: performance.now(), startT: clamped };

    const plan = getDrawPlan(clamped);
    plan.forEach(({ seg, localTime }) => {
      const v = videoElsRef.current[seg.clip.id];
      if (v) {
        v.currentTime = localTime;
      }
    });

    renderAt(clamped); // immediate draw; onSeeked will repaint crisp frame when decoded
  };

  useImperativeHandle(ref, () => ({
    seekTo,
    seek: seekTo,        // callers use both names

    play: () => { if (!isPlaying) togglePlay(); },
    pause: () => { if (isPlaying) togglePlay(); },
    toggle: togglePlay,
    isPlaying: () => isPlaying,
  }));

  const handleScrubInput = (e) => {
    if (isPlaying) setIsPlaying(false);
    seekTo(parseFloat(e.target.value));
  };

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-center gap-2">
      {/* Hidden decode elements -- one per clip, always mounted so metadata
          loads and pre-seek/pre-play can happen ahead of a cut/fade.
          Kept technically visible (1px, off-screen, opacity near 0) rather
          than display:none, which lets Chromium decode well past real-time
          since nothing paces it against the compositor (measured ~3-7x) --
          the wall-clock playhead above already corrects for any remaining
          drift, this just keeps it small. */}
      <div className="absolute -left-[9999px] top-0 w-px h-px overflow-hidden opacity-0" aria-hidden="true">
        {clips.map((c) => (
          <video
            key={c.id}
            ref={(el) => { if (el) videoElsRef.current[c.id] = el; }}
            src={toMediaUrl(c.source_path)}
            preload="auto"
            muted
            playsInline
            onLoadedData={() => { if (!isPlaying) renderAt(playheadRef.current); }}
            onSeeked={() => { if (!isPlaying) renderAt(playheadRef.current); }}
          />
        ))}
      </div>

      {/* Stage. This wrapper is the one that flexes: it takes whatever height
          the transport row leaves over, and the 9:16 box inside sizes itself
          against that. Sizing the 9:16 box directly off the column made it
          claim the full height and push the transport row off the pane. */}
      <div className="flex min-h-0 w-full flex-1 items-center justify-center">
        <div
          className="relative overflow-hidden rounded-2xl border border-[#363430] bg-black shadow-2xl"
          style={{ height: '100%', width: 'auto', aspectRatio: '9/16', maxWidth: '100%' }}
        >
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            className="absolute inset-0 h-full w-full"
          />
          {!metadataReady && clips.length > 0 && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/70 text-xs font-bold text-[#9C968F] backdrop-blur-sm">
              กำลังโหลดวิดีโอ...
            </div>
          )}
          {clips.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-[#6B6660]">
              เพิ่มคลิปเข้าไทม์ไลน์เพื่อดูพรีวิว
            </div>
          )}
          {metadataReady && clips.length > 0 && (
            <button
              onClick={togglePlay}
              className="group absolute inset-0 flex cursor-pointer items-center justify-center bg-black/0 transition-colors hover:bg-black/20"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-black/60 text-white opacity-0 shadow-lg transition-all group-hover:bg-[#D97757] group-hover:opacity-100">
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </div>
            </button>
          )}
        </div>
      </div>

      {metadataReady && clips.length > 0 && (
        <>
          {/* Compact mode has no scrub bar, so the button + timecode would
              otherwise sit far left of a centred preview. */}
          <div className={`flex w-full flex-shrink-0 items-center gap-2 pt-1 ${compact ? 'justify-center' : ''}`}>
            <button
              onClick={togglePlay}
              className="w-8 h-8 rounded-xl bg-[#D97757] text-white flex items-center justify-center flex-shrink-0 cursor-pointer hover:bg-[#C2683D] transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757]"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
            </button>
            {!compact && (
              <input
                type="range" min={0} max={totalDuration || 0} step={0.01}
                value={playhead}
                onChange={handleScrubInput}
                className="flex-1 accent-[#D97757]"
              />
            )}
            <span className="text-xs font-mono text-[#9C968F] w-20 text-right flex-shrink-0 font-bold">
              {playhead.toFixed(1)}s / {totalDuration.toFixed(1)}s
            </span>
          </div>
          {!compact && (
            <p className="flex flex-shrink-0 items-center gap-1 text-sm text-[#9C968F]">
              <Eye className="w-3.5 h-3.5 text-[#9C968F]" /> พรีวิวรวมทั้ง sequence แบบประมาณ (ฟอนต์/สีจริงยึดผลจาก Apply เท่านั้น)
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default forwardRef(SequencePlayer);
