import React, { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { Play, Pause, Eye } from 'lucide-react';
import { toMediaUrl } from '../lib/mediaUrl';
import { createLutRenderer, loadCube } from '../lib/lut3d';
import {
  buildSegments, totalDuration as totalDurationOf, getDrawPlan as planAt
} from '../lib/timelineMath';

const CANVAS_W = 540;
const CANVAS_H = 960;
// How far a stream's decoded currentTime may drift from the master clock
// before it is pulled back. Hidden <video> elements were measured decoding at
// ~3-7x real time in this environment (Chromium doesn't pace paint/compositor
// work the same way for off-screen media) -- an independent clock plus these
// resyncs keeps playback at real speed regardless of how fast the browser is
// willing to decode.
//
// There used to be a single RESYNC_THRESHOLD here that nothing read, while the
// values actually in force sat as literals spread through the tick.
const RESYNC = {
  AUDIO: 0.3,        // media element (voice/BGM) vs the master clock
  VIDEO_HARD: 0.4,   // past this a video is seeked rather than slewed
  VIDEO_SLEW: 0.04,  // inside this a video is nudged +-6% instead of seeked
  START: 0.12,       // close enough to start a paused clip without seeking
  PREROLL: 0.08,     // close enough to leave a pre-rolled clip where it is
};

// Mix constants, paired one-for-one with SFXManager.mix_audio_track's ffmpeg
// graph (scripts/sfx_manager.py) so the preview's stem playback lands at the
// same level and the same time as the rendered mix. Change one side, change
// the other -- see .agents/rules/preview_render_parity.md.
const AUDIO_MIX = {
  VOICE_GAIN: 1.0,              // voice_vol   -- sfx_manager.py:61
  // A clip's own audio is mixed in at the clip's `volume` (video_editor.py's
  // per-clip `volume=` filter), then the whole raw-audio bus meets the voice
  // bed through amix with normalize=0 -- so no extra scaling here.
  CLIP_GAIN: 1.0,
  BGM_GAIN: 0.12,               // bgm_vol     -- sfx_manager.py:60
  SFX_GAIN: 0.28,               // sfx_vol     -- sfx_manager.py:63
  // The render ducks with sidechaincompress, which has no WebAudio equivalent.
  // Its threshold/ratio were picked by measuring 13.7 dB of reduction while
  // the voice speaks, so the preview applies that same 13.7 dB as a plain gain
  // envelope over the cue spans: 10^(-13.7/20).
  BGM_DUCK_GAIN: 0.2065,
  BGM_DUCK_ATTACK: 0.020,       // attack=20   -- sfx_manager.py:157
  BGM_DUCK_RELEASE: 0.300,      // release=300 -- sfx_manager.py:157
  BGM_FADE_OUT: 0.35,           // afade=t=out:d=0.35 -- sfx_manager.py:146
  BGM_TEMPO_BASELINE: 10.0,     // BASELINE_CHARS_PER_SEC -- sfx_manager.py:132
  SFX_PRE_ROLL: 0.12,           // pre_roll    -- sfx_manager.py:109
  SFX_MIN_TIME: 0.02,           // max(0.02, ...) -- sfx_manager.py:110
  SFX_LOOKAHEAD: 0.5,           // how early a one-shot is handed to WebAudio
  SFX_LATE_LIMIT: 0.25,         // a hit later than this is dropped, not rushed
};

// Same word list the render uses to decide a transition whoosh starts early.
const TRANSITION_SFX_WORDS = ['whoosh', 'swish', 'swoosh', 'transition'];

/** Timeline time an SFX fires at, matching sfx_manager.py's adelay exactly. */
function sfxFireTime(cueStart, sfxId) {
  const low = String(sfxId || '').toLowerCase();
  const preRoll = TRANSITION_SFX_WORDS.some((w) => low.includes(w)) ? AUDIO_MIX.SFX_PRE_ROLL : 0;
  const secs = Math.max(AUDIO_MIX.SFX_MIN_TIME, (Number(cueStart) || 0) - preRoll);
  // The render floors to whole milliseconds (int(secs * 1000)); match it so the
  // two never disagree by a sub-millisecond rounding step.
  return Math.floor(secs * 1000) / 1000;
}

/**
 * The render nudges the BGM's tempo toward the script's reading speed
 * (atempo, clamped to +-8%). Reproduced here from the same cue text so the bed
 * loops at the same rate -- with the caveat that playbackRate shifts pitch
 * where atempo preserves it.
 */
function bgmTempoRatio(cues) {
  const totalChars = (cues || []).reduce((s, c) => s + String(c.text || '').length, 0);
  const span = (cues || []).reduce(
    (s, c) => s + Math.max(0.01, (Number(c.end) || 0) - (Number(c.start) || 0)), 0
  );
  const cps = span > 0 ? totalChars / span : AUDIO_MIX.BGM_TEMPO_BASELINE;
  return Math.min(1.08, Math.max(0.92, cps / AUDIO_MIX.BGM_TEMPO_BASELINE));
}

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

function mirrorFlag(clip) { return !!clip?.mirror; }

// ---------------------------------------------------------------- transitions
// Every boundary used to preview as a crossfade, so a wipe, a slide and a
// circle all looked the same until the file came out of ffmpeg. These are
// ffmpeg xfade's own geometries, measured off real renders rather than guessed:
// two inputs were built to carry their own coordinates (input A its x in the
// red channel, input B its y in the blue channel) so every output pixel said
// which input it came from and where in that input it sat.
//
// Measured at progress 0.5 on a 120x200 frame:
//   wipeleft   A kept x<=60, B took x>=61, no displacement
//   wiperight  mirrored
//   wipeup     A kept y<=100, B took y>=101
//   wipedown   mirrored
//   slideleft  A displaced by -60px (-p*W), B entered from the right
//   slideright A displaced by +60px, B entered from the left
//   slideup    B displaced by +100px (+(1-p)*H): the pair travels up as one
//   slidedown  mirrored
//   dissolve   50/50 per-pixel noise, deterministic, monotonic reveal
//   circleopen weight of B = smoothstep(0, 1, (1 - r/z) + 3*(p - 0.5))
//   circleclose same with r/z instead of (1 - r/z)
// The circle fits are exact to within 0.03 of weight across the whole radius
// at every progress from 0.1 to 0.9.
const SMOOTHSTEP = (x) => {
  const c = Math.max(0, Math.min(1, x));
  return c * c * (3 - 2 * c);
};

// fadeblack/fadewhite dip through a solid colour rather than crossfading.
// Measured on a 30-frame transition: the outgoing frame reaches the bridge
// colour at p = 0.167 and the incoming one starts leaving it at p = 0.267,
// with an S-curve on each side. Reproduced to within 0.06 of weight -- the
// exact easing of a one-sixth-of-a-transition dip is below what the eye can
// separate, and the rendered file remains the source of truth.
const FADE_BRIDGE_OUT = 1 / 6;
const FADE_BRIDGE_IN = 0.2667;

function bridgeWeights(progress) {
  const wA = 1 - SMOOTHSTEP(progress / FADE_BRIDGE_OUT);
  const wB = SMOOTHSTEP((progress - FADE_BRIDGE_IN) / (1 - FADE_BRIDGE_IN));
  return { wA, wB, bridge: Math.max(0, 1 - wA - wB) };
}

// `dissolve` reveals the incoming clip per pixel. Measured on real renders: the
// revealed share equals progress exactly, no pixel ever reverts as progress
// grows, and the pattern is fine-grained per-pixel noise, not blocks. The
// pattern is ffmpeg's own and is not the common sin-hash -- tested and it
// agreed with the real frames only 59% of the time, i.e. a coin flip -- so the
// preview uses its own uniform noise with a fixed seed. Same character, same
// share, same monotonic reveal; the individual pixels differ, which is the one
// approximation here and is invisible on a moving frame.
let dissolveNoise = null;
let dissolveMaskCanvas = null;
let dissolveImage = null;
let dissolveWords = null;
let dissolveThreshold = -1;

/** Mask canvas whose alpha is 255 exactly where the incoming clip shows. */
function dissolveMaskFor(progress) {
  if (!dissolveNoise) {
    const n = CANVAS_W * CANVAS_H;
    dissolveNoise = new Float32Array(n);
    let seed = 0x9e3779b9;
    for (let i = 0; i < n; i++) {
      seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5;
      dissolveNoise[i] = (seed >>> 0) / 4294967296;
    }
    dissolveMaskCanvas = document.createElement('canvas');
    dissolveMaskCanvas.width = CANVAS_W;
    dissolveMaskCanvas.height = CANVAS_H;
    dissolveImage = dissolveMaskCanvas.getContext('2d').createImageData(CANVAS_W, CANVAS_H);
    // One 32-bit write per pixel instead of four 8-bit ones.
    dissolveWords = new Uint32Array(dissolveImage.data.buffer);
  }
  const threshold = 1 - Math.max(0, Math.min(1, progress));
  if (threshold !== dissolveThreshold) {
    for (let i = 0; i < dissolveWords.length; i++) {
      dissolveWords[i] = dissolveNoise[i] >= threshold ? 0xFFFFFFFF : 0;
    }
    dissolveMaskCanvas.getContext('2d').putImageData(dissolveImage, 0, 0);
    dissolveThreshold = threshold;
  }
  return dissolveMaskCanvas;
}

/**
 * Clips `ctx` to the region the incoming clip owns at this progress, for the
 * transitions that are a hard mask rather than a blend. Returns false when the
 * type is not mask-based.
 */
function clipIncomingRegion(ctx, kind, p) {
  switch (kind) {
    case 'wipeleft':   // B enters from the right, edge travels left
      ctx.rect((1 - p) * CANVAS_W, 0, CANVAS_W, CANVAS_H); return true;
    case 'wiperight':
      ctx.rect(0, 0, p * CANVAS_W, CANVAS_H); return true;
    case 'wipeup':     // B enters from the bottom, edge travels up
      ctx.rect(0, (1 - p) * CANVAS_H, CANVAS_W, CANVAS_H); return true;
    case 'wipedown':
      ctx.rect(0, 0, CANVAS_W, p * CANVAS_H); return true;
    default:
      return false;
  }
}

/** Slide displacement, in canvas pixels, for the outgoing and incoming clip. */
function slideOffsets(kind, p) {
  switch (kind) {
    case 'slideleft':  return [[-p * CANVAS_W, 0], [(1 - p) * CANVAS_W, 0]];
    case 'slideright': return [[p * CANVAS_W, 0], [-(1 - p) * CANVAS_W, 0]];
    case 'slideup':    return [[0, -p * CANVAS_H], [0, (1 - p) * CANVAS_H]];
    case 'slidedown':  return [[0, p * CANVAS_H], [0, -(1 - p) * CANVAS_H]];
    default:           return null;
  }
}

/**
 * How much of the incoming clip shows, ring by ring, for the two circle
 * transitions. Canvas has no per-pixel shader, so the smooth radial ramp is
 * drawn as concentric bands -- 24 of them across the diagonal, which is finer
 * than the eye resolves on a moving frame.
 */
const CIRCLE_BANDS = 24;

function circleWeightAt(kind, p, dNorm) {
  const shifted = 3 * (p - 0.5);
  return kind === 'circleopen'
    ? SMOOTHSTEP((1 - dNorm) + shifted)
    : SMOOTHSTEP(dNorm + shifted);
}

/** Draws one clip's frame with its grade, at `alpha`. */
function drawClipInto(ctx, video, clip, alpha = 1) {
  ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
  ctx.filter = clipFilter(clip);
  const painted = drawVideoFrame(ctx, video, clip);
  ctx.globalAlpha = 1;
  ctx.filter = 'none';
  return painted;
}

/**
 * Paints one draw-plan entry with whatever geometry its transition calls for:
 * a mask for the wipes and the dissolve, a displacement for the slides, a
 * radial alpha ramp for the circles, a solid bridge colour for fadeblack and
 * fadewhite, and a plain crossfade only for `fade` itself.
 */
function paintEntry(ctx, entry, video, offscreen) {
  const { seg, transition: kind, progress: p, role, alpha } = entry;
  const clip = seg.clip;

  // Slides move both clips as one strip, so each side gets its own offset.
  const slide = role && role !== 'solo' ? slideOffsets(kind, p) : null;
  if (slide) {
    const [dx, dy] = role === 'out' ? slide[0] : slide[1];
    ctx.save();
    ctx.translate(dx, dy);
    const painted = drawClipInto(ctx, video, clip);
    ctx.restore();
    return painted;
  }

  if (role !== 'in') {
    const painted = drawClipInto(ctx, video, clip);
    // The outgoing side of a bridge fade also lays down the colour it dips
    // through, so the incoming side only has to blend over it.
    if (painted && role === 'out' && (kind === 'fadeblack' || kind === 'fadewhite')) {
      const { wB, bridge } = bridgeWeights(p);
      const cover = wB >= 1 ? 1 : bridge / (1 - wB);
      if (cover > 0.001) {
        ctx.globalAlpha = Math.min(1, cover);
        ctx.fillStyle = kind === 'fadewhite' ? '#FFFFFF' : '#000000';
        ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
        ctx.globalAlpha = 1;
      }
    }
    return painted;
  }

  if (kind === 'dissolve') {
    // Same off-screen route as the circles: draw the frame, then keep it only
    // where the noise mask says the incoming clip has arrived.
    const oc = offscreen.getContext('2d');
    oc.setTransform(1, 0, 0, 1, 0, 0);
    oc.globalCompositeOperation = 'source-over';
    oc.clearRect(0, 0, CANVAS_W, CANVAS_H);
    if (!drawClipInto(oc, video, clip)) return false;
    oc.globalCompositeOperation = 'destination-in';
    oc.drawImage(dissolveMaskFor(p), 0, 0);
    oc.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.drawImage(offscreen, 0, 0);
    return true;
  }

  if (kind === 'circleopen' || kind === 'circleclose') {
    // A per-pixel radial weight with no shader: draw the frame off-screen,
    // then keep it in proportion to a radial gradient built from the measured
    // curve. One extra full-frame draw, instead of 24 clipped ones.
    const oc = offscreen.getContext('2d');
    oc.setTransform(1, 0, 0, 1, 0, 0);
    oc.globalCompositeOperation = 'source-over';
    oc.clearRect(0, 0, CANVAS_W, CANVAS_H);
    if (!drawClipInto(oc, video, clip)) return false;
    const cx = CANVAS_W / 2;
    const cy = CANVAS_H / 2;
    const z = Math.hypot(cx, cy);
    const grad = oc.createRadialGradient(cx, cy, 0, cx, cy, z);
    for (let i = 0; i <= CIRCLE_BANDS; i++) {
      const d = i / CIRCLE_BANDS;
      grad.addColorStop(d, `rgba(0,0,0,${circleWeightAt(kind, p, d).toFixed(4)})`);
    }
    oc.globalCompositeOperation = 'destination-in';
    oc.fillStyle = grad;
    oc.fillRect(0, 0, CANVAS_W, CANVAS_H);
    oc.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.drawImage(offscreen, 0, 0);
    return true;
  }

  ctx.save();
  ctx.beginPath();
  if (clipIncomingRegion(ctx, kind, p)) {
    ctx.clip();
    const painted = drawClipInto(ctx, video, clip);
    ctx.restore();
    return painted;
  }
  ctx.restore();

  const blend = (kind === 'fadeblack' || kind === 'fadewhite') ? bridgeWeights(p).wB : alpha;
  return drawClipInto(ctx, video, clip, blend);
}

function drawVideoFrame(ctx, video, clip) {
  if (!video || !video.videoWidth || video.readyState < 2) return false;
  const rotation = Number(clip?.rotation || 0) % 360;
  const isRotated90or270 = rotation === 90 || rotation === 270;
  const vw = isRotated90or270 ? video.videoHeight : video.videoWidth;
  const vh = isRotated90or270 ? video.videoWidth : video.videoHeight;
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

  // Blurred-pillarbox framing: the renderer splits the clip, covers the frame
  // with a boxblur(25:5) copy, lays the whole (contain-fit) frame over it, and
  // only then applies the zoom crop. Drawing just the cover-fit crop here hid
  // that entirely -- the preview cropped the sides off a shot the render was
  // showing whole.
  const useBgBlur = !!clip?.bg_blur || clip?.fit_mode === 'blur';
  if (useBgBlur && rotation === 0) {
    const zoomK = Math.min(3, Math.max(1, clip?.zoom || 1));
    const panX = Math.min(1, Math.max(-1, clip?.pan_x || 0));
    const panY = Math.min(1, Math.max(-1, clip?.pan_y || 0));
    ctx.save();
    // zoom/pan act on the finished composite, so they are a transform here
    ctx.translate(CANVAS_W / 2, CANVAS_H / 2);
    ctx.scale(zoomK, zoomK);
    ctx.translate(-(CANVAS_W / 2) - (panX * (CANVAS_W * (zoomK - 1))) / (2 * zoomK),
                  -(CANVAS_H / 2) - (panY * (CANVAS_H * (zoomK - 1))) / (2 * zoomK));
    if (mirrorFlag(clip)) { ctx.translate(CANVAS_W, 0); ctx.scale(-1, 1); }
    // background: cover-fit, blurred (boxblur 25 at 1080w ~= 12px at 540w)
    let bx, by, bw, bh;
    if (vRatio > cRatio) { bh = vh; bw = vh * cRatio; by = 0; bx = (vw - bw) / 2; }
    else { bw = vw; bh = vw / cRatio; bx = 0; by = (vh - bh) / 2; }
    ctx.filter = 'blur(12px)';
    ctx.drawImage(video, bx, by, bw, bh, 0, 0, CANVAS_W, CANVAS_H);
    ctx.filter = 'none';
    // foreground: whole frame, contain-fit, centred
    const fitScale = Math.min(CANVAS_W / vw, CANVAS_H / vh);
    const fw = vw * fitScale, fh = vh * fitScale;
    ctx.drawImage(video, 0, 0, vw, vh, (CANVAS_W - fw) / 2, (CANVAS_H - fh) / 2, fw, fh);
    ctx.restore();
    return true;
  }

  const mirror = !!clip?.mirror;
  if (mirror || rotation !== 0) {
    ctx.save();
    ctx.translate(CANVAS_W / 2, CANVAS_H / 2);
    if (mirror) ctx.scale(-1, 1);
    if (rotation !== 0) ctx.rotate((rotation * Math.PI) / 180);

    if (rotation === 90) {
      const rawSx = sy;
      const rawSy = video.videoHeight - (sx + sw);
      ctx.drawImage(video, Math.max(0, rawSx), Math.max(0, rawSy), Math.min(video.videoWidth, sh), Math.min(video.videoHeight, sw), -CANVAS_H / 2, -CANVAS_W / 2, CANVAS_H, CANVAS_W);
    } else if (rotation === 270) {
      const rawSx = video.videoWidth - (sy + sh);
      const rawSy = sx;
      ctx.drawImage(video, Math.max(0, rawSx), Math.max(0, rawSy), Math.min(video.videoWidth, sh), Math.min(video.videoHeight, sw), -CANVAS_H / 2, -CANVAS_W / 2, CANVAS_H, CANVAS_W);
    } else if (rotation === 180) {
      const rawSx = video.videoWidth - (sx + sw);
      const rawSy = video.videoHeight - (sy + sh);
      ctx.drawImage(video, Math.max(0, rawSx), Math.max(0, rawSy), sw, sh, -CANVAS_W / 2, -CANVAS_H / 2, CANVAS_W, CANVAS_H);
    } else {
      ctx.drawImage(video, sx, sy, sw, sh, -CANVAS_W / 2, -CANVAS_H / 2, CANVAS_W, CANVAS_H);
    }
    ctx.restore();
  } else {
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, CANVAS_W, CANVAS_H);
  }
  return true;
}

