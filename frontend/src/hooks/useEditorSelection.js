import { useCallback, useMemo, useState } from 'react';
import { resolveSelectedItem } from '../lib/selectionResolver.js';

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
  seekPlayer = () => {},
} = {}) {
  const [selection, setSelection] = useState(null);

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
    if (!sel || !autoSeek) return;

    if (sel.type === 'caption') {
      const cue = resolveSelectedItem(sel, 'caption', cuesList, {
        matches: (item, id) => item._uid === id || item.id === id,
      });
      if (cue && typeof cue.start === 'number') {
        const cueEnd = typeof cue.end === 'number' ? cue.end : cue.start + 2.0;
        if (playhead < cue.start - 0.05 || playhead > cueEnd + 0.05) {
          seekPlayer(cue.start);
        }
      }
    } else if (sel.type === 'clip') {
      const seg = resolveSelectedItem(sel, 'clip', segments, {
        matches: (item, id) => item.clip?.id === id,
      });
      if (seg && typeof seg.segStart === 'number') {
        const segEnd = typeof seg.segEnd === 'number' ? seg.segEnd : seg.segStart + 2.0;
        if (playhead < seg.segStart - 0.05 || playhead > segEnd + 0.05) {
          seekPlayer(seg.segStart);
        }
      }
    } else if (sel.type === 'text_overlay' || sel.type === 'hook') {
      const item = resolveSelectedItem(sel, ['text_overlay', 'hook'], overlays, {
        fallback: sel.type === 'hook' ? hookOverlay : null,
      });
      if (item && typeof item.start === 'number') {
        const itemEnd = typeof item.end === 'number' ? item.end : item.start + 2.0;
        if (playhead < item.start - 0.05 || playhead > itemEnd + 0.05) {
          seekPlayer(item.start);
        }
      }
    }
  }, [cuesList, segments, overlays, hookOverlay, playhead, seekPlayer]);

  const [selectedIds, setSelectedIds] = useState([]);

  const toggleMultiSelect = useCallback((id, type) => {
    setSelectedIds((prev) => {
      const exists = prev.includes(id);
      const next = exists ? prev.filter((x) => x !== id) : [...prev, id];
      if (next.length === 1) {
        setSelection({ type, id: next[0] });
      } else if (next.length === 0) {
        setSelection(null);
      }
      return next;
    });
  }, []);

  const isMultiSelected = useCallback((id) => selectedIds.includes(id), [selectedIds]);

  const clearSelection = useCallback(() => {
    setSelection(null);
    setSelectedIds([]);
  }, []);

  return {
    selection,
    setSelection,
    selectedIds,
    setSelectedIds,
    toggleMultiSelect,
    isMultiSelected,
    handleSelect,
    clearSelection,
    selectedSeg,
    selectedCaption,
    selectedOverlay,
  };
}
