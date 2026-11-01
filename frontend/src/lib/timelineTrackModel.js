/**
 * Pure math and layout functions for Timeline tracks and interaction.
 */

/** Tick spacing that keeps labels readable at any zoom. */
export function tickStep(pxPerSec) {
  for (const step of [1, 2, 5, 10, 15, 30, 60]) {
    if (step * pxPerSec >= 56) return step;
  }
  return 120;
}

/**
 * Pixel width of one frame (fps frames per second) when the ruler is zoomed in
 * far enough to draw a tick per frame, otherwise null. Below `minPx` per frame
 * the ticks would merge into a solid line, so none are drawn.
 */
export function frameTickSpacing(pxPerSec, fps = 30, minPx = 6) {
  const framePx = pxPerSec / fps;
  return Number.isFinite(framePx) && framePx >= minPx ? framePx : null;
}

/** What a lane chip calls an overlay: its first tier that has words. */
export function overlayLabel(overlay) {
  const tier = (overlay?.tiers || []).find((t) => (t.text || '').trim());
  return (tier?.text || '').trim() || 'ข้อความเสริม';
}

/**
 * Packs timed items into the first lane whose previous item has finished.
 *
 * The timeline has several item kinds with the same interval-packing contract
 * (text overlays, stickers, and effects) but different public result names.
 * Keep the primitive concerned only with start/end and lane assignment so the
 * kind-specific wrappers can preserve their existing APIs.
 */
export function packTimedLanes(items, { epsilon = 0.05 } = {}) {
  if (!items || items.length === 0) {
    return { packedItems: [], laneCount: 0 };
  }

  const sorted = [...items].sort((a, b) => a.start - b.start);
  const laneEndTimes = [];
  const packedItems = sorted.map((item) => {
    let assignedLane = -1;
    for (let i = 0; i < laneEndTimes.length; i++) {
      if (item.start >= laneEndTimes[i] - epsilon) {
        assignedLane = i;
        laneEndTimes[i] = item.end;
        break;
      }
    }
    if (assignedLane === -1) {
      assignedLane = laneEndTimes.length;
      laneEndTimes.push(item.end);
    }
    return { ...item, lane: assignedLane };
  });

  return { packedItems, laneCount: Math.max(1, laneEndTimes.length) };
}

/**
 * Auto-stacking multi-layer calculation for overlapping text overlays.
 * Assigns each overlay to the first available lane that doesn't overlap.
 */
export function packTextOverlays(textOverlays) {
  const { packedItems, laneCount } = packTimedLanes(textOverlays);
  return { packedTextOverlays: packedItems, textLaneCount: laneCount };
}

/**
 * Auto-stacking multi-layer calculation for overlapping stickers.
 * Assigns each sticker to the first available lane that doesn't overlap.
 */
export function packStickers(stickers) {
  const { packedItems, laneCount } = packTimedLanes(stickers);
  return { packedStickers: packedItems, stickerLaneCount: laneCount };
}

/**
 * Computes deterministic magnetic ripple on cues when a cue is trimmed or dragged.
 * Extends -> pushes subsequent cues forward.
 * Shrinks -> magnetically pulls subsequent cues backward without leaving gaps.
 * Cues never overlap and maintain relative order with zero cumulative drift.
 */
export function applyCaptionMagneticRipple(initialCues, targetUid, newStart, newEnd) {
  if (!initialCues || !initialCues.length) return [];
  const list = initialCues.map((c) => ({ ...c }));
  const targetIdx = list.findIndex((c) => c._uid === targetUid || c.id === targetUid);
  if (targetIdx === -1) return list;

  const validStart = Math.max(0, Math.round(newStart * 100) / 100);
  const validEnd = Math.max(validStart + 0.2, Math.round(newEnd * 100) / 100);

  const initTarget = initialCues[targetIdx];
  list[targetIdx] = {
    ...list[targetIdx],
    start: validStart,
    end: validEnd,
  };

  const deltaEnd = Math.round((validEnd - initTarget.end) * 100) / 100;
  const deltaStart = Math.round((validStart - initTarget.start) * 100) / 100;
  const shiftDelta = Math.abs(deltaEnd) > 0.001 ? deltaEnd : deltaStart;

  for (let i = targetIdx + 1; i < list.length; i++) {
    const prevCue = list[i - 1];
    const initCur = initialCues[i];
    const curDur = Math.max(0.2, Math.round((initCur.end - initCur.start) * 100) / 100);

    const wantedStart = Math.round((initCur.start + shiftDelta) * 100) / 100;
    const shiftedStart = Math.max(prevCue.end, wantedStart);
    const shiftedEnd = Math.round((shiftedStart + curDur) * 100) / 100;

    list[i] = {
      ...list[i],
      start: shiftedStart,
      end: shiftedEnd,
    };
  }

  return list;
}

/**
 * Computes the insert index of a dropped clip based on pointer x position.
 */
export function indexFromX(clientX, laneRect, pxPerSec, segments = []) {
  if (!laneRect) return segments.length;
  const t = (clientX - laneRect.left) / pxPerSec;
  let i = 0;
  while (i < segments.length && t > (segments[i].segStart + segments[i].segEnd) / 2) i += 1;
  return i;
}

