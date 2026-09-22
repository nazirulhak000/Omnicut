import React, { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import {
  Play, Pause, Eye, Shield, Trash2, Move, RotateCcw, Plus,
  AlertTriangle, CheckCircle2, Loader2,
} from 'lucide-react';
import { toMediaUrl } from '../lib/mediaUrl';
import api from '../api';
import { createLutRenderer, loadCube } from '../lib/lut3d';
import {
  ACCENT_COLOR,
  ANCHOR_TOP,
  CANVAS_SCALE,
  HOOK_ANIM,
  PILL_PAD_X_EM,
  PILL_PAD_Y_EM,
  PILL_RADIUS_MAX_PX,
  TEXT_FS_RATIO,
  TEXT_POSITIONS,
  fontWeight,
  overlayRenderProfile,
  resolveLook,
} from '../lib/overlayModel';
import {
  buildSegments, totalDuration as totalDurationOf, getDrawPlan as planAt,
  resolveClipTransforms, localTimeAt, motionTimeAt,
} from '../lib/timelineMath';
import { DEFAULT_STYLE_PRESET, getStylePreset } from '../lib/stylePresetCatalog.js';
import { requestOverlayLayout, getCachedOverlayLayout } from '../lib/overlayLayoutClient.js';
import {
  projectOverlayScale,
  positionPatchForBox,
  resolveSelectedBox,
  roundNormalizedPoint,
  scalePatchForBox,
  snapNormalizedPoint,
} from '../lib/overlayBoxGeometry.js';
import { bindWindowPointerLifecycle } from '../lib/pointerDragLifecycle.js';
import { drawMediaWithAccentRecolor } from '../lib/overlayRecolor.js';
import { reconcileEffectPlayback } from '../lib/effectPlayback.js';
import { getMotionPreset, MOTION_PRESETS } from '../lib/motion/motionPresets.js';
import { sampleCanvasMotion } from '../lib/motion/rendererAdapter.js';
import {
  backgroundIsolationPrefetchTimes,
  resolveBackgroundIsolationConfig,
  resolveBackgroundIsolationPreview,
  splitBackgroundIsolationOverlays,
  backgroundIsolationStatusMeta,
} from '../lib/backgroundIsolationPreview.js';

const CANVAS_W = 540;
const CANVAS_H = 960;
const BACKGROUND_ISOLATION_BG = '#0B1220';
const BACKGROUND_FRAME_RETRY_DELAYS_MS = Object.freeze([250, 1000, 4000]);
const BACKGROUND_FRAME_CACHE_LIMIT = 120;

function backgroundFrameRetryDelay(retryCount) {
  const index = Math.max(0, Math.floor(Number(retryCount) || 0));
  if (index >= BACKGROUND_FRAME_RETRY_DELAYS_MS.length) return null;
  return BACKGROUND_FRAME_RETRY_DELAYS_MS[index];
}

function evictBackgroundIsolationFrameCache(cache, keepKey) {
  while (cache.size >= BACKGROUND_FRAME_CACHE_LIMIT) {
    const oldest = cache.keys().next().value;
    if (oldest == null) return;
    if (oldest === keepKey) return;
    const entry = cache.get(oldest);
    if (entry?.retryTimer != null) clearTimeout(entry.retryTimer);
    if (entry?.objectUrl) URL.revokeObjectURL(entry.objectUrl);
    cache.delete(oldest);
  }
}

// SpotlightV1 is an opt-in footage treatment. These values mirror
// scripts/spotlight_effect.py exactly; the preview normalises here because it
// can also receive an editor-era manifest before the backend has rendered it.
const SPOTLIGHT_SCHEMA_VERSION = 1;
const SPOTLIGHT_SHAPES = new Set(['ellipse', 'rectangle', 'rounded_rect']);
const SPOTLIGHT_DEFAULT_SHAPE = 'ellipse';
const SPOTLIGHT_DEFAULT_FOCUS = Object.freeze({ x: 0.5, y: 0.5, width: 0.62, height: 0.42 });
const SPOTLIGHT_DEFAULT_DIM_OPACITY = 0.42;
const SPOTLIGHT_DEFAULT_FEATHER = 0.035;
const SPOTLIGHT_DEFAULT_CORNER_RADIUS = 0.08;
const SPOTLIGHT_MAX_DIM_OPACITY = 0.95;
const SPOTLIGHT_MAX_FEATHER = 0.25;

const finiteSpotlightNumber = (value) => (
  typeof value === 'number' && Number.isFinite(value) ? value : null
);
const clampSpotlight = (value, min, max) => Math.max(min, Math.min(max, value));
const roundSpotlight = (value) => Math.round(value * 1000000) / 1000000;

/**
 * Canvas-side normalisation for the backend's SpotlightV1 contract.
 * Missing, disabled, malformed, or unsupported configs are a strict no-op.
 */
export function normalizeSpotlightPreview(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const hasSchemaVersion = Object.prototype.hasOwnProperty.call(value, 'schema_version');
  if ((hasSchemaVersion ? value.schema_version : SPOTLIGHT_SCHEMA_VERSION) !== SPOTLIGHT_SCHEMA_VERSION) return null;
  if (value.enabled !== true) return null;

  const shapeAliases = { rect: 'rectangle', 'rounded-rect': 'rounded_rect', 'rounded-rectangle': 'rounded_rect' };
  const hasShape = Object.prototype.hasOwnProperty.call(value, 'shape');
  if (hasShape && typeof value.shape !== 'string') return null;
  const shapeValue = hasShape ? value.shape.trim().toLowerCase() : SPOTLIGHT_DEFAULT_SHAPE;
  const shape = shapeAliases[shapeValue] || shapeValue;
  if (!SPOTLIGHT_SHAPES.has(shape)) return null;

  const rawFocus = value.focus == null ? SPOTLIGHT_DEFAULT_FOCUS : value.focus;
  if (!rawFocus || typeof rawFocus !== 'object' || Array.isArray(rawFocus)) return null;
  const focusNumber = (key, fallback) => finiteSpotlightNumber(rawFocus[key]) ?? fallback;
  const width = clampSpotlight(focusNumber('width', SPOTLIGHT_DEFAULT_FOCUS.width), 0.02, 1);
  const height = clampSpotlight(focusNumber('height', SPOTLIGHT_DEFAULT_FOCUS.height), 0.02, 1);
  const x = clampSpotlight(focusNumber('x', SPOTLIGHT_DEFAULT_FOCUS.x), width / 2, 1 - width / 2);
  const y = clampSpotlight(focusNumber('y', SPOTLIGHT_DEFAULT_FOCUS.y), height / 2, 1 - height / 2);
  const dimOpacity = clampSpotlight(
    finiteSpotlightNumber(value.dim_opacity) ?? SPOTLIGHT_DEFAULT_DIM_OPACITY,
    0,
    SPOTLIGHT_MAX_DIM_OPACITY,
  );
  const feather = clampSpotlight(
    finiteSpotlightNumber(value.feather) ?? SPOTLIGHT_DEFAULT_FEATHER,
    0,
    SPOTLIGHT_MAX_FEATHER,
  );
  const cornerRadius = Math.min(
    clampSpotlight(
      finiteSpotlightNumber(value.corner_radius) ?? SPOTLIGHT_DEFAULT_CORNER_RADIUS,
      0,
      0.5,
    ),
    Math.min(width, height) / 2,
  );

  return {
    schema_version: SPOTLIGHT_SCHEMA_VERSION,
    enabled: true,
    shape,
    focus: { x: roundSpotlight(x), y: roundSpotlight(y), width: roundSpotlight(width), height: roundSpotlight(height) },
    dim_opacity: roundSpotlight(dimOpacity),
    feather: roundSpotlight(feather),
    corner_radius: roundSpotlight(cornerRadius),
  };
}

function spotlightFromEffects(effects) {
  if (!Array.isArray(effects)) return undefined;
  const item = effects.find((entry) => {
    const kind = String(entry?.kind || entry?.type || entry?.effect_type || '').trim().toLowerCase();
    return kind === 'spotlight' || kind === 'spotlightv1';
  });
  if (!item) return undefined;
  return item.config ?? item.spotlight ?? item;
}

function resolveSpotlightPreview(spotlight, effects) {
  // `undefined` means the caller did not expose the new prop yet, so accept a
  // SpotlightV1 item carried by the existing effects manifest. Explicit null
  // remains a deliberate no-op.
  return normalizeSpotlightPreview(spotlight === undefined ? spotlightFromEffects(effects) : spotlight);
}

function drawSpotlightShape(ctx, effect, width, height) {
  const focus = effect.focus;
  const cx = focus.x * width;
  const cy = focus.y * height;
  const halfWidth = focus.width * width / 2;
  const halfHeight = focus.height * height / 2;
  const left = cx - halfWidth;
  const top = cy - halfHeight;
  const shapeWidth = halfWidth * 2;
  const shapeHeight = halfHeight * 2;

  ctx.beginPath();
  if (effect.shape === 'ellipse') {
    ctx.ellipse(cx, cy, halfWidth, halfHeight, 0, 0, Math.PI * 2);
  } else if (effect.shape === 'rounded_rect') {
    const radius = Math.min(effect.corner_radius * Math.min(width, height), halfWidth, halfHeight);
    if (typeof ctx.roundRect === 'function') {
      ctx.roundRect(left, top, shapeWidth, shapeHeight, radius);
    } else {
      const r = Math.max(0, radius);
      ctx.moveTo(left + r, top);
      ctx.lineTo(left + shapeWidth - r, top);
      ctx.quadraticCurveTo(left + shapeWidth, top, left + shapeWidth, top + r);
      ctx.lineTo(left + shapeWidth, top + shapeHeight - r);
      ctx.quadraticCurveTo(left + shapeWidth, top + shapeHeight, left + shapeWidth - r, top + shapeHeight);
      ctx.lineTo(left + r, top + shapeHeight);
      ctx.quadraticCurveTo(left, top + shapeHeight, left, top + shapeHeight - r);
      ctx.lineTo(left, top + r);
      ctx.quadraticCurveTo(left, top, left + r, top);
      ctx.closePath();
    }
  } else {
    ctx.rect(left, top, shapeWidth, shapeHeight);
  }
}

function drawSpotlightHardCutout(ctx, effect, width, height) {
  // Fallback for browsers without a usable offscreen canvas/filter. The
  // contract remains safe and deterministic; feather degrades to a clean hard
  // edge rather than dimming the product window or throwing during playback.
  ctx.save();
  ctx.globalAlpha = effect.dim_opacity;
  ctx.fillStyle = '#000000';
  ctx.beginPath();
  ctx.rect(0, 0, width, height);
  drawSpotlightShape(ctx, effect, width, height);
  try {
    ctx.clip('evenodd');
    ctx.fillRect(0, 0, width, height);
  } catch {
    // An old canvas implementation without even-odd clipping cannot safely
    // invert the focus path, so this frame is a strict no-op.
  }
  ctx.restore();
}

/** Draw dimmed footage with the configured focus window; never draws text. */
export function drawSpotlight(ctx, value, width = CANVAS_W, height = CANVAS_H) {
  const effect = normalizeSpotlightPreview(value);
  if (!ctx || !effect || effect.dim_opacity <= 0) return false;

  const canCreateCanvas = typeof document !== 'undefined' && typeof document.createElement === 'function';
  if (!canCreateCanvas) {
    drawSpotlightHardCutout(ctx, effect, width, height);
    return true;
  }

  try {
    const source = document.createElement('canvas');
    const mask = document.createElement('canvas');
    const focus = document.createElement('canvas');
    [source, mask, focus].forEach((canvas) => { canvas.width = width; canvas.height = height; });
    const sourceCtx = source.getContext('2d');
    const maskCtx = mask.getContext('2d');
    const focusCtx = focus.getContext('2d');
    if (!sourceCtx || !maskCtx || !focusCtx) throw new Error('spotlight canvas unavailable');

    sourceCtx.drawImage(ctx.canvas, 0, 0, width, height);
    maskCtx.fillStyle = '#FFFFFF';
    if (effect.feather > 0) maskCtx.filter = `blur(${effect.feather * Math.min(width, height)}px)`;
    drawSpotlightShape(maskCtx, effect, width, height);
    maskCtx.fill();
    maskCtx.filter = 'none';

    ctx.save();
    ctx.globalAlpha = effect.dim_opacity;
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);
    ctx.restore();

    focusCtx.drawImage(source, 0, 0);
    focusCtx.globalCompositeOperation = 'destination-in';
    focusCtx.drawImage(mask, 0, 0);
    ctx.drawImage(focus, 0, 0);
    return true;
  } catch {
    drawSpotlightHardCutout(ctx, effect, width, height);
    return true;
  }
}

