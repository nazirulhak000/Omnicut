import { resolveClipTransforms } from './keyframeModel.js';

// Points are stored in the worker's untransformed, letterboxed 9:16 canvas.
// The visible original video is cover-fit; a ready Cutout is already letterboxed.
const W = 1080;
const H = 1920;
const EPSILON = 1e-8;

function inside(x, y, width, height) {
  return x >= -EPSILON && y >= -EPSILON && x <= width + EPSILON && y <= height + EPSILON;
}

function geometry({ sourceWidth, sourceHeight, sourceIsLetterboxed = false, clip = {}, motionTime = 0 } = {}) {
  if (!(sourceWidth > 0 && sourceHeight > 0)) return null;
  const rw = sourceIsLetterboxed ? W : sourceWidth;
  const rh = sourceIsLetterboxed ? H : sourceHeight;
  const camera = resolveClipTransforms(clip, motionTime);
  const rotation = ((Number(clip.rotation || 0) % 360) + 360) % 360;
  const swapped = rotation === 90 || rotation === 270;
  const vw = swapped ? rh : rw;
  const vh = swapped ? rw : rh;
  let sw = Math.min(vw, vh * W / H);
  let sh = sw * H / W;
  let sx = (vw - sw) / 2;
  let sy = (vh - sh) / 2;
  if (camera.zoom > 1.001) {
    sx += (sw - sw / camera.zoom) * (1 + camera.pan_x) / 2;
    sy += (sh - sh / camera.zoom) * (1 + camera.pan_y) / 2;
    sw /= camera.zoom;
    sh /= camera.zoom;
  }
  let crop = { x: sx, y: sy, width: sw, height: sh };
  if (rotation === 90) crop = { x: sy, y: rh - sx - sw, width: sh, height: sw };
  else if (rotation === 270) crop = { x: rw - sy - sh, y: sx, width: sh, height: sw };
  else if (rotation === 180) crop = { x: rw - sx - sw, y: rh - sy - sh, width: sw, height: sh };
  const fit = Math.min(W / rw, H / rh);
  return { rw, rh, camera, rotation, mirror: !!clip.mirror, crop,
    dw: swapped ? H : W, dh: swapped ? W : H,
    blur: !sourceIsLetterboxed && rotation === 0 && (!!clip.bg_blur || clip.fit_mode === 'blur'),
    fit, padX: (W - rw * fit) / 2, padY: (H - rh * fit) / 2, sourceIsLetterboxed };
}

function rotate(x, y, degrees) {
  const a = degrees * Math.PI / 180;
  return [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)];
}

function workerToRaw(point, g) {
  if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) return null;
  const x = (point.x * W - g.padX) / g.fit;
  const y = (point.y * H - g.padY) / g.fit;
  return inside(x, y, g.rw, g.rh) ? [x, y] : null;
}

/** Invert the actual preview framing before sending a SAM2 prompt. */
export function previewPointToSource(point, options) {
  const g = geometry(options);
  if (!g || !point || !Number.isFinite(point.x) || !Number.isFinite(point.y)
    || !inside(point.x, point.y, 1, 1)) return null;
  let x = point.x * W;
  let y = point.y * H;
  if (g.blur) {
    x = (x - W / 2) / g.camera.zoom + W / 2 + g.camera.pan_x * W * (g.camera.zoom - 1) / (2 * g.camera.zoom);
    y = (y - H / 2) / g.camera.zoom + H / 2 + g.camera.pan_y * H * (g.camera.zoom - 1) / (2 * g.camera.zoom);
    if (g.mirror) x = W - x;
    x = (x - g.padX) / g.fit;
    y = (y - g.padY) / g.fit;
  } else {
    x -= W / 2; y -= H / 2;
    if (g.mirror) x = -x;
    [x, y] = rotate(x, y, -g.rotation);
    if (!inside(x + g.dw / 2, y + g.dh / 2, g.dw, g.dh)) return null;
    x = g.crop.x + (x / g.dw + 0.5) * g.crop.width;
    y = g.crop.y + (y / g.dh + 0.5) * g.crop.height;
  }
  if (!inside(x, y, g.rw, g.rh)) return null;
  return { x: (g.padX + x * g.fit) / W, y: (g.padY + y * g.fit) / H, label: point.label ?? 1 };
}

/** Project a saved worker prompt back onto the current visible video. */
export function sourcePointToPreview(point, options) {
  const g = geometry(options);
  if (!g) return null;
  const raw = workerToRaw(point, g);
  if (!raw) return null;
  let [x, y] = raw;
  if (g.blur) {
    x = g.padX + x * g.fit;
    y = g.padY + y * g.fit;
    if (g.mirror) x = W - x;
    x = W / 2 + g.camera.zoom * (x - W / 2) - g.camera.pan_x * W * (g.camera.zoom - 1) / 2;
    y = H / 2 + g.camera.zoom * (y - H / 2) - g.camera.pan_y * H * (g.camera.zoom - 1) / 2;
  } else {
    x = ((x - g.crop.x) / g.crop.width - 0.5) * g.dw;
    y = ((y - g.crop.y) / g.crop.height - 0.5) * g.dh;
    if (!inside(x + g.dw / 2, y + g.dh / 2, g.dw, g.dh)) return null;
    [x, y] = rotate(x, y, g.rotation);
    if (g.mirror) x = -x;
    x += W / 2; y += H / 2;
  }
  return inside(x, y, W, H) ? { x: x / W, y: y / H, label: point.label ?? 1 } : null;
}
