// Sticker/effect entrance + exit animation, mirrored 1:1 by
// scripts/video_editor.py overlay_anim_timing/overlay_anim_state (the ffmpeg
// chain is overlay_anim_filters). Entrance = linear alpha fade plus, for
// stickers, an ease_out scale settle 0.88 -> 1.0 about the resting centre;
// exit = linear alpha fade. Durations are whole frames, capped at 40% of the
// visible window so a short sticker still reaches full opacity. The resting
// geometry (position, size, opacity) is untouched.
import { CAMERA_EASINGS, FPS } from './timelineMath.js';

export const OVERLAY_ANIM = Object.freeze({
  IN_FRAMES: 7,      // 7/30 s = 0.233 s (<= 0.25 s)
  OUT_FRAMES: 6,     // 6/30 s = 0.2 s
  MAX_SHARE: 0.4,
  SCALE_FROM: 0.88,
  OPEN_END: 99999,   // Canvas uses end=999999 for "no end"
});

/** {inSec, outSec} on the 1/fps grid; outSec is 0 without a real end. */
export function overlayAnimTiming(start, end, fps = FPS) {
  const s = Number(start);
  const e = end == null ? NaN : Number(end);
  const hasEnd = Number.isFinite(e) && e < OVERLAY_ANIM.OPEN_END;
  let cap = OVERLAY_ANIM.IN_FRAMES;
  if (hasEnd) {
    const visible = e - s;
    if (!(visible > 0)) return { inSec: 0, outSec: 0 };
    cap = Math.floor(visible * OVERLAY_ANIM.MAX_SHARE * fps + 1e-6);
  }
  const inFrames = Math.max(0, Math.min(OVERLAY_ANIM.IN_FRAMES, cap));
  const outFrames = hasEnd ? Math.max(0, Math.min(OVERLAY_ANIM.OUT_FRAMES, cap)) : 0;
  return { inSec: inFrames / fps, outSec: outFrames / fps };
}

/** {alpha, scale} at timeline time t (scale is about the resting centre). */
export function overlayAnimState(t, start, end, { scaleIn = true, anim = 'ease_out', fps = FPS } = {}) {
  const { inSec, outSec } = overlayAnimTiming(start, end, fps);
  let alpha = 1;
  let scale = 1;
  if (inSec > 0) {
    const p = Math.min(1, Math.max(0, (t - Number(start)) / inSec));
    alpha = p;
    if (scaleIn) {
      if (anim === 'spring_bounce') {
        scale = capcutSpringScale(p, { fromScale: OVERLAY_ANIM.SCALE_FROM });
      } else if (anim === 'elastic_out') {
        scale = OVERLAY_ANIM.SCALE_FROM + (1 - OVERLAY_ANIM.SCALE_FROM) * capcutElasticOut(p);
      } else if (anim === 'back_out') {
        scale = OVERLAY_ANIM.SCALE_FROM + (1 - OVERLAY_ANIM.SCALE_FROM) * capcutBackOut(p);
      } else {
        scale = OVERLAY_ANIM.SCALE_FROM + (1 - OVERLAY_ANIM.SCALE_FROM) * CAMERA_EASINGS.ease_out(p);
      }
    }
  }
  if (outSec > 0) {
    // ffmpeg chains two `fade` filters, which multiply their factors.
    alpha *= Math.min(1, Math.max(0, (Number(end) - t) / outSec));
  }
  return { alpha, scale };
}


/**
 * CapCut 7.1 Damped Harmonic Oscillator spring scale (`template_sticker` / `lumi_js_resources_video`).
 * s(p) = 1 - (1 - fromScale) * exp(-zeta * omega * p) * cos(omega * sqrt(1 - zeta^2) * p)
 */
export function capcutSpringScale(p, { omega = 18.0, zeta = 0.45, fromScale = OVERLAY_ANIM.SCALE_FROM } = {}) {
  const t = Math.max(0, Math.min(1, Number(p) || 0));
  const wd = omega * Math.sqrt(Math.max(0, 1 - zeta * zeta));
  return 1 - (1 - fromScale) * Math.exp(-zeta * omega * t) * Math.cos(wd * t);
}

/** CapCut 7.1 `Easing.Elastic.Out` from `Resources/template_sticker/js/template/template.js`. */
export function capcutElasticOut(p) {
  const amount = Math.max(0, Math.min(1, Number(p) || 0));
  if (amount === 0) return 0;
  if (amount === 1) return 1;
  return Math.pow(2, -10 * amount) * Math.sin((amount - 0.1) * 5 * Math.PI) + 1;
}

/** CapCut 7.1 `Easing.Back.Out` from `Resources/template_sticker/js/template/template.js`. */
export function capcutBackOut(p) {
  let amount = Math.max(0, Math.min(1, Number(p) || 0));
  if (amount === 0) return 0;
  const s = 1.70158;
  amount -= 1;
  return amount * amount * ((s + 1) * amount + s) + 1;
}

/** CapCut 7.1 `Resources/MixMode/MixMode.json` blend mode options. */
export const BLEND_MODE_OPTIONS = Object.freeze([
  { id: 'normal', label: 'ปกติ (Normal)', compositeOp: 'source-over' },
  { id: 'screen', label: 'สว่างใส (Screen)', compositeOp: 'screen' },
  { id: 'multiply', label: 'คูณสีเข้ม (Multiply)', compositeOp: 'multiply' },
  { id: 'overlay', label: 'ซ้อนทับ (Overlay)', compositeOp: 'overlay' },
  { id: 'soft-light', label: 'แสงนุ่ม (Soft Light)', compositeOp: 'soft-light' },
  { id: 'lighten', label: 'เลือกสีสว่าง (Lighten)', compositeOp: 'lighten' },
  { id: 'darken', label: 'เลือกสีมืด (Darken)', compositeOp: 'darken' },
]);

export function resolveCanvasCompositeOp(blendMode) {
  const mode = String(blendMode || 'normal').trim().toLowerCase();
  const found = BLEND_MODE_OPTIONS.find((m) => m.id === mode);
  return found ? found.compositeOp : 'source-over';
}

/**
 * Exact GLSL SoftLight formula extracted from CapCut 7.1
 * `Resources/MixMode/soft_light/AmazingFeature/xshader/5ccf14a16ee408733fb178d87473b43b.frag`:
 * SOFT_LIGHT(f, b): f < 0.5 ? 2*b*f + b*b*(1 - 2*f) : sqrt(b)*(2*f - 1) + 2*b*(1 - f)
 */
export function capcutSoftLightChannel(fg, bg) {
  const f = Math.max(0, Math.min(1, Number(fg) || 0));
  const b = Math.max(0, Math.min(1, Number(bg) || 0));
  if (f < 0.5) {
    return 2.0 * b * f + b * b * (1.0 - 2.0 * f);
  }
  return Math.sqrt(b) * (2.0 * f - 1.0) + 2.0 * b * (1.0 - f);
}