/**
 * Calculates timeline time in seconds from a pointer event.
 */
export function timeFromEvent(clientX, laneRect, pxPerSec, maxDuration = 0) {
  if (!laneRect) return 0;
  const rawT = (clientX - laneRect.left) / pxPerSec;
  return Math.max(0, maxDuration > 0 ? Math.min(maxDuration, rawT) : rawT);
}

/**
 * Links an audio stem or track to a video clip so they move synchronously.
 */
export function linkClipAudio(clip, audioTrackId = 'track-a1') {
  if (!clip) return null;
  return {
    ...clip,
    audio_linked: true,
    linked_audio_track: audioTrackId,
  };
}

/**
 * Unlinks an audio stem or track from a video clip.
 */
export function unlinkClipAudio(clip) {
  if (!clip) return null;
  const copy = { ...clip, audio_linked: false };
  delete copy.linked_audio_track;
  return copy;
}

/**
 * Computes deterministic ripple position shift for clips on the same track.
 */
export function computeRippleClipMove(clips = [], movedClipId, newStart) {
  if (!clips.length) return [];
  const list = clips.map((c) => ({ ...c }));
  const idx = list.findIndex((c) => c.id === movedClipId);
  if (idx === -1) return list;

  const validStart = Math.max(0, Math.round(newStart * 100) / 100);
  const oldStart = list[idx].start ?? 0;
  const delta = Math.round((validStart - oldStart) * 100) / 100;
  list[idx].start = validStart;

  for (let i = idx + 1; i < list.length; i++) {
    if (list[i].track_id === list[idx].track_id) {
      list[i].start = Math.max(
        (list[i - 1].start ?? 0) + (list[i - 1].duration ?? 0),
        Math.round(((list[i].start ?? 0) + delta) * 100) / 100
      );
    }
  }
  return list;
}


/**
 * CapCut 7.1 Linkage Types (globalSetting E11):
 * linkageEnableTypes = text, effect, sticker, filter, adjust, sound, tts
 */
export const LINKAGE_ENABLE_TYPES = Object.freeze([
  'text',
  'effect',
  'sticker',
  'filter',
  'adjust',
  'sound',
  'tts',
]);

export function isLinkageType(type) {
  if (!type || typeof type !== 'string') return false;
  const normalized = type.toLowerCase().trim();
  return LINKAGE_ENABLE_TYPES.includes(normalized);
}

/**
 * Finds all timed items (cues, overlays, stickers, effects) overlapping a time window [start, end].
 */
export function findOverlappingItems(items = [], start = 0, end = 0, { epsilon = 0.001 } = {}) {
  if (!Array.isArray(items) || end <= start) return [];
  return items.filter((item) => {
    const iStart = Number(item.start ?? item.time ?? 0);
    const iEnd = Number(item.end ?? (iStart + (item.duration ?? 0)));
    return Math.max(start, iStart) < Math.min(end, iEnd) - epsilon;
  });
}

/**
 * Shifts linked items by deltaSec if trackLinkageEnabled is active.
 */
export function shiftLinkedItems(items = [], linkedIds = new Set(), deltaSec = 0) {
  if (!Array.isArray(items) || !linkedIds.size || Math.abs(deltaSec) < 0.0001) {
    return items;
  }
  return items.map((item) => {
    const id = item.id;
    if (!linkedIds.has(id)) return item;
    const iStart = Number(item.start ?? 0);
    const iEnd = Number(item.end ?? (iStart + (item.duration ?? 0)));
    const nextStart = Math.max(0, Math.round((iStart + deltaSec) * 1000) / 1000);
    const nextEnd = Math.max(nextStart + 0.1, Math.round((iEnd + deltaSec) * 1000) / 1000);
    return {
      ...item,
      start: nextStart,
      end: nextEnd,
    };
  });
}

/**
 * Compound Sub-Tracks / Grouping (CapCut 7.1 Ctrl+G / Ctrl+Shift+G, E13).
 */
export function groupTimelineItems(items = [], selectedIds = [], existingGroupId = null) {
  if (!Array.isArray(items) || !Array.isArray(selectedIds) || selectedIds.length < 2) {
    return items;
  }
  const idSet = new Set(selectedIds);
  const groupId = existingGroupId || `group_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  return items.map((item) => {
    if (!idSet.has(item.id)) return item;
    return { ...item, groupId };
  });
}

export function ungroupTimelineItems(items = [], targetGroupIdOrItemId) {
  if (!Array.isArray(items) || !targetGroupIdOrItemId) return items;
  let effectiveGroupId = targetGroupIdOrItemId;
  const itemWithId = items.find((i) => i.id === targetGroupIdOrItemId);
  if (itemWithId && itemWithId.groupId) {
    effectiveGroupId = itemWithId.groupId;
  }
  return items.map((item) => {
    if (item.groupId !== effectiveGroupId) return item;
    const copy = { ...item };
    delete copy.groupId;
    return copy;
  });
}

export function findGroupMembers(items = [], groupId) {
  if (!Array.isArray(items) || !groupId) return [];
  return items.filter((item) => item.groupId === groupId);
}
