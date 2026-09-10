export const ACCENT_RECOLOR_MODE = 'accent';
export const DEFAULT_EFFECT_SOURCE_HUE = 205;

export const SAFE_STICKER_SOURCE_HUES = Object.freeze({
  accent_sparkle_star_3d: 52,
  arrow_pointer_cyan_3d: 180,
  arrow_pointer_yellow_3d: 52,
  arrow_tech_cyan_3d: 180,
  frame_tech_callout_3d: 180,
  frame_tech_callout_hollow_3d: 180,
  hud_callout_bracket_3d: 180,
  plate_banner_coral_3d: 8,
  plate_banner_cyan_3d: 180,
  plate_banner_yellow_3d: 52,
});

function assetStem(assetId) {
  return String(assetId || '').trim().split(/[\\/]/).pop().toLowerCase().replace(/\.(png|webp|jpg|webm|mov)$/i, '');
}

export function getOverlayRecolorMetadata(kind, assetId) {
  const stem = assetStem(assetId);
  if (kind === 'sticker' && Object.prototype.hasOwnProperty.call(SAFE_STICKER_SOURCE_HUES, stem)) {
    return { recolorable: true, recolor_source_hue: SAFE_STICKER_SOURCE_HUES[stem] };
  }
  if (kind === 'effect' && stem.startsWith('fx_')) {
    return { recolorable: true, recolor_source_hue: DEFAULT_EFFECT_SOURCE_HUE };
  }
  return { recolorable: false };
}

function hexToHue(value) {
  const rawValue = String(value || '').trim().replace(/^#/, '');
  const raw = rawValue.length === 3 ? rawValue.split('').map((char) => char + char).join('') : rawValue;
  if (!/^[0-9a-f]{6}$/i.test(raw)) return null;
  const [r, g, b] = [0, 2, 4].map((index) => parseInt(raw.slice(index, index + 2), 16) / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  if (delta === 0) return 0;
  let hue;
  if (max === r) hue = ((g - b) / delta) % 6;
  else if (max === g) hue = (b - r) / delta + 2;
  else hue = (r - g) / delta + 4;
  return (hue * 60 + 360) % 360;
}

function shortestHueDelta(target, source) {
  const delta = ((target - source + 180) % 360 + 360) % 360 - 180;
  return delta === -180 ? 180 : delta;
}

export function getOverlayHueRotation(item, accentColor, kind = '', assetId = null) {
  const data = item && typeof item === 'object' ? item : {};
  const requested = data.recolor ?? data.tint;
  if (!(requested === true || String(requested || '').trim().toLowerCase() === ACCENT_RECOLOR_MODE)) return null;
  const metadata = getOverlayRecolorMetadata(kind, assetId);
  const source = Number(data.recolorSourceHue ?? data.recolor_source_hue ?? metadata.recolor_source_hue);
  const target = hexToHue(accentColor);
  if (!Number.isFinite(source) || target == null) return null;
  return shortestHueDelta(target, source);
}

export function drawMediaWithAccentRecolor(ctx, media, x, y, w, h, item, accentColor, kind, assetId) {
  const rotation = getOverlayHueRotation(item, accentColor, kind, assetId);
  ctx.save();
  if (rotation != null) ctx.filter = `hue-rotate(${rotation.toFixed(3)}deg)`;
  ctx.drawImage(media, x, y, w, h);
  ctx.restore();
}