// Mirrors the .ass style the renderer burns: CAPTION_POSITIONS in
// subtitle_engine.py puts the block at the bottom (margin 420 of 1920),
// centre, or top (margin 260). Same fractions here so the preview does not
// promise a placement the file will not have.
const CAPTION_Y = { bottom: 1 - 420 / 1920, middle: 0.5, top: 260 / 1920 };
const CAPTION_COLORS = { white: '#fff', yellow: '#FFE600' };

/**
 * Wraps Thai and English text into natural lines based on canvas width,
 * preventing horizontal font squeezing/compression.
 */
function wrapCanvasText(text, ctx, maxW) {
  if (!text) return [];
  const rawParas = String(text).replace(/\\N/g, '\n').split('\n');
  const resultLines = [];

  for (const para of rawParas) {
    const trimmed = para.trim();
    if (!trimmed) continue;

    if (ctx.measureText(trimmed).width <= maxW) {
      resultLines.push(trimmed);
      continue;
    }

    // Tokenize using Intl.Segmenter if available, fallback to whitespace
    let tokens = [];
    if (typeof Intl !== 'undefined' && Intl.Segmenter) {
      try {
        const segmenter = new Intl.Segmenter(['th', 'en'], { granularity: 'word' });
        tokens = Array.from(segmenter.segment(trimmed)).map(s => s.segment);
      } catch (e) {
        tokens = trimmed.split(/(\s+)/);
      }
    } else {
      tokens = trimmed.split(/(\s+)/);
    }

    // Glue Thai grammatical prefixes so they never hang alone at the end of a line
    const THAI_PREFIXES = new Set(['ผู้', 'การ', 'ความ', 'นัก', 'ชาว', 'จาก']);
    const gluedTokens = [];
    for (let i = 0; i < tokens.length; i++) {
      const tok = tokens[i];
      if (THAI_PREFIXES.has(tok) && i + 1 < tokens.length) {
        gluedTokens.push(tok + tokens[i + 1]);
        i++;
      } else {
        gluedTokens.push(tok);
      }
    }
    tokens = gluedTokens;

    // Check if 2 balanced lines fit nicely
    const totalW = ctx.measureText(trimmed).width;
    if (totalW <= maxW * 1.95 && tokens.length > 2) {
      const targetMid = totalW / 2;
      let accumW = 0;
      let bestIdx = 1;
      let bestDiff = 999999;
      for (let i = 0; i < tokens.length - 1; i++) {
        accumW += ctx.measureText(tokens[i]).width;
        const diff = Math.abs(accumW - targetMid);
        if (diff < bestDiff) {
          bestDiff = diff;
          bestIdx = i + 1;
        }
      }
      const l1 = tokens.slice(0, bestIdx).join('').trim();
      const l2 = tokens.slice(bestIdx).join('').trim();
      if (ctx.measureText(l1).width <= maxW * 1.05 && ctx.measureText(l2).width <= maxW * 1.05) {
        resultLines.push(l1, l2);
        continue;
      }
    }

    // Multi-line wrap
    let currentLine = '';
    for (const w of tokens) {
      const test = currentLine + w;
      if (ctx.measureText(test).width > maxW && currentLine.trim().length > 0) {
        resultLines.push(currentLine.trim());
        currentLine = w.trimStart();
      } else {
        currentLine = test;
      }
    }
    if (currentLine.trim()) {
      resultLines.push(currentLine.trim());
    }
  }

  return resultLines.length > 0 ? resultLines : [text];
}

