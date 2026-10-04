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
export function overlayAnimState(t, start, end, { scaleIn = true, fps = FPS } = {}) {
  const { inSec, outSec } = overlayAnimTiming(start, end, fps);
  let alpha = 1;
  let scale = 1;
  if (inSec > 0) {
    const p = Math.min(1, Math.max(0, (t - Number(start)) / inSec));
    alpha = p;
    if (scaleIn) {
      scale = OVERLAY_ANIM.SCALE_FROM + (1 - OVERLAY_ANIM.SCALE_FROM) * CAMERA_EASINGS.ease_out(p);
    }
  }
  if (outSec > 0) {
    // ffmpeg chains two `fade` filters, which multiply their factors.
    alpha *= Math.min(1, Math.max(0, (Number(end) - t) / outSec));
  }
  return { alpha, scale };
}
