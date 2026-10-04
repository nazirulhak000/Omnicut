/**
 * Multi-selection of timeline clips.
 *
 * The editor keeps ONE primary selection ({type:'clip', id}) -- the clip the
 * Inspector, split, Q/W trim and the context menu act on. Multi-select adds a
 * set of EXTRA clip ids beside it, so every existing consumer of `selection`
 * keeps working unchanged. Delete (and paste-settings) are the only verbs that
 * look at the whole set.
 *
 * State: { primaryId, extraIds, anchorId }. `anchorId` is the clip a Shift+click
 * range grows from (the last plain/Ctrl click), so repeated Shift+clicks pivot
 * on the same clip instead of drifting.
 *
 * Pure and DOM-free so it can be unit tested.
 */

export const EMPTY_CLIP_SELECTION = Object.freeze({ primaryId: null, extraIds: Object.freeze([]), anchorId: null });

/** Plain click, Ctrl/Cmd+click and Shift+click as a selection mode. */
export function clickMode(event) {
  if (!event) return 'replace';
  if (event.ctrlKey || event.metaKey) return 'toggle';
  if (event.shiftKey) return 'range';
  return 'replace';
}

const single = (id) => ({ primaryId: id, extraIds: [], anchorId: id });

/** All selected ids, primary first, without duplicates. */
function members(state) {
  if (!state?.primaryId) return [];
  return [state.primaryId, ...(state.extraIds || []).filter((id) => id !== state.primaryId)]
    .filter((id, i, all) => all.indexOf(id) === i);
}

/**
 * Next selection state after a click on `clickedId`.
 *  - 'replace': that clip alone.
 *  - 'toggle' : add it (becoming primary) or remove it from the set; removing
 *               the primary promotes the most recently added remaining clip.
 *  - 'range'  : every clip from the anchor to it in timeline order; it becomes
 *               primary, the anchor stays put.
 *  - 'focus'  : right-click. A member of the set becomes primary and the set is
 *               kept (so the menu's verbs act on the clip that was clicked);
 *               anything else replaces the selection.
 * `clipOrder` is the clip ids in timeline order.
 */
export function applyClipClick(state, clickedId, mode, clipOrder = []) {
  if (!clickedId) return EMPTY_CLIP_SELECTION;
  const current = members(state);

  if (mode === 'toggle') {
    if (current.includes(clickedId)) {
      const remaining = current.filter((id) => id !== clickedId);
      if (!remaining.length) return EMPTY_CLIP_SELECTION;
      const primaryId = clickedId === state.primaryId ? remaining[remaining.length - 1] : state.primaryId;
      return {
        primaryId,
        extraIds: remaining.filter((id) => id !== primaryId),
        anchorId: primaryId,
      };
    }
    return { primaryId: clickedId, extraIds: current, anchorId: clickedId };
  }

  if (mode === 'range') {
    const anchorId = state?.anchorId && clipOrder.includes(state.anchorId)
      ? state.anchorId
      : (state?.primaryId && clipOrder.includes(state.primaryId) ? state.primaryId : clickedId);
    const a = clipOrder.indexOf(anchorId);
    const b = clipOrder.indexOf(clickedId);
    if (a < 0 || b < 0) return single(clickedId);
    const [from, to] = a <= b ? [a, b] : [b, a];
    const span = clipOrder.slice(from, to + 1);
    return { primaryId: clickedId, extraIds: span.filter((id) => id !== clickedId), anchorId };
  }

  if (mode === 'focus') {
    if (!current.includes(clickedId)) return single(clickedId);
    return {
      primaryId: clickedId,
      extraIds: current.filter((id) => id !== clickedId),
      anchorId: state.anchorId && current.includes(state.anchorId) ? state.anchorId : clickedId,
    };
  }

  return single(clickedId);
}

/**
 * The selected clip ids in timeline order, dropping ids that no longer exist.
 * Returns [] unless `primaryId` is itself selected as the current primary.
 */
export function selectedClipIdsInOrder(state, primaryId, clipOrder = []) {
  if (!primaryId) return [];
  const ids = new Set([primaryId]);
  if (state?.primaryId === primaryId) for (const id of state.extraIds || []) ids.add(id);
  return clipOrder.filter((id) => ids.has(id));
}

/** Clip ids selected besides `primaryId`, in timeline order. */
export function extraClipIds(state, primaryId, clipOrder = []) {
  return selectedClipIdsInOrder(state, primaryId, clipOrder).filter((id) => id !== primaryId);
}

/** Selection state to use as the base of a click when `primaryId` is current. */
export function baseSelectionState(state, primaryId) {
  if (!primaryId) return EMPTY_CLIP_SELECTION;
  if (state?.primaryId === primaryId) return state;
  return single(primaryId);
}