// Permanent copyright watermark -- mirrors the always-on Dialogue event
// scripts/subtitle_engine.py burns into every export (WATERMARK_TEXT /
// WATERMARK_X_RATIO / WATERMARK_Y_RATIO / WATERMARK_FS_RATIO there). Keep
// these four values identical on both sides; this is the preview half of
// that render/preview parity, not an independent design choice.
const WATERMARK_TEXT = 'สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง';
const WATERMARK_X_RATIO = 0.945;
const WATERMARK_Y_RATIO = 0.72;
const WATERMARK_FS_RATIO = 0.038;
const WATERMARK_COLOR = '#FF0000';
const WATERMARK_ALPHA = 0.4;
// Canvas playback remains frame-paced, but React only needs enough playhead
// updates to keep the editor chrome and selection box visually current. The
// preview/render contract is 30 FPS, so this caps React state publication at
// that same rate without changing the audio master clock or Canvas drawing.
const PLAYHEAD_UI_INTERVAL_MS = 1000 / 30;
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
function drawClipInto(ctx, video, clip, alpha = 1, motionTime = 0, isolatedImage = null) {
  ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
  ctx.filter = clipFilter(clip);
  const painted = isolatedImage
    ? drawIsolatedFrame(ctx, isolatedImage, clip, motionTime)
    : drawVideoFrame(ctx, video, clip, motionTime);
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
function paintEntry(ctx, entry, video, offscreen, isolatedImage = null) {
  const { seg, transition: kind, progress: p, role, alpha } = entry;
  const clip = seg.clip;

  // Slides move both clips as one strip, so each side gets its own offset.
  const slide = role && role !== 'solo' ? slideOffsets(kind, p) : null;
  if (slide) {
    const [dx, dy] = role === 'out' ? slide[0] : slide[1];
    ctx.save();
    ctx.translate(dx, dy);
    const painted = drawClipInto(ctx, video, clip, 1, entry.motionTime, isolatedImage);
    ctx.restore();
    return painted;
  }

  if (role !== 'in') {
    const painted = drawClipInto(ctx, video, clip, 1, entry.motionTime, isolatedImage);
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
    if (!drawClipInto(oc, video, clip, 1, entry.motionTime, isolatedImage)) return false;
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
    if (!drawClipInto(oc, video, clip, 1, entry.motionTime, isolatedImage)) return false;
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
    const painted = drawClipInto(ctx, video, clip, 1, entry.motionTime, isolatedImage);
    ctx.restore();
    return painted;
  }
  ctx.restore();

  const blend = (kind === 'fadeblack' || kind === 'fadewhite') ? bridgeWeights(p).wB : alpha;
  return drawClipInto(ctx, video, clip, blend, entry.motionTime, isolatedImage);
}

function drawVideoFrame(ctx, video, clip, motionTime = 0) {
  if (!video || !video.videoWidth || video.readyState < 2) return false;
  const camera = resolveClipTransforms(clip, motionTime);
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
  const zoom = camera.zoom;
  if (zoom > 1.001) {
    const zw = sw / zoom, zh = sh / zoom;
    const roomX = sw - zw, roomY = sh - zh;
    const panX = camera.pan_x;
    const panY = camera.pan_y;
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
    const zoomK = camera.zoom;
    const panX = camera.pan_x;
    const panY = camera.pan_y;
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

/** Draw a ready RGBA cutout over the same deterministic mood background used
 * by the FFmpeg renderer. The cutout is a full source frame, so crop/zoom,
 * mirror, and rotation must follow the ordinary video path exactly. */
function drawIsolatedFrame(ctx, image, clip, motionTime = 0, { includeBackground = true } = {}) {
  if (!image || !image.naturalWidth || !image.naturalHeight || !image.complete) return false;
  const camera = resolveClipTransforms(clip, motionTime);
  const rotation = Number(clip?.rotation || 0) % 360;
  const isRotated90or270 = rotation === 90 || rotation === 270;
  const sourceWidth = image.naturalWidth;
  const sourceHeight = image.naturalHeight;
  const vw = isRotated90or270 ? sourceHeight : sourceWidth;
  const vh = isRotated90or270 ? sourceWidth : sourceHeight;
  const vRatio = vw / vh;
  const cRatio = CANVAS_W / CANVAS_H;
  let sx; let sy; let sw; let sh;
  if (vRatio > cRatio) {
    sh = vh; sw = vh * cRatio; sy = 0; sx = (vw - sw) / 2;
  } else {
    sw = vw; sh = vw / cRatio; sx = 0; sy = (vh - sh) / 2;
  }
  const zoom = camera.zoom;
  if (zoom > 1.001) {
    const zw = sw / zoom; const zh = sh / zoom;
    sx += ((sw - zw) / 2) * (1 + camera.pan_x);
    sy += ((sh - zh) / 2) * (1 + camera.pan_y);
    sw = zw; sh = zh;
  }

  const frameFilter = ctx.filter;
  ctx.filter = 'none';
  if (includeBackground) {
    ctx.fillStyle = BACKGROUND_ISOLATION_BG;
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
  }
  ctx.filter = frameFilter;
  const mirror = !!clip?.mirror;
  if (mirror || rotation !== 0) {
    ctx.save();
    ctx.translate(CANVAS_W / 2, CANVAS_H / 2);
    if (mirror) ctx.scale(-1, 1);
    if (rotation !== 0) ctx.rotate((rotation * Math.PI) / 180);
    if (rotation === 90) {
      ctx.drawImage(image, Math.max(0, sy), Math.max(0, sourceHeight - (sx + sw)), Math.min(sourceWidth, sh), Math.min(sourceHeight, sw), -CANVAS_H / 2, -CANVAS_W / 2, CANVAS_H, CANVAS_W);
    } else if (rotation === 270) {
      ctx.drawImage(image, Math.max(0, sourceWidth - (sy + sh)), Math.max(0, sx), Math.min(sourceWidth, sh), Math.min(sourceHeight, sw), -CANVAS_H / 2, -CANVAS_W / 2, CANVAS_H, CANVAS_W);
    } else if (rotation === 180) {
      ctx.drawImage(image, sourceWidth - (sx + sw), sourceHeight - (sy + sh), sw, sh, -CANVAS_W / 2, -CANVAS_H / 2, CANVAS_W, CANVAS_H);
    } else {
      ctx.drawImage(image, sx, sy, sw, sh, -CANVAS_W / 2, -CANVAS_H / 2, CANVAS_W, CANVAS_H);
    }
    ctx.restore();
  } else {
    ctx.drawImage(image, sx, sy, sw, sh, 0, 0, CANVAS_W, CANVAS_H);
  }
  return true;
}

function backgroundArtifactId(config) {
  if (!config || typeof config !== 'object' || Array.isArray(config)) return null;
  const artifact = config.artifact;
  if (!artifact || typeof artifact !== 'object' || Array.isArray(artifact)) return null;
  return artifact.sequence_id || artifact.sequenceId || artifact.id || null;
}

function BackgroundIsolationStatusBadge({ status = 'off' }) {
  const meta = backgroundIsolationStatusMeta(status);
  const tone = {
    off: 'border-white/[0.12] bg-black/70 text-slate-300',
    missing: 'border-amber-300/40 bg-amber-950/75 text-amber-100',
    processing: 'border-amber-300/40 bg-amber-950/75 text-amber-100',
    ready: 'border-emerald-300/45 bg-emerald-950/80 text-emerald-100',
    partial: 'border-amber-300/40 bg-amber-950/75 text-amber-100',
    quality_failed: 'border-rose-300/45 bg-rose-950/80 text-rose-100',
  }[status] || 'border-white/[0.12] bg-black/70 text-slate-300';
  const icon = status === 'ready'
    ? <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
    : status === 'processing'
      ? <Loader2 className="h-3.5 w-3.5 flex-shrink-0 animate-spin" aria-hidden="true" />
      : status === 'quality_failed'
        ? <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
        : <Eye className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`${meta.label}: ${meta.detail}`}
      title={`${meta.label}: ${meta.detail}`}
      className={`pointer-events-none absolute left-2 top-2 z-30 flex max-w-[78%] items-start gap-1.5 rounded-lg border px-2 py-1 text-[10px] font-bold leading-tight shadow-md backdrop-blur-md ${tone}`}
    >
      {icon}
      <span className="min-w-0">
        <span className="block">{meta.label}</span>
        <span className="mt-0.5 block text-[9px] font-medium opacity-75">{meta.detail}</span>
      </span>
    </div>
  );
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
  const needsSpace = idx > 0 && /[\u0E00-\u0E7F]/.test(text[idx - 1]) && text[idx - 1] !== ' ';
  const beforeStr = text.slice(0, idx) + (needsSpace ? ' ' : '');
  if (beforeStr) segments.push({ text: beforeStr, color: defaultColor });
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
          const needsSpace = idx > 0 && /[\u0E00-\u0E7F]/.test(text[idx - 1]) && text[idx - 1] !== ' ';
          const beforeStr = text.slice(0, idx) + (needsSpace ? ' ' : '');
          if (beforeStr) segments.push({ text: beforeStr, color: defaultColor });
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

// Thai-safe caption entrance, mirroring `caption_anim` in subtitle_engine.py.
// Fade changes visibility only; scaling a shaped Thai run can collapse the
// stacked Thai upper-vowel/tone marks in libass during the first frames.
const CAPTION_FADE_MS = 70;
const THAI_UPPER_VOWELS = '\u0E31\u0E34\u0E35\u0E36\u0E37';
const THAI_TONE_MARKS = '\u0E48\u0E49\u0E4A\u0E4B';
const THAI_STACKED_MARK_RE = new RegExp(`([${THAI_UPPER_VOWELS}])([${THAI_TONE_MARKS}])`, 'g');
const THAI_STACKED_MARK_RAISE_EM = 0.13;

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

// Several bundled Thai faces rasterise upper-vowel/tone pairs into one
// crowded vertical band through ASS/libass. Keep the same 20-pair repair in
// Canvas so Preview and Render use one deterministic two-level stack.
function drawCaptionText(ctx, text, x, y, fontSize, drawText, repairThaiMarks = true) {
  const matches = repairThaiMarks ? [...text.matchAll(THAI_STACKED_MARK_RE)] : [];
  if (matches.length === 0) {
    drawText(text, x, y);
    return;
  }

  const body = text.replace(THAI_STACKED_MARK_RE, '$1');
  drawText(body, x, y);

  for (const match of matches) {
    const pairAt = match.index;
    if (pairAt < 1) continue;
    const baseAt = pairAt - 1;
    const prefix = text.slice(0, baseAt).replace(THAI_STACKED_MARK_RE, '$1');
    const base = text[baseAt];
    // The IBM Thai mark-to-base anchor is at the far side of the consonant's
    // advance, so using its midpoint leaves the detached tone a few pixels
    // left of the base glyph on centred lines.
    const toneX = x + ctx.measureText(prefix).width + ctx.measureText(base).width;
    // The body uses the full caption outline, but a detached tone uses only
    // a one-pixel ASS border at render scale. A full-width stroke would turn
    // narrow tone glyphs into blocks.
    const oldLineWidth = ctx.lineWidth;
    ctx.lineWidth = Math.max(1, Math.round(fontSize * 2 * 0.02));
    // Keep the same font-relative optical raise as the ASS/libass renderer.
    drawText(match[2], toneX, y - Math.max(4, Math.round(fontSize * THAI_STACKED_MARK_RAISE_EM)));
    ctx.lineWidth = oldLineWidth;
  }
}

// Product callouts are editorial overlays, but Thai shaping still needs the
// same two-level repair as captions. Keep the opt-in flag local to callouts so
// legacy text overlays retain their exact historical glyph output.
function drawProductCalloutText(ctx, text, x, y, fontSize, drawText, repairThaiMarks = false) {
  if (!repairThaiMarks) {
    drawText(text, x, y);
    return;
  }
  const matches = [...String(text).matchAll(THAI_STACKED_MARK_RE)];
  if (matches.length === 0) {
    drawText(text, x, y);
    return;
  }

  const body = String(text).replace(THAI_STACKED_MARK_RE, '$1');
  drawText(body, x, y);
  for (const match of matches) {
    const pairAt = match.index;
    if (pairAt < 1) continue;
    const baseAt = pairAt - 1;
    const prefix = String(text).slice(0, baseAt).replace(THAI_STACKED_MARK_RE, '$1');
    const base = String(text)[baseAt];
    const toneX = x + ctx.measureText(prefix).width + ctx.measureText(base).width;
    const oldLineWidth = ctx.lineWidth;
    // ASS companion events use a one-pixel render outline. This is the
    // half-resolution Canvas equivalent, preventing a narrow tone from
    // becoming a dark block above the callout.
    ctx.lineWidth = Math.max(1, Math.round(fontSize * 2 * 0.02));
    drawText(match[2], toneX, y - Math.max(4, Math.round(fontSize * THAI_STACKED_MARK_RAISE_EM)));
    ctx.lineWidth = oldLineWidth;
  }
}

function drawSingleCue(ctx, cue, t, style = {}, outBounds = null) {
  if (!cue || !cue.text) return;
  const globalScale = Math.min(2.5, Math.max(0.5, style.captionScale ?? 1.0));
  const effectiveScale = typeof cue.scale === 'number' && cue.scale > 0
    ? Math.min(3.0, Math.max(0.4, cue.scale))
    : globalScale;
  // Standard TikTok Subtitle Size: 100% (scale=1.0) is calibrated to 50pt on 1080w
  // (25px on 540w Canvas), exactly matching the user's preferred visual proportion.
  const baseFs = Math.round(CANVAS_W * 0.0463);
  const fontSize = Math.max(14, Math.round(baseFs * effectiveScale));
  
  const fontFamName = cue.fontName || style.fontName || 'Kanit';
  let fontFam = "'Kanit', sans-serif";
  let fontWeight = '900';
  if (fontFamName === 'IBMPlex' || fontFamName === 'IBM Plex Sans Thai') {
    fontFam = "'IBM Plex Sans Thai', sans-serif";
    // Keep body captions on the same physical cut as ASS/libass.  The IBM
    // family also ships Bold; requesting it here made the browser and render
    // choose different Thai mark anchors for `ั` + `่` in `นั่ง`.
    fontWeight = '600';
  } else if (fontFamName === 'Prompt') {
    fontFam = "'Prompt', sans-serif";
    fontWeight = '800';
  }
  // Use one deterministic stack for every face. Prompt/Kanit/Mitr/Itim need
  // the repair in libass, and mirroring it here prevents Preview/Render drift.
  const repairThaiMarks = true;

  ctx.save();
  const fadeElapsedMs = (t - cue.start) * 1000;
  const captionAlpha = fadeElapsedMs >= CAPTION_FADE_MS
    ? 1
    : Math.min(1, Math.max(0, fadeElapsedMs / CAPTION_FADE_MS));
  ctx.globalAlpha *= captionAlpha;
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
  const showBilingual = style.bilingualSubtitles !== false && cue.bilingual !== false;
  if (showBilingual && cue.translation && !cue.translation.includes('Error 500')) {
    ctx.font = `700 ${enFontSize}px ${fontFam}`;
    enLines = wrapCanvasText(cue.translation, ctx, CANVAS_W * 0.86);
  }

  // Vertical anchoring: support per-cue position override (top / middle / bottom) or custom normalized y
  const totalBlockH = (thaiLines.length + enLines.length) * fontSize;
  const pos = cue.position || style.captionPosition || 'bottom';
  const anchorY = CANVAS_H * (CAPTION_Y[pos] ?? CAPTION_Y.bottom);
  let blockTop;
  if (typeof cue.y === 'number') {
    blockTop = CANVAS_H * Math.max(0.05, Math.min(0.95, cue.y)) - totalBlockH / 2;
  } else if (pos === 'top') {
    blockTop = anchorY;
  } else if (pos === 'middle') {
    blockTop = anchorY - totalBlockH / 2;
  } else {
    blockTop = anchorY - totalBlockH;
  }
  const thaiStartY = blockTop + thaiLineH / 2;
  const normX = typeof cue.x === 'number' ? Math.max(0.05, Math.min(0.95, cue.x)) : (typeof style.captionX === 'number' ? style.captionX : 0.50);
  const xCenter = CANVAS_W * normX;

  if (outBounds && cue) {
    const measuredW = Math.max(
      ...thaiLines.map(l => ctx.measureText(l).width),
      ...(enLines.length ? enLines.map(l => ctx.measureText(l).width) : [0]),
      100
    );
    outBounds.push({
      type: 'caption',
      id: cue._uid || cue.id,
      x: xCenter - measuredW / 2 - 12,
      y: blockTop - 6,
      w: measuredW + 24,
      h: totalBlockH + 12,
      normX,
      normY: (blockTop + totalBlockH / 2) / CANVAS_H,
      scale: effectiveScale,
      label: (cue.text || 'คำบรรยาย').slice(0, 15),
      cue,
    });
  }

  // Synchronized Bilingual Kinetic Highlighting
  const primaryColor = CAPTION_COLORS[style.captionColor] || style.captionColor || '#FFFFFF';
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

  // Draw Thai lines
  thaiLines.forEach((line, idx) => {
    const lineY = thaiStartY + (idx * thaiLineH);
    const segments = parsedThaiLines[idx] || [{ text: line, color: primaryColor }];

    ctx.font = `${fontWeight} ${fontSize}px ${fontFam}`;
    // When repairThaiMarks is active, drawCaptionText strips the tone from
    // the ั่ pair and draws it as a separate glyph.  The advance of the body
    // (without the tone) differs from the original, so segmentWidths must
    // measure the repaired body text -- otherwise the next segment is offset
    // by the advance gap and Thai vowels/tones appear to float.
    const segmentWidths = segments.map(seg => {
      const txt = repairThaiMarks
        ? seg.text.replace(THAI_STACKED_MARK_RE, '$1')
        : seg.text;
      return ctx.measureText(txt).width;
    });
    const totalLineW = segmentWidths.reduce((sum, w) => sum + w, 0);

    // Pass 1: Outline / Stroke with crisp shadow
    ctx.textAlign = 'left';
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = captionOutlineWidth(fontSize);
    ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
    ctx.shadowBlur = 3;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 3;

    let curX = xCenter - totalLineW / 2;
    segments.forEach((seg, sIdx) => {
      drawCaptionText(ctx, seg.text, curX, lineY, fontSize, (value, px, py) => ctx.strokeText(value, px, py), repairThaiMarks);
      curX += segmentWidths[sIdx];
    });

    // Pass 2: Color fills (sharp contrast without doubled shadow)
    ctx.shadowColor = 'transparent';
    curX = xCenter - totalLineW / 2;
    segments.forEach((seg, sIdx) => {
      ctx.fillStyle = seg.color;
      drawCaptionText(ctx, seg.text, curX, lineY, fontSize, (value, px, py) => drawTextWithMonoEmoji(ctx, value, px, py), repairThaiMarks);
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

      let curX = xCenter - totalLineW / 2;
      segments.forEach((seg, sIdx) => {
        ctx.strokeText(seg.text, curX, lineY);
        curX += segmentWidths[sIdx];
      });

      // Pass 2: Color fills (sharp contrast without doubled shadow)
      ctx.shadowColor = 'transparent';
      curX = xCenter - totalLineW / 2;
      segments.forEach((seg, sIdx) => {
        ctx.fillStyle = seg.color;
        ctx.fillText(seg.text, curX, lineY);
        curX += segmentWidths[sIdx];
      });
    });
  }

  ctx.restore();
}

function drawCaption(ctx, cues = [], t, style = {}, outBounds = null) {
  if (!cues || cues.length === 0) return;
  const activeCues = cues.filter((c) => t >= c.start && t < c.end);
  activeCues.forEach((cue) => {
    drawSingleCue(ctx, cue, t, style, outBounds);
  });
}

function drawSingleSticker(ctx, img, t, stk, outBounds = null, accentColor = '#FFE600') {
  if (!img || !img.complete || !img.naturalWidth) return;
  const startTime = stk.start ?? stk.startTime ?? 0.5;
  const endTime = stk.end != null ? stk.end : (stk.endTime != null ? stk.endTime : 999999);
  if (t < startTime || t > endTime) return;

  const scale = Math.min(3.5, Math.max(0.3, stk.scale ?? 1));
  const baseW = 160;
  const w = Math.round(baseW * scale);
  const h = Math.round(w * (img.naturalHeight / img.naturalWidth));

  let x = CANVAS_W - w - 40;
  let y = 140;
  const normX = typeof stk.normX === 'number' ? stk.normX : stk.norm_x;
  const normY = typeof stk.normY === 'number' ? stk.normY : stk.norm_y;
  if (typeof normX === 'number' && typeof normY === 'number') {
    x = Math.round(normX * CANVAS_W - w / 2);
    y = Math.round(normY * CANVAS_H - h / 2);
  } else {
    const pos = stk.position || 'top_right';
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
  }

  if (outBounds) {
    outBounds.push({
      type: 'sticker',
      id: stk.id || 'sticker_badge',
      x,
      y,
      w,
      h,
      normX: (x + w / 2) / CANVAS_W,
      normY: (y + h / 2) / CANVAS_H,
      scale,
      label: stk.badge?.replace(/\.[^.]+$/, '') || 'สติกเกอร์ 3D',
      item: stk,
    });
  }

  const elapsed = t - startTime;
  const alpha = Math.min(1, Math.max(0, elapsed / 0.3));
  ctx.save();
  ctx.globalAlpha = alpha;
  drawMediaWithAccentRecolor(ctx, img, x, y, w, h, stk, accentColor, 'sticker', stk.badge);
  ctx.restore();
}

function drawStickers(ctx, imagesMap, singleImg, t, stickersList, outBounds = null, isStickerHidden = false, previewSticker = null, accentColor = '#FFE600') {
  if (isStickerHidden) return;
  if (stickersList && stickersList.length > 0) {
    stickersList.forEach((stk) => {
      if (stk.hidden) return;
      const bKey = stk.badge || '';
      const img = imagesMap?.get?.(bKey) || imagesMap?.get?.(bKey.toLowerCase()) || singleImg;
      if (img) drawSingleSticker(ctx, img, t, stk, outBounds, accentColor);
    });
  } else if (singleImg) {
    drawSingleSticker(ctx, singleImg, t, {}, outBounds, accentColor);
  }

  // Ephemeral preview sticker on canvas (centered)
  if (previewSticker) {
    const pKey = previewSticker;
    const img = imagesMap?.get?.(pKey) || imagesMap?.get?.(pKey.toLowerCase()) || singleImg;
    if (img && img.complete && img.naturalWidth) {
      const baseW = 160;
      const scale = 1.0;
      const w = Math.round(baseW * scale);
      const h = Math.round(w * (img.naturalHeight / img.naturalWidth));
      const x = Math.round(CANVAS_W * 0.5 - w / 2);
      const y = Math.round(CANVAS_H * 0.5 - h / 2);
      if (outBounds) {
        outBounds.push({
          type: 'sticker_preview',
          id: 'sticker_preview',
          x,
          y,
          w,
          h,
          normX: 0.5,
          normY: 0.5,
          scale: 1.0,
          label: previewSticker.replace(/\.[^.]+$/, ''),
        });
      }
      ctx.save();
      drawMediaWithAccentRecolor(ctx, img, x, y, w, h, { recolor: 'accent' }, accentColor, 'sticker', pKey);
      ctx.restore();
    }
  }
}

function drawSticker(ctx, img, t, stkStyle, outBounds = null, accentColor = '#FFE600') {
  drawSingleSticker(ctx, img, t, stkStyle || {}, outBounds, accentColor);
}

// Video overlay effects (checkmark/warning/arrow/etc). Their source clips are
// white-bg, no real alpha -- drawn with globalCompositeOperation='multiply'
// so the white blends into whatever's already painted on the canvas at that
// spot (the actual video frame drawn earlier in renderAt), same trick as the
// backend's crop+blend+overlay chain in video_editor.py. The <video> element
// is synchronised to the master timeline before each paint, so a frame/effect
// overlay starts at its configured time and does not drift during playback.
function drawSingleEffect(ctx, videoEl, t, fx, outBounds = null, accentColor = '#FFE600') {
  if (!videoEl || videoEl.readyState < 2) return;
  const startTime = fx.start ?? 0.5;
  const endTime = fx.end != null ? fx.end : 999999;
  if (t < startTime || t > endTime) return;

  const scale = Math.min(3.5, Math.max(0.3, fx.scale ?? 1));
  const baseSize = 180; // half of the backend's EFFECT_BASE_SIZE=360, matching CANVAS_W/H being half render resolution
  const w = Math.round(baseSize * scale);
  const h = w;

  const normX = typeof fx.normX === 'number' ? fx.normX : 0.5;
  const normY = typeof fx.normY === 'number' ? fx.normY : 0.35;
  const x = Math.round(normX * CANVAS_W - w / 2);
  const y = Math.round(normY * CANVAS_H - h / 2);

  if (outBounds) {
    outBounds.push({
      type: 'effect',
      id: fx.id,
      x, y, w, h,
      normX: (x + w / 2) / CANVAS_W,
      normY: (y + h / 2) / CANVAS_H,
      scale,
      label: fx.effectId || 'เอฟเฟกต์',
      item: fx,
    });
  }

  ctx.save();
  ctx.globalCompositeOperation = 'multiply';
  drawMediaWithAccentRecolor(ctx, videoEl, x, y, w, h, fx, accentColor, 'effect', fx.effectId);
  ctx.restore();
}

function syncEffectVideos(videosMap, timelineTime, effectsList = [], isPlaying = true) {
  (effectsList || []).forEach((fx) => {
    if (!fx || fx.hidden) return;
    const videoEl = videosMap?.get?.(fx.effectId);
    if (!videoEl || videoEl.readyState < 1) return;

    const decision = reconcileEffectPlayback({
      timelineTime,
      effectStart: fx.start ?? 0.5,
      mediaTime: videoEl.currentTime,
      mediaDuration: videoEl.duration,
      paused: videoEl.paused,
    });
    if (decision.action === 'idle') {
      videoEl.pause();
      videoEl.playbackRate = 1;
      return;
    }
    if (decision.targetTime != null && decision.action !== 'hold' && decision.action !== 'slew') {
      try { videoEl.currentTime = decision.targetTime; } catch {}
    }
    if (!isPlaying) {
      videoEl.pause();
      videoEl.playbackRate = 1;
      return;
    }
    videoEl.playbackRate = decision.playbackRate;
    if (decision.action === 'seek-and-play' || decision.action === 'play' || videoEl.paused) {
      videoEl.play().catch(() => {});
    }
  });
}

function drawEffects(ctx, videosMap, t, effectsList, outBounds = null, accentColor = '#FFE600') {
  (effectsList || []).forEach((fx) => {
    if (!fx || fx.hidden) return;
    const videoEl = videosMap?.get?.(fx.effectId);
    if (videoEl) drawSingleEffect(ctx, videoEl, t, fx, outBounds, accentColor);
  });
}

// Where custom text overlays sit vertically as a fraction of canvas height.
// Mirrors TEXT_OVERLAY_POSITIONS in subtitle_engine.py: top (0.20), middle (0.50), bottom (0.72).

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
const HOOK_MOTION_DEFAULTS = { in: 'bounce', stagger: true, loop: 'pulse', out: 'fade', accent: 'underline', reveal: 'simultaneous' };
const DEFAULT_HOOK_STEP_DELAY_MS = 350;
const HOOK_STAGGER_STEP = 0.15; // seconds; mirrors STAGGER_STEP_MS
const HOOK_DIM_OPACITY = 1 - 0x25 / 255; // mirrors ASS \alpha&H25&
const HOOK_SWEEP_OPACITY = 1 - 0x20 / 255; // mirrors ASS \alpha&H20&

function hookStaggerStepSec(motion = {}) {
  const factor = motion.speed === 'fast' ? 0.6 : motion.speed === 'smooth' ? 1.5 : 1;
  return Math.max(0.05, HOOK_STAGGER_STEP * factor);
}
// The pill's padding, matching HookHeaderPill's Outline=12 in the ASS styles.
const HOOK_PILL_PAD = 12;

// Mirrors front_outline = max(1.8, font_size * 0.040) in subtitle_engine.py,
// where font_size is the render-resolution size (twice this canvas one).
// An ASS outline grows outward only while strokeText centres its stroke, so
// the canvas width is twice the outward thickness it needs to imitate.
function captionOutlineWidth(canvasFontSize) {
  return Math.max(1.8, canvasFontSize * 2 * 0.04);
}

// Easing power-law constants matching motion_effects.py
const ACCEL_SOFT_OUT = 0.6;
const ACCEL_SNAP_IN = 2.2;

/** Piecewise interpolation over [[ms, value, accel?], ...] keyframes with power-law easing. */
function hookKeyframeAt(ms, kf) {
  if (ms <= kf[0][0]) return kf[0][1];
  const last = kf[kf.length - 1];
  if (ms >= last[0]) return last[1];
  for (let i = 0; i < kf.length - 1; i++) {
    const [t1, v1] = kf[i];
    const [t2, v2, accel = 1.0] = kf[i + 1];
    if (ms >= t1 && ms <= t2) {
      const p = (ms - t1) / (t2 - t1);
      return v1 + (v2 - v1) * Math.pow(p, accel);
    }
  }
  return last[1];
}

// Each In preset returns {scale, alpha, dy, reveal} for `elapsedSec` since
// this line's own stagger start, plus how long it runs (durSec) so the loop
// phase knows when every line has settled. reveal (0..1) drives the
// typewriter's left-to-right clip.
//
// The first eight came from the banner and the last five from the text
// overlays, which had their own shorter, harder versions of three of the same
// ideas -- a text `pop` snapped 1.25x down in 70ms where the banner's
// overshot to 1.18x over 200ms. Merging them would have re-timed every
// existing project, so both survive under separate names and
// LEGACY_TEXT_ANIM in overlayModel.js maps the old spellings onto the new.
const OVERLAY_IN_TRANSFORMS = {
  bounce: {
    durSec: 0.45,
    at: (ms) => ({ scale: hookKeyframeAt(ms, [[0, 0.6], [150, 1.25], [280, 0.92], [380, 1.05], [450, 1.0]]) }),
  },
  bounce_soft: {
    durSec: 0.45,
    at: (ms) => ({
      scale: hookKeyframeAt(ms, [
        [0, 0.6],
        [150, 1.25, ACCEL_SOFT_OUT],
        [280, 0.92, 1.0],
        [380, 1.05, 1.0],
        [450, 1.0, ACCEL_SOFT_OUT],
      ]),
    }),
  },
  pop: {
    durSec: 0.2,
    at: (ms) => ({ scale: hookKeyframeAt(ms, [[0, 0.55], [120, 1.18], [200, 1.0]]) }),
  },
  pop_soft: {
    durSec: 0.2,
    at: (ms) => ({
      scale: hookKeyframeAt(ms, [
        [0, 0.55],
        [120, 1.18, ACCEL_SOFT_OUT],
        [200, 1.0, ACCEL_SNAP_IN],
      ]),
    }),
  },
  slam: {
    durSec: 0.18,
    at: (ms) => ({
      scale: hookKeyframeAt(ms, [
        [0, 2.2],
        [180, 1.0, ACCEL_SNAP_IN],
      ]),
      alpha: hookKeyframeAt(ms, [
        [0, 0],
        [50, 1],
      ]),
    }),
  },
  elastic_bounce: {
    durSec: 0.52,
    at: (ms) => ({
      scale: hookKeyframeAt(ms, [
        [0, 0.4],
        [160, 1.28, ACCEL_SOFT_OUT],
        [290, 0.88, 1.0],
        [390, 1.08, 1.0],
        [460, 0.98, 1.0],
        [520, 1.0, ACCEL_SOFT_OUT],
      ]),
      alpha: hookKeyframeAt(ms, [
        [0, 0],
        [40, 1],
      ]),
    }),
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
  // --- the text overlays' own entrances, unchanged in timing ---
  snap: {
    durSec: 0.07,
    at: (ms) => ({ scale: hookKeyframeAt(ms, [[0, 1.25], [70, 1.0]]) }),
  },
  pop_zoom: {
    durSec: 0.1,
    at: (ms) => ({
      scale: hookKeyframeAt(ms, [[0, 1.45], [100, 1.0]]),
      alpha: hookKeyframeAt(ms, [[0, 0], [70, 1]]),
    }),
  },
  stamp: {
    durSec: 0.08,
    at: (ms) => ({ scale: hookKeyframeAt(ms, [[0, 1.65], [80, 1.0]]) }),
  },
  quick_fade: {
    durSec: 0.15,
    at: (ms) => ({ alpha: hookKeyframeAt(ms, [[0, 0], [150, 1]]) }),
  },
  rise: {
    durSec: 0.2,
    at: (ms) => ({
      dy: hookKeyframeAt(ms, [[0, 40], [200, 0]]),
      alpha: hookKeyframeAt(ms, [[0, 0], [200, 1]]),
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

const OVERLAY_LOOP_TRANSFORMS = {
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

const OVERLAY_OUT_TRANSFORMS = {
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

// Motion contracts are deliberately opt-in. Existing overlays only carry the
// legacy `anim` object, so they must continue through the historical Canvas
// transforms until their data explicitly opts into the contract seam.
function explicitMotionMetadata(overlay) {
  const metadata = overlay?.motionMetadata || overlay?.metadata || {};
  const inline = overlay?.motionContract
    ?? overlay?.motion_contract
    ?? metadata.motionContract
    ?? metadata.motion_contract
    ?? null;
  const id = overlay?.motionContractId
    ?? overlay?.motion_contract_id
    ?? metadata.motionContractId
    ?? metadata.motion_contract_id
    ?? (typeof inline === 'string' ? inline : null);
  return { inline, id, metadata };
}

function presetFromMotionContractId(id, role = null, phase = null) {
  if (typeof id !== 'string' || !id.trim()) return null;
  const normalized = id.trim();
  if (MOTION_PRESETS[normalized]) return MOTION_PRESETS[normalized];
  const parts = normalized.split('.');
  if (parts.length >= 3) {
    const role = parts.shift();
    const phase = parts.shift();
    return getMotionPreset(role, phase, parts.join('.'));
  }
  if (role && phase) return getMotionPreset(role, phase, normalized);
  return null;
}

function phaseContractsFromMotionSource(source, fallback = null) {
  if (!source || typeof source !== 'object' || Array.isArray(source)) return {};
  if (source.tracks && source.phase) return { [source.phase]: source };
  if (source.phases && typeof source.phases === 'object') return source.phases;
  const phaseKeys = ['in', 'loop', 'out'];
  const phases = {};
  for (const phase of phaseKeys) {
    if (source[phase] && typeof source[phase] === 'object') phases[phase] = source[phase];
  }
  if (Object.keys(phases).length) return phases;
  if (fallback?.id) {
    const preset = presetFromMotionContractId(fallback.id, fallback.role, fallback.phase);
    return preset ? { [preset.phase]: preset } : {};
  }
  return {};
}

function explicitMotionPlan(overlay, durationSec) {
  const { inline, id, metadata } = explicitMotionMetadata(overlay);
  const role = metadata.role || (overlay?.kind === 'hook' ? 'hook' : 'text');
  const phase = metadata.phase || metadata.motionPhase || null;
  const source = inline && typeof inline === 'object'
    ? inline
    : presetFromMotionContractId(id, role, phase);
  const contracts = phaseContractsFromMotionSource(source, id ? { role, phase, id } : null);
  const phases = Object.keys(contracts).filter((phase) => ['in', 'loop', 'out'].includes(phase));
  if (!phases.length) return null;

  const sourceTiming = source?.phase_timing
    || source?.phaseTiming
    || source?.metadata?.phase_timing
    || source?.metadata?.phaseTiming
    || metadata.phase_timing
    || metadata.phaseTiming
    || {};
  const phaseTiming = {};
  const duration = Math.max(0.001, Number(durationSec) || 0.001);
  const phaseDuration = (phase) => Math.max(0, Number(contracts[phase]?.duration_ms || 0) / 1000);
  const inEnd = sourceTiming.in?.end ?? (contracts.in ? Math.min(1, phaseDuration('in') / duration) : 0);
  const outStart = sourceTiming.out?.start ?? (contracts.out ? Math.max(0, 1 - phaseDuration('out') / duration) : 1);
  if (contracts.in) phaseTiming.in = {
    start: sourceTiming.in?.start ?? 0,
    end: inEnd,
  };
  if (contracts.loop) phaseTiming.loop = {
    start: sourceTiming.loop?.start ?? inEnd,
    end: sourceTiming.loop?.end ?? outStart,
  };
  if (contracts.out) phaseTiming.out = {
    start: outStart,
    end: sourceTiming.out?.end ?? 1,
  };

  return { contracts, phaseTiming, phases: new Set(Object.keys(phaseTiming)) };
}

function motionStateToLegacyFx(state = {}) {
  return {
    scale: Number.isFinite(state.scale) ? state.scale : 1,
    alpha: Number.isFinite(state.alpha) ? state.alpha : 1,
    dy: Number.isFinite(state.dy) ? state.dy : 0,
    rot: Number.isFinite(state.rotation) ? state.rotation : 0,
    blur: Number.isFinite(state.blur) ? state.blur : 0,
    reveal: Number.isFinite(state.reveal) ? state.reveal : 1,
  };
}

function sampleExplicitOverlayMotion(overlay, tRel, durationSec) {
  const plan = explicitMotionPlan(overlay, durationSec);
  if (!plan) return null;
  try {
    const sample = sampleCanvasMotion(
      { phases: plan.contracts },
      Math.max(0, Math.min(1, tRel / Math.max(0.001, durationSec))),
      { phaseTiming: plan.phaseTiming },
    );
    if (!plan.phases.has(sample.metadata.phase)) return null;
    return {
      phase: sample.metadata.phase,
      fx: motionStateToLegacyFx(sample.state),
      phaseTiming: plan.phaseTiming,
    };
  } catch {
    // Invalid or incomplete opt-in data must never take down the preview.
    // Returning null keeps the exact legacy path for that overlay.
    return null;
  }
}

// Text geometry is static for the lifetime of one overlay edit. Keeping it
// outside the RAF path avoids repeating wrapCanvasText/measureText, which was
// a major source of dropped frames when several overlays were visible.
const OVERLAY_GEOMETRY_CACHE = new WeakMap();

function overlayGeometrySignature(tiers) {
  return JSON.stringify((tiers || []).map(({ text, look, tierIdx, color }) => [
    tierIdx,
    text,
    look?.font,
    look?.size_pct,
    look?.bold,
    look?.italic,
    look?.upper,
    look?.skew,
    color,
  ]));
}

function getOverlayGeometry(ctx, overlay, tiers, baseFontSize, maxW, normY, motion) {
  const layoutRef = overlay.layout || null;
  const signature = overlayGeometrySignature(tiers);
  const cached = OVERLAY_GEOMETRY_CACHE.get(overlay);
  if (
    cached
    && cached.layoutRef === layoutRef
    && cached.baseFontSize === baseFontSize
    && cached.maxW === maxW
    && cached.normY === normY
    && cached.accent === motion.accent
    && cached.signature === signature
  ) {
    return cached.geometry;
  }

  ctx.save();
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';

  const masterScale = ((resolveLook(overlay.look, null).size_pct ?? 100) / 100);
  const wrapped = [];
  for (const tier of tiers) {
    const tierFs = Math.max(10, Math.round(((baseFontSize * (tier.look.size_pct ?? 100)) / 100) * masterScale));
    ctx.font = overlayFont(tier.look, tierFs);
    for (const line of wrapCanvasText(tier.text, ctx, maxW)) {
      wrapped.push({ line, fontSize: tierFs, look: tier.look, color: tier.color, tierIdx: tier.tierIdx });
    }
  }

  const comfortable = overlay.comfortable_lines;
  const shrink = comfortable ? Math.max(0.7, Math.min(1, comfortable / wrapped.length)) : 1;
  const lineGap = 1.0;
  let blockH = 0;
  for (let i = 0; i < wrapped.length; i++) {
    const w = wrapped[i];
    w.lineIndex = i;
    w.settledFs = Math.max(10, Math.round(w.fontSize * shrink));
    blockH += w.settledFs * lineGap;
    const isLastModelLine = w.tierIdx === 1
      && (i + 1 >= wrapped.length || wrapped[i + 1].tierIdx !== 1);
    w.accentReserve = isLastModelLine && motion.accent !== 'none'
      ? w.settledFs * (motion.accent === 'badge' ? 0.08 : 0.22)
      : 0;
    blockH += w.accentReserve;
  }

  const blockTop = overlay.anchor === ANCHOR_TOP
    ? CANVAS_H * normY
    : CANVAS_H * normY - blockH / 2;

  let cursor = blockTop;
  let maxLineW = 0;
  const tierBoxes = new Map();
  for (const w of wrapped) {
    w.y = cursor;
    ctx.font = overlayFont(w.look, w.settledFs);
    w.width = ctx.measureText(w.line).width;
    maxLineW = Math.max(maxLineW, w.width);
    const box = tierBoxes.get(w.tierIdx);
    if (!box) {
      tierBoxes.set(w.tierIdx, {
        tierIdx: w.tierIdx,
        look: w.look,
        top: w.y,
        bottom: w.y + w.settledFs,
        width: w.width,
        fs: w.settledFs,
      });
    } else {
      box.bottom = w.y + w.settledFs;
      box.width = Math.max(box.width, w.width);
    }
    cursor += w.settledFs * lineGap + w.accentReserve;
  }

  const geometry = {
    wrapped,
    blockH,
    blockTop,
    maxLineW,
    tierBoxes,
    modelLine: wrapped.find((w) => w.tierIdx === 1),
  };
  ctx.restore();
  OVERLAY_GEOMETRY_CACHE.set(overlay, {
    layoutRef,
    baseFontSize,
    maxW,
    normY,
    accent: motion.accent,
    signature,
    geometry,
  });
  return geometry;
}

// The heaviest weight index.html actually loads for each face. The ASS side
// sets Bold=1 and libass emboldens whatever it finds, so the closest match is
// the heaviest real weight -- asking for 900 from a face that only ships 400
// gets a synthesised bold that is heavier than the render's.
/**
 * Every piece of text burned into the frame, drawn by one function.
 *
 * The banner and the text overlays used to be two of these, each with its own
 * font resolution, its own outline rule, its own line spacing and its own idea
 * of what a background pill was -- and only the banner could set an outline
 * colour at all, which is why a text overlay always looked the cheaper of the
 * two. An overlay is a stack of tiers now; a banner has three, a text overlay
 * has one, and everything below this line runs for both.
 *
 * Mirrors overlay_events() in scripts/subtitle/overlay_events.py. Draw order inside one
 * overlay is scrim, then pills, then the accent shape, then the glyphs --
 * shapes behind text, which is what the ASS Layer numbers encode
 * (parity rule 2.11).
 */
function overlayFont(look, px) {
  const weight = look?.bold ? 'bold' : fontWeight(look?.font);
  const style = look?.italic ? 'italic ' : '';
  return `${style}${weight} ${px}px '${look?.font}', sans-serif`;
}

function overlayIsLive(overlay, t) {
  return !!overlay && !overlay.hidden && t >= overlay.start && t < overlay.end;
}

/**
 * The dark wash an overlay can lay behind itself, mirroring video_editor.py's
 * geq gradient. It is a separate pass because the render burns it AFTER the
 * sticker badge and BEFORE the subtitles (video_editor.py: sticker overlay,
 * then grad_alpha overlay, then the subtitles filter). The preview used to
 * paint it first of all, so the badge stayed bright in the editor and came
 * back dimmed in the file.
 */
function drawOverlayScrims(ctx, overlays = [], t, predicate = () => true) {
  for (const overlay of overlays) {
    if (!predicate(overlay) || !overlayIsLive(overlay, t) || !overlay.scrim) continue;
    const duration = Math.max(0.001, overlay.end - overlay.start);
    const tRel = t - overlay.start;
    const exitStartSec = Math.max(0.12, duration - 0.15);
    const motion = { ...HOOK_ANIM, ...(overlay.anim || {}) };
    const outFn = OVERLAY_OUT_TRANSFORMS[motion.out] || OVERLAY_OUT_TRANSFORMS.fade;
    const explicitMotion = sampleExplicitOverlayMotion(overlay, tRel, duration);
    const alpha = explicitMotion?.phase === 'out'
      ? explicitMotion.fx.alpha
      : (tRel >= exitStartSec
        ? ((outFn(tRel, exitStartSec, duration) || {}).alpha ?? 1)
        : 1);
    const gradH = Math.round(CANVAS_H * 0.25);
    const grad = ctx.createLinearGradient(0, 0, 0, gradH);
    grad.addColorStop(0, `rgba(0,0,0,${0.75 * alpha})`);
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.save();
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, CANVAS_W, gradH);
    ctx.restore();
  }
}

/**
 * Burned-in on every export regardless of the project's overlay list -- see
 * scripts/subtitle_engine.py's unconditional Watermark Dialogue event. Drawn
 * separately from drawOverlays() (which returns early on an empty list) so
 * it still shows with zero overlays, same as the render.
 */
function drawWatermark(ctx) {
  const x = CANVAS_W * WATERMARK_X_RATIO;
  const y = CANVAS_H * WATERMARK_Y_RATIO;
  const fontSize = Math.max(7, Math.round(CANVAS_W * WATERMARK_FS_RATIO));
  ctx.save();
  ctx.translate(x, y);
  // \frz-90 in the ASS render reads top-to-bottom. Canvas rotate() turns
  // clockwise for a positive angle (y-down screen space), which carries
  // local +x (the text's normal left-to-right direction) to point screen-
  // down -- the same top-to-bottom reading -- so this is +90 deg, not -90.
  ctx.rotate(Math.PI / 2);
  ctx.font = `600 ${fontSize}px 'IBM Plex Sans Thai', sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineWidth = Math.max(1.5, fontSize * 0.1);
  ctx.globalAlpha = WATERMARK_ALPHA;
  ctx.strokeStyle = '#FFFFFF';
  ctx.fillStyle = WATERMARK_COLOR;
  ctx.strokeText(WATERMARK_TEXT, 0, 0);
  ctx.fillText(WATERMARK_TEXT, 0, 0);
  ctx.restore();
}

function drawOverlays(ctx, overlays = [], t, accentColor = '#FFE600', outBounds = null, predicate = () => true) {
  if (!overlays || !overlays.length) return;
  // Painted in ASS Layer order, which is the z-order the render burns: the
  // banner (2) under the text overlays (4).
  const live = overlays.filter((o) => predicate(o) && overlayIsLive(o, t));
  live.sort((a, b) => (a.layer ?? 0) - (b.layer ?? 0));
  for (const overlay of live) drawOneOverlay(ctx, overlay, t, accentColor, outBounds);
}

function drawOneOverlay(ctx, overlay, t, accentColor, outBounds) {
  const renderProfile = overlayRenderProfile(overlay);
  const repairThaiMarks = overlay.role === 'product_callout';
  const motion = { ...renderProfile.defaultAnim, ...(overlay.anim || {}) };
  const duration = Math.max(0.001, overlay.end - overlay.start);
  // Every animation clock is relative to the overlay's own start. The banner
  // used to assume it began at 0 because it always did; it can be dragged now.
  const tRel = t - overlay.start;

  const tiers = (overlay.tiers || [])
    .map((tier, tierIdx) => {
      const look = resolveLook(overlay.look, tier.look);
      const raw = String(tier.text || '').trim();
      const color = look.color === ACCENT_COLOR ? accentColor : look.color;
      return { text: look.upper ? raw.toUpperCase() : raw, look, color, tierIdx };
    })
    .filter((tier) => tier.text);
  if (!tiers.length) return;

  const baseFontSize = Math.round(CANVAS_W * (overlay.base_fs_ratio || TEXT_FS_RATIO));
  const maxW = CANVAS_W * 0.85;
  const normX = typeof overlay.x === 'number' ? Math.max(0.05, Math.min(0.95, overlay.x)) : 0.5;
  const normY = typeof overlay.y === 'number'
    ? Math.max(0.05, Math.min(0.95, overlay.y))
    : (TEXT_POSITIONS[overlay.position || 'middle'] ?? 0.5);
  const x = CANVAS_W * normX;

  const wordStaggerSec = (motion.word_stagger_ms || 0) / 1000;
  const isWordStagger = renderProfile.supportsWordStagger && wordStaggerSec > 0;

  if (renderProfile.clearLayout && overlay.layout) {
    delete overlay.layout;
  }

  if (isWordStagger && !overlay.layout) {
    const primaryText = tiers.map(t => t.text).join('\n');
    const primaryLook = tiers[0]?.look || {};
    const primaryFsPx = Math.round((baseFontSize * (primaryLook.size_pct || 100)) / 100 * 2);
    const layoutParams = {
      text: primaryText,
      fontName: primaryLook.font,
      fontSizePx: primaryFsPx,
      normX,
      normY,
    };
    const cached = getCachedOverlayLayout(layoutParams);
    if (cached) {
      overlay.layout = cached;
    } else {
      requestOverlayLayout(layoutParams, (res) => {
        overlay.layout = res;
      });
    }
  }

  const geometry = getOverlayGeometry(ctx, overlay, tiers, baseFontSize, maxW, normY, motion);
  const { wrapped, blockH, blockTop, maxLineW, tierBoxes, modelLine } = geometry;
  if (!wrapped.length) return;

  ctx.save();
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';

  const inPreset = OVERLAY_IN_TRANSFORMS[motion.in] || OVERLAY_IN_TRANSFORMS.none;
  const loopFn = OVERLAY_LOOP_TRANSFORMS[motion.loop] || OVERLAY_LOOP_TRANSFORMS.none;
  const outFn = OVERLAY_OUT_TRANSFORMS[motion.out] || OVERLAY_OUT_TRANSFORMS.fade;
  const explicitMotion = sampleExplicitOverlayMotion(overlay, tRel, duration);

  const revealMode = motion.reveal || 'simultaneous';
  const isCumulative = revealMode === 'cumulative' || revealMode === 'tier_step';
  const stepDelaySec = (motion.step_delay_ms || DEFAULT_HOOK_STEP_DELAY_MS) / 1000;
  const staggerStepSec = hookStaggerStepSec(motion);

  // The loop phase cannot start until every tier's own entry has settled.
  let maxEntryEndSec = 0;
  if (wordStaggerSec > 0 && overlay.layout?.lines) {
    let totalWords = 0;
    for (const line of overlay.layout.lines) {
      if (line.words) totalWords += line.words.length;
    }
    if (totalWords > 0) {
      maxEntryEndSec = (totalWords - 1) * wordStaggerSec + inPreset.durSec;
    }
  }
  for (const { tierIdx } of wrapped) {
    const t0 = isCumulative ? tierIdx * stepDelaySec : (motion.stagger ? tierIdx * staggerStepSec : 0);
    maxEntryEndSec = Math.max(maxEntryEndSec, t0 + inPreset.durSec);
  }
  const explicitEntryEndSec = explicitMotion?.phaseTiming?.in
    ? explicitMotion.phaseTiming.in.end * duration
    : null;
  const exitStartSec = explicitMotion?.phaseTiming?.out
    ? explicitMotion.phaseTiming.out.start * duration
    : Math.max(0.12, duration - 0.15);
  if (explicitEntryEndSec != null) maxEntryEndSec = explicitEntryEndSec;
  const legacyLoopFx = loopFn(tRel, maxEntryEndSec, exitStartSec) || {};
  const legacyOutFx = tRel >= exitStartSec ? (outFn(tRel, exitStartSec, duration) || {}) : {};
  const loopFx = explicitMotion?.phase === 'loop' ? explicitMotion.fx : legacyLoopFx;
  const outFx = explicitMotion?.phase === 'out' ? explicitMotion.fx : legacyOutFx;

  if (outBounds) {
    const padX = Math.round(maxLineW * 0.04) + 8;
    outBounds.push({
      type: renderProfile.boundsType,
      id: overlay.id,
      x: x - maxLineW / 2 - padX,
      y: blockTop - 6,
      w: maxLineW + padX * 2,
      h: blockH + 12,
      normX,
      normY,
      sizePct: resolveLook(overlay.look, null).size_pct,
      label: String((overlay.tiers[0] || {}).text || '').slice(0, 15),
      item: overlay,
    });
  }

  // The scrim is drawn by drawOverlayScrims, in its own earlier pass -- the
  // render burns it before the subtitles but after the sticker badge.

  // Pills, behind everything the tier draws.
  for (const box of tierBoxes.values()) {
    const pill = box.look.pill;
    if (!pill) continue;
    const boxT0 = isCumulative ? box.tierIdx * stepDelaySec : (motion.stagger ? box.tierIdx * staggerStepSec : 0);
    if (isCumulative && tRel < boxT0) continue;
    const padX = Math.round(box.fs * (pill.pad_x_em ?? PILL_PAD_X_EM));
    const padY = Math.round(box.fs * (pill.pad_y_em ?? PILL_PAD_Y_EM));
    const pw = box.width + padX * 2;
    const ph = (box.bottom - box.top) + padY * 2;
    ctx.save();
    ctx.globalAlpha = (outFx.alpha ?? 1) * (loopFx.alpha ?? 1);
    ctx.shadowColor = 'transparent';
    ctx.fillStyle = pill.fill;
    ctx.beginPath();
    const radius = Math.min(ph / 2, PILL_RADIUS_MAX_PX * CANVAS_SCALE);
    if (ctx.roundRect) ctx.roundRect(x - pw / 2, box.top - padY, pw, ph, radius);
    else ctx.rect(x - pw / 2, box.top - padY, pw, ph);
    ctx.fill();
    if (pill.border) {
      ctx.strokeStyle = pill.border;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
    ctx.restore();
  }

  // Accent shape under / behind the model tier. Follows the entry and exit
  // envelope but not the loop -- matching the backend, which never threads
  // loop keyframes into the accent events.
  if (motion.accent !== 'none' && modelLine) {
    const revealStart = isCumulative ? 1 * stepDelaySec : (motion.stagger ? staggerStepSec * 2 : 0);
    const revealFrac = tRel <= revealStart ? 0 : Math.min(1, (tRel - revealStart) / 0.3);
    const modelFontSize = modelLine.settledFs;
    const accentColor = overlay.look?.accent_color || modelLine.look?.accent_color || modelLine.color;
    ctx.save();
    ctx.shadowColor = 'transparent';
    ctx.globalAlpha = (outFx.alpha ?? 1);
    ctx.fillStyle = accentColor;
    if (motion.accent === 'badge') {
      const padX = Math.round(modelFontSize * 0.38);
      const padY = Math.round(modelFontSize * 0.2);
      const fullBw = (modelLine.width / 2 + padX) * 2;
      const bw = fullBw * revealFrac;
      // ASS \alpha is TRANSPARENCY, so &HB0& means 0.31 opacity, not 0.69.
      ctx.globalAlpha *= 1 - 0xB0 / 255;
      // Anchor left edge at x - fullBw / 2 matching \an7 anchor in ASS
      const bx = x - fullBw / 2;
      const by = modelLine.y - padY;
      const bh = modelFontSize + padY * 2;
      const radius = Math.min(Math.round(padY * 0.9), 16, Math.max(0, bw / 2), bh / 2);
      if (ctx.roundRect && radius > 0 && bw > 0) {
        ctx.beginPath();
        ctx.roundRect(bx, by, bw, bh, radius);
        ctx.fill();
      } else {
        ctx.fillRect(x - fullBw / 2, modelLine.y - padY, bw, modelFontSize + padY * 2);
      }
    } else if (motion.accent === 'bracket') {
      const padX = Math.round(modelFontSize * 0.25);
      const padY = Math.round(modelFontSize * 0.08);
      const bracketW = Math.max(6, Math.round(modelFontSize * 0.16));
      const thickness = Math.max(3, Math.round(modelFontSize * 0.08));
      const h = modelFontSize + padY * 2;
      const topY = modelLine.y - padY;
      const leftX = x - modelLine.width / 2 - padX;
      const rightX = x + modelLine.width / 2 + padX - bracketW;
      ctx.globalAlpha *= revealFrac;
      // Left bracket: [
      ctx.fillRect(leftX, topY, bracketW, thickness);
      ctx.fillRect(leftX, topY, thickness, h);
      ctx.fillRect(leftX, topY + h - thickness, bracketW, thickness);
      // Right bracket: ]
      ctx.fillRect(rightX, topY, bracketW, thickness);
      ctx.fillRect(rightX + bracketW - thickness, topY, thickness, h);
      ctx.fillRect(rightX, topY + h - thickness, bracketW, thickness);
    } else if (motion.accent === 'glow_box') {
      const padX = Math.round(modelFontSize * 0.30);
      const padY = Math.round(modelFontSize * 0.12);
      const bw = (modelLine.width / 2 + padX) * 2;
      const bh = modelFontSize + padY * 2;
      const thickness = Math.max(3, Math.round(modelFontSize * 0.07));
      const boxX = x - bw / 2;
      const boxY = modelLine.y - padY;
      ctx.globalAlpha *= revealFrac;
      ctx.save();
      ctx.strokeStyle = accentColor;
      ctx.lineWidth = thickness;
      ctx.shadowColor = accentColor;
      ctx.shadowBlur = 6;
      ctx.strokeRect(boxX + thickness / 2, boxY + thickness / 2, bw - thickness, bh - thickness);
      ctx.restore();
    } else if (motion.accent === 'double_bar') {
      const gap = Math.round(modelFontSize * 0.12);
      const thickness = Math.max(3, Math.round(modelFontSize * 0.08));
      const w = modelLine.width * revealFrac;
      const barX = x - modelLine.width / 2;
      const topBarY = modelLine.y - gap - thickness;
      const botBarY = modelLine.y + modelFontSize + gap;
      ctx.fillRect(barX, topBarY, w, thickness);
      ctx.fillRect(barX, botBarY, w, thickness);
    } else if (motion.accent === 'sale_tag') {
      const padX = Math.round(modelFontSize * 0.36);
      const padY = Math.round(modelFontSize * 0.12);
      const bw = (modelLine.width / 2 + padX) * 2;
      const bh = modelFontSize + padY * 2;
      const notch = Math.round(bh * 0.40);
      const tagX = x - bw / 2;
      const tagY = modelLine.y - padY;
      const tagOpacity = 1 - 0xB8 / 255;
      ctx.globalAlpha *= revealFrac * tagOpacity;
      ctx.beginPath();
      ctx.moveTo(tagX, tagY + bh / 2);
      ctx.lineTo(tagX + notch, tagY);
      ctx.lineTo(tagX + bw, tagY);
      ctx.lineTo(tagX + bw, tagY + bh);
      ctx.lineTo(tagX + notch, tagY + bh);
      ctx.closePath();
      ctx.fill();
    } else if (motion.accent === 'pill_badge') {
      const padX = Math.round(modelFontSize * 0.35);
      const padY = Math.round(modelFontSize * 0.14);
      const bw = (modelLine.width / 2 + padX) * 2;
      const bh = modelFontSize + padY * 2;
      const r = bh / 2;
      const thickness = Math.max(3, Math.round(modelFontSize * 0.07));
      const boxX = x - bw / 2;
      const boxY = modelLine.y - padY;
      ctx.globalAlpha *= revealFrac;
      ctx.strokeStyle = accentColor;
      ctx.lineWidth = thickness;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(boxX + thickness / 2, boxY + thickness / 2, bw - thickness, bh - thickness, r);
      else ctx.rect(boxX + thickness / 2, boxY + thickness / 2, bw - thickness, bh - thickness);
      ctx.stroke();
    } else if (motion.accent === 'marker') {
      const padX = Math.round(modelFontSize * 0.22);
      const fullBw = (modelLine.width / 2 + padX) * 2;
      const bw = fullBw * revealFrac;
      const bh = Math.round(modelFontSize * 0.46);
      const markerY = modelLine.y + Math.round(modelFontSize * 0.42);
      const r = Math.min(6, bh / 3);
      const markerOpacity = 1 - 0xA0 / 255;
      ctx.globalAlpha *= markerOpacity;
      const mx = x - fullBw / 2;
      ctx.beginPath();
      if (ctx.roundRect && r > 0 && bw > 0) ctx.roundRect(mx, markerY, bw, bh, r);
      else ctx.fillRect(mx, markerY, bw, bh);
      ctx.fill();
    } else if (motion.accent === 'bold_quotes') {
      const padX = Math.round(modelFontSize * 0.28);
      const quoteFs = Math.round(modelFontSize * 1.15);
      const leftX = x - modelLine.width / 2 - padX;
      const rightX = x + modelLine.width / 2 + Math.round(padX * 0.3);
      ctx.globalAlpha *= revealFrac;
      ctx.font = `900 ${quoteFs}px sans-serif`;
      ctx.fillText('“', leftX, modelLine.y + quoteFs * 0.7);
      ctx.fillText('”', rightX, modelLine.y + quoteFs * 0.7);
    } else if (motion.accent === 'dashed_box') {
      const padX = Math.round(modelFontSize * 0.28);
      const padY = Math.round(modelFontSize * 0.10);
      const bw = (modelLine.width / 2 + padX) * 2;
      const bh = modelFontSize + padY * 2;
      const clen = Math.max(8, Math.round(modelFontSize * 0.22));
      const thickness = Math.max(3, Math.round(modelFontSize * 0.07));
      const boxX = x - bw / 2;
      const boxY = modelLine.y - padY;
      ctx.globalAlpha *= revealFrac;
      // 4 focus corners: top-left, top-right, bottom-left, bottom-right
      ctx.fillRect(boxX, boxY, clen, thickness);
      ctx.fillRect(boxX, boxY, thickness, clen);
      ctx.fillRect(boxX + bw - clen, boxY, clen, thickness);
      ctx.fillRect(boxX + bw - thickness, boxY, thickness, clen);
      ctx.fillRect(boxX, boxY + bh - clen, thickness, clen);
      ctx.fillRect(boxX, boxY + bh - thickness, clen, thickness);
      ctx.fillRect(boxX + bw - clen, boxY + bh - thickness, clen, thickness);
      ctx.fillRect(boxX + bw - thickness, boxY + bh - clen, thickness, clen);
    } else if (motion.accent === 'speed_slash') {
      const padX = Math.round(modelFontSize * 0.26);
      const padY = Math.round(modelFontSize * 0.08);
      const h = modelFontSize + padY * 2;
      const sw = Math.max(4, Math.round(modelFontSize * 0.08));
      const gapS = Math.max(3, Math.round(modelFontSize * 0.06));
      const skewDx = Math.round(h * 0.28);
      const pairW = skewDx + sw * 2 + gapS;
      const leftX = x - modelLine.width / 2 - padX - pairW;
      const rightX = x + modelLine.width / 2 + padX;
      const topY = modelLine.y - padY;
      ctx.globalAlpha *= revealFrac;
      const drawPair = (startX) => {
        ctx.beginPath();
        ctx.moveTo(startX + skewDx, topY);
        ctx.lineTo(startX + skewDx + sw, topY);
        ctx.lineTo(startX + sw, topY + h);
        ctx.lineTo(startX, topY + h);
        ctx.closePath();
        ctx.fill();
        ctx.beginPath();
        ctx.moveTo(startX + skewDx + sw + gapS, topY);
        ctx.lineTo(startX + skewDx + sw * 2 + gapS, topY);
        ctx.lineTo(startX + sw * 2 + gapS, topY + h);
        ctx.lineTo(startX + sw + gapS, topY + h);
        ctx.closePath();
        ctx.fill();
      };
      drawPair(leftX);
      drawPair(rightX);
    } else if (motion.accent === 'gradient_line') {
      const gap = Math.round(modelFontSize * 0.12);
      const thickness = Math.max(2, Math.round(modelFontSize * 0.06));
      const w = modelLine.width * revealFrac;
      const barY = modelLine.y + modelFontSize + gap;
      const barX = x - modelLine.width / 2;
      const gradLineOpacity = 1 - 0x40 / 255;
      ctx.globalAlpha *= gradLineOpacity;
      ctx.fillRect(barX, barY, w, thickness);
    } else {
      const thickness = Math.max(4, Math.round(modelFontSize * 0.1));
      const gap = Math.round(modelFontSize * 0.12);
      const w = modelLine.width * revealFrac;
      const barY = modelLine.y + modelFontSize + gap;
      const barX = x - modelLine.width / 2;
      // The renderer lays a blurred copy under the crisp bar (\blur7 at
      // \alpha&H60&) for glow; without it the preview's bar reads flatter
      // than what actually renders.
      ctx.save();
      ctx.shadowColor = accentColor;
      ctx.shadowBlur = 7;
      ctx.globalAlpha *= 1 - 0x60 / 255;
      ctx.fillRect(barX, barY, w, thickness);
      ctx.restore();
      ctx.fillRect(barX, barY, w, thickness);
    }
    ctx.restore();
  }

  const sweeps = [];
  let runningWordCounter = 0;
  for (const w of wrapped) {
    // The cumulative y-cursor advanced using the SETTLED size, not the
    // currently-animating scale -- an ASS \t transform (and this mirror of it)
    // animates glyph rendering, not layout reflow, so other lines must not
    // jitter as this one animates.
    const t0 = isCumulative ? w.tierIdx * stepDelaySec : (motion.stagger ? w.tierIdx * staggerStepSec : 0);
    if (isCumulative && tRel < t0) {
      continue;
    }
    const lineInFx = explicitMotion?.phase === 'in'
      ? explicitMotion.fx
      : (inPreset.at((tRel - t0) * 1000) || {});

    const scale = (lineInFx.scale ?? 1) * (outFx.scale ?? 1);
    const dy = (lineInFx.dy ?? 0) + (outFx.dy ?? 0);
    const rot = (loopFx.rot ?? 0) + (outFx.rot ?? 0);
    const lineY = w.y + dy;

    const shadow = w.look.shadow;
    const lineIndex = wrapped.indexOf(w);
    const lineLayout = overlay.layout?.lines?.[lineIndex];
    const lineWords = lineLayout?.words;

    if (isWordStagger && lineWords && lineWords.length > 0) {
      const wordStartIdx = runningWordCounter;
      runningWordCounter += lineWords.length;

      ctx.save();
      ctx.globalAlpha = (loopFx.alpha ?? 1) * (outFx.alpha ?? 1);
      if (rot) {
        ctx.translate(x, lineY + w.settledFs / 2);
        ctx.rotate((rot * Math.PI) / 180);
        ctx.translate(-x, -(lineY + w.settledFs / 2));
      }
      ctx.font = overlayFont(w.look, w.settledFs);

      // Pass 1: Outlines (with shadow if outline exists)
      if (w.look.outline_px > 0.01) {
        ctx.strokeStyle = w.look.outline_color;
        ctx.lineWidth = w.look.outline_px;
        ctx.lineJoin = 'round';
        ctx.miterLimit = 2;
        for (let wi = 0; wi < lineWords.length; wi++) {
          const wordItem = lineWords[wi];
          const wordIdx = wordStartIdx + wi;
          const wordT0 = wordStaggerSec > 0 ? wordIdx * wordStaggerSec : 0;
          const wordTRel = tRel - wordT0;
          if (wordTRel < 0) continue;

          const wordInFx = explicitMotion?.phase === 'in'
            ? explicitMotion.fx
            : (inPreset.at(wordTRel * 1000) || {});
          const wordScale = (wordInFx.scale ?? 1) * (outFx.scale ?? 1);
          const wordDy = (wordInFx.dy ?? 0) + (outFx.dy ?? 0);
          const wordAlpha = (wordInFx.alpha ?? 1);
          if (wordAlpha <= 0.001) continue;

          const wx = wordItem.x * CANVAS_W;
          const ww = (wordItem.w || 0) * CANVAS_W;
          const wordCx = wx + ww / 2;
          const wordCy = lineY + w.settledFs / 2;
          const targetY = lineY + wordDy;

          ctx.save();
          ctx.globalAlpha *= wordAlpha;
          if (wordInFx.blur) ctx.filter = `blur(${wordInFx.blur.toFixed(1)}px)`;
          if (shadow) {
            ctx.shadowColor = shadow.color === '#000000' ? 'rgba(0, 0, 0, 0.9)' : shadow.color;
            ctx.shadowBlur = shadow.blur * CANVAS_SCALE * 2;
            ctx.shadowOffsetX = shadow.dx * CANVAS_SCALE;
            ctx.shadowOffsetY = shadow.dy * CANVAS_SCALE;
          } else {
            ctx.shadowColor = 'transparent';
          }
          const hasSkew = w.look.skew && Math.abs(w.look.skew) > 0.001;
          const hasScale = Math.abs(wordScale - 1) > 0.001;
          if (hasScale || hasSkew) {
            ctx.translate(wordCx, wordCy);
            if (hasScale) ctx.scale(wordScale, wordScale);
            if (hasSkew) ctx.transform(1, 0, w.look.skew, 1, 0, 0);
            ctx.translate(-wordCx, -wordCy);
          }
          drawProductCalloutText(
            ctx, wordItem.text, wx, targetY, w.settledFs,
            (value, px, py) => ctx.strokeText(value, px, py),
            repairThaiMarks,
          );
          ctx.restore();
        }
      }

      // Pass 2: Fills (with shadow only if no outline was drawn)
      ctx.fillStyle = w.color;
      for (let wi = 0; wi < lineWords.length; wi++) {
        const wordItem = lineWords[wi];
        const wordIdx = wordStartIdx + wi;
        const wordT0 = wordStaggerSec > 0 ? wordIdx * wordStaggerSec : 0;
        const wordTRel = tRel - wordT0;
        if (wordTRel < 0) continue;

        const wordInFx = explicitMotion?.phase === 'in'
          ? explicitMotion.fx
          : (inPreset.at(wordTRel * 1000) || {});
        const wordScale = (wordInFx.scale ?? 1) * (outFx.scale ?? 1);
        const wordDy = (wordInFx.dy ?? 0) + (outFx.dy ?? 0);
        const wordAlpha = (wordInFx.alpha ?? 1);
        if (wordAlpha <= 0.001) continue;

        const wx = wordItem.x * CANVAS_W;
        const ww = (wordItem.w || 0) * CANVAS_W;
        const wordCx = wx + ww / 2;
        const wordCy = lineY + w.settledFs / 2;
        const targetY = lineY + wordDy;

        ctx.save();
        ctx.globalAlpha *= wordAlpha;
        if (wordInFx.blur) ctx.filter = `blur(${wordInFx.blur.toFixed(1)}px)`;
        if (!w.look.outline_px || w.look.outline_px <= 0.01) {
          if (shadow) {
            ctx.shadowColor = shadow.color === '#000000' ? 'rgba(0, 0, 0, 0.9)' : shadow.color;
            ctx.shadowBlur = shadow.blur * CANVAS_SCALE * 2;
            ctx.shadowOffsetX = shadow.dx * CANVAS_SCALE;
            ctx.shadowOffsetY = shadow.dy * CANVAS_SCALE;
          } else {
            ctx.shadowColor = 'transparent';
          }
        } else {
          ctx.shadowColor = 'transparent';
        }
        const hasSkew = w.look.skew && Math.abs(w.look.skew) > 0.001;
        const hasScale = Math.abs(wordScale - 1) > 0.001;
        if (hasScale || hasSkew) {
          ctx.translate(wordCx, wordCy);
          if (hasScale) ctx.scale(wordScale, wordScale);
          if (hasSkew) ctx.transform(1, 0, w.look.skew, 1, 0, 0);
          ctx.translate(-wordCx, -wordCy);
        }
        drawProductCalloutText(
          ctx, wordItem.text, wx, targetY, w.settledFs,
          (value, px, py) => drawTextWithMonoEmoji(ctx, value, px, py),
          repairThaiMarks,
        );
        if (w.look.underline) {
          ctx.save();
          ctx.strokeStyle = w.color;
          ctx.lineWidth = Math.max(1.5, Math.round(w.settledFs * 0.07));
          const underlineY = targetY + w.settledFs * 0.95;
          ctx.beginPath();
          ctx.moveTo(wx, underlineY);
          ctx.lineTo(wx + ww, underlineY);
          ctx.stroke();
          ctx.restore();
        }
        ctx.restore();
      }
      ctx.restore();
    } else {
      const renderFs = Math.max(6, Math.round(w.settledFs * scale));
      ctx.save();
      ctx.globalAlpha = (lineInFx.alpha ?? 1) * (loopFx.alpha ?? 1) * (outFx.alpha ?? 1);
      if (lineInFx.blur) ctx.filter = `blur(${lineInFx.blur.toFixed(1)}px)`;
      if (rot) {
        // rotate about the line's own centre, matching \frz around \pos
        ctx.translate(x, lineY + w.settledFs / 2);
        ctx.rotate((rot * Math.PI) / 180);
        ctx.translate(-x, -(lineY + w.settledFs / 2));
      }
      if (w.look.skew && Math.abs(w.look.skew) > 0.001) {
        const lineCy = lineY + w.settledFs / 2;
        ctx.translate(x, lineCy);
        ctx.transform(1, 0, w.look.skew, 1, 0, 0);
        ctx.translate(-x, -lineCy);
      }
      ctx.font = overlayFont(w.look, renderFs);
      const drawnW = ctx.measureText(w.line).width;
      const lineX = x - drawnW / 2;
      if (lineInFx.reveal != null) {
        // typewriter: same left-to-right clip the ASS \clip animation performs
        ctx.beginPath();
        ctx.rect(lineX, 0, drawnW * lineInFx.reveal, CANVAS_H);
        ctx.clip();
      }

      // The shadow is a dark copy offset down-right. Its offsets are render
      // pixels in the model, and this canvas is exactly half the render's width
      // (parity rule 2.3).
      if (shadow) {
        ctx.shadowColor = shadow.color === '#000000' ? 'rgba(0, 0, 0, 0.9)' : shadow.color;
        ctx.shadowBlur = shadow.blur * CANVAS_SCALE * 2;
        ctx.shadowOffsetX = shadow.dx * CANVAS_SCALE;
        ctx.shadowOffsetY = shadow.dy * CANVAS_SCALE;
      } else {
        ctx.shadowColor = 'transparent';
      }
      if (w.look.outline_px > 0.01) {
        ctx.strokeStyle = w.look.outline_color;
        ctx.lineWidth = w.look.outline_px;
        ctx.lineJoin = 'round';
        ctx.miterLimit = 2;
        drawProductCalloutText(
          ctx, w.line, lineX, lineY, renderFs,
          (value, px, py) => ctx.strokeText(value, px, py, maxW),
          repairThaiMarks,
        );
      }
      ctx.shadowColor = 'transparent';
      ctx.fillStyle = w.color;
      drawProductCalloutText(
        ctx, w.line, lineX, lineY, renderFs,
        (value, px, py) => drawTextWithMonoEmoji(ctx, value, px, py),
        repairThaiMarks,
      );
      if (w.look.underline) {
        ctx.save();
        ctx.strokeStyle = w.color;
        ctx.lineWidth = Math.max(1.5, Math.round(renderFs * 0.07));
        const underlineY = lineY + renderFs * 0.95;
        ctx.beginPath();
        ctx.moveTo(lineX, underlineY);
        ctx.lineTo(lineX + drawnW, underlineY);
        ctx.stroke();
        ctx.restore();
      }
      ctx.restore();
    }

    if (motion.loop === 'lightsweep') {
      ctx.font = overlayFont(w.look, w.settledFs);
      const drawnW = ctx.measureText(w.line).width;
      sweeps.push({ line: w.line, y: lineY, fs: w.settledFs, look: w.look, halfW: drawnW / 2 });
    }
  }

  // Shimmer band travelling across each line, repeatedly, for the hold --
  // mirrors _hook_lightsweep_event's 500ms cycle plus its instant reset.
  if (sweeps.length && tRel >= maxEntryEndSec && tRel < exitStartSec) {
    const CYCLE = 0.501;
    const phase = ((tRel - maxEntryEndSec) % CYCLE) / 0.5;
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
        ctx.rect(bandX, 0, bandW, CANVAS_H);
        ctx.clip();
        ctx.font = overlayFont(s.look, s.fs);
        if (s.look.skew && Math.abs(s.look.skew) > 0.001) {
          const lineCy = s.y + s.fs / 2;
          ctx.translate(x, lineCy);
          ctx.transform(1, 0, s.look.skew, 1, 0, 0);
          ctx.translate(-x, -lineCy);
        }
        ctx.fillText(s.line, x - s.halfW, s.y, maxW);
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
function SequencePlayer({
  clips,
  cues = [],
  overlays = [],
  audioUrl = null,
  audioStems = null,
  grade = null,
  spotlight = undefined,
  backgroundIsolation = null,
  backgroundIsolationStatus = null,
  stylePreset = DEFAULT_STYLE_PRESET,
  trackMix = null,
  compact = false,
  onPlayhead,
  onDurations,
  captionStyle = {},
  stickerStyle = {},
  stickers = [],
  effects = [],
  effectAssets = [],
  onUpdateEffect = null,
  onSpotlightChange = null,
  onSpotlightChangeLive = null,
  onBeginDrag = null,
  onEndDrag = null,
  isMuted = false,
  selection = null,
  onSelect = null,
  onUpdateOverlay = null,
  onDeleteOverlay = null,
  onUpdateCaption = null,
  applyToAllCaptions = true,
  onUpdateAllCaptions = null,
  onStyleChange = null,
  onUpdateSticker = null,
  isStickerHidden = false,
  previewSticker = null,
  onDismissPreviewSticker = null,
  previewTextTemplate = null,
  onCommitPreviewTextTemplate = null,
  onDismissPreviewTextTemplate = null,
  showSafeZone: externalShowSafeZone = undefined,
  onToggleSafeZone = null,
  showWatermark = true,
}, ref) {
  const visualStyle = useMemo(() => getStylePreset(stylePreset), [stylePreset]);
  const previewAccentColor = visualStyle?.accent || '#FFE600';
  const previewSpotlight = useMemo(
    () => resolveSpotlightPreview(spotlight, effects),
    [spotlight, effects],
  );
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const boundsRef = useRef([]);
  // The template card the user is hovering is drawn as a real overlay rather
  // than through a second near-copy of the drawing code, which is how the
  // ephemeral preview used to drift from what committing it produced.
  const drawnOverlays = useMemo(
    () => (previewTextTemplate ? [...overlays, previewTextTemplate] : overlays),
    [overlays, previewTextTemplate],
  );
  const { behindSubject: overlaysBehindSubject, foreground: overlaysInFront } = useMemo(
    () => splitBackgroundIsolationOverlays(drawnOverlays),
    [drawnOverlays],
  );
  const [internalShowSafeZone, setInternalShowSafeZone] = useState(false);
  const showSafeZone = externalShowSafeZone !== undefined ? externalShowSafeZone : internalShowSafeZone;
  const toggleSafeZone = useCallback(() => {
    if (onToggleSafeZone) {
      onToggleSafeZone();
    } else {
      setInternalShowSafeZone((v) => !v);
    }
  }, [onToggleSafeZone]);
  const [snapGuide, setSnapGuide] = useState({ x: null, y: null });
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
  const stickerImagesRef = useRef(new Map());
  const effectVideosRef = useRef(new Map());
  const lutRef = useRef(null);          // parsed .cube for the chosen filter
  const lutRendererRef = useRef(null);  // WebGL2 pass, or null where unavailable
  const [lutReady, setLutReady] = useState(0);

  const effectiveStickersList = useMemo(() => {
    if (Array.isArray(stickers) && stickers.length > 0) {
      return stickers;
    }
    if (stickerStyle?.badge) {
      return [{
        id: 'sticker_badge',
        badge: stickerStyle.badge,
        start: stickerStyle.startTime ?? 0,
        end: stickerStyle.endTime ?? 999999,
        scale: stickerStyle.scale ?? 1,
        normX: stickerStyle.normX ?? 0.8,
        normY: stickerStyle.normY ?? 0.15,
        position: stickerStyle.position || 'top_right',
      }];
    }
    return [];
  }, [stickers, stickerStyle]);

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
  const lastPlayheadUiUpdateRef = useRef(null);
  const prevActiveClipIdRef = useRef(null);
  const backgroundIsolationImagesRef = useRef(new Map());
  const [backgroundIsolationManifests, setBackgroundIsolationManifests] = useState({});
  const [backgroundIsolationTick, setBackgroundIsolationTick] = useState(0);

  const backgroundIsolationArtifactIds = useMemo(() => {
    const ids = new Set();
    (clips || []).map((clip) => resolveBackgroundIsolationConfig(clip, backgroundIsolation)).forEach((config) => {
      const id = backgroundArtifactId(config);
      if (id) ids.add(id);
    });
    return [...ids];
  }, [backgroundIsolation, clips]);

  useEffect(() => {
    let cancelled = false;
    if (!backgroundIsolationArtifactIds.length) {
      setBackgroundIsolationManifests({});
      return undefined;
    }
    Promise.all(backgroundIsolationArtifactIds.map(async (artifactId) => {
      try {
        const response = await api.get(`/background-isolation/sequences/${encodeURIComponent(artifactId)}/manifest`);
        return [artifactId, response.data];
      } catch {
        return [artifactId, null];
      }
    })).then((entries) => {
      if (!cancelled) setBackgroundIsolationManifests(Object.fromEntries(entries));
    });
    return () => { cancelled = true; };
  }, [backgroundIsolationArtifactIds.join('|')]);

  const loadedBackgroundIsolationFrame = useCallback(function loadBackgroundIsolationFrame(clip, sourceTime, prefetch = true) {
    // The legacy blurred-canvas path has different geometry and filter order
    // from subject isolation.  Keep Preview on the same fail-closed branch as
    // the renderer for these clips.
    if (clip?.bg_blur || clip?.fit_mode === 'blur') return null;
    const config = resolveBackgroundIsolationConfig(clip, backgroundIsolation);
    const artifactId = backgroundArtifactId(config);
    const manifest = artifactId ? backgroundIsolationManifests[artifactId] : null;
    const resolution = resolveBackgroundIsolationPreview({
      config,
      manifest,
      artifactBaseUrl: '/api/background-isolation/sequences',
      sourceTime: Math.max(0, Number(sourceTime) || 0),
    });
    if (!resolution.useArtifact || !resolution.frameUrl) return null;
    const cache = backgroundIsolationImagesRef.current;
    const cached = cache.get(resolution.frameUrl);
    if (cached) return cached.status === 'ready' ? cached.image : null;

    evictBackgroundIsolationFrameCache(cache, resolution.frameUrl);

    const entry = {
      image: new Image(),
      status: 'loading',
      objectUrl: null,
      retryCount: 0,
      retryTimer: null,
    };
    cache.set(resolution.frameUrl, entry);
    const apiPath = resolution.frameUrl.startsWith('/api/')
      ? resolution.frameUrl.slice(4)
      : resolution.frameUrl;

    const releaseObjectUrl = () => {
      if (!entry.objectUrl) return;
      URL.revokeObjectURL(entry.objectUrl);
      entry.objectUrl = null;
    };
    const markError = () => {
      if (cache.get(resolution.frameUrl) !== entry) return;
      if (entry.status === 'error') return;
      releaseObjectUrl();
      entry.status = 'error';
      const retryDelay = backgroundFrameRetryDelay(entry.retryCount);
      if (retryDelay != null) {
        entry.retryCount += 1;
        entry.retryTimer = setTimeout(() => {
          if (cache.get(resolution.frameUrl) !== entry) return;
          entry.retryTimer = null;
          entry.status = 'loading';
          setBackgroundIsolationTick((value) => value + 1);
          requestFrame();
        }, retryDelay);
      }
      setBackgroundIsolationTick((value) => value + 1);
    };
    const requestFrame = () => {
      if (cache.get(resolution.frameUrl) !== entry) return;
      api.get(apiPath, { responseType: 'blob' }).then((response) => {
        if (cache.get(resolution.frameUrl) !== entry) return;
        if (!response?.data) throw new Error('empty background isolation frame');
        entry.objectUrl = URL.createObjectURL(response.data);
        entry.image.onload = () => {
          if (cache.get(resolution.frameUrl) !== entry) return;
          entry.status = 'ready';
          entry.retryCount = 0;
          setBackgroundIsolationTick((value) => value + 1);
        };
        entry.image.onerror = markError;
        entry.image.src = entry.objectUrl;
      }).catch(markError);
    };
    requestFrame();
    if (prefetch) {
      backgroundIsolationPrefetchTimes({
        sourceTime: Math.max(0, Number(sourceTime) || 0),
        fps: resolution.fps,
        count: 4,
        sourceStart: resolution.sourceStart,
        sourceDuration: resolution.sourceDuration,
      }).slice(1).forEach((nextSourceTime) => {
        loadBackgroundIsolationFrame(clip, nextSourceTime, false);
      });
    }
    return null;
  }, [backgroundIsolation, backgroundIsolationManifests]);

  useEffect(() => () => {
    backgroundIsolationImagesRef.current.forEach((entry) => {
      if (entry?.retryTimer != null) clearTimeout(entry.retryTimer);
      if (entry?.objectUrl) URL.revokeObjectURL(entry.objectUrl);
    });
    backgroundIsolationImagesRef.current.clear();
  }, []);

  const publishPlayhead = (t, force = false, now = performance.now()) => {
    playheadRef.current = t;
    const lastUpdate = lastPlayheadUiUpdateRef.current;
    if (!force && lastUpdate != null && now - lastUpdate < PLAYHEAD_UI_INTERVAL_MS) return;
    lastPlayheadUiUpdateRef.current = now;
    setPlayhead(t);
  };

  const captionKey = `${captionStyle.hidden}:${captionStyle.captionPosition}:${captionStyle.captionColor}:${captionStyle.captionScale}:${captionStyle.captionX ?? ''}:${captionStyle.captionY ?? ''}:${captionStyle.fontName}:${visualStyle.id}`;
  const cuesKey = (cues || []).map(c => `${c._uid || c.id}:${c.start}:${c.end}:${c.text}:${c.translation}:${c.scale || 1}:${c.x ?? ''}:${c.y ?? ''}:${c.position ?? ''}`).join(';;');
  // An overlay carries a whole look per tier now, so anything short of the
  // real thing would miss a colour or an outline the user just changed.
  const overlaysKey = JSON.stringify(drawnOverlays);
  const spotlightKey = JSON.stringify(previewSpotlight);
  const stickerKey = `${stickerStyle.badge}:${stickerStyle.position}:${stickerStyle.scale}:${stickerStyle.startTime}:${stickerStyle.endTime}:${stickerStyle.normX}:${stickerStyle.normY}`;
  const stickersKey = (stickers || []).map(s => `${s.id}:${s.badge}:${s.start}:${s.end}:${s.scale}:${s.normX}:${s.normY}:${s.hidden}`).join('|');
  const clipKey = clips.map(c => `${c.id}:${c.source_path}:${c.trim_start}:${c.trim_end}:${c.transition_in}:${c.transition_duration}:${c.brightness}:${c.contrast}:${c.saturation}:${c.zoom}:${c.pan_x}:${c.pan_y}:${c.mirror}:${c.rotation}:${JSON.stringify(c.keyframes || [])}`).join('|');


  // Interactive Bounding Box calculations
  const selectedBox = useMemo(() => {
    return resolveSelectedBox({
      selection,
      bounds: boundsRef.current,
      cues,
      captionStyle,
      overlays,
      effectiveStickersList,
      stickerStyle,
      isStickerHidden,
      effects,
      stickerImages: stickerImagesRef.current,
      canvasWidth: CANVAS_W,
      canvasHeight: CANVAS_H,
      captionY: CAPTION_Y,
      textPositions: TEXT_POSITIONS,
      resolveLook,
      anchorTop: ANCHOR_TOP,
    });
  }, [selection, overlays, cues, playhead, effectiveStickersList, stickerStyle, isStickerHidden, effects]);

  const handleBoxDragStart = (e) => {
    e.stopPropagation();
    e.preventDefault();
    if (!selectedBox || !containerRef.current) return;
    const startMouseX = e.clientX;
    const startMouseY = e.clientY;
    const rect = containerRef.current.getBoundingClientRect();
    const initialNormX = selectedBox.normX;
    const initialNormY = selectedBox.normY;

    const onPointerMove = (moveEvt) => {
      const deltaPxX = moveEvt.clientX - startMouseX;
      const deltaPxY = moveEvt.clientY - startMouseY;
      const snappedPoint = snapNormalizedPoint(
        initialNormX + deltaPxX / rect.width,
        initialNormY + deltaPxY / rect.height,
      );
      setSnapGuide({ x: snappedPoint.snapX, y: snappedPoint.snapY });

      const { x: roundedX, y: roundedY } = roundNormalizedPoint(snappedPoint.x, snappedPoint.y);
      const positionPatch = positionPatchForBox(selectedBox.type, roundedX, roundedY);

      if (selectedBox.type === 'text_overlay' || selectedBox.type === 'hook') {
        onUpdateOverlay?.(selectedBox.id, positionPatch);
      } else if (selectedBox.type === 'sticker') {
        onUpdateSticker?.(selectedBox.id, positionPatch);
      } else if (selectedBox.type === 'effect') {
        onUpdateEffect?.(selectedBox.id, positionPatch);
      } else if (selectedBox.type === 'caption') {
        if (applyToAllCaptions && onUpdateAllCaptions) {
          onUpdateAllCaptions(positionPatch, true);
          onStyleChange?.({ captionX: roundedX, captionY: roundedY });
        } else {
          onUpdateCaption?.(selectedBox.id, positionPatch, true);
        }
      }
    };

    const onPointerUp = (upEvt) => {
      cleanupPointerLifecycle();
      setSnapGuide({ x: null, y: null });

      if (selectedBox.type === 'caption' && upEvt) {
        const deltaPxX = upEvt.clientX - startMouseX;
        const deltaPxY = upEvt.clientY - startMouseY;
        const finalPoint = snapNormalizedPoint(
          initialNormX + deltaPxX / rect.width,
          initialNormY + deltaPxY / rect.height,
          { yGuides: [0.5] },
        );
        const { x: roundedX, y: roundedY } = roundNormalizedPoint(finalPoint.x, finalPoint.y);
        if (applyToAllCaptions && onUpdateAllCaptions) {
          onUpdateAllCaptions({ x: roundedX, y: roundedY }, false);
          onStyleChange?.({ captionX: roundedX, captionY: roundedY });
        } else {
          onUpdateCaption?.(selectedBox.id, {
            x: roundedX,
            y: roundedY,
          }, false);
        }
      }
    };

    const cleanupPointerLifecycle = bindWindowPointerLifecycle(onPointerMove, onPointerUp);
  };

  const handleResizeStart = (e, corner) => {
    e.stopPropagation();
    e.preventDefault();
    if (!selectedBox || !containerRef.current) return;
    const startMouseX = e.clientX;
    const startMouseY = e.clientY;
    // Captions still carry a bare multiplier; an overlay's size is a percent
    // on its look, which is the number its tier editor shows.
    const initialScale = selectedBox.sizePct != null
      ? selectedBox.sizePct / 100
      : (selectedBox.scale || 1.0);
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width * selectedBox.normX;
    const centerY = rect.top + rect.height * selectedBox.normY;
    const dx = startMouseX - centerX;
    const dy = startMouseY - centerY;
    const initialDist = Math.hypot(dx, dy);
    if (initialDist < 10) return;
    const dirX = dx / initialDist;
    const dirY = dy / initialDist;

    const onPointerMove = (moveEvt) => {
      const deltaX = moveEvt.clientX - startMouseX;
      const deltaY = moveEvt.clientY - startMouseY;
      const projectedDelta = deltaX * dirX + deltaY * dirY;
      const newScale = projectOverlayScale(initialScale, projectedDelta, initialDist, selectedBox.type);
      const scalePatch = scalePatchForBox(selectedBox.type, newScale, selectedBox.item?.look);

      if (selectedBox.type === 'text_overlay' || selectedBox.type === 'hook') {
        onUpdateOverlay?.(selectedBox.id, scalePatch);
      } else if (selectedBox.type === 'sticker') {
        onUpdateSticker?.(selectedBox.id, scalePatch);
      } else if (selectedBox.type === 'effect') {
        onUpdateEffect?.(selectedBox.id, scalePatch);
      } else if (selectedBox.type === 'caption') {
        if (applyToAllCaptions && onUpdateAllCaptions) {
          onUpdateAllCaptions(scalePatch, true);
          onStyleChange?.({ captionScale: newScale });
        } else {
          onUpdateCaption?.(selectedBox.id, scalePatch, true);
        }
      }
    };

    const onPointerUp = (upEvt) => {
      cleanupPointerLifecycle();

      if (selectedBox.type === 'caption' && upEvt) {
        const deltaX = upEvt.clientX - startMouseX;
        const deltaY = upEvt.clientY - startMouseY;
        const projectedDelta = deltaX * dirX + deltaY * dirY;
        const newScale = projectOverlayScale(initialScale, projectedDelta, initialDist, selectedBox.type);
        if (applyToAllCaptions && onUpdateAllCaptions) {
          onUpdateAllCaptions({ scale: newScale }, false);
          onStyleChange?.({ captionScale: newScale });
        } else {
          onUpdateCaption?.(selectedBox.id, { scale: newScale }, false);
        }
      }
    };

    const cleanupPointerLifecycle = bindWindowPointerLifecycle(onPointerMove, onPointerUp);
  };

  const handleSpotlightKeyDown = (e) => {
    if (!previewSpotlight || !onSpotlightChange) return;
    const step = e.shiftKey ? 0.05 : 0.01;
    const delta = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    }[e.key];
    if (!delta) return;
    e.preventDefault();
    e.stopPropagation();
    const { focus } = previewSpotlight;
    const x = clampSpotlight(focus.x + delta[0], focus.width / 2, 1 - focus.width / 2);
    const y = clampSpotlight(focus.y + delta[1], focus.height / 2, 1 - focus.height / 2);
    onSpotlightChange({ focus: { x: roundSpotlight(x), y: roundSpotlight(y) } });
  };

  const handleSpotlightDragStart = (e) => {
    e.stopPropagation();
    e.preventDefault();
    if (!previewSpotlight || !containerRef.current || !onSpotlightChangeLive) return;
    const startMouseX = e.clientX;
    const startMouseY = e.clientY;
    const rect = containerRef.current.getBoundingClientRect();
    const { focus } = previewSpotlight;
    onBeginDrag?.();

    const updateFocus = (clientX, clientY) => {
      const x = clampSpotlight(
        focus.x + (clientX - startMouseX) / rect.width,
        focus.width / 2,
        1 - focus.width / 2,
      );
      const y = clampSpotlight(
        focus.y + (clientY - startMouseY) / rect.height,
        focus.height / 2,
        1 - focus.height / 2,
      );
      onSpotlightChangeLive({
        focus: { x: roundSpotlight(x), y: roundSpotlight(y) },
      });
    };

    const onPointerMove = (moveEvt) => updateFocus(moveEvt.clientX, moveEvt.clientY);
    const onPointerUp = (upEvt) => {
      if (upEvt) updateFocus(upEvt.clientX, upEvt.clientY);
      cleanupPointerLifecycle();
      onEndDrag?.();
    };
    const cleanupPointerLifecycle = bindWindowPointerLifecycle(onPointerMove, onPointerUp);
  };

  const handleContainerClick = (e) => {
    if (e.target.closest('.interactive-bounding-box')) return;
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const clickX = ((e.clientX - rect.left) / rect.width) * CANVAS_W;
    const clickY = ((e.clientY - rect.top) / rect.height) * CANVAS_H;

    const hit = boundsRef.current.find(
      (b) => clickX >= b.x && clickX <= b.x + b.w && clickY >= b.y && clickY <= b.y + b.h
    );

    if (hit) {
      if (hit.type === 'template_preview' || hit.type === 'sticker_preview') {
        // Clicking the preview box itself can be handled by the preview UI overlay
        return;
      }
      if (hit.type === 'sticker' && isStickerHidden) {
        return;
      }
      onSelect?.({ type: hit.type, id: hit.id });
    } else {
      if (previewTextTemplate) {
        onDismissPreviewTextTemplate?.();
      }
      if (previewSticker) {
        onDismissPreviewSticker?.();
      }
      if (selection) {
        onSelect?.(null);
      } else {
        togglePlay();
      }
    }
  };

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
    const catalog = stickerStyle?.stickers || [];
    if (!catalog.length && !effectiveStickersList.length && !stickerStyle?.badge) {
      stickerImgRef.current = null;
      stickerImagesRef.current.clear();
      renderAt(playheadRef.current);
      return;
    }

    if (stickerStyle?.badge) {
      const found = catalog.find((s) => 
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
      }
    }

    effectiveStickersList.forEach((stk) => {
      const bKey = stk.badge;
      if (!bKey) return;
      if (stickerImagesRef.current.has(bKey)) return;

      const found = catalog.find((s) =>
        s.name === bKey ||
        s.id === bKey ||
        s.path === bKey ||
        (s.name && s.name.toLowerCase() === String(bKey).toLowerCase())
      );
      if (found?.img_url) {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.src = found.img_url;
        img.onload = () => {
          stickerImagesRef.current.set(bKey, img);
          stickerImagesRef.current.set(bKey.toLowerCase(), img);
          renderAt(playheadRef.current);
        };
      }
    });

    if (previewSticker && !stickerImagesRef.current.has(previewSticker)) {
      const bKey = previewSticker;
      const found = catalog.find((s) =>
        s.name === bKey ||
        s.id === bKey ||
        s.path === bKey ||
        (s.name && s.name.toLowerCase() === String(bKey).toLowerCase())
      );
      if (found?.img_url) {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.src = found.img_url;
        img.onload = () => {
          stickerImagesRef.current.set(bKey, img);
          stickerImagesRef.current.set(bKey.toLowerCase(), img);
          renderAt(playheadRef.current);
        };
      }
    }

    renderAt(playheadRef.current);
  }, [stickerStyle.badge, stickerStyle.stickers, effectiveStickersList, previewSticker]);

  useEffect(() => {
    renderAt(playheadRef.current);
  }, [isStickerHidden, previewSticker]);

  // Video overlay effects -- one hidden, autoplay-looping <video> element per
  // unique effectId in use, drawn from in drawEffects() above. A newly-added
  // or newly-loaded element doesn't get picked up by anything else while
  // paused (unlike the main clip <video>s, which have onLoadedData/onSeeked
  // handlers -- see below), so both cases need an explicit renderAt() here,
  // mirroring the sticker <img> preload's onload -> renderAt() pattern.
  useEffect(() => {
    const wantedIds = new Set((effects || []).filter((fx) => fx && !fx.hidden && fx.effectId).map((fx) => fx.effectId));
    const map = effectVideosRef.current;
    let changed = false;

    for (const [id, el] of map.entries()) {
      if (!wantedIds.has(id)) {
        el.pause();
        el.removeAttribute('src');
        el.load();
        map.delete(id);
        changed = true;
      }
    }

    wantedIds.forEach((id) => {
      if (map.has(id)) return;
      const asset = (effectAssets || []).find((a) => a.id === id);
      const src = asset?.video_url || `/api/media/02_Assets/Effects/${id}.webm`;
      const el = document.createElement('video');
      el.crossOrigin = 'anonymous';
      el.muted = true;
      el.loop = true;
      el.playsInline = true;
      el.addEventListener('loadeddata', () => {
        if (!isPlaying) renderAt(playheadRef.current);
      });
      el.src = src;
      el.play().catch(() => {});
      map.set(id, el);
      changed = true;
    });

    if (changed && !isPlaying) renderAt(playheadRef.current);
  }, [effects, effectAssets]);

  // Load real duration for every clip up front -- segment timing needs it
  // (a clip with trim_end === null trims to "the source's own end").
  useEffect(() => {
    if (!clips || clips.length === 0) {
      setMetadataReady(false);
      setIsPlaying(false);
      publishPlayhead(0, true);
      setDurations({});
      return undefined;
    }

    setMetadataReady(false);
    setIsPlaying(false);
    let cancelled = false;

    const collectDurations = () => {
      const d = {};
      clips.forEach((c) => {
        const measured = videoElsRef.current[c.id]?.duration;
        d[c.id] = (Number.isFinite(measured) && measured > 0)
          ? measured
          : (Number(c.duration) || Number(c.source_duration) || Number(c.trim_end) || 0);
      });
      return d;
    };

    const finishLoading = () => {
      if (cancelled) return;
      const d = collectDurations();
      setDurations(d);
      setMetadataReady(true);
      onDurations?.(d);

      // Seek active video element to the playhead so first frame renders immediately
      const activeSegs = buildSegments(clips, d);
      const targetT = playheadRef.current || 0;
      const plan = planAt(activeSegs, targetT);
      plan.forEach(({ seg, localTime }) => {
        const v = videoElsRef.current[seg.clip.id];
        if (v && Number.isFinite(localTime)) {
          try { v.currentTime = localTime; } catch {}
        }
      });
      requestAnimationFrame(() => renderAt(targetT));
    };

    const waits = clips.map((c) => new Promise((resolve) => {
      const v = videoElsRef.current[c.id];
      if (!v || v.readyState >= 1) return resolve();
      let done = false;
      const cleanup = () => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        v.removeEventListener('loadedmetadata', cleanup);
        v.removeEventListener('loadeddata', cleanup);
        v.removeEventListener('canplay', cleanup);
        v.removeEventListener('error', cleanup);
        resolve();
      };
      // Individual per-clip safety timeout so a slow or stalled media request doesn't block the UI
      const timer = setTimeout(cleanup, 800);
      v.addEventListener('loadedmetadata', cleanup);
      v.addEventListener('loadeddata', cleanup);
      v.addEventListener('canplay', cleanup);
      v.addEventListener('error', cleanup);
    }));

    // Global race with a 1200ms ceiling: even if multiple offscreen requests queue up in Chromium,
    // we never leave the user permanently blocked on "กำลังโหลดวิดีโอ...".
    const globalTimeout = new Promise((resolve) => setTimeout(resolve, 1200));

    Promise.race([Promise.all(waits), globalTimeout]).then(() => {
      finishLoading();
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clipKey]);

  const segments = useMemo(
    () => buildSegments(clips, durations),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [clipKey, metadataReady, durations]
  );

  const segmentsByClipId = useMemo(() => {
    const byId = new Map();
    segments.forEach((segment) => {
      const id = segment.clip?.id;
      // Preserve the old `segments.find(...)` behavior if malformed input ever
      // contains duplicate clip ids: the first segment wins.
      if (id != null && !byId.has(id)) byId.set(id, segment);
    });
    return byId;
  }, [segments]);

  const totalDuration = totalDurationOf(segments);

  const getDrawPlan = (t) => planAt(segments, t);

  const currentBackgroundIsolationStatus = useMemo(() => {
    const fallbackState = backgroundIsolationStatus?.state || 'off';
    if (fallbackState === 'off' || !segments.length) return fallbackState;

    const currentEntry = getDrawPlan(playhead)[0];
    const config = currentEntry
      ? resolveBackgroundIsolationConfig(currentEntry.seg.clip, backgroundIsolation)
      : backgroundIsolation;
    if (!config || config.enabled !== true) return 'off';

    const artifactId = backgroundArtifactId(config);
    if (!artifactId) return 'missing';

    const hasManifestResponse = Object.prototype.hasOwnProperty.call(backgroundIsolationManifests, artifactId);
    if (!hasManifestResponse) return 'processing';

    const manifest = backgroundIsolationManifests[artifactId];
    const resolution = resolveBackgroundIsolationPreview({
      config,
      manifest,
      artifactBaseUrl: '/api/background-isolation/sequences',
      sourceTime: Math.max(0, Number(currentEntry?.localTime) || 0),
    });
    if (resolution.useArtifact && resolution.frameUrl) {
      const frame = backgroundIsolationImagesRef.current.get(resolution.frameUrl);
      if (!frame || frame.status === 'loading') return 'processing';
      if (frame.status === 'ready') return 'ready';
      return 'quality_failed';
    }
    if (['error', 'stale', 'cancelled'].includes(resolution.status) || resolution.reason === 'manifest_invalid') {
      return 'quality_failed';
    }
    if (resolution.status === 'disabled') return 'off';
    return fallbackState === 'ready' ? 'processing' : fallbackState;
  }, [backgroundIsolation, backgroundIsolationManifests, backgroundIsolationStatus, backgroundIsolationTick, playhead, segments]);

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
      if (video) {
        const isolatedImage = loadedBackgroundIsolationFrame(entry.seg.clip, entry.localTime);
        paintEntry(ctx, entry, video, getOffscreen(), isolatedImage);
      }
    });
    ctx.globalAlpha = 1;
    ctx.filter = 'none';
    const bounds = [];
    applyGrade(ctx, canvas);
    // Spotlight is a footage-only pass: above the graded video, below every
    // sticker, effect, subtitle, and product overlay.
    drawSpotlight(ctx, previewSpotlight);
    // Same order the render burns in (video_editor.py): the badge, then the
    // scrim over it, then everything libass draws on top.
    drawStickers(ctx, stickerImagesRef.current, stickerImgRef.current, t, effectiveStickersList, bounds, isStickerHidden, previewSticker, previewAccentColor);
    syncEffectVideos(effectVideosRef.current, t, effects, isPlaying);
    drawEffects(ctx, effectVideosRef.current, t, effects, bounds, previewAccentColor);
    drawOverlayScrims(ctx, overlaysBehindSubject, t);
    drawOverlays(ctx, overlaysBehindSubject, t, previewAccentColor, bounds);
    // Repaint only the RGBA subject after the Hook.  The isolated frame's
    // opaque mood background must not be repainted here or it would erase the
    // Hook we intentionally placed behind the product.
    plan.forEach((entry) => {
      const isolatedImage = loadedBackgroundIsolationFrame(entry.seg.clip, entry.localTime);
      if (isolatedImage) {
        drawIsolatedFrame(ctx, isolatedImage, entry.seg.clip, entry.motionTime, { includeBackground: false });
      }
    });
    drawOverlayScrims(ctx, overlaysInFront, t);
    if (!captionStyle.hidden) {
      drawCaption(ctx, cues, t, captionStyle, bounds);
    }
    drawOverlays(ctx, overlaysInFront, t, previewAccentColor, bounds);
    if (showWatermark !== false) {
      drawWatermark(ctx);
    }
    boundsRef.current = bounds;
  };

  useEffect(() => {
    renderAt(playheadRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segments, captionKey, stickerKey, stickersKey, cuesKey, overlaysKey, spotlightKey, backgroundIsolationManifests, backgroundIsolationTick, lutReady, grade?.intensity, previewAccentColor, showWatermark]);

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
        publishPlayhead(totalDuration, true);
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
        ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
        let framePainted = false;
        plan.forEach((entry) => {
          const { seg } = entry;
          const video = videoElsRef.current[seg.clip.id];
          if (!video) return;

          // If incoming video is still actively seeking to its cut point,
          // hold the outgoing clip's frame to eliminate any flash or random frame stutter
          if (video.seeking && prevActiveClipIdRef.current && prevActiveClipIdRef.current !== seg.clip.id) {
            const prevV = videoElsRef.current[prevActiveClipIdRef.current];
            const prevSeg = segmentsByClipId.get(prevActiveClipIdRef.current);
            if (prevV && prevSeg && prevV.readyState >= 2) {
              ctx.globalAlpha = 1;
              ctx.filter = clipFilter(prevSeg.clip);
              const prevImage = loadedBackgroundIsolationFrame(prevSeg.clip, localTimeAt(prevSeg, t));
              if (prevImage) {
                drawIsolatedFrame(ctx, prevImage, prevSeg.clip, motionTimeAt(prevSeg, t));
              } else {
                drawVideoFrame(ctx, prevV, prevSeg.clip);
              }
              framePainted = true;
              return;
            }
          }

          const isolatedImage = loadedBackgroundIsolationFrame(entry.seg.clip, entry.localTime);
          if (video.readyState >= 2 || isolatedImage) {
            paintEntry(ctx, entry, video, getOffscreen(), isolatedImage);
            framePainted = true;
            prevActiveClipIdRef.current = seg.clip.id;
          }
        });

        ctx.globalAlpha = 1;
        ctx.filter = 'none';
        const bounds = [];
        if (framePainted) applyGrade(ctx, canvas);
        drawSpotlight(ctx, previewSpotlight);
        drawStickers(ctx, stickerImagesRef.current, stickerImgRef.current, t, effectiveStickersList, bounds, isStickerHidden, previewSticker, previewAccentColor);
        syncEffectVideos(effectVideosRef.current, t, effects);
        drawEffects(ctx, effectVideosRef.current, t, effects, bounds, previewAccentColor);
        drawOverlayScrims(ctx, overlaysBehindSubject, t);
        drawOverlays(ctx, overlaysBehindSubject, t, previewAccentColor, bounds);
        plan.forEach((entry) => {
          const isolatedImage = loadedBackgroundIsolationFrame(entry.seg.clip, entry.localTime);
          if (isolatedImage) {
            drawIsolatedFrame(ctx, isolatedImage, entry.seg.clip, entry.motionTime, { includeBackground: false });
          }
        });
        drawOverlayScrims(ctx, overlaysInFront, t);
        if (!captionStyle.hidden) {
          drawCaption(ctx, cues, t, captionStyle, bounds);
        }
        drawOverlays(ctx, overlaysInFront, t, previewAccentColor, bounds);
        if (showWatermark !== false) {
          drawWatermark(ctx);
        }
        boundsRef.current = bounds;
      }

      const now = performance.now();
      publishPlayhead(t, false, now);
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
    // effectiveStickersList/effects included so an add/edit mid-playback is
    // picked up immediately -- tick() closes over them, and without this the
    // RAF loop kept drawing whatever array existed when isPlaying last
    // flipped true until some other dep (e.g. overlays) happened to change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, segments, segmentsByClipId, cues, overlays, totalDuration, effectiveStickersList, effects, spotlightKey, backgroundIsolationManifests, backgroundIsolationTick]);

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
      publishPlayhead(startT, true);
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
    publishPlayhead(clamped, true);
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

    // The Cover Studio can use the same painted Timeline frame before an MP4
    // exists. Keep this on the player so the capture includes the active
    // clip, overlays, captions, stickers and grade at the current playhead.
    captureFrame: () => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      renderAt(playheadRef.current);
      return canvas.toDataURL('image/jpeg', 0.92);
    },

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
            ref={(el) => {
              if (el) {
                videoElsRef.current[c.id] = el;
              } else {
                delete videoElsRef.current[c.id];
              }
            }}
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
          ref={containerRef}
          onClick={handleContainerClick}
          className="relative overflow-hidden rounded-2xl border border-[#363430] bg-black shadow-2xl select-none"
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
              <BackgroundIsolationStatusBadge status={currentBackgroundIsolationStatus} />

              {/* Smart Snap Guides (Center Guidelines) */}
              {snapGuide.x !== null && (
                <div
                  className="pointer-events-none absolute top-0 bottom-0 w-[1.5px] bg-[#25F4EE] shadow-[0_0_8px_#25F4EE] z-20"
                  style={{ left: `${snapGuide.x * 100}%` }}
                />
              )}
              {snapGuide.y !== null && (
                <div
                  className="pointer-events-none absolute left-0 right-0 h-[1.5px] bg-[#25F4EE] shadow-[0_0_8px_#25F4EE] z-20"
                  style={{ top: `${snapGuide.y * 100}%` }}
                />
              )}

              {/* TikTok Safe Zone Overlay (Safe 9:16 Area) */}
              {showSafeZone && (
                <div className="pointer-events-none absolute inset-0 z-20 overflow-hidden">
                  {/* Top Margin (180px / 1920 = 9.4%) */}
                  <div className="absolute top-0 left-0 right-0 h-[9.4%] bg-black/25 border-b border-dashed border-white/40 flex items-center px-2">
                    <span className="text-[9px] font-medium text-slate-300 bg-black/70 px-1.5 py-0.5 rounded border border-white/15">
                      หลบแถบ Following / For You (180px)
                    </span>
                  </div>

                  {/* Right Side Bar (120px / 1080 = 11.1%) */}
                  <div className="absolute top-[9.4%] bottom-[21.9%] right-0 w-[11.1%] bg-rose-500/[0.08] border-l border-dashed border-[#FE2C55]/70 flex flex-col items-center justify-center gap-2.5 p-1">
                    <div className="text-[7.5px] font-bold text-rose-300 rotate-90 whitespace-nowrap bg-black/80 px-1 py-0.5 rounded border border-rose-500/30">
                      หลบปุ่ม Like / Share
                    </div>
                    <div className="w-4 h-4 rounded-full border border-white/25 bg-white/10 flex items-center justify-center text-[8px] text-white/50">👤</div>
                    <div className="w-4 h-4 rounded-full border border-rose-500/30 bg-rose-500/10 flex items-center justify-center text-[8px] text-rose-300">♥</div>
                    <div className="w-4 h-4 rounded-full border border-white/25 bg-white/10 flex items-center justify-center text-[8px] text-white/50">💬</div>
                    <div className="w-4 h-4 rounded-full border border-white/25 bg-white/10 flex items-center justify-center text-[8px] text-white/50">↗</div>
                  </div>

                  {/* Bottom Danger Zone (420px / 1920 = 21.9%) */}
                  <div className="absolute bottom-0 left-0 right-0 h-[21.9%] bg-rose-500/[0.08] border-t-2 border-dashed border-[#FE2C55] flex flex-col justify-end p-2">
                    <div className="flex items-center gap-1.5 text-[9px] font-bold text-[#FE2C55] bg-black/85 px-2 py-0.5 rounded w-fit backdrop-blur-sm border border-[#FE2C55]/40 mb-1">
                      <span>Safe Zone ล่าง 420px (หลบแคปชัน/ตะกร้า/เพลง)</span>
                    </div>
                    <div className="text-[8px] text-rose-200/60 pl-0.5">
                      ห้ามวางซับไตเติลหรือสติกเกอร์ในโซนนี้
                    </div>
                  </div>

                  {/* 100% Safe Region Corner Indicator */}
                  <div className="absolute top-[9.4%] left-0 right-[11.1%] bottom-[21.9%] pointer-events-none border border-emerald-500/20">
                    <div className="absolute top-1 left-1.5 text-[8px] font-bold text-emerald-400 bg-black/75 px-1.5 py-0.5 rounded border border-emerald-500/30 shadow">
                      SAFE ZONE (9:16)
                    </div>
                  </div>
                </div>
              )}

              {/* Product Spotlight focus window: drag the active focus directly
                  on the preview; the dimmed footage remains painted on canvas. */}
              {previewSpotlight && onSpotlightChangeLive && (
                <div
                  role="button"
                  tabIndex={0}
                  aria-label="จุดโฟกัส Product Spotlight ลากเพื่อย้าย กดลูกศรเพื่อขยับ"
                  className={`absolute z-25 cursor-move select-none border-2 border-dashed border-[#25F4EE] bg-[#25F4EE]/[0.04] shadow-[0_0_18px_rgba(37,244,238,0.35)] ${
                    previewSpotlight.shape === 'ellipse'
                      ? 'rounded-[50%]'
                      : previewSpotlight.shape === 'rounded_rect'
                        ? 'rounded-2xl'
                        : 'rounded-none'
                  }`}
                  style={{
                    left: `${(previewSpotlight.focus.x - previewSpotlight.focus.width / 2) * 100}%`,
                    top: `${(previewSpotlight.focus.y - previewSpotlight.focus.height / 2) * 100}%`,
                    width: `${previewSpotlight.focus.width * 100}%`,
                    height: `${previewSpotlight.focus.height * 100}%`,
                    touchAction: 'none',
                  }}
                  onPointerDown={handleSpotlightDragStart}
                  onKeyDown={handleSpotlightKeyDown}
                  title="ลากเพื่อย้ายจุดโฟกัส Product Spotlight"
                >
                  <span className="pointer-events-none absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-[#25F4EE]/40 bg-black/85 px-2 py-0.5 text-[9px] font-bold text-[#25F4EE] shadow-md">
                    Spotlight · ลากเพื่อย้าย
                  </span>
                </div>
              )}

              {/* Interactive Bounding Box for Selected Element */}
              {selectedBox && (
                <div
                  className="interactive-bounding-box absolute z-30 pointer-events-auto border-2 border-[#25F4EE] shadow-[0_0_12px_rgba(37,244,238,0.5)] cursor-move select-none"
                  style={{
                    left: `${(selectedBox.x / CANVAS_W) * 100}%`,
                    top: `${(selectedBox.y / CANVAS_H) * 100}%`,
                    width: `${(selectedBox.w / CANVAS_W) * 100}%`,
                    height: `${(selectedBox.h / CANVAS_H) * 100}%`,
                    touchAction: 'none',
                    userSelect: 'none',
                  }}
                  onPointerDown={handleBoxDragStart}
                >
                  {/* Floating Info Tag on Top */}
                  <div className="absolute -top-7 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-black/85 backdrop-blur-md border border-[#25F4EE]/40 text-[10px] text-white whitespace-nowrap pointer-events-none shadow-md">
                    <span className="font-semibold text-[#25F4EE]">
                      {selectedBox.label || 'ข้อความ'}
                    </span>
                    <span className="text-slate-300">
                      {selectedBox.sizePct != null
                        ? `${Math.round(selectedBox.sizePct)}%`
                        : `${Math.round((selectedBox.scale || 1) * 100)}%`}
                    </span>
                    <span className="text-slate-400 font-mono text-[9px]">
                      ({Math.round(selectedBox.normX * 100)}%, {Math.round(selectedBox.normY * 100)}%)
                    </span>
                  </div>

                  {/* 4 Corner Resize Handles */}
                  <div
                    className="absolute -top-2 -left-2 w-4 h-4 rounded-full bg-white border-2 border-[#25F4EE] shadow-md cursor-nwse-resize hover:scale-125 transition-transform"
                    style={{ touchAction: 'none' }}
                    onPointerDown={(e) => handleResizeStart(e, 'nw')}
                    title="ลากเพื่อย่อ/ขยาย"
                  />
                  <div
                    className="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-white border-2 border-[#25F4EE] shadow-md cursor-nesw-resize hover:scale-125 transition-transform"
                    style={{ touchAction: 'none' }}
                    onPointerDown={(e) => handleResizeStart(e, 'ne')}
                    title="ลากเพื่อย่อ/ขยาย"
                  />
                  <div
                    className="absolute -bottom-2 -right-2 w-4 h-4 rounded-full bg-white border-2 border-[#25F4EE] shadow-md cursor-nwse-resize hover:scale-125 transition-transform"
                    style={{ touchAction: 'none' }}
                    onPointerDown={(e) => handleResizeStart(e, 'se')}
                    title="ลากเพื่อย่อ/ขยาย"
                  />
                  <div
                    className="absolute -bottom-2 -left-2 w-4 h-4 rounded-full bg-white border-2 border-[#25F4EE] shadow-md cursor-nesw-resize hover:scale-125 transition-transform"
                    style={{ touchAction: 'none' }}
                    onPointerDown={(e) => handleResizeStart(e, 'sw')}
                    title="ลากเพื่อย่อ/ขยาย"
                  />

                  {/* 4 Edge Capsule Handles */}
                  <div
                    className="absolute top-1/2 -left-1.5 -translate-y-1/2 w-2.5 h-5 rounded-full bg-white border border-[#25F4EE] shadow-sm cursor-ew-resize hover:scale-125 transition-transform"
                    style={{ touchAction: 'none' }}
                    onPointerDown={(e) => handleResizeStart(e, 'w')}
                    title="ลากเพื่อย่อ/ขยาย"
                  />
                  <div
                    className="absolute top-1/2 -right-1.5 -translate-y-1/2 w-2.5 h-5 rounded-full bg-white border border-[#25F4EE] shadow-sm cursor-ew-resize hover:scale-125 transition-transform"
                    style={{ touchAction: 'none' }}
                    onPointerDown={(e) => handleResizeStart(e, 'e')}
                    title="ลากเพื่อย่อ/ขยาย"
                  />
                  <div
                    className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-5 h-2.5 rounded-full bg-white border border-[#25F4EE] shadow-sm cursor-ns-resize hover:scale-125 transition-transform"
                    style={{ touchAction: 'none' }}
                    onPointerDown={(e) => handleResizeStart(e, 'n')}
                    title="ลากเพื่อย่อ/ขยาย"
                  />
                  <div
                    className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-5 h-2.5 rounded-full bg-white border border-[#25F4EE] shadow-sm cursor-ns-resize hover:scale-125 transition-transform"
                    style={{ touchAction: 'none' }}
                    onPointerDown={(e) => handleResizeStart(e, 's')}
                    title="ลากเพื่อย่อ/ขยาย"
                  />

                  {/* Center Anchor Point */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[#25F4EE] pointer-events-none" />
                </div>
              )}

              {/* Hover Play Button (Only active when no bounding box is selected and not previewing template) */}
              {!selectedBox && !previewTextTemplate && (
                <button
                  type="button"
                  onClick={togglePlay}
                  className="group absolute inset-0 flex cursor-pointer items-center justify-center bg-black/0 transition-colors hover:bg-black/20"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-black/60 text-white opacity-0 shadow-lg transition-all group-hover:bg-[#25F4EE] group-hover:text-black group-hover:opacity-100">
                    {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                  </div>
                </button>
              )}

              {/* Ephemeral Text Template Preview Box Overlay (Clean Dashed Border Only) */}
              {previewTextTemplate && (() => {
                const previewBound = boundsRef.current.find((b) => b.type === 'template_preview');
                const pX = previewBound ? (previewBound.x / CANVAS_W) * 100 : 15;
                const pY = previewBound ? (previewBound.y / CANVAS_H) * 100 : 45;
                const pW = previewBound ? (previewBound.w / CANVAS_W) * 100 : 70;
                const pH = previewBound ? (previewBound.h / CANVAS_H) * 100 : 10;
                return (
                  <div
                    className="pointer-events-none absolute z-35 select-none rounded-lg border border-dashed border-[#25F4EE]/80 shadow-[0_0_15px_rgba(37,244,238,0.25)]"
                    style={{
                      left: `${pX}%`,
                      top: `${pY}%`,
                      width: `${pW}%`,
                      height: `${pH}%`,
                    }}
                  />
                );
              })()}

              {/* Ephemeral Sticker Preview Box Overlay */}
              {previewSticker && (() => {
                const previewBound = boundsRef.current.find((b) => b.type === 'sticker_preview');
                const pX = previewBound ? (previewBound.x / CANVAS_W) * 100 : 42.6;
                const pY = previewBound ? (previewBound.y / CANVAS_H) * 100 : 46;
                const pW = previewBound ? (previewBound.w / CANVAS_W) * 100 : 14.8;
                const pH = previewBound ? (previewBound.h / CANVAS_H) * 100 : 8.3;
                return (
                  <div
                    className="pointer-events-none absolute z-35 select-none rounded-2xl border border-dashed border-[#25F4EE] shadow-[0_0_18px_rgba(37,244,238,0.35)] flex items-start justify-center"
                    style={{
                      left: `${pX}%`,
                      top: `${pY}%`,
                      width: `${pW}%`,
                      height: `${pH}%`,
                    }}
                  >
                    <span className="absolute -top-5 px-2 py-0.5 rounded-full bg-[#25F4EE] text-[9px] font-bold text-slate-950 shadow animate-pulse">
                      พรีวิวสติกเกอร์
                    </span>
                  </div>
                );
              })()}

              {/* Safe Zone Toggle Button */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleSafeZone();
                }}
                title={showSafeZone ? 'ซ่อน Safe Zone' : 'แสดง TikTok Safe Zone (9:16)'}
                className={`absolute top-2 right-2 z-30 flex h-7 px-2 items-center gap-1 rounded-lg text-[10px] font-bold border transition-all cursor-pointer backdrop-blur-md shadow-md ${
                  showSafeZone
                    ? 'bg-[#25F4EE]/20 border-[#25F4EE] text-[#25F4EE]'
                    : 'bg-black/60 border-white/[0.1] text-slate-400 hover:text-white'
                }`}
              >
                <Shield className="w-3.5 h-3.5" />
                <span>Safe Zone</span>
              </button>

              {/* Timecode lives here, over the stage */}
              <div className="pointer-events-none absolute bottom-2 right-2 z-20 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-mono font-bold text-white/90 backdrop-blur-sm">
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
