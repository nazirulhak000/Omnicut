import { useRef, useCallback, useMemo, useState } from 'react';
import { resolveSelectedItem } from '../lib/selectionResolver.js';
import {
  EMPTY_CLIP_SELECTION,
  applyClipClick,
  baseSelectionState,
  extraClipIds,
  selectedClipIdsInOrder,
} from '../lib/clipMultiSelect.js';

/**
 * Hook to manage item selection (clip, caption, overlay/hook)
 * and synchronize playhead seeking to the selected item.
 */
export function useEditorSelection({
  segments = [],
  cuesList = [],
  overlays = [],
  hookOverlay = null,
  playhead = 0,
  // Returns the playhead "now". The editor passes it so the handlers below do
  // not depend on a `playhead` value that only changes when playback settles.
  getPlayhead = null,
  seekPlayer = () => {},
} = {}) {
  // Event-time read of the playhead (see getPlayhead above).
  const playheadFallbackRef = useRef(playhead);
  playheadFallbackRef.current = playhead;
  const readPlayhead = useCallback(
    () => (getPlayhead ? getPlayhead() : playheadFallbackRef.current),
    [getPlayhead],
  );
  const [selection, setSelection] = useState(null);
  // Extra clips selected beside the primary `selection` (Ctrl/Shift+click).
  // Only meaningful while `selection` is still the clip it was built around.
  const [clipMulti, setClipMulti] = useState(EMPTY_CLIP_SELECTION);
  const clipOrder = useMemo(() => segments.map((seg) => seg.clip?.id).filter(Boolean), [segments]);
  const primaryClipId = selection?.type === 'clip' ? selection.id : null;
  // Timeline order, primary included; [] when no clip is the primary.
  const selectedClipIds = useMemo(
    () => selectedClipIdsInOrder(clipMulti, primaryClipId, clipOrder),
    [clipMulti, primaryClipId, clipOrder]
  );
  const extraSelectedClipIds = useMemo(
    () => extraClipIds(clipMulti, primaryClipId, clipOrder),
    [clipMulti, primaryClipId, clipOrder]
  );

  const selectedSeg = useMemo(
    () => resolveSelectedItem(selection, 'clip', segments, {
      matches: (segment, id) => segment.clip?.id === id,
    }),
    [selection, segments]
  );

  const selectedCaption = useMemo(
    () => resolveSelectedItem(selection, 'caption', cuesList, {
      matches: (cue, id) => cue._uid === id || cue.id === id,
    }),
    [selection, cuesList]
  );

  const selectedOverlay = useMemo(
    () => resolveSelectedItem(selection, ['text_overlay', 'hook'], overlays, {
      fallback: selection?.type === 'hook' ? hookOverlay : null,
    }),
    [selection, overlays, hookOverlay]
  );

  const handleSelect = useCallback((sel, autoSeek = true) => {
    setSelection(sel);
    // Any plain selection drops the extra clips; Ctrl/Shift+click goes through
    // selectClipWithMode below instead.
    setClipMulti(sel?.type === 'clip' && sel.id ? applyClipClick(EMPTY_CLIP_SELECTION, sel.id, 'replace') : EMPTY_CLIP_SELECTION);
    if (!sel || !autoSeek) return;

    if (sel.type === 'caption') {
      const cue = resolveSelectedItem(sel, 'caption', cuesList, {
        matches: (item, id) => item._uid === id || item.id === id,
      });
      if (cue && typeof cue.start === 'number') {
        const cueEnd = typeof cue.end === 'number' ? cue.end : cue.start + 2.0;
        if (readPlayhead() < cue.start - 0.05 || readPlayhead() > cueEnd + 0.05) {
          seekPlayer(cue.start);
        }
      }
    } else if (sel.type === 'clip') {
      const seg = resolveSelectedItem(sel, 'clip', segments, {
        matches: (item, id) => item.clip?.id === id,
      });
      if (seg && typeof seg.segStart === 'number') {
        const segEnd = typeof seg.segEnd === 'number' ? seg.segEnd : seg.segStart + 2.0;
        if (readPlayhead() < seg.segStart - 0.05 || readPlayhead() > segEnd + 0.05) {
          seekPlayer(seg.segStart);
        }
      }
    } else if (sel.type === 'text_overlay' || sel.type === 'hook') {
      const item = resolveSelectedItem(sel, ['text_overlay', 'hook'], overlays, {
        fallback: sel.type === 'hook' ? hookOverlay : null,
      });
      if (item && typeof item.start === 'number') {
        const itemEnd = typeof item.end === 'number' ? item.end : item.start + 2.0;
        if (readPlayhead() < item.start - 0.05 || readPlayhead() > itemEnd + 0.05) {
          seekPlayer(item.start);
        }
      }
    }
  }, [cuesList, segments, overlays, hookOverlay, readPlayhead, seekPlayer]);

  // Ctrl/Cmd+click ('toggle'), Shift+click ('range') and right-click ('focus')
  // on a clip. The clicked clip becomes the primary selection (the Inspector,
  // split and Q/W act on it); the rest of the set rides along in `clipMulti`.
  const selectClipWithMode = useCallback((id, mode) => {
    const next = applyClipClick(baseSelectionState(clipMulti, primaryClipId), id, mode, clipOrder);
    setClipMulti(next);
    setSelection(next.primaryId ? { type: 'clip', id: next.primaryId } : null);
    if (next.primaryId && next.primaryId === id) {
      const seg = segments.find((item) => item.clip?.id === id);
      if (seg && typeof seg.segStart === 'number') {
        const segEnd = typeof seg.segEnd === 'number' ? seg.segEnd : seg.segStart + 2.0;
        if (readPlayhead() < seg.segStart - 0.05 || readPlayhead() > segEnd + 0.05) seekPlayer(seg.segStart);
      }
    }
  }, [clipMulti, primaryClipId, clipOrder, segments, readPlayhead, seekPlayer]);

  const clearSelection = useCallback(() => {
    setSelection(null);
    setClipMulti(EMPTY_CLIP_SELECTION);
  }, []);

  return {
    selection,
    setSelection,
    selectedClipIds,
    extraSelectedClipIds,
    selectClipWithMode,
    handleSelect,
    clearSelection,
    selectedSeg,
    selectedCaption,
    selectedOverlay,
  };
}
