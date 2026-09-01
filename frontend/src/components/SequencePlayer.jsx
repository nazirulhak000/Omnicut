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

function drawVideoFrame(ctx, video) {
  if (!video || !video.videoWidth) return;
  const vw = video.videoWidth, vh = video.videoHeight;
  const vRatio = vw / vh, cRatio = CANVAS_W / CANVAS_H;
  let sx, sy, sw, sh;
  if (vRatio > cRatio) {
    sh = vh; sw = vh * cRatio; sy = 0; sx = (vw - sw) / 2;
  } else {
    sw = vw; sh = vw / cRatio; sx = 0; sy = (vh - sh) / 2;
  }
  ctx.drawImage(video, sx, sy, sw, sh, 0, 0, CANVAS_W, CANVAS_H);
}

function drawCaption(ctx, cues, t) {
  const cue = cues.find(c => t >= c.start && t < c.end);
  if (!cue || !cue.text) return;
  const fontSize = Math.round(CANVAS_W * 0.075);
  ctx.font = `900 ${fontSize}px Kanit, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineWidth = fontSize * 0.18;
  ctx.strokeStyle = 'rgba(0,0,0,0.85)';
  ctx.fillStyle = '#fff';
  const x = CANVAS_W / 2;
  const y = CANVAS_H * 0.8;
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
function SequencePlayer({ clips, cues = [], compact = false, onPlayhead, onDurations }, ref) {
  const canvasRef = useRef(null);
  const videoElsRef = useRef({});
  const rafRef = useRef(null);
  const clockRef = useRef({ startWall: 0, startT: 0 });

  const [durations, setDurations] = useState({});
  const [metadataReady, setMetadataReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playhead, setPlayhead] = useState(0);
  const playheadRef = useRef(0);

  const clipKey = clips.map(c => `${c.id}:${c.source_path}:${c.trim_start}:${c.trim_end}:${c.transition_in}`).join('|');

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
      drawVideoFrame(ctx, video);
    });
    ctx.globalAlpha = 1;
    drawCaption(ctx, cues, t);
  };

  useEffect(() => {
    renderAt(playhead);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segments]);

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
          drawVideoFrame(ctx, video);
        });
        ctx.globalAlpha = 1;
        drawCaption(ctx, cues, t);
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
    const clamped = Math.max(0, Math.min(totalDuration, t));
    Object.values(videoElsRef.current).forEach(v => v?.pause());
    setPlayhead(clamped);
    playheadRef.current = clamped;
    onPlayhead?.(clamped);
    clockRef.current = { startWall: performance.now(), startT: clamped };
    renderAt(clamped);   // immediate (may be stale); onSeeked repaints when decoded
  };

  useImperativeHandle(ref, () => ({
    seekTo,
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
    <div className="flex min-h-0 w-full flex-col items-center gap-2">
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

      <div className="relative mx-auto rounded-2xl overflow-hidden bg-black border border-white/[0.1] shadow-2xl" style={{ maxWidth: 260, maxHeight: '100%', aspectRatio: '9/16', width: 'auto', height: '100%' }}>
        <canvas ref={canvasRef} width={CANVAS_W} height={CANVAS_H} className="w-full h-full" />
        {!metadataReady && clips.length > 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-slate-400 bg-black/70 backdrop-blur-sm">
            กำลังโหลดวิดีโอ...
          </div>
        )}
        {clips.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-slate-500">
            เพิ่มคลิปเข้าไทม์ไลน์เพื่อดูพรีวิว
          </div>
        )}
        {metadataReady && clips.length > 0 && (
          <button
            onClick={togglePlay}
            className="absolute inset-0 flex items-center justify-center bg-black/0 hover:bg-black/20 transition-colors cursor-pointer group"
          >
            <div className="w-12 h-12 rounded-full bg-black/60 group-hover:bg-[#25F4EE] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all text-white group-hover:text-slate-950 shadow-lg">
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
            </div>
          </button>
        )}
      </div>

      {metadataReady && clips.length > 0 && (
        <>
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={togglePlay}
              className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-[#25F4EE] text-white flex items-center justify-center flex-shrink-0 cursor-pointer shadow-md shadow-[#FE2C55]/20 hover:brightness-110 transition-all"
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
            <span className="text-xs font-mono text-slate-400 w-20 text-right flex-shrink-0 font-bold">
              {playhead.toFixed(1)}s / {totalDuration.toFixed(1)}s
            </span>
          </div>
          {!compact && (
            <p className="text-[11px] text-slate-400 flex items-center gap-1">
              <Eye className="w-3.5 h-3.5 text-[#25F4EE]" /> พรีวิวรวมทั้ง sequence แบบประมาณ (ฟอนต์/สีจริงยึดผลจาก Apply เท่านั้น)
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default forwardRef(SequencePlayer);
