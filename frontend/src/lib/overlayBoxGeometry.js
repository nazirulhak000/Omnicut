export function resolveSelectedBox({
  selection,
  bounds,
  cues,
  captionStyle,
  overlays,
  effectiveStickersList,
  stickerStyle,
  isStickerHidden,
  effects,
  stickerImages,
  canvasWidth,
  canvasHeight,
  captionY,
  textPositions,
  resolveLook,
  anchorTop,
}) {
  if (!selection) return null;
  const fromBounds = (bounds || []).find((b) => b.type === selection.type && b.id === selection.id);
  if (fromBounds) return fromBounds;

  if (selection.type === 'caption') {
    const cue = (cues || []).find((c) => c._uid === selection.id || c.id === selection.id);
    if (cue) {
      const normX = typeof cue.x === 'number' ? cue.x : 0.5;
      const pos = cue.position || captionStyle.captionPosition || 'bottom';
      const normY = typeof cue.y === 'number' ? cue.y : (captionY[pos] ?? captionY.bottom);
      const scale = Number(cue.scale) || 1.0;
      const estW = Math.min(canvasWidth * 0.85, Math.max(120, (cue.text?.length || 10) * 20 * scale));
      const estH = Math.max(48, 52 * scale);
      return {
        type: 'caption',
        id: cue._uid || cue.id,
        x: canvasWidth * normX - estW / 2,
        y: canvasHeight * normY - estH / 2,
        w: estW,
        h: estH,
        normX,
        normY,
        scale,
        label: (cue.text || 'คำบรรยาย').slice(0, 15),
        cue,
      };
    }
  }

  if (selection.type === 'text_overlay' || selection.type === 'hook') {
    const item = (overlays || []).find((o) => o.id === selection.id)
      || (selection.type === 'hook' ? (overlays || []).find((o) => o.kind === 'hook') : null);
    if (item) {
      const look = resolveLook(item.look, null);
      const firstText = String((item.tiers || [{}])[0].text || '');
      const normX = typeof item.x === 'number' ? item.x : 0.5;
      const normY = typeof item.y === 'number'
        ? item.y
        : (textPositions[item.position || 'middle'] ?? 0.5);
      const sizeScale = (look.size_pct || 100) / 100;
      const estimatedW = Math.max(140, Math.min(canvasWidth * 0.85, (firstText.length || 8) * 22 * sizeScale));
      const estimatedH = Math.max(48, 52 * sizeScale * (item.tiers || []).length);
      const anchoredTop = item.anchor === anchorTop;
      return {
        type: selection.type,
        id: item.id,
        x: canvasWidth * normX - estimatedW / 2,
        y: anchoredTop ? canvasHeight * normY : canvasHeight * normY - estimatedH / 2,
        w: estimatedW,
        h: estimatedH,
        normX,
        normY,
        sizePct: look.size_pct,
        label: (firstText || 'ข้อความ').slice(0, 15),
        item,
      };
    }
  }

  if (selection.type === 'sticker') {
    if (isStickerHidden) return null;
    // Do NOT fall back to index 0 when the selected id has no match (e.g. the
    // selected sticker was just deleted) -- that silently substitutes a different
    // sticker as "selected", so a drag/resize would move the wrong item.
    const matchedSticker = (effectiveStickersList || []).find((s) => s.id === selection.id);
    if (!matchedSticker) return null;
    const scale = Math.min(3.5, Math.max(0.3, matchedSticker?.scale ?? stickerStyle?.scale ?? 1));
    const baseWidth = 160;
    const width = Math.round(baseWidth * scale);
    const badgeKey = matchedSticker?.badge;
    const image = badgeKey
      ? (stickerImages?.get?.(badgeKey) || stickerImages?.get?.(badgeKey.toLowerCase()))
      : null;
    const aspect = (image && image.naturalWidth) ? (image.naturalHeight / image.naturalWidth) : 1.0;
    const height = Math.round(width * aspect);
    const normX = typeof matchedSticker?.normX === 'number'
      ? matchedSticker.normX
      : (typeof stickerStyle?.normX === 'number' ? stickerStyle.normX : 0.5);
    const normY = typeof matchedSticker?.normY === 'number'
      ? matchedSticker.normY
      : (typeof stickerStyle?.normY === 'number' ? stickerStyle.normY : 0.35);
    return {
      type: 'sticker',
      id: matchedSticker?.id || 'sticker_badge',
      x: Math.round(canvasWidth * normX - width / 2),
      y: Math.round(canvasHeight * normY - height / 2),
      w: width,
      h: height,
      normX,
      normY,
      scale,
      label: matchedSticker?.badge?.replace(/\.[^.]+$/, '') || 'สติกเกอร์ 3D',
      item: matchedSticker,
    };
  }

  if (selection.type === 'effect') {
    const matchedEffect = (effects || []).find((effect) => effect.id === selection.id);
    if (!matchedEffect) return null;
    const scale = Math.min(3.5, Math.max(0.3, matchedEffect.scale ?? 1));
    const baseSize = 180;
    const size = Math.round(baseSize * scale);
    const normX = typeof matchedEffect.normX === 'number' ? matchedEffect.normX : 0.5;
    const normY = typeof matchedEffect.normY === 'number' ? matchedEffect.normY : 0.35;
    return {
      type: 'effect',
      id: matchedEffect.id,
      x: Math.round(canvasWidth * normX - size / 2),
      y: Math.round(canvasHeight * normY - size / 2),
      w: size,
      h: size,
      normX,
      normY,
      scale,
      label: matchedEffect.effectId || 'เอฟเฟกต์',
      item: matchedEffect,
    };
  }
  return null;
}

export function snapNormalizedPoint(x, y, { min = 0.05, max = 0.95, yGuides = [0.5, 0.2, 0.72] } = {}) {
  let nextX = Math.max(min, Math.min(max, x));
  let nextY = Math.max(min, Math.min(max, y));
  let snapX = null;
  let snapY = null;

  if (Math.abs(nextX - 0.5) < 0.025) {
    nextX = 0.5;
    snapX = 0.5;
  }
  for (const guide of yGuides) {
    if (Math.abs(nextY - guide) < 0.025) {
      nextY = guide;
      snapY = guide;
      break;
    }
  }
  return { x: nextX, y: nextY, snapX, snapY };
}

export function roundNormalizedPoint(x, y) {
  return {
    x: Math.round(x * 1000) / 1000,
    y: Math.round(y * 1000) / 1000,
  };
}

export function resizeScaleLimits(type) {
  const wideRange = type === 'sticker' || type === 'effect';
  return wideRange ? { min: 0.3, max: 3.5 } : { min: 0.4, max: 2.5 };
}

export function projectOverlayScale(initialScale, projectedDelta, initialDistance, type) {
  const { min, max } = resizeScaleLimits(type);
  const scaleFactor = 1 + projectedDelta / initialDistance;
  return Math.max(min, Math.min(max, Math.round(initialScale * scaleFactor * 100) / 100));
}

export function positionPatchForBox(type, x, y) {
  if (type === 'sticker' || type === 'effect') {
    return { normX: x, normY: y };
  }
  return { x, y };
}

export function scalePatchForBox(type, scale, look = {}) {
  if (type === 'text_overlay' || type === 'hook') {
    return { look: { ...look, size_pct: Math.round(scale * 100) } };
  }
  return { scale };
}