const KINETIC_COLOR_MAP = {
  '#FFE600': [ // 🟡 Neon Yellow (Pain points, prices, deals, primary punch, positive reactions)
    // 1. Physical Discomfort & Pain Points
    'ออฟฟิศซินโดรม', 'ปวดข้อมือ', 'ปวดหลัง', 'ปวดคอ', 'ปวดหัว', 'ปวดไหล่', 'ปวดขา', 'ปวดเมื่อย',
    'ปวดมือ', 'ปวดตัว', 'ปวด', 'เมื่อยล้า', 'เมื่อย', 'ทรมาน', 'เหนื่อยล้า', 'เหนื่อย',
    'เจ็บมือ', 'บาดมือ', 'แสบตา', 'รกโต๊ะ', 'เสียงดังหนวกหู', 'เสียงกวนใจ',
    // 2. Tech & Everyday Frustrations
    'สายพันกัน', 'สายขาด', 'แบตหมดไว', 'แบตเสื่อม', 'กระตุก', 'เครื่องค้าง', 'ค้าง', 'ช้ามาก', 'ช้า',
    'พังง่าย', 'พัง', 'หักง่าย', 'หัก', 'เสียเงินฟรี', 'เสียดายเงิน', 'เสีย', 'หลุดบ่อย', 'หลุด',
    // 3. Beauty, Skin & Personal Care Problems
    'สิวบุก', 'สิวเห่อ', 'สิวขึ้น', 'เป็นสิว', 'รอยสิว', 'รอยดำ', 'รอยแดง', 'หน้ามัน', 'หน้าหมอง', 'หมองคล้ำ',
    'ผิวแห้ง', 'ผิวลอก', 'เหนียวเหนอะหนะ', 'เหนอะหนะ', 'คราบฝังลึก', 'สกปรก', 'กลิ่นอับ', 'เหม็นอับ', 'เหม็น',
    // 4. Fashion, Body & Confidence
    'อึดอัด', 'แน่นพุง', 'พุงยื่น', 'ขาใหญ่', 'ดูอ้วน', 'เชยๆ', 'เชย', 'ล้าสมัย', 'ไม่มั่นใจ', 'ไม่สวย',
    'ปัญหา', 'ยุ่งยาก', 'เสียเวลา', 'เปลืองแรง', 'เปลืองเงิน', 'หงุดหงิด',
    // 5. Price, Deals, Vouchers & E-Commerce CTA
    'ราคาพิเศษ', 'ลดราคา', 'ลดกระหน่ำ', 'ลดแรง', 'ดีลพิเศษ', 'ดีลลับ', 'โปรเด็ด', 'โปรแรง', 'โปรโมชั่น',
    'แฟลชเซล', 'flash sale', 'โค้ดลด', 'โค้ดลับ', 'คูปอง', 'ส่งฟรี', '1 แถม 1', 'หนึ่งแถมหนึ่ง',
    'ของแถม', 'แจกฟรี', 'ฟรี', 'บาท', 'หลักสิบ', 'หลักร้อย', 'ราคาดี', 'ราคาโดน', 'ถูกและดี',
    'ถูกสุดๆ', 'ถูกมาก', 'คุ้มสุดๆ', 'คุ้มค่า', 'คุ้มราคา', 'เกินคุ้ม', 'คุ้ม', 'ประหยัด', 'ตกใจราคา',
    'ตะกร้าส้ม', 'ตะกร้าซ้ายล่าง', 'ตะกร้า', 'ใส่ตะกร้า', 'จิ้มตะกร้า', 'จิ้มเลย', 'จิ้มตรงนี้', 'กดตรงนี้',
    'พิกัดในคอมเมนต์', 'พิกัดในโปรไฟล์', 'พิกัด', 'ปักหมุด', 'อย่ารอ', 'อย่าช้า', 'ช้าหมด',
    'รีบตำ', 'รีบจัด', 'ด่วนเลย', 'ด่วน', 'ต้องมี', 'ของมันต้องมี', 'ขาดไม่ได้', 'สอยด่วน', 'รีบสอย',
    'เคาะราคา', 'สั่งซื้อเลย', 'กดลงตะกร้า', 'ลิงก์หน้าโปรไฟล์', 'กดที่ลิงก์', 'จัดโปร', 'ลดเยอะมาก',
    // 6. Viral Praise & Reviewer Hype
    'ป้ายยา', 'ตัวท็อป', 'ตัวแม่', 'ยืนหนึ่ง', 'ตัวตึง', 'ของดีบอกต่อ', 'ใช้ดีบอกต่อ', 'ของดี',
    'ดีจริง', 'ดูดีมาก', 'ดีมาก', 'ดีเกินคาด', 'ดีเกินราคา', 'ว้าวมาก', 'ว้าว', 'ตาแตก', 'ตะลึง',
    'สุดปัง', 'ปังมาก', 'จึ้งมาก', 'จึ้ง', 'เลิศมาก', 'เลิศ', 'เอาเรื่อง', 'ของแทร่', 'เปลี่ยนชีวิต',
    'ยกระดับ', 'หลงรักเลย', 'หลงรัก', 'ชอบมาก', 'ติดใจ', 'ไม่ผิดหวัง', 'ไม่จกตา', 'รีวิวจริง',
    'ใช้จริง', 'หมดปัญหา', 'ลืมแบบเก่าไปเลย', 'โคตรดี', 'โคตรคุ้ม', 'ฟินมาก', 'ช็อค', 'น่ารักกว่าในรูป', 'ของที่รอคอย',
    'สมคำร่ำลือ', 'ตอบโจทย์', 'ตัวจริง', 'ปังไม่ไหว', 'สิบเต็มสิบ', '10/10', 'คุ้มสุดในรุ่น', 'ยืนยันอีกเสียง',
    'ขาดตัวนี้ไม่ได้', 'ต้องมีติดบ้าน', 'ไอเทมลับ', 'ไอเทมเด็ด', 'รอดไม่รอด', 'ของมันต้องลอง', 'ประทับใจ',
    'เกินต้าน', 'ยอมใจ', 'เด็ดจริง', 'ไม่คิดว่าจะดี', 'ดีกว่าที่คิด', 'คุ้มเกินเบอร์', 'ปังสุด', 'สุดจัด',
    'ลองแล้วรัก', 'ถูกใจมาก', 'ใช้เองรีวิวเอง', 'โนสปอน', 'ซื้อเองใช้เอง', 'ใช้จนหมด', 'ซื้อซ้ำ', 'ตุนด่วน', 'ต้องตุน', 'ตำด่วน', 'ใช้ทุกวัน',
    // English Counterparts
    'office syndrome', 'wrist pain', 'back pain', 'neck pain', 'shoulder pain', 'headache', 'leg pain',
    'body pain', 'hand hurts', 'hurts', 'painful', 'pain', 'tight', 'sore', 'exhausted',
    'tiring', 'tired', 'suffering', 'messy desk', 'noisy',
    'tangled', 'broken cord', 'dead battery', 'low battery', 'laggy', 'lagging', 'freezing', 'too slow', 'slow',
    'breaks easily', 'broken', 'waste of money', 'waste of time', 'wasted', 'annoying',
    'acne breakout', 'breakouts', 'pimples', 'dark spots', 'redness', 'oily skin', 'dull skin',
    'dry skin', 'peeling skin', 'sticky', 'greasy', 'deep stains', 'dirty', 'bad odor', 'smelly',
    'uncomfortable', 'stuffy', 'bloated', 'tight fit', 'outdated', 'unconfident', 'insecure',
    'problems', 'problem', 'frustrating', 'troublesome', 'not sure',
    'special price', 'huge discount', 'discount', 'special deal', 'secret deal', 'best promo', 'promotion',
    'flash sale', 'promo code', 'voucher', 'coupon', 'free shipping', 'buy 1 get 1', 'bogo',
    'free gift', 'giveaway', 'free', 'baht', 'super cheap', 'cheap', 'affordable', 'best price',
    'best value', 'great value', 'worth every penny', 'worth it', 'save money', 'shocking price',
    'yellow basket', 'orange basket', 'cart', 'add to cart', 'click cart', 'click now', 'click here',
    'pinned link', 'link in bio', 'coordinates', 'don\'t wait', 'don\'t delay', 'almost gone',
    'buy now', 'grab it now', 'hurry up', 'must have', 'essential', 'check profile link', 'grab yours',
    'holy grail', 'game changer', 'life-changing', 'top tier', 'the best', 'highly recommend',
    'really good', 'looks really good', 'looks good', 'so good', 'very good', 'good', 'exceeded expectations',
    'unbelievable', 'very wow', 'wow', 'mind blowing', 'stunning', 'gorgeous', 'slay',
    'aesthetic', 'next level', 'fell in love', 'obsessed', 'love it', 'no regret', 'won\'t be disappointed',
    'real review', 'tried and tested', 'problem solved', 'insanely good', 'super worth it', 'so satisfying',
    'much cuter', 'long-awaited', 'recommend', '10 out of 10', '10/10', 'worth the hype', 'honest review',
    'holy grail item', 'no sponsor', 'bought it myself', 'repurchase', 'stock up', 'daily staple'
  ],
  '#00E5FF': [ // 🔵 Electric Cyan (Features, tech, ergonomics, certifications, comfort)
    // 1. Tech, Gadgets & Hardware
    'Logitech Wave Keys', 'Logitech', 'Wave Keys', 'คีย์บอร์ดในฝัน', 'คีย์บอร์ด', 'ไร้สาย', 'บลูทูธ',
    'แม่เหล็ก', 'แรงดูดสูง', 'ดูดแน่น', '540 องศา', '360 องศา', 'ชาร์จไว', 'ฟาสชาร์จ', '66W', '100W',
    'แบตอึด', 'แบตทน', 'ทนทาน', 'แข็งแรง', 'ประกันศูนย์', 'ของแท้', 'แท้ 100%', 'จอสวย', 'จอลื่น',
    '120Hz', 'คมชัด', 'กล้องชัด', 'เสียงดี', 'เบสแน่น', 'ตัดเสียงรบกวน', 'กันน้ำ', 'ชิปเร็ว',
    'ลื่นไหล', 'ไม่สะดุด', 'เชื่อมต่อง่าย', 'เสียบปุ๊บติดปั๊บ', 'พกพาสะดวก', 'น้ำหนักเบา', 'กะทัดรัด',
    'ปรับระดับได้', 'พับเก็บได้', 'ประหยัดพื้นที่', 'ประกอบง่าย', 'ใช้งานง่าย',
    'ปุ่มเงียบ', 'สวิตช์เงียบ', 'ไร้สาย 2.4G', 'ต่อได้ 3 อุปกรณ์', 'สลับเครื่องไว', 'รองรับ Mac และ Windows',
    'ปรับความสูงได้', 'วัสดุพรีเมียม', 'งานประกอบเนี๊ยบ', 'แบตเตอรี่ใช้ได้นาน', 'ชาร์จครั้งเดียวอยู่ได้ยาว', 'จับถนัดมือ',
    // 2. Ergonomics, Comfort, Softness & Apparel
    'สรีรศาสตร์', 'เมมโมรี่โฟม', 'ที่รองข้อมือ', 'พิมพ์สบาย', 'นั่งสบาย', 'นอนสบาย', 'ใส่สบาย',
    'สบายมาก', 'นุ่มสบาย', 'สบายมือ', 'สบายหลัง', 'สบายตา', 'สบายตัว', 'สบาย', 'นุ่มนิ่ม', 'นุ่มฟู',
    'นุ่มมาก', 'นุ่มๆ', 'นุ่ม', 'ยืดหยุ่น', 'สัมผัสนุ่ม', 'ไม่ระคายเคือง', 'ไม่บาดผิว', 'ทรงสวย',
    'ทรงเป๊ะ', 'พอดีตัว', 'เข้ารูป', 'ทิ้งตัวสวย', 'พรางหุ่น', 'เก็บพุง', 'ระบายอากาศ', 'ไม่อับชื้น',
    'ไม่ร้อน', 'เย็นสบาย', 'มินิมอล', 'ดีไซน์แบบคลื่นๆ', 'แบบคลื่นๆ', 'คลื่น', 'ดีไซน์สวย',
    // 3. Skincare, Beauty & Quality Efficacy
    'ผิวฉ่ำวาว', 'ผิวฉ่ำน้ำ', 'ผิวฉ่ำ', 'หน้าใส', 'ผิวเนียน', 'ผิวกระจก', 'ผิวนุ่มเด้ง', 'หน้าเด็ก',
    'ซึมไว', 'ซึมเร็ว', 'แห้งไว', 'บางเบา', 'ไม่เหนอะหนะ', 'คุมมัน', 'ผิวกระชับ', 'รูขุมขนกระชับ',
    'กลิ่นหอม', 'หอมละมุน', 'หอมฟุ้ง', 'ติดทน', 'ติดทนนาน', 'ไม่ติดแมสก์', 'กันเหงื่อ', 'กันน้ำกันเหงื่อ',
    'ปกปิดเนียน', 'กลบเนียน', 'ไม่วอก', 'ไม่ลอย', 'อ่อนโยน', 'แพ้ง่ายใช้ได้', 'สารสกัดธรรมชาติ',
    'ออร์แกนิก', 'พรีเมียมสุดๆ', 'พรีเมียม', 'หรูหรา', 'ดูแพง', 'สะอาดหมดจด', 'ฆ่าเชื้อ', 'กรองฝุ่น',
    'รับรอง', 'ผู้เชี่ยวชาญ', 'แพทย์ผิวหนัง', 'สุขภาพดี', 'ปลอดภัย',
    // English Counterparts
    'logitech wave keys', 'wave keys', 'logitech', 'dream keyboard', 'keyboard', 'wireless', 'bluetooth',
    'magnetic', 'strong magnet', '540 degrees', '360 degrees', 'fast charging', 'quick charge', '66w', '100w',
    'long battery', 'battery life', 'durable', 'sturdy', 'warranty', 'genuine', 'authentic', 'smooth screen',
    '120hz', 'crystal clear', 'sharp camera', 'great sound', 'deep bass', 'noise cancelling', 'anc', 'waterproof',
    'fast chip', 'ultra smooth', 'easy connect', 'plug and play', 'portable', 'lightweight', 'compact',
    'adjustable', 'foldable', 'space saving', 'easy to assemble', 'easy to use',
    'silent keys', 'quiet typing', 'multi-device', 'easy switch', 'mac and windows compatible',
    'ergonomic', 'ergonomics', 'memory foam', 'wrist rest', 'typing comfortable', 'sit comfortably',
    'comfortable fit', 'comfortable', 'comfy', 'super comfy', 'soft and comfy', 'extra soft', 'pillow soft',
    'very soft', 'soft', 'flexible', 'gentle touch', 'non-irritating', 'flattering fit',
    'perfect fit', 'slim fit', 'tummy control', 'breathable', 'airy', 'cool and fresh',
    'minimalist', 'minimal', 'wavy design', 'wavy', 'sleek design', 'beautiful design',
    'glass skin', 'glowy skin', 'glowing skin', 'clear skin', 'smooth skin', 'bouncy skin', 'youthful',
    'fast absorbing', 'quick absorb', 'quick drying', 'lightweight texture', 'non-sticky', 'non-greasy', 'oil control',
    'firming', 'pore tightening', 'nice scent', 'pleasant smell', 'long lasting', 'transfer-proof', 'sweat-proof',
    'water resistant', 'full coverage', 'natural finish', 'no white cast', 'gentle formula', 'sensitive skin friendly',
    'natural extracts', 'organic', 'very premium', 'premium', 'luxury', 'looks expensive',
    'deep clean', 'antibacterial', 'hepa filter', 'certified', 'experts', 'expert',
    'dermatologist', 'healthy', 'safe'
  ],
  '#FF3B30': [ // 🔴 Alert Red (Urgency, warnings)
    'อย่าเพิ่งซื้อ', 'อย่าเพิ่ง', 'หยุดก่อน', 'หยุดดูคลิปนี้', 'ฟังทางนี้', 'เตือนภัย', 'เตือน',
    'ระวังของปลอม', 'ระวัง', 'อันตราย', 'เสี่ยง', 'ห้ามทำ', 'อย่าหาทำ', 'อย่าพลาด',
    'ห้ามพลาด', 'ห้ามเลื่อนผ่าน', 'ของปลอมระบาด', 'ซื้อผิดรุ่น', 'ดูให้จบ', 'ข้อเสีย', 'สิ่งที่ควรรู้',
    'เช็กด่วน', 'ระวังโดนหลอก', 'ข้อควรระวัง', 'อย่าเพิ่งเลื่อน', 'เตือนไว้ก่อน', 'ก่อนจะสาย', 'จุดสังเกต', 'ระวังผิดหวัง', 'ดูตรงนี้ก่อน',
    // English Counterparts
    'don\'t buy yet', 'don\'t buy', 'stop scrolling', 'wait a minute', 'listen to this', 'urgent warning', 'warning',
    'beware of fake', 'beware', 'danger', 'risky', 'don\'t do this', 'don\'t miss out',
    'don\'t miss', 'watch till the end', 'counterfeit', 'fake products', 'cons', 'must know',
    'look at this', 'watch this', 'warn', 'stop', 'before you buy', 'watch out', 'critical warning', 'check this before buying'
  ]
};

const EN_STOPWORDS = new Set([
  'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'am', 'of', 'to', 'in',
  'on', 'at', 'for', 'with', 'and', 'or', 'but', 'if', 'it', 'its', 'this', 'that',
  'these', 'those', 'as', 'by', 'from', 'up', 'out', 'so', 'than', 'then', 'too',
  'very', 'can', 'will', 'just', 'not', 'no', 'do', 'does', 'did', 'you', 'your',
  'i', 'my', 'we', 'our', 'they', 'their', 'he', 'she', 'his', 'her', 'how', 'what',
  'who', 'why', 'when', 'where', 'all', 'any', 'more', 'most', 'some', 'such', 'own',
  'about', 'into', 'over', 'also', 'have', 'has', 'had', 'would', 'could', 'should',
]);

