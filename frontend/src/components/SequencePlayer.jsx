import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, Eye } from 'lucide-react';
import { toMediaUrl } from '../lib/mediaUrl';

// Must match SFXManager/video_editor.py's crossfade overlap exactly, or the
// preview's segment timing (and therefore captions) drifts from what Apply
// actually renders.
const FADE_DURATION = 0.4;
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
export default function SequencePlayer({ clips, cues = [] }) {
  const canvasRef = useRef(null);
  const videoElsRef = useRef({});
  const rafRef = useRef(null);
  const clockRef = useRef({ startWall: 0, startT: 0 });

  const [durations, setDurations] = useState({});
  const [metadataReady, setMetadataReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playhead, setPlayhead] = useState(0);

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
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clipKey]);

  const segments = useMemo(() => {
    if (!metadataReady) return [];
    let acc = 0;
    return clips.map((c, i) => {
      const srcDur = durations[c.id] || 0;
      const dur = Math.max(0.1, (c.trim_end ?? srcDur) - c.trim_start);
      const isFade = i > 0 && c.transition_in === 'fade';
      const segStart = i === 0 ? 0 : (isFade ? acc - FADE_DURATION : acc);
      const segEnd = segStart + dur;
      acc = segEnd;
      return { clip: c, srcDur, isFade, segStart, segEnd };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clipKey, metadataReady]);

  const totalDuration = segments.length ? segments[segments.length - 1].segEnd : 0;

  // Given a global sequence time, which clip(s) to draw and at what alpha
  // -- two entries during a fade's overlap window, one otherwise.
  const getDrawPlan = (t) => {
    let idx = segments.findIndex(s => t >= s.segStart && t < s.segEnd);
    if (idx === -1) idx = t < 0 ? 0 : segments.length - 1;
    const seg = segments[idx];
    const localTime = seg.clip.trim_start + (t - seg.segStart);
    const plan = [{ seg, localTime, alpha: 1 }];
    if (seg.isFade && idx > 0 && t < seg.segStart + FADE_DURATION) {
      const prevSeg = segments[idx - 1];
      const prevLocalTime = prevSeg.clip.trim_start + (t - prevSeg.segStart);
      const alpha = Math.max(0, Math.min(1, (t - seg.segStart) / FADE_DURATION));
      plan[0] = { seg: prevSeg, localTime: prevLocalTime, alpha: 1 - alpha };
      plan.push({ seg, localTime, alpha });
    }
    return plan;
  };

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
      setIsPlaying(true);
    }
  };

  const seekTo = (t) => {
    const clamped = Math.max(0, Math.min(totalDuration, t));
    Object.values(videoElsRef.current).forEach(v => v?.pause());
    setPlayhead(clamped);
    clockRef.current = { startWall: performance.now(), startT: clamped };
    renderAt(clamped);
  };

  const handleScrubInput = (e) => {
    if (isPlaying) setIsPlaying(false);
    seekTo(parseFloat(e.target.value));
  };

  return (
    <div className="space-y-2.5">
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
          />
        ))}
      </div>

      <div className="relative mx-auto rounded-xl overflow-hidden bg-black border border-white/10" style={{ width: '100%', maxWidth: 260, aspectRatio: '9/16' }}>
        <canvas ref={canvasRef} width={CANVAS_W} height={CANVAS_H} className="w-full h-full" />
        {!metadataReady && clips.length > 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-[10px] text-slate-400 bg-black/60">
            กำลังโหลดวิดีโอ...
          </div>
        )}
        {clips.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-[10px] text-slate-500">
            เพิ่มคลิปเข้าไทม์ไลน์เพื่อดูพรีวิว
          </div>
        )}
        {metadataReady && clips.length > 0 && (
          <button
            onClick={togglePlay}
            className="absolute inset-0 flex items-center justify-center bg-black/0 hover:bg-black/20 transition-colors cursor-pointer group"
          >
            <div className="w-11 h-11 rounded-full bg-black/50 group-hover:bg-[#25F4EE]/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
              {isPlaying ? <Pause className="w-5 h-5 text-white" /> : <Play className="w-5 h-5 text-white ml-0.5" />}
            </div>
          </button>
        )}
      </div>

      {metadataReady && clips.length > 0 && (
        <>
          <div className="flex items-center gap-2">
            <button
              onClick={togglePlay}
              className="w-7 h-7 rounded-lg bg-[#25F4EE] text-slate-950 flex items-center justify-center flex-shrink-0 cursor-pointer"
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
            </button>
            <input
              type="range" min={0} max={totalDuration || 0} step={0.01}
              value={playhead}
              onChange={handleScrubInput}
              className="flex-1 accent-[#25F4EE]"
            />
            <span className="text-[10px] font-mono text-slate-400 w-16 text-right flex-shrink-0">
              {playhead.toFixed(1)}s / {totalDuration.toFixed(1)}s
            </span>
          </div>
          <p className="text-[9px] text-slate-500 flex items-center gap-1">
            <Eye className="w-3 h-3" /> พรีวิวรวมทั้ง sequence แบบประมาณ (ฟอนต์/สีจริงยึดผลจาก Apply เท่านั้น)
          </p>
        </>
      )}
    </div>
  );
}