function salientWordEn(text) {
  let best = null;
  const words = text.match(/[A-Za-z][A-Za-z'-]*/g) || [];
  for (const raw of words) {
    if (EN_STOPWORDS.has(raw.toLowerCase()) || raw.length < 3) continue;
    if (!best || raw.length > best.length) best = raw;
  }
  return best;
}

function forceHighlightWord(text, word, color, defaultColor) {
  if (!word || !text.includes(word)) return [{ text, color: defaultColor }];
  const idx = text.indexOf(word);
  const segments = [];
  if (idx > 0) segments.push({ text: text.slice(0, idx), color: defaultColor });
  segments.push({ text: word, color });
  if (idx + word.length < text.length) segments.push({ text: text.slice(idx + word.length), color: defaultColor });
  return segments;
}

function parseKineticSegments(text, defaultColor = '#FFFFFF', colorHint = null, customKeywords = []) {
  if (!text) return [];

  // Tier 1: Check for explicit user / AI markers like *keyword* or [keyword]
  const markerRegex = /(\*([^*]+)\*|\[([^\]]+)\])/;
  const markerMatch = markerRegex.exec(text);
  if (markerMatch) {
    const chosenColor = colorHint || '#FFE600';
    const before = text.slice(0, markerMatch.index);
    const kw = markerMatch[2] || markerMatch[3];
    const after = text.slice(markerMatch.index + markerMatch[0].length);
    const segments = [];
    if (before) segments.push({ text: before, color: defaultColor });
    segments.push({ text: kw, color: chosenColor });
    if (after) segments.push({ text: after, color: defaultColor });
    return segments;
  }

  // Tier 2 & 3: Word-level kinetic highlighting (mirrors subtitle_engine.py)
  const lowerText = text.toLowerCase();
  const colors = Object.keys(KINETIC_COLOR_MAP);
  const colorOrder = colorHint && colors.includes(colorHint)
    ? [colorHint, ...colors.filter(c => c !== colorHint)]
    : colors;

  for (const color of colorOrder) {
    let keywords = KINETIC_COLOR_MAP[color] || [];
    if (color === '#00E5FF' && customKeywords && customKeywords.length > 0) {
      keywords = [...customKeywords, ...keywords];
    }
    const sorted = [...keywords].sort((a, b) => b.length - a.length);
    for (const kw of sorted) {
      const lowerKw = kw.toLowerCase();
      if (/[^\u0000-\u007F]/.test(kw)) {
        const idx = text.indexOf(kw);
        if (idx !== -1) {
          const segments = [];
          if (idx > 0) segments.push({ text: text.slice(0, idx), color: defaultColor });
          segments.push({ text: kw, color });
          if (idx + kw.length < text.length) segments.push({ text: text.slice(idx + kw.length), color: defaultColor });
          return segments;
        }
      } else {
        const escaped = lowerKw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(?:^|(?<=[^a-zA-Z0-9]))(${escaped})(?:(?=[^a-zA-Z0-9])|$)`, 'i');
        const match = regex.exec(text);
        if (match) {
          const idx = match.index;
          const matchStr = match[1];
          const segments = [];
          if (idx > 0) segments.push({ text: text.slice(0, idx), color: defaultColor });
          segments.push({ text: matchStr, color });
          if (idx + matchStr.length < text.length) segments.push({ text: text.slice(idx + matchStr.length), color: defaultColor });
          return segments;
        }
      }
    }
  }

  return [{ text, color: defaultColor }];
}

// The browser paints emoji as colour bitmap glyphs, which ignore fillStyle;
// libass paints the same characters as ordinary monochrome glyphs in the
// text colour. Drawing emoji runs through a desaturating filter is what
// keeps the preview honest about what the render will actually look like.
const EMOJI_RUN_RE = /(\p{Extended_Pictographic}(?:️|‍\p{Extended_Pictographic})*\s*)/gu;

// Caption kinetic pop, mirroring `anim` in subtitle_engine.py: snap in at
// 125% and settle to the cue's own scale over 70ms, linear, no alpha ramp.
const CAPTION_POP_MS = 70;
const CAPTION_POP_FROM = 1.25;

function drawTextWithMonoEmoji(ctx, text, x, y) {
  if (!EMOJI_RUN_RE.test(text)) {
    ctx.fillText(text, x, y);
    return;
  }
  EMOJI_RUN_RE.lastIndex = 0;
  let cursor = x;
  for (const part of text.split(EMOJI_RUN_RE)) {
    if (!part) continue;
    EMOJI_RUN_RE.lastIndex = 0;
    const isEmoji = EMOJI_RUN_RE.test(part);
    if (isEmoji) {
      ctx.save();
      ctx.filter = 'grayscale(1) brightness(2.2)';
      ctx.fillText(part, cursor, y);
      ctx.restore();
    } else {
      ctx.fillText(part, cursor, y);
    }
    cursor += ctx.measureText(part).width;
  }
}

function drawSingleCue(ctx, cue, t, style = {}) {
  if (!cue || !cue.text) return;
  const cueScale = Number(cue.scale) || 1.0;
  const globalScale = Math.min(2.5, Math.max(0.5, style.captionScale ?? 1));
  const effectiveScale = Math.min(3.0, Math.max(0.4, globalScale * cueScale));
  // Standard TikTok Subtitle Size: 100% (scale=1.0) is calibrated to 50pt on 1080w
  // (25px on 540w Canvas), exactly matching the user's preferred visual proportion.
  const baseFs = Math.round(CANVAS_W * 0.0463);
  const fontSize = Math.max(14, Math.round(baseFs * effectiveScale));
  
  let fontFam = "'Kanit', sans-serif";
  let fontWeight = '900';
  if (style.fontName === 'IBMPlex' || style.fontName === 'IBM Plex Sans Thai') {
    fontFam = "'IBM Plex Sans Thai', sans-serif";
    fontWeight = '700';
  } else if (style.fontName === 'Prompt') {
    fontFam = "'Prompt', sans-serif";
    fontWeight = '800';
  }

  ctx.save();
  ctx.font = `${fontWeight} ${fontSize}px ${fontFam}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  
  // Crisp outline + punchy shadow matching libass
  ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
  ctx.shadowBlur = 3;
  ctx.shadowOffsetX = 2;
  ctx.shadowOffsetY = 3;
  
  ctx.strokeStyle = '#000000';
  ctx.lineWidth = captionOutlineWidth(fontSize);
  ctx.lineJoin = 'round';
  ctx.miterLimit = 2;
  
  const maxLineW = CANVAS_W * 0.86;
  const thaiLines = wrapCanvasText(cue.text, ctx, maxLineW);
  const thaiLineH = fontSize;

  // Stacked bilingual English subtitle
  let enLines = [];
  const enFontSize = Math.round(fontSize * 0.68);
  const enLineH = fontSize;
  if (cue.translation && !cue.translation.includes('Error 500')) {
    ctx.font = `700 ${enFontSize}px ${fontFam}`;
    enLines = wrapCanvasText(cue.translation, ctx, CANVAS_W * 0.86);
  }

  // Vertical anchoring: support per-cue position override (top / middle / bottom)
  const totalBlockH = (thaiLines.length + enLines.length) * fontSize;
  const pos = cue.position || style.captionPosition || 'bottom';
  const anchorY = CANVAS_H * (CAPTION_Y[pos] ?? CAPTION_Y.bottom);
  let blockTop;
  if (pos === 'top') blockTop = anchorY;
  else if (pos === 'middle') blockTop = anchorY - totalBlockH / 2;
  else blockTop = anchorY - totalBlockH;
  const thaiStartY = blockTop + thaiLineH / 2;

  // Synchronized Bilingual Kinetic Highlighting
  const primaryColor = CAPTION_COLORS[style.captionColor] || '#FFFFFF';
  const enDefaultColor = '#EAEAEA';

  let activeKineticColor = null;
  let parsedThaiLines = thaiLines.map((line) => {
    const segs = parseKineticSegments(line, primaryColor);
    const matched = segs.find(s => s.color !== primaryColor);
    if (matched) activeKineticColor = matched.color;
    return segs;
  });

  let parsedEnLines = [];
  if (enLines.length > 0) {
    let enMatchedColor = null;
    parsedEnLines = enLines.map((line) => {
      const segs = parseKineticSegments(line, enDefaultColor, activeKineticColor);
      const matched = segs.find(s => s.color !== enDefaultColor);
      if (matched) enMatchedColor = matched.color;
      return segs;
    });

    // If Thai had no match initially, but English matched a color, re-parse Thai with English's color
    if (!activeKineticColor && enMatchedColor) {
      activeKineticColor = enMatchedColor;
      parsedThaiLines = thaiLines.map(line => parseKineticSegments(line, primaryColor, enMatchedColor));
    }

    // Parity fallback: 100% color synchronization between Thai and English (no lopsided cues)
    if (activeKineticColor && !enMatchedColor) {
      parsedEnLines = enLines.map(line => {
        const sw = salientWordEn(line);
        return sw ? forceHighlightWord(line, sw, activeKineticColor, enDefaultColor) : [{ text: line, color: enDefaultColor }];
      });
    }
  }

  // Kinetic pop, mirroring subtitle_engine.py's per-cue `anim`:
  // \fscx125\fscy125 settling to the cue's own scale over 70ms from cue start.
  // Only the Thai run pops -- the English run re-declares \fscx68 absolutely,
  // so the transform never reaches it. Layout keeps using the settled size
  // because libass advances lines by the STYLE size, not the animated one.
  const popElapsedMs = (t - cue.start) * 1000;
  const popScale = popElapsedMs >= CAPTION_POP_MS
    ? 1
    : CAPTION_POP_FROM + (1 - CAPTION_POP_FROM) * Math.max(0, popElapsedMs) / CAPTION_POP_MS;
  const drawFs = Math.max(1, Math.round(fontSize * popScale));

  // Draw Thai lines
  thaiLines.forEach((line, idx) => {
    const lineY = thaiStartY + (idx * thaiLineH);
    const segments = parsedThaiLines[idx] || [{ text: line, color: primaryColor }];

    ctx.font = `${fontWeight} ${drawFs}px ${fontFam}`;
    const segmentWidths = segments.map(seg => ctx.measureText(seg.text).width);
    const totalLineW = segmentWidths.reduce((sum, w) => sum + w, 0);

    // Pass 1: Outline / Stroke with crisp shadow
    ctx.textAlign = 'left';
    ctx.strokeStyle = '#000000';
    // ScaledBorderAndShadow: yes in the ASS header, so the border scales with
    // the pop too.
    ctx.lineWidth = captionOutlineWidth(drawFs);
    ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
    ctx.shadowBlur = 3;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 3;

    let curX = (CANVAS_W - totalLineW) / 2;
    segments.forEach((seg, sIdx) => {
      ctx.strokeText(seg.text, curX, lineY);
      curX += segmentWidths[sIdx];
    });

    // Pass 2: Color fills (sharp contrast without doubled shadow)
    ctx.shadowColor = 'transparent';
    curX = (CANVAS_W - totalLineW) / 2;
    segments.forEach((seg, sIdx) => {
      ctx.fillStyle = seg.color;
      drawTextWithMonoEmoji(ctx, seg.text, curX, lineY);
      curX += segmentWidths[sIdx];
    });
  });

  // Draw English lines (stacked underneath) with matching kinetic color highlighting
  if (enLines.length > 0) {
    ctx.font = `700 ${enFontSize}px ${fontFam}`;
    // Continues the same one-font-size-per-line cadence, no extra gap.
    const enStartY = thaiStartY + thaiLines.length * thaiLineH;

    enLines.forEach((line, idx) => {
      const lineY = enStartY + (idx * enLineH);
      const segments = parsedEnLines[idx] || [{ text: line, color: enDefaultColor }];
      const segmentWidths = segments.map(seg => ctx.measureText(seg.text).width);
      const totalLineW = segmentWidths.reduce((sum, w) => sum + w, 0);

      // Pass 1: Outline / Stroke with soft shadow
      ctx.textAlign = 'left';
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = Math.round(enFontSize * 0.18);
      ctx.shadowColor = 'rgba(0, 0, 0, 0.85)';
      ctx.shadowBlur = 3;
      ctx.shadowOffsetX = 1.5;
      ctx.shadowOffsetY = 2;

      let curX = (CANVAS_W - totalLineW) / 2;
      segments.forEach((seg, sIdx) => {
        ctx.strokeText(seg.text, curX, lineY);
        curX += segmentWidths[sIdx];
      });

      // Pass 2: Color fills (sharp contrast without doubled shadow)
      ctx.shadowColor = 'transparent';
      curX = (CANVAS_W - totalLineW) / 2;
      segments.forEach((seg, sIdx) => {
        ctx.fillStyle = seg.color;
        ctx.fillText(seg.text, curX, lineY);
        curX += segmentWidths[sIdx];
      });
    });
  }

  ctx.restore();
}

function drawCaption(ctx, cues = [], t, style = {}) {
  if (!cues || cues.length === 0) return;
  const activeCues = cues.filter((c) => t >= c.start && t < c.end);
  activeCues.forEach((cue) => {
    drawSingleCue(ctx, cue, t, style);
  });
}

function drawSticker(ctx, img, t, style = {}) {
  if (!img || !img.complete || !img.naturalWidth) return;
  const startTime = style.startTime ?? 0.5;
  if (t < startTime) return;

  const scale = Math.min(2, Math.max(0.4, style.scale ?? 1));
  const baseW = 380;
  const w = Math.round(baseW * scale);
  const h = Math.round(w * (img.naturalHeight / img.naturalWidth));

  let x = CANVAS_W - w - 40;
  let y = 140;
  const pos = style.position || 'top_right';
  if (pos === 'top_left') {
    x = 40; y = 140;
  } else if (pos === 'bottom_right') {
    x = CANVAS_W - w - 40; y = CANVAS_H - h - 420;
  } else if (pos === 'bottom_left') {
    x = 40; y = CANVAS_H - h - 420;
  } else if (pos === 'top_center') {
    x = Math.round((CANVAS_W - w) / 2); y = 140;
  } else if (pos === 'bottom_center') {
    x = Math.round((CANVAS_W - w) / 2); y = CANVAS_H - h - 420;
  }

  const elapsed = t - startTime;
  const alpha = Math.min(1, Math.max(0, elapsed / 0.3));
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.drawImage(img, x, y, w, h);
  ctx.restore();
}

// Where custom text overlays sit vertically as a fraction of canvas height.
// Mirrors TEXT_OVERLAY_POSITIONS in subtitle_engine.py: top (0.20), middle (0.50), bottom (0.72).
const TEXT_OVERLAY_Y = {
  top: 0.20,
  middle: 0.50,
  bottom: 0.72,
};

function drawTextOverlays(ctx, textOverlays = [], t, fontName = 'Kanit') {
  if (!textOverlays || textOverlays.length === 0) return;
  const activeItems = textOverlays.filter(item => t >= item.start && t < item.end);
  if (!activeItems.length) return;

  let fontFam = "'Kanit', sans-serif";
  let fontWeight = '900';
  if (fontName === 'IBMPlex' || fontName === 'IBM Plex Sans Thai') {
    fontFam = "'IBM Plex Sans Thai', sans-serif";
    fontWeight = '700';
  } else if (fontName === 'Prompt') {
    fontFam = "'Prompt', sans-serif";
    fontWeight = '800';
  }

  const baseFs = Math.round(CANVAS_W * 0.0463);

  activeItems.forEach(item => {
    const rawTxt = String(item.text || '').trim();
    if (!rawTxt) return;

    const scale = Math.min(2.5, Math.max(0.4, Number(item.scale) || 1.0));
    const fs = Math.max(12, Math.round(baseFs * scale));

    const elapsed = t - item.start;
    const remaining = item.end - t;

    let animScale = 1.0;
    let animAlpha = 1.0;
    let animDy = 0;

    const anim = item.anim || 'pop';
    if (anim === 'pop') {
      const popElapsedMs = elapsed * 1000;
      animScale = popElapsedMs >= 70 ? 1.0 : 1.25 + (1.0 - 1.25) * Math.max(0, popElapsedMs) / 70;
    } else if (anim === 'fade') {
      const fadeElapsedMs = elapsed * 1000;
      animAlpha = Math.min(1.0, Math.max(0, fadeElapsedMs / 150));
    } else if (anim === 'slide') {
      const slideElapsedMs = elapsed * 1000;
      const frac = Math.min(1.0, Math.max(0, slideElapsedMs / 200));
      animDy = 40 * (1.0 - frac);
      animAlpha = frac;
    }

    // Exit fade (last 150ms)
    if (remaining < 0.15) {
      animAlpha *= Math.max(0, remaining / 0.15);
    }

    const renderFs = Math.max(8, Math.round(fs * animScale));
    ctx.save();
    ctx.font = `${fontWeight} ${renderFs}px ${fontFam}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const maxW = CANVAS_W * 0.85;
    const rawLines = rawTxt.split('\n');
    const wrappedLines = [];
    rawLines.forEach(l => {
      wrappedLines.push(...wrapCanvasText(l, ctx, maxW));
    });
    if (!wrappedLines.length) {
      ctx.restore();
      return;
    }

    const lineH = renderFs * 1.2;
    const totalH = wrappedLines.length * lineH;
    const pos = item.position || 'middle';
    const yCenter = CANVAS_H * (TEXT_OVERLAY_Y[pos] ?? 0.50) + animDy;
    const startY = yCenter - (totalH / 2) + (lineH / 2);
    const xCenter = CANVAS_W / 2;

    ctx.globalAlpha = animAlpha;

    // Background style: pill badge
    if (item.bgStyle === 'pill') {
      let maxLineW = 0;
      wrappedLines.forEach(l => {
        const w = ctx.measureText(l).width;
        if (w > maxLineW) maxLineW = w;
      });
      const padX = Math.round(renderFs * 0.6);
      const padY = Math.round(renderFs * 0.35);
      const pillW = maxLineW + padX * 2;
      const pillH = totalH + padY * 2;
      const pillX = xCenter - pillW / 2;
      const pillY = yCenter - totalH / 2 - padY;
      const radius = Math.round(pillH / 2);

      ctx.save();
      ctx.fillStyle = 'rgba(0, 0, 0, 0.65)';
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(pillX, pillY, pillW, pillH, Math.min(radius, 14));
      } else {
        ctx.rect(pillX, pillY, pillW, pillH);
      }
      ctx.fill();
      ctx.restore();
    }

    // Draw text lines
    ctx.textAlign = 'left';
    wrappedLines.forEach((line, idx) => {
      const lineY = startY + idx * lineH;
      const lineW = ctx.measureText(line).width;
      const lineX = xCenter - lineW / 2;

      ctx.strokeStyle = '#000000';
      ctx.lineWidth = Math.max(2, Math.round(renderFs * 0.12));
      ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
      ctx.shadowBlur = 4;
      ctx.shadowOffsetX = 1.5;
      ctx.shadowOffsetY = 2;
      ctx.strokeText(line, lineX, lineY);

      ctx.shadowColor = 'transparent';
      ctx.fillStyle = item.color || '#FFFFFF';
      drawTextWithMonoEmoji(ctx, line, lineX, lineY);
    });

    ctx.restore();
  });
}

/**
 * 3-tier hook banner preview: brand (largest) / model (mid) / label
 * (smallest), mirroring subtitle_engine.py's generate_ass hook composition
 * (tier scale %s, HOOK_COMFORTABLE_LINES shrink, gradient backdrop) so what
 * plays here matches what Apply's ffmpeg render actually burns -- an
 * approximation on animation easing (this canvas fades alpha, the .ass pops
 * scale in), not on layout or which text shows where.
 */
// Canvas mirror of subtitle_engine.py's hook motion presets. Every preset
// here reproduces the keyframes its Python builder emits, so what plays in
// this preview is what libass will draw -- the two are meant to be read side
// by side; changing one without the other is a bug.
const HOOK_MOTION_DEFAULTS = { in: 'bounce', stagger: true, loop: 'pulse', out: 'fade', accent: 'underline' };
const HOOK_STAGGER_STEP = 0.15; // seconds; mirrors STAGGER_STEP_MS
const HOOK_DIM_OPACITY = 1 - 0x25 / 255; // mirrors ASS \alpha&H25&
const HOOK_SWEEP_OPACITY = 1 - 0x60 / 255; // mirrors ASS \alpha&H60&
const HOOK_OUTLINE_PX = 6; // HookHeader style Outline=6.0, flat for every tier

// Mirrors front_outline = max(1.8, font_size * 0.040) in subtitle_engine.py,
// where font_size is the render-resolution size (twice this canvas one).
// An ASS outline grows outward only while strokeText centres its stroke, so
// the canvas width is twice the outward thickness it needs to imitate.
function captionOutlineWidth(canvasFontSize) {
  return Math.max(1.8, canvasFontSize * 2 * 0.04);
}

/** Piecewise-linear interpolation over [[ms, value], ...] keyframes. */
function hookKeyframeAt(ms, kf) {
  if (ms <= kf[0][0]) return kf[0][1];
  const last = kf[kf.length - 1];
  if (ms >= last[0]) return last[1];
  for (let i = 0; i < kf.length - 1; i++) {
    const [t1, v1] = kf[i];
    const [t2, v2] = kf[i + 1];
    if (ms >= t1 && ms <= t2) return v1 + (v2 - v1) * ((ms - t1) / (t2 - t1));
  }
  return last[1];
}

// Each In preset returns {scale, alpha, dy, reveal} for `elapsedSec` since
// this line's own stagger start, plus how long it runs (durSec) so the loop
// phase knows when every line has settled. reveal (0..1) drives the
// typewriter's left-to-right clip.
const HOOK_IN_TRANSFORMS = {
  bounce: {
    durSec: 0.45,
    at: (ms) => ({ scale: hookKeyframeAt(ms, [[0, 0.6], [150, 1.25], [280, 0.92], [380, 1.05], [450, 1.0]]) }),
  },
  pop: {
    durSec: 0.2,
    at: (ms) => ({ scale: hookKeyframeAt(ms, [[0, 0.55], [120, 1.18], [200, 1.0]]) }),
  },
  fade: {
    durSec: 0.25,
    at: (ms) => ({ alpha: hookKeyframeAt(ms, [[0, 0], [250, 1]]) }),
  },
  zoom: {
    durSec: 0.3,
    at: (ms) => ({
      scale: hookKeyframeAt(ms, [[0, 1.8], [300, 1.0]]),
      alpha: hookKeyframeAt(ms, [[0, 0], [150, 1]]),
    }),
  },
  slide_up: {
    durSec: 0.3,
    at: (ms) => ({
      dy: hookKeyframeAt(ms, [[0, 60], [300, 0]]),
      alpha: hookKeyframeAt(ms, [[0, 0], [300, 1]]),
    }),
  },
  typewriter: {
    durSec: 0.4,
    at: (ms) => ({ reveal: hookKeyframeAt(ms, [[0, 0], [400, 1]]) }),
  },
  blur: {
    durSec: 0.35,
    at: (ms) => ({
      alpha: hookKeyframeAt(ms, [[0, 0], [350, 1]]),
      blur: hookKeyframeAt(ms, [[0, 12], [350, 0]]),
    }),
  },
  none: { durSec: 0, at: () => ({}) },
};

// Loop presets run from when the last line settles until the exit starts.
// Mirrors _chained_keyframes: fixed-length steps cycling through values,
// emitting nothing at all if not even one step fits.
function hookCycleAt(tSec, startSec, endSec, stepSec, values) {
  if (tSec < startSec) return values[values.length - 1];
  let segStart = startSec;
  let i = 0;
  let prev = values[values.length - 1];
  while (segStart + stepSec <= endSec) {
    const segEnd = segStart + stepSec;
    const target = values[i % values.length];
    if (tSec >= segStart && tSec < segEnd) {
      return prev + (target - prev) * ((tSec - segStart) / stepSec);
    }
    prev = target;
    segStart = segEnd;
    i += 1;
  }
  return i === 0 ? values[values.length - 1] : prev;
}

const HOOK_LOOP_TRANSFORMS = {
  pulse: (t, s, e) => ({ alpha: hookCycleAt(t, s, e, 0.35, [HOOK_DIM_OPACITY, 1.0]) }),
  wave: (t, s, e) => ({ rot: hookCycleAt(t, s, e, 0.4, [-3, 3, 0]) }),
  shake: (t, s, e) => ({ rot: hookCycleAt(t, s, e, 0.09, [-3, 3, -2, 2, 0]) }),
  flicker: (t, s, e) => {
    // irregular step lengths, matching _loop_flicker's hardcoded pattern
    const pattern = [[0.08, 1 - 0x30 / 255], [0.15, 1.0], [0.06, 1 - 0x45 / 255], [0.2, 1.0], [0.09, 1 - 0x20 / 255], [0.18, 1.0]];
    if (t < s) return { alpha: 1.0 };
    let segStart = s;
    let i = 0;
    let prev = 1.0;
    while (true) {
      const [dur, target] = pattern[i % pattern.length];
      if (segStart + dur > e) return { alpha: prev };
      if (t >= segStart && t < segStart + dur) {
        return { alpha: prev + (target - prev) * ((t - segStart) / dur) };
      }
      prev = target;
      segStart += dur;
      i += 1;
    }
  },
  lightsweep: () => ({}), // drawn as a separate highlight pass, not a transform
  none: () => ({}),
};

const HOOK_OUT_TRANSFORMS = {
  fade: (t, s, e) => ({ alpha: 1 - hookKeyframeAt((t - s) * 1000, [[0, 0], [(e - s) * 1000, 1]]) }),
  slide: (t, s, e) => ({
    alpha: 1 - hookKeyframeAt((t - s) * 1000, [[0, 0], [(e - s) * 1000, 1]]),
    dy: hookKeyframeAt((t - s) * 1000, [[0, 0], [(e - s) * 1000, 60]]),
  }),
  zoom: (t, s, e) => ({
    alpha: 1 - hookKeyframeAt((t - s) * 1000, [[0, 0], [(e - s) * 1000, 1]]),
    scale: hookKeyframeAt((t - s) * 1000, [[0, 1], [(e - s) * 1000, 1.4]]),
  }),
  glitch: (t, s, e) => ({
    rot: hookCycleAt(t, s, Math.max(s + 0.001, e - 0.04), 0.04, [-3, 3, 0]),
    alpha: t >= e - 0.04 ? 1 - (t - (e - 0.04)) / 0.04 : 1,
  }),
  none: (t, s, e) => ({ alpha: t >= e - 0.001 ? 0 : 1 }),
};

function drawHookHeader(ctx, hookBrand, hookModel, hookLabel, t, hookDuration = 3.5, fontName = 'Kanit', accentColor = '#FFE600', hookMotion = null, hookColors = null) {
  if ((!hookBrand && !hookModel && !hookLabel) || t > hookDuration) return;
  const motion = { ...HOOK_MOTION_DEFAULTS, ...(hookMotion || {}) };
  const colors = hookColors || {};

  let fontFam = "'Kanit', sans-serif";
  if (fontName === 'IBMPlex' || fontName === 'IBM Plex Sans Thai') {
    fontFam = "'IBM Plex Sans Thai', sans-serif";
  } else if (fontName === 'Prompt') {
    fontFam = "'Prompt', sans-serif";
  }

  // Must stay the same fraction of frame width the renderer uses (hook_fs =
  // video_width * 0.065 in subtitle_engine.py). This canvas is exactly half
  // of the 1080-wide output, so the same ratio lands on the same on-screen
  // size -- an earlier 0.052 * 1.64 made the preview ~31% larger than what
  // actually rendered, which is why header sizes never matched.
  const baseFontSize = Math.round(CANVAS_W * 0.065);
  // Same tier percentages and colour fallbacks as hook_tier_specs in
  // subtitle_engine.py. tierIdx doubles as the stagger slot and marks the
  // model tier for the accent shape.
  const tierSpecs = [
    { text: (hookBrand || '').trim().toUpperCase(), sizePct: 130, color: colors.brand || '#FFFFFF', tierIdx: 0 },
    { text: (hookModel || '').trim(), sizePct: 100, color: colors.model || accentColor, tierIdx: 1 },
    { text: (hookLabel || '').trim(), sizePct: 58, color: colors.label || '#E0E0E0', tierIdx: 2 },
  ].filter((tier) => tier.text);
  if (!tierSpecs.length) return;

  const maxW = CANVAS_W * 0.85;
  const x = CANVAS_W / 2;

  ctx.save();
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';

  // Pass 1: wrap each tier at its OWN font size before measuring line count.
  const wrapped = [];
  for (const tier of tierSpecs) {
    const tierFs = Math.max(10, Math.round((baseFontSize * tier.sizePct) / 100));
    ctx.font = `900 ${tierFs}px ${fontFam}`;
    for (const line of wrapCanvasText(tier.text, ctx, maxW)) {
      wrapped.push({ line, fontSize: tierFs, color: tier.color, tierIdx: tier.tierIdx });
    }
  }

  // Pass 2: same HOOK_COMFORTABLE_LINES=4 shrink as the backend, so a long
  // brand/model that wraps twice doesn't crowd the sticker badge (top-right,
  // y=140) instead of just overflowing unbounded.
  const shrink = Math.max(0.7, Math.min(1, 4 / wrapped.length));

  const inPreset = HOOK_IN_TRANSFORMS[motion.in] || HOOK_IN_TRANSFORMS.bounce;
  const loopFn = HOOK_LOOP_TRANSFORMS[motion.loop] || HOOK_LOOP_TRANSFORMS.pulse;
  const outFn = HOOK_OUT_TRANSFORMS[motion.out] || HOOK_OUT_TRANSFORMS.fade;

  // The loop phase can't start until every tier's own entry has settled.
  let maxEntryEndSec = 0;
  for (const { tierIdx } of wrapped) {
    const t0 = motion.stagger ? tierIdx * HOOK_STAGGER_STEP : 0;
    maxEntryEndSec = Math.max(maxEntryEndSec, t0 + inPreset.durSec);
  }
  const exitStartSec = Math.max(0.12, hookDuration - 0.15);
  const loopFx = loopFn(t, maxEntryEndSec, exitStartSec) || {};
  const outFx = t >= exitStartSec ? (outFn(t, exitStartSec, hookDuration) || {}) : {};

  // Gradient backdrop -- mirrors video_editor.py's geq overlay (dark at the
  // top of the frame, fading to transparent by ~25% down), fades out
  // alongside the banner's outFx during the exit window.
  const gradH = Math.round(CANVAS_H * 0.25);
  const grad = ctx.createLinearGradient(0, 0, 0, gradH);
  const bgAlpha = t >= exitStartSec ? (outFx.alpha ?? 1) : 1;
  grad.addColorStop(0, `rgba(0,0,0,${0.75 * bgAlpha})`);
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, CANVAS_W, gradH);

  ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
  ctx.shadowBlur = 10;
  ctx.shadowOffsetX = 3;
  ctx.shadowOffsetY = 4;
  ctx.strokeStyle = '#000000';
  ctx.lineJoin = 'round';
  ctx.miterLimit = 2;

  let y = 130; // ~HookHeader's ASS MarginV=260 of 1920, scaled to this 960-tall canvas
  // Must equal LINE_HEIGHT_FACTOR in subtitle_engine.py (1.0, measured off a
  // real libass render). At 1.15 the preview stacked the tiers further apart
  // than the render did, so the block never matched even once the font size
  // itself lined up.
  const lineGap = 1.0;
  // Accent bookkeeping. Unlike the ASS side (which can't ask libass where a
  // wrapped line landed and has to walk a LINE_HEIGHT_FACTOR cursor), the
  // canvas measures its own text, so these come straight from layout.
  let modelTopY = null, modelLineWidth = 0, modelFontSize = 0, modelColor = accentColor;

  // Layout pre-pass: resolve every line's y (and the model tier's metrics)
  // BEFORE anything is painted, so the accent shape can be drawn first and
  // sit behind the text. The renderer puts accents on a lower ASS layer for
  // the same reason -- painting them after the text, as this used to, made
  // the preview show a badge covering the words it is supposed to sit under.
  {
    let layoutY = y;
    wrapped.forEach(({ fontSize, color, tierIdx }, idx) => {
      const settledFs = Math.max(10, Math.round(fontSize * shrink));
      if (tierIdx === 1) {
        ctx.font = `900 ${settledFs}px ${fontFam}`;
        modelLineWidth = ctx.measureText(wrapped[idx].line).width;
        modelFontSize = settledFs;
        modelColor = color;
        modelTopY = layoutY;
      }
      layoutY += settledFs * lineGap;
      const isLastModelLine = tierIdx === 1 && (idx + 1 >= wrapped.length || wrapped[idx + 1].tierIdx !== 1);
      if (isLastModelLine && motion.accent !== 'none') {
        layoutY += settledFs * (motion.accent === 'badge' ? 0.45 : 0.80);
      }
    });
  }

  // Accent shape under / behind the model tier. Follows the entry and exit
  // envelope but not the loop -- matching the backend, which never threads
  // loop keyframes into the accent events.
  if (motion.accent !== 'none' && modelTopY != null) {
    const revealStart = motion.stagger ? HOOK_STAGGER_STEP * 2 : 0;
    const revealFrac = t <= revealStart ? 0 : Math.min(1, (t - revealStart) / 0.3);
    ctx.save();
    ctx.shadowColor = 'transparent';
    ctx.globalAlpha = (outFx.alpha ?? 1);
    ctx.fillStyle = modelColor;
    if (motion.accent === 'badge') {
      const padX = Math.round(modelFontSize * 0.38);
      const padY = Math.round(modelFontSize * 0.2);
      const fullBw = (modelLineWidth / 2 + padX) * 2;
      const bw = fullBw * revealFrac;
      // ASS \alpha is TRANSPARENCY, so &HB0& means 0.31 opacity, not 0.69.
      ctx.globalAlpha *= 1 - 0xB0 / 255;
      // Anchor left edge at x - fullBw / 2 matching \an7 anchor in ASS
      ctx.fillRect(x - fullBw / 2, modelTopY - padY, bw, modelFontSize + padY * 2);
    } else {
      const thickness = Math.max(4, Math.round(modelFontSize * 0.1));
      const gap = Math.round(modelFontSize * 0.50);
      const w = modelLineWidth * revealFrac;
      const barY = modelTopY + modelFontSize + gap;
      const barX = x - modelLineWidth / 2;
      // The renderer lays a blurred copy under the crisp bar (\blur7 at
      // \alpha&H60&) for glow; without it the preview's bar reads flatter
      // than what actually renders.
      ctx.save();
      ctx.shadowColor = modelColor;
      ctx.shadowBlur = 7;
      ctx.globalAlpha *= 1 - 0x60 / 255;
      ctx.fillRect(barX, barY, w, thickness);
      ctx.restore();
      ctx.fillRect(barX, barY, w, thickness);
    }
    ctx.restore();
  }

  const sweeps = [];
  wrapped.forEach(({ line, fontSize, color, tierIdx }, idx) => {
    // The cumulative y-cursor advances using the SETTLED size, not the
    // currently-animating scale -- an ASS \t transform (and this mirror of
    // it) animates glyph rendering, not layout reflow, so other lines must
    // not jitter as this one animates.
    const settledFs = Math.max(10, Math.round(fontSize * shrink));
    const t0 = motion.stagger ? tierIdx * HOOK_STAGGER_STEP : 0;
    const inFx = inPreset.at((t - t0) * 1000) || {};

    const scale = (inFx.scale ?? 1) * (outFx.scale ?? 1);
    const dy = (inFx.dy ?? 0) + (outFx.dy ?? 0);
    const rot = (loopFx.rot ?? 0) + (outFx.rot ?? 0);
    const renderFs = Math.max(6, Math.round(settledFs * scale));

    ctx.save();
    ctx.globalAlpha = (inFx.alpha ?? 1) * (loopFx.alpha ?? 1) * (outFx.alpha ?? 1);
    if (inFx.blur) ctx.filter = `blur(${inFx.blur.toFixed(1)}px)`;
    if (rot) {
      // rotate about the line's own centre, matching \frz around \pos
      ctx.translate(x, y + settledFs / 2 + dy);
      ctx.rotate((rot * Math.PI) / 180);
      ctx.translate(-x, -(y + settledFs / 2 + dy));
    }
    if (inFx.reveal != null) {
      // typewriter: same left-to-right clip the ASS \clip animation performs
      ctx.font = `900 ${settledFs}px ${fontFam}`;
      const halfW = ctx.measureText(line).width / 2;
      ctx.beginPath();
      ctx.rect(x - halfW, y + dy - 5, halfW * 2 * inFx.reveal, settledFs + 10);
      ctx.clip();
    }
    ctx.font = `900 ${renderFs}px ${fontFam}`;
    // HookHeader's ASS Outline is a flat 6.0 render px for every tier;
    // strokeText centres its stroke so only half lands outside the glyph.
    ctx.lineWidth = HOOK_OUTLINE_PX;
    ctx.strokeText(line, x, y + dy, maxW);
    ctx.fillStyle = color;
    ctx.fillText(line, x, y + dy, maxW);
    ctx.restore();

    if (motion.loop === 'lightsweep') {
      ctx.font = `900 ${settledFs}px ${fontFam}`;
      sweeps.push({ line, y: y + dy, fs: settledFs, halfW: ctx.measureText(line).width / 2 });
    }

    y += settledFs * lineGap;

    // Accent shapes take layout space after the model tier's last line, so
    // the label below is never drawn through -- mirrors the same reserve in
    // subtitle_engine.py's y-cursor walk.
    const isLastModelLine = tierIdx === 1 && (idx + 1 >= wrapped.length || wrapped[idx + 1].tierIdx !== 1);
    if (isLastModelLine && motion.accent !== 'none') {
      y += settledFs * (motion.accent === 'badge' ? 0.45 : 0.80);
    }
  });

  // Shimmer band travelling across each line, repeatedly, for the hold --
  // mirrors _hook_lightsweep_event's 500ms cycle plus its instant reset.
  if (sweeps.length && t >= maxEntryEndSec && t < exitStartSec) {
    const CYCLE = 0.501;
    const phase = ((t - maxEntryEndSec) % CYCLE) / 0.5;
    if (phase <= 1) {
      ctx.save();
      ctx.globalAlpha = (outFx.alpha ?? 1) * HOOK_SWEEP_OPACITY;
      ctx.fillStyle = '#FFFFFF';
      for (const s of sweeps) {
        const bandW = Math.max(10, s.halfW * 0.7);
        // Travels exactly 2 * halfW, the same distance the renderer's clip
        // band covers (left edge from c-hw-bw to c+hw-bw).
        const bandX = (x - s.halfW - bandW) + phase * (s.halfW * 2);
        ctx.save();
        ctx.beginPath();
        ctx.rect(bandX, s.y - 5, bandW, s.fs + 10);
        ctx.clip();
        ctx.font = `900 ${s.fs}px ${fontFam}`;
        ctx.fillText(s.line, x, s.y, maxW);
        ctx.restore();
      }
      ctx.restore();
    }
  }

  ctx.restore();
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
 * not by trusting a <video> element's own playback rate -- see RESYNC's
 * comment for why.
 */
function SequencePlayer({ clips, cues = [], textOverlays = [], hookBrand = '', hookModel = '', hookLabel = '', hookDuration = 3.0, hookMotion = null, hookColors = null, audioUrl = null, audioStems = null, grade = null, trackMix = null, compact = false, onPlayhead, onDurations, captionStyle = {}, stickerStyle = {}, isMuted = false }, ref) {
  const canvasRef = useRef(null);
  const videoElsRef = useRef({});
  const audioElRef = useRef(null);
  const bgmElRef = useRef(null);
  const audioCtxRef = useRef(null);
  const audioNodesRef = useRef(null);      // { master, voice, bgm, sfx }
  const mediaSourcesRef = useRef(new Map()); // element -> MediaElementAudioSourceNode
  const clipGainsRef = useRef(new Map());    // clip id -> { el, gain } for clip audio
  const sfxBuffersRef = useRef(new Map());   // url -> AudioBuffer | Promise
  const sfxLiveRef = useRef([]);             // { key, time, node } already handed to WebAudio
  const rafRef = useRef(null);
  const clockRef = useRef({ startWall: 0, startT: 0 });
  const stickerImgRef = useRef(null);
  const lutRef = useRef(null);          // parsed .cube for the chosen filter
  const lutRendererRef = useRef(null);  // WebGL2 pass, or null where unavailable
  const [lutReady, setLutReady] = useState(0);

  // Scratch frame for transitions that need a per-pixel alpha ramp.
  const offscreenRef = useRef(null);
  const getOffscreen = () => {
    if (!offscreenRef.current) {
      const c = document.createElement('canvas');
      c.width = CANVAS_W;
      c.height = CANVAS_H;
      offscreenRef.current = c;
    }
    return offscreenRef.current;
  };

  const [durations, setDurations] = useState({});
  const [metadataReady, setMetadataReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playhead, setPlayhead] = useState(0);
  const playheadRef = useRef(0);
  const prevActiveClipIdRef = useRef(null);

  const captionKey = `${captionStyle.hidden}:${captionStyle.captionPosition}:${captionStyle.captionColor}:${captionStyle.captionScale}:${captionStyle.fontName}:${hookBrand}:${hookModel}:${hookLabel}:${hookDuration}:${JSON.stringify(hookMotion || {})}:${JSON.stringify(hookColors || {})}`;
  const cuesKey = (cues || []).map(c => `${c._uid || c.id}:${c.start}:${c.end}:${c.text}:${c.translation}:${c.scale || 1}`).join(';;');
  const textOverlaysKey = (textOverlays || []).map(t => `${t.id}:${t.start}:${t.end}:${t.text}:${t.position}:${t.scale}:${t.color}:${t.bgStyle}:${t.anim}`).join(';;');
  const stickerKey = `${stickerStyle.badge}:${stickerStyle.position}:${stickerStyle.scale}:${stickerStyle.startTime}`;
  const clipKey = clips.map(c => `${c.id}:${c.source_path}:${c.trim_start}:${c.trim_end}:${c.transition_in}:${c.transition_duration}:${c.brightness}:${c.contrast}:${c.saturation}:${c.zoom}:${c.pan_x}:${c.pan_y}:${c.mirror}:${c.rotation}`).join('|');

  // The Filter picker used to change nothing on screen -- the grade only
  // showed up after a render. Load the same .cube the renderer will hand to
  // lut3d and apply it to the video layer here.
  useEffect(() => {
    let alive = true;
    if (!grade?.url) {
      lutRef.current = null;
      setLutReady((n) => n + 1);
      return undefined;
    }
    loadCube(grade.url).then((lut) => {
      if (!alive) return;
      lutRef.current = lut;
      setLutReady((n) => n + 1);
    });
    return () => { alive = false; };
  }, [grade?.url]);

  useEffect(() => () => {
    lutRendererRef.current?.dispose();
    lutRendererRef.current = null;
  }, []);

  useEffect(() => {
    if (!stickerStyle?.badge || !stickerStyle?.stickers?.length) {
      stickerImgRef.current = null;
      renderAt(playheadRef.current);
      return;
    }
    const found = stickerStyle.stickers.find((s) => 
      s.name === stickerStyle.badge || 
      s.id === stickerStyle.badge || 
      s.path === stickerStyle.badge ||
      (s.name && stickerStyle.badge && s.name.toLowerCase() === String(stickerStyle.badge).toLowerCase())
    );
    if (found?.img_url) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = found.img_url;
      img.onload = () => {
        stickerImgRef.current = img;
        renderAt(playheadRef.current);
      };
    } else {
      stickerImgRef.current = null;
      renderAt(playheadRef.current);
    }
  }, [stickerStyle.badge, stickerStyle.stickers]);

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

  // --- Stem audio -------------------------------------------------------
  // 1-Click no longer bakes a mix (pipeline.py skips it unless a video is
  // actually being exported), so the preview plays the separate stems the
  // renderer will mix later: the voice wav on a media element, the chosen BGM
  // looped on a second element, and one AudioBufferSourceNode per SFX hit.
  // A BGM swap or a new SFX on a cue is then audible immediately instead of
  // needing a full re-render to hear.
  //
  // The voice element stays the master clock (as the old mixed file was),
  // because it is the one stem whose timeline is 1:1 with the video's.

  const stemsKey = JSON.stringify(audioStems || null);

  const sfxShots = useMemo(() => (
    (audioStems?.sfx || [])
      .map((s, i) => ({
        key: `${i}:${s.id}@${s.time}`,
        url: s.url,
        // Pre-roll is decided by the resolved filename, exactly as the render
        // does -- the cue tag can be a legacy alias that does not contain the
        // word at all (whoosh -> sfx_whoosh_fast.wav).
        time: sfxFireTime(s.time, s.name || s.id),
      }))
      .sort((a, b) => a.time - b.time)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ), [stemsKey]);

  const bgmRate = useMemo(() => bgmTempoRatio(cues), [cuesKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const bgmVolume = audioStems?.bgm?.volume ?? AUDIO_MIX.BGM_GAIN;
  const bgmDucking = !!audioStems?.bgm?.ducking;

  // The tick loop only re-subscribes on a few deps, so anything it reads that
  // can change mid-playback has to come through a ref -- otherwise a volume
  // slider move or a freshly dropped SFX is invisible to it, and its stale
  // copy of the level fights the gain-setting effect right back down.
  const soloedTracks = Object.keys(trackMix?.solo || {}).filter((k) => trackMix.solo[k]);
  const trackAudible = (track) => (
    soloedTracks.length ? soloedTracks.includes(track) : !trackMix?.mute?.[track]
  );
  const trackBase = { voice: AUDIO_MIX.VOICE_GAIN, bgm: bgmVolume, sfx: AUDIO_MIX.SFX_GAIN, clip: AUDIO_MIX.CLIP_GAIN };
  /** Level a bus should sit at right now, mute and solo included. */
  const trackLevel = (track) => (trackAudible(track) ? trackBase[track] : 0);

  const audioLiveRef = useRef({});
  audioLiveRef.current = {
    bgmVolume, bgmDucking, bgmRate, totalDuration, cues, shots: sfxShots,
    // The tick needs the mute state too, or its envelope undoes the mute.
    bgmAudible: trackAudible('bgm'),
  };

  /**
   * Creates the graph on first use and routes whatever elements exist into it.
   * Must be called from a user gesture (play), or the context starts suspended
   * and nothing is heard.
   */
  const ensureAudioGraph = () => {
    const Ctx = typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext);
    if (!Ctx) return null;
    if (!audioCtxRef.current) {
      const ctx = new Ctx();
      const master = ctx.createGain();
      master.gain.value = isMuted ? 0 : 1;
      master.connect(ctx.destination);
      const bus = (gain) => {
        const n = ctx.createGain();
        n.gain.value = gain;
        n.connect(master);
        return n;
      };
      audioCtxRef.current = ctx;
      // Built at the level the mix state says, not the raw one. Muting a
      // track before ever pressing play left nothing to apply the mute to, and
      // the effect that would have applied it does not re-run for a graph that
      // did not exist when it last fired -- so the music came back at full
      // level on the first play with every M lit.
      audioNodesRef.current = {
        master,
        voice: bus(trackLevel('voice')),
        bgm: bus(trackLevel('bgm')),
        sfx: bus(trackLevel('sfx')),
        clip: bus(trackLevel('clip')),
      };
    }
    const ctx = audioCtxRef.current;
    if (ctx.state === 'suspended') ctx.resume().catch(() => {});
    // createMediaElementSource throws if called twice for the same element, and
    // once routed, an element reaches the speakers only through this graph --
    // so wire each one exactly once and remember it.
    const wire = (el, node) => {
      if (!el || !node || mediaSourcesRef.current.has(el)) return;
      try {
        const src = ctx.createMediaElementSource(el);
        src.connect(node);
        mediaSourcesRef.current.set(el, src);
      } catch {
        /* element already belongs to another graph -- leave it alone */
      }
    };
    wire(audioElRef.current, audioNodesRef.current.voice);
    wire(bgmElRef.current, audioNodesRef.current.bgm);
    // Decode every one-shot up front. Left to fire time, the first pass over a
    // cue is the one that has to wait for the fetch.
    (audioLiveRef.current.shots || []).forEach((shot) => loadSfxBuffer(ctx, shot.url));
    wireClipAudio();
    return ctx;
  };

  /**
   * Routes one clip's <video> element into the clip-audio bus at its own
   * volume. The elements are muted by default (they exist to decode frames),
   * so a clip with volume > 0 was silent in the preview while the render mixed
   * it in -- the slider moved a number nothing could hear.
   */
  const wireClipAudio = () => {
    const ctx = audioCtxRef.current;
    const bus = audioNodesRef.current?.clip;
    if (!ctx || !bus) return;
    clips.forEach((clip) => {
      const el = videoElsRef.current[clip.id];
      if (!el) return;
      const vol = Math.min(1, Math.max(0, Number(clip.volume) || 0));
      if (vol <= 0.001) {
        el.muted = true;
        return;
      }
      el.muted = false;
      let entry = clipGainsRef.current.get(clip.id);
      if (!entry || entry.el !== el) {
        if (mediaSourcesRef.current.has(el)) {
          // Same element, already routed -- reuse its gain node.
          entry = clipGainsRef.current.get(clip.id);
        }
        if (!entry || entry.el !== el) {
          try {
            const gain = ctx.createGain();
            gain.connect(bus);
            const src = ctx.createMediaElementSource(el);
            src.connect(gain);
            mediaSourcesRef.current.set(el, src);
            entry = { el, gain };
            clipGainsRef.current.set(clip.id, entry);
          } catch {
            return;   // element already belongs to another graph
          }
        }
      }
      entry.gain.gain.setTargetAtTime(vol, ctx.currentTime, 0.01);
    });
  };

  /** Drops every one-shot already handed to WebAudio (seek, stop, unmount). */
  const flushSfx = () => {
    sfxLiveRef.current.forEach(({ node }) => {
      try {
        if (node) { node.onended = null; node.stop(); }
      } catch {
        /* already finished */
      }
    });
    sfxLiveRef.current = [];
  };

  /** Fetch + decode once per URL; the decoded buffer is reused every pass. */
  const loadSfxBuffer = (ctx, url) => {
    const cached = sfxBuffersRef.current.get(url);
    if (cached) return cached;
    const pending = fetch(url)
      .then((r) => r.arrayBuffer())
      .then((b) => ctx.decodeAudioData(b))
      .then((buf) => { sfxBuffersRef.current.set(url, buf); return buf; })
      .catch(() => { sfxBuffersRef.current.delete(url); return null; });
    sfxBuffersRef.current.set(url, pending);
    return pending;
  };

  /**
   * Hands WebAudio every shot due within the lookahead window, converting
   * timeline seconds to context seconds. Called each tick; scheduled shots are
   * tracked so one fires once per pass over its time.
   */
  const pumpSfx = (t) => {
    const ctx = audioCtxRef.current;
    const node = audioNodesRef.current?.sfx;
    if (!ctx || !node || ctx.state !== 'running') return;
    (audioLiveRef.current.shots || []).forEach((shot) => {
      if (shot.time < t - 0.05 || shot.time > t + AUDIO_MIX.SFX_LOOKAHEAD) return;
      // An entry stays in the list once fired -- it is only cleared by
      // flushSfx (stop/seek). Removing it when the sound ended would let a
      // short SFX be scheduled again while the playhead was still inside its
      // lookahead window, firing it twice.
      if (sfxLiveRef.current.some((s) => s.key === shot.key)) return;
      const when = ctx.currentTime + Math.max(0, shot.time - t);
      const entry = { key: shot.key, time: shot.time, node: null };
      sfxLiveRef.current.push(entry);
      Promise.resolve(loadSfxBuffer(ctx, shot.url)).then((buf) => {
        if (!buf || !sfxLiveRef.current.includes(entry)) return;
        // A first, uncached hit can finish decoding after its moment has
        // passed. Playing it from that far into the buffer keeps the sound
        // aligned with the timeline instead of arriving audibly late; past
        // SFX_LATE_LIMIT there is nothing worth salvaging.
        const late = ctx.currentTime - when;
        if (late > AUDIO_MIX.SFX_LATE_LIMIT || late > buf.duration) return;
        const src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(node);
        src.onended = () => { entry.node = null; };
        entry.node = src;
        if (late > 0) src.start(ctx.currentTime, late);
        else src.start(when);
      });
    });
  };

  /**
   * BGM level for timeline position `t`. The render ducks with
   * sidechaincompress keyed off the voice, which WebAudio cannot do -- so the
   * cue spans stand in for "the voice is speaking" and the measured 13.7 dB of
   * reduction is applied across them with the same attack/release times. The
   * 0.35s tail fade (afade=t=out) is reproduced from the same end position.
   */
  const applyBgmEnvelope = (t) => {
    const ctx = audioCtxRef.current;
    const node = audioNodesRef.current?.bgm;
    if (!ctx || !node) return;
    const live = audioLiveRef.current;
    // Muted or soloed out, the bed stays down whatever the envelope wants.
    // Muted or soloed out, the bed stays down whatever the envelope wants.
    if (live.bgmAudible === false) {
      if (node.gain.value !== 0) {
        node.gain.cancelScheduledValues(ctx.currentTime);
        node.gain.setTargetAtTime(0, ctx.currentTime, 0.01);
      }
      return;
    }
    let target = live.bgmVolume ?? AUDIO_MIX.BGM_GAIN;
    const speaking = (live.cues || []).some(
      (c) => t >= (Number(c.start) || 0) && t <= (Number(c.end) || 0)
    );
    if (live.bgmDucking && speaking) target *= AUDIO_MIX.BGM_DUCK_GAIN;
    const total = live.totalDuration || 0;
    const fadeStart = Math.max(0, total - AUDIO_MIX.BGM_FADE_OUT);
    if (total > 0 && t > fadeStart) {
      target *= Math.max(0, 1 - (t - fadeStart) / AUDIO_MIX.BGM_FADE_OUT);
    }
    if (Math.abs(node.gain.value - target) < 1e-4) return;
    const ramp = target < node.gain.value ? AUDIO_MIX.BGM_DUCK_ATTACK : AUDIO_MIX.BGM_DUCK_RELEASE;
    node.gain.cancelScheduledValues(ctx.currentTime);
    node.gain.setTargetAtTime(target, ctx.currentTime, ramp / 3);
  };

  /** Puts every stem at timeline position `t` without starting playback. */
  const cueStemsTo = (t) => {
    if (audioElRef.current) {
      try { audioElRef.current.currentTime = t; } catch { /* not seekable yet */ }
    }
    const bgm = bgmElRef.current;
    if (bgm) {
      // atempo runs before atrim in the render, so timeline second `t` sits
      // `t * rate` seconds into the source file.
      const dur = bgm.duration;
      const pos = t * (audioLiveRef.current.bgmRate || 1);
      try {
        bgm.currentTime = Number.isFinite(dur) && dur > 0 ? pos % dur : pos;
      } catch {
        /* metadata still loading */
      }
    }
    flushSfx();
  };

  const startStems = () => {
    ensureAudioGraph();
    audioElRef.current?.play().catch(() => {});
    const bgm = bgmElRef.current;
    if (bgm) {
      bgm.playbackRate = audioLiveRef.current.bgmRate || 1;
      bgm.play().catch(() => {});
    }
  };

  const stopStems = () => {
    audioElRef.current?.pause();
    bgmElRef.current?.pause();
    flushSfx();
  };

  // Swapping BGM (or loading another project) mounts a new element, keyed by
  // URL, that the graph has never seen -- so wire it up and pick playback back
  // up in place rather than going quiet until the next press of play. The old
  // element is gone from the DOM by now, so its source node goes with it.
  useEffect(() => {
    mediaSourcesRef.current.forEach((src, el) => {
      if (el.isConnected) return;
      try { src.disconnect(); } catch { /* already detached */ }
      mediaSourcesRef.current.delete(el);
    });
    if (!isPlaying) return;
    ensureAudioGraph();
    cueStemsTo(playheadRef.current);
    startStems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioStems?.voiceUrl, audioStems?.bgm?.url]);

  // Muting has to happen at the master gain: once an element is routed through
  // WebAudio its own `muted` flag is the only other lever, and SFX have no
  // element at all.
  useEffect(() => {
    const nodes = audioNodesRef.current;
    const ctx = audioCtxRef.current;
    if (nodes && ctx) nodes.master.gain.setTargetAtTime(isMuted ? 0 : 1, ctx.currentTime, 0.01);
  }, [isMuted]);

  // Per-track mute/solo. With the stems separate there is finally something to
  // solo: checking whether the BGM is fighting the voice, or whether an SFX
  // landed where it was meant to, no longer means guessing from the mix.
  const trackKey = `${JSON.stringify(trackMix?.mute || {})}|${[...soloedTracks].sort().join(',')}`;
  useEffect(() => {
    const nodes = audioNodesRef.current;
    const ctx = audioCtxRef.current;
    if (!nodes || !ctx) return;
    Object.keys(trackBase).forEach((track) => {
      nodes[track].gain.setTargetAtTime(trackLevel(track), ctx.currentTime, 0.01);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackKey, bgmVolume]);

  // A clip's volume can change while it plays, and a clip can appear or vanish.
  useEffect(() => {
    if (audioCtxRef.current) wireClipAudio();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clipKey]);

  // A BGM volume change from the Inspector must be audible without a replay.
  useEffect(() => {
    const nodes = audioNodesRef.current;
    const ctx = audioCtxRef.current;
    if (nodes && ctx) nodes.bgm.gain.setTargetAtTime(bgmVolume, ctx.currentTime, 0.01);
  }, [bgmVolume]);

  // Teardown: without this the elements keep decoding and the AudioContext
  // stays open after the editor unmounts (browsers cap how many may exist).
  useEffect(() => () => {
    flushSfx();
    [audioElRef.current, bgmElRef.current].forEach((el) => {
      if (!el) return;
      el.pause();
      el.removeAttribute('src');
      el.load();
    });
    Object.values(videoElsRef.current).forEach((v) => {
      try { v?.pause(); } catch { /* already detached */ }
    });
    videoElsRef.current = {};
    mediaSourcesRef.current = new Map();
    clipGainsRef.current = new Map();
    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;
    audioNodesRef.current = null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  /**
   * Grades whatever the video layers have painted, in place. The render applies
   * lut3d before the sticker overlay and the subtitle burn, so this runs at
   * the same point -- captions and badges keep their exact colours.
   */
  const applyGrade = (ctx, canvas) => {
    const lut = lutRef.current;
    const strength = grade?.intensity ?? 1;
    if (!lut || !(strength > 0.001)) return;
    if (!lutRendererRef.current) {
      lutRendererRef.current = createLutRenderer(CANVAS_W, CANVAS_H) || { apply: () => null, dispose: () => {} };
    }
    const graded = lutRendererRef.current.apply(canvas, lut, strength);
    if (!graded) return;
    const prevAlpha = ctx.globalAlpha;
    const prevFilter = ctx.filter;
    ctx.globalAlpha = 1;
    ctx.filter = 'none';
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    ctx.drawImage(graded, 0, 0);
    ctx.globalAlpha = prevAlpha;
    ctx.filter = prevFilter;
  };

  const renderAt = (t) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!ctx || !segments.length) return;
    const plan = getDrawPlan(t);
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    plan.forEach((entry) => {
      const video = videoElsRef.current[entry.seg.clip.id];
      if (video) paintEntry(ctx, entry, video, getOffscreen());
    });
    ctx.globalAlpha = 1;
    ctx.filter = 'none';
    applyGrade(ctx, canvas);
    drawHookHeader(ctx, hookBrand, hookModel, hookLabel, t, hookDuration, captionStyle.fontName, captionStyle.captionColor || '#FFE600', hookMotion, hookColors);
    if (!captionStyle.hidden) {
      drawCaption(ctx, cues, t, captionStyle);
    }
    drawSticker(ctx, stickerImgRef.current, t, stickerStyle);
    drawTextOverlays(ctx, textOverlays, t, captionStyle.fontName);
  };

  useEffect(() => {
    renderAt(playheadRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segments, captionKey, stickerKey, cuesKey, textOverlaysKey, lutReady, grade?.intensity]);

  const lastNotifyRef = useRef(0);

  useEffect(() => {
    if (!isPlaying || segments.length === 0) return;

    const tick = () => {
      // Audio Master Clock: Lock subtitle and video frames directly to the audio element's playback
      const audio = audioElRef.current;
      let t;
      if (audio && audio.src && !audio.paused && !audio.ended && audio.currentTime > 0) {
        t = audio.currentTime;
      } else {
        t = clockRef.current.startT + (performance.now() - clockRef.current.startWall) / 1000;
      }

      if (t >= totalDuration) {
        Object.values(videoElsRef.current).forEach(v => v?.pause());
        stopStems();
        setPlayhead(totalDuration);
        onPlayhead?.(totalDuration);
        renderAt(totalDuration);
        setIsPlaying(false);
        return;
      }

      // Keep Audio Element in check if it fell behind/drifted
      if (audio && audio.src && !audio.paused && Math.abs(audio.currentTime - t) > RESYNC.AUDIO) {
        audio.currentTime = t;
      }

      // Stems: fire the SFX due in the next lookahead window, hold the BGM at
      // its ducked/faded level for this instant, and pull the looping bed back
      // if it has drifted (its own loop restart is the usual cause).
      pumpSfx(t);
      applyBgmEnvelope(t);
      const bgmEl = bgmElRef.current;
      if (bgmEl && bgmEl.src && !bgmEl.paused && Number.isFinite(bgmEl.duration) && bgmEl.duration > 0) {
        const want = (t * (audioLiveRef.current.bgmRate || 1)) % bgmEl.duration;
        if (Math.abs(bgmEl.currentTime - want) > RESYNC.AUDIO) bgmEl.currentTime = want;
      }

      const plan = getDrawPlan(t);
      const neededIds = new Set(plan.map(p => p.seg.clip.id));

      // 1. Lookahead Pre-Roll: Pre-seek upcoming clips 0.8s - 1.2s in advance so they
      // have their first frame decoded and cached in memory before the cut boundary.
      const upcomingSeg = segments.find(s => s.segStart > t && s.segStart <= t + 1.2);
      if (upcomingSeg) {
        const nextV = videoElsRef.current[upcomingSeg.clip.id];
        const nextStart = upcomingSeg.clip.trim_start || 0;
        if (nextV && nextV.paused && !nextV.seeking) {
          if (Math.abs(nextV.currentTime - nextStart) > RESYNC.PREROLL) {
            nextV.currentTime = nextStart;
          }
        }
      }

      // 2. Play active clips & compensate drift smoothly via playbackRate (slew rate)
      // rather than aggressive currentTime seeking which stalls the decoder pipeline.
      plan.forEach(({ seg, localTime }) => {
        const v = videoElsRef.current[seg.clip.id];
        if (!v) return;
        if (v.paused) {
          // If already near localTime from pre-roll, start immediately without seek!
          if (Math.abs(v.currentTime - localTime) > RESYNC.START) {
            v.currentTime = localTime;
          }
          v.playbackRate = 1.0;
          v.play().catch(() => {});
        } else {
          const drift = v.currentTime - localTime;
          if (Math.abs(drift) > RESYNC.VIDEO_HARD) {
            // Large drift (after scrub or tab resume) -> hard seek
            v.currentTime = localTime;
            v.playbackRate = 1.0;
          } else if (drift < -RESYNC.VIDEO_SLEW) {
            // Video is slightly trailing behind -> accelerate 6% to catch up smoothly
            v.playbackRate = 1.06;
          } else if (drift > RESYNC.VIDEO_SLEW) {
            // Video is slightly ahead -> slow down 6% to let master clock catch up
            v.playbackRate = 0.94;
          } else {
            if (v.playbackRate !== 1.0) v.playbackRate = 1.0;
          }
        }
      });

      // 3. Pause video elements no longer in the plan
      Object.entries(videoElsRef.current).forEach(([id, v]) => {
        if (v && !v.paused && !neededIds.has(id)) {
          v.playbackRate = 1.0;
          v.pause();
        }
      });

      // 4. Glitch-Protected Double-Buffered Rendering
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (ctx) {
        let framePainted = false;
        plan.forEach((entry) => {
          const { seg } = entry;
          const video = videoElsRef.current[seg.clip.id];
          if (!video) return;

          // If incoming video is still actively seeking to its cut point,
          // hold the outgoing clip's frame to eliminate any flash or random frame stutter
          if (video.seeking && prevActiveClipIdRef.current && prevActiveClipIdRef.current !== seg.clip.id) {
            const prevV = videoElsRef.current[prevActiveClipIdRef.current];
            const prevSeg = segments.find(s => s.clip.id === prevActiveClipIdRef.current);
            if (prevV && prevSeg && prevV.readyState >= 2 && !prevV.seeking) {
              if (!framePainted) ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
              ctx.globalAlpha = 1;
              ctx.filter = clipFilter(prevSeg.clip);
              drawVideoFrame(ctx, prevV, prevSeg.clip);
              framePainted = true;
              return;
            }
          }

          if (video.readyState >= 2 && !video.seeking) {
            if (!framePainted) ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
            paintEntry(ctx, entry, video, getOffscreen());
            framePainted = true;
            prevActiveClipIdRef.current = seg.clip.id;
          }
        });

        ctx.globalAlpha = 1;
        ctx.filter = 'none';
        if (framePainted) applyGrade(ctx, canvas);
        drawHookHeader(ctx, hookBrand, hookModel, hookLabel, t, hookDuration, captionStyle.fontName, captionStyle.captionColor || '#FFE600', hookMotion, hookColors);
        if (!captionStyle.hidden) {
          drawCaption(ctx, cues, t, captionStyle);
        }
        drawSticker(ctx, stickerImgRef.current, t, stickerStyle);
        drawTextOverlays(ctx, textOverlays, t, captionStyle.fontName);
      }

      setPlayhead(t);
      const now = performance.now();
      if (!lastNotifyRef.current || now - lastNotifyRef.current > 50) {
        lastNotifyRef.current = now;
        onPlayhead?.(t);
      }
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, segments, cues, textOverlays, totalDuration]);

  const togglePlay = () => {
    if (!segments.length) return;
    if (isPlaying) {
      Object.values(videoElsRef.current).forEach(v => v?.pause());
      stopStems();
      setIsPlaying(false);
    } else {
      const startT = playhead >= totalDuration ? 0 : playhead;
      clockRef.current = { startWall: performance.now(), startT };
      cueStemsTo(startT);
      startStems();
      setPlayhead(startT);
      onPlayhead?.(startT);
      setIsPlaying(true);
    }
  };

  const seekTo = (t) => {
    const maxDur = totalDuration || 999999;
    const clamped = Math.max(0, Math.min(maxDur, t));
    Object.values(videoElsRef.current).forEach(v => v?.pause());
    // Stop the stems before repositioning them. Seeking a *playing* media
    // element is asynchronous, so a drag used to issue a new seek every frame
    // while the last one was still pending -- the element fell behind, the
    // tick kept reading its stale currentTime as the master clock, and the
    // playhead snapped back under the cursor. Pausing first also drops any
    // SFX already handed to WebAudio, which would otherwise fire again on the
    // way back over their cue.
    stopStems();
    cueStemsTo(clamped);
    setPlayhead(clamped);
    playheadRef.current = clamped;
    onPlayhead?.(clamped);
    clockRef.current = { startWall: performance.now(), startT: clamped };
    if (isPlaying) startStems();

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
    if (isPlaying) {
      stopStems();
      setIsPlaying(false);
    }
    seekTo(parseFloat(e.target.value));
  };

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-center gap-2">
      {/* Master-clock audio: the voice stem when the project has one, else the
          legacy baked mix so projects rendered before stem playback still have
          sound. Both are muted through the WebAudio master gain, not the
          element's own flag, once the graph has claimed them. */}
      {(audioStems?.voiceUrl || audioUrl) && (
        <audio
          key={audioStems?.voiceUrl || audioUrl}
          ref={(el) => { audioElRef.current = el; if (el) el.muted = isMuted; }}
          src={toMediaUrl(audioStems?.voiceUrl || audioUrl)}
          preload="auto"
          playsInline
          muted={isMuted}
        />
      )}

      {/* Background music, looped exactly as the render's -stream_loop -1 does.
          Level and ducking live on its gain node, not here. */}
      {audioStems?.bgm?.url && (
        <audio
          key={audioStems.bgm.url}
          ref={(el) => { bgmElRef.current = el; if (el) el.muted = isMuted; }}
          src={audioStems.bgm.url}
          preload="auto"
          playsInline
          loop
          muted={isMuted}
        />
      )}

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
            // These elements exist to decode frames, so they stay muted --
            // except where the clip has its own volume, which the render mixes
            // in and the preview now plays through the clip-audio bus.
            muted={!(Number(c.volume) > 0)}
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
            <>
              <button
                onClick={togglePlay}
                className="group absolute inset-0 flex cursor-pointer items-center justify-center bg-black/0 transition-colors hover:bg-black/20"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-black/60 text-white opacity-0 shadow-lg transition-all group-hover:bg-[#D97757] group-hover:opacity-100">
                  {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                </div>
              </button>
              {/* Timecode lives here, over the stage, instead of in a
                  transport row below it -- the row's own play button was
                  redundant with the click-to-play overlay above, and
                  removing the row entirely (compact mode) gives the stage
                  the full column height instead of losing a strip to it. */}
              <div className="pointer-events-none absolute bottom-2 right-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-mono font-bold text-white/90 backdrop-blur-sm">
                {playhead.toFixed(1)}s / {totalDuration.toFixed(1)}s
              </div>
            </>
          )}
        </div>
      </div>

      {metadataReady && clips.length > 0 && !compact && (
        <>
          <div className="flex w-full flex-shrink-0 items-center gap-2 pt-1">
            <input
              type="range" min={0} max={totalDuration || 0} step={0.01}
              value={playhead}
              onChange={handleScrubInput}
              className="flex-1 accent-[#D97757]"
            />
          </div>
          <p className="flex flex-shrink-0 items-center gap-1 text-sm text-[#9C968F]">
            <Eye className="w-3.5 h-3.5 text-[#9C968F]" /> พรีวิวรวมทั้ง sequence แบบประมาณ (ฟอนต์/สีจริงยึดผลจาก Apply เท่านั้น)
          </p>
        </>
      )}
    </div>
  );
}

export default forwardRef(SequencePlayer);
