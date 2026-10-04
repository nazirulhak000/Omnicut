import { useCallback, useState } from 'react';
import { FADE_DURATION, resolveSplitTarget, splitClipAt } from '../lib/timelineMath.js';
import { resolveTrimHead, resolveTrimTail } from '../lib/timelineTrimOps.js';
import { copyClipSettings, pasteClipSettingsInState, pasteClipSettingsToClips } from '../lib/clipSettingsClipboard.js';
import { removeItemById } from '../lib/collectionOperations.js';
import {
  applyRipplePlan,
  defaultRippleScope as defaultRippleScopeFor,
  planRippleRanges,
} from '../lib/rippleRange.js';
import { patchAllClipsInState, patchClipInState } from '../lib/inspectorModel.js';
import {
  captionPatchHistoryOptions,
  mergeCueReveals,
  reconcileCueReveal,
  reconcileCuesReveal,
  splitCueReveal,
  withReveal,
} from '../lib/captionEdits.js';

/**
 * Hook providing all timeline manipulation commands (Clips & Captions).
 */
export function useEditorCommands({
  set,
  setSilent = set,
  newId = () => `clip-${Date.now().toString(36)}`,
  durations = {},
  playhead = 0,
  segments = [],
  selectedSeg = null,
  selection = null,
  setSelection = () => {},
  // Every clip selected with Ctrl/Shift+click (primary included, timeline order).
  // Only Delete looks at the whole set; split/trim/Q/W act on the primary.
  selectedClipIds = [],
  cuesDirtyRef = { current: false },
  handleDeleteOverlay = () => {},
  onImportSuccess,
  onNotify,
  onSeek,
  // Ripple delete: the history state (for the dry-run plan), whether the
  // project has a voiceover, and the voice length as it is on the timeline now.
  editorState = null,
  hasVoice = false,
  audioDuration = 0,
}) {
  const markCuesDirty = useCallback(() => {
    if (cuesDirtyRef) cuesDirtyRef.current = true;
  }, [cuesDirtyRef]);

  // ──────────────── Clip Commands ────────────────

  const addClip = useCallback((video, insertAt = null) => {
    const rawDur = video.duration || durations[video.path] || 10;
    const dur = Math.min(rawDur, 12);
    set((prev) => {
      const clip = {
        id: newId(),
        source_path: video.path,
        trim_start: 0,
        trim_end: dur,
        duration: dur,
        speed: 1,
        transition_in: 'cut',
        transition_duration: FADE_DURATION,
        track_id: 'video-1',
        keyframes: [],
      };
      if (insertAt === null || insertAt === undefined) {
        return { ...prev, clipList: [...prev.clipList, clip] };
      }
      const next = [...prev.clipList];
      next.splice(insertAt, 0, clip);
      return { ...prev, clipList: next };
    });
  }, [durations, newId, set]);

  // `options.coalesceKey` lets a slider burst share one undo step (see
  // useEditorHistory). Silent patches are mid-gesture and never get a step.
  const patchClip = useCallback((clipId, patch, silent = false, options = undefined) => {
    const updater = (prev) => patchClipInState(prev, clipId, patch);
    if (silent) setSilent(updater);
    else set(updater, options);
  }, [set, setSilent]);

  // One look applied to every clip in a single set(): one Ctrl+Z undoes it all.
  // Only the whitelisted look fields are copied (never keyframes/trim/source),
  // and a call that changes nothing leaves the history alone.
  const patchAllClips = useCallback((patch) => {
    set((prev) => patchAllClipsInState(prev, patch));
  }, [set]);

  const reorderClip = useCallback((id, direction, silent = false) => {
    (silent ? setSilent : set)((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === id);
      const target = idx + direction;
      if (idx === -1 || target < 0 || target >= prev.clipList.length) return prev;
      const next = [...prev.clipList];
      [next[idx], next[target]] = [next[target], next[idx]];
      return { ...prev, clipList: next };
    });
  }, [set, setSilent]);

  const splitAtPlayhead = useCallback(() => {
    // Same resolver the toolbar's Split button uses for `canSplit`. The cut
    // time is the frame-snapped playhead; a refusal always says why instead of
    // doing nothing.
    const target = resolveSplitTarget(segments, selectedSeg, playhead);
    if (!target.seg) {
      onNotify?.(target.message);
      return;
    }
    const seg = target.seg;
    const pieces = splitClipAt(seg, target.time, newId);
    if (!pieces) {
      onNotify?.('แยกคลิปตรงนี้ไม่ได้');
      return;
    }
    const [left, right] = pieces;
    set((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === seg.clip.id);
      if (idx === -1) return prev;
      const next = [...prev.clipList];
      next.splice(idx, 1, left, right);
      return { ...prev, clipList: next };
    });
    setSelection({ type: 'clip', id: right.id });
  }, [newId, onNotify, playhead, segments, selectedSeg, set, setSelection]);

  // Q / W: cut the clip's head or tail off at the frame-snapped playhead. One
  // set() call = one undo step; a refusal says why (like splitAtPlayhead).
  // A head trim slides the kept part back to the clip's own start, so the
  // playhead follows it and the preview keeps showing the frame it was on.
  const trimEdgeAtPlayhead = useCallback((edge) => {
    const target = (edge === 'tail' ? resolveTrimTail : resolveTrimHead)(segments, selectedSeg, playhead);
    if (!target.seg) {
      onNotify?.(target.message);
      return;
    }
    const clipId = target.seg.clip.id;
    set((prev) => patchClipInState(prev, clipId, target.patch));
    setSelection({ type: 'clip', id: clipId });
    if (target.seekTo !== null && target.seekTo !== undefined) onSeek?.(target.seekTo);
  }, [onNotify, onSeek, playhead, segments, selectedSeg, set, setSelection]);
  const trimHeadAtPlayhead = useCallback(() => trimEdgeAtPlayhead('head'), [trimEdgeAtPlayhead]);
  const trimTailAtPlayhead = useCallback(() => trimEdgeAtPlayhead('tail'), [trimEdgeAtPlayhead]);

  const duplicateSelected = useCallback(() => {
    if (!selectedSeg) return;
    const orig = selectedSeg.clip;
    const dup = { ...orig, id: newId(), transition_in: 'cut' };
    set((prev) => {
      const idx = prev.clipList.findIndex((c) => c.id === orig.id);
      if (idx === -1) return prev;
      const next = [...prev.clipList];
      next.splice(idx + 1, 0, dup);
      return { ...prev, clipList: next };
    });
    setSelection({ type: 'clip', id: dup.id });
  }, [newId, selectedSeg, set, setSelection]);

  // Copy / paste of clip settings (speed, zoom/pan + camera keyframes, colour,
  // incoming transition). The copy lives for this editing session only; paste
  // goes to every selected clip in ONE set() = one undo step.
  const [copiedClipSettings, setCopiedClipSettings] = useState(null);

  const copyClipSettingsFromPrimary = useCallback(() => {
    if (!selectedSeg) {
      onNotify?.('เลือกคลิปที่จะคัดลอกการตั้งค่าก่อน');
      return;
    }
    setCopiedClipSettings(copyClipSettings(selectedSeg.clip, selectedSeg.srcDur));
    onNotify?.('คัดลอกการตั้งค่าคลิปแล้ว (ความเร็ว ซูม/แพน สี ทรานซิชัน)');
  }, [onNotify, selectedSeg]);

  const pasteClipSettingsToSelected = useCallback(() => {
    if (!copiedClipSettings) {
      onNotify?.('ยังไม่ได้คัดลอกการตั้งค่าคลิป');
      return;
    }
    const targetIds = selectedClipIds.length ? selectedClipIds : (selectedSeg ? [selectedSeg.clip.id] : []);
    if (!targetIds.length) {
      onNotify?.('เลือกคลิปที่จะวางการตั้งค่าก่อน');
      return;
    }
    const sourceDurations = Object.fromEntries(segments.map((seg) => [seg.clip.id, seg.srcDur]));
    const { changed } = pasteClipSettingsToClips(
      segments.map((seg) => seg.clip), copiedClipSettings, targetIds, sourceDurations,
    );
    if (!changed) {
      onNotify?.('คลิปที่เลือกมีการตั้งค่าตรงกับที่คัดลอกไว้อยู่แล้ว');
      return;
    }
    set((prev) => pasteClipSettingsInState(prev, copiedClipSettings, targetIds, sourceDurations));
    onNotify?.(`วางการตั้งค่าลง ${changed} คลิปแล้ว`);
  }, [copiedClipSettings, onNotify, segments, selectedClipIds, selectedSeg, set]);

  const deleteSelected = useCallback(() => {
    if (selection?.type === 'clip') {
      // The whole multi-selection goes in ONE set(): one Ctrl+Z brings it back.
      const doomed = new Set(selectedClipIds.length > 1 ? selectedClipIds : [selection.id]);
      set((prev) => ({ ...prev, clipList: prev.clipList.filter((c) => !doomed.has(c.id)) }));
      setSelection(null);
    } else if (selection?.type === 'caption') {
      markCuesDirty();
      set((prev) => ({ ...prev, cuesList: prev.cuesList.filter((c) => c._uid !== selection.id) }));
      setSelection(null);
    } else if (selection?.type === 'text_overlay' || selection?.type === 'hook') {
      handleDeleteOverlay(selection.id);
    } else if (selection?.type === 'sticker') {
      set((prev) => {
        const nextStickers = removeItemById(prev.stickers, selection.id);
        return {
          ...prev,
          stickers: nextStickers,
          // Without this, the legacy mirror field outlives the sticker it
          // came from: Timeline.jsx's effectiveStickers (and the matching
          // fallback in overlayBoxGeometry.js) synthesize a fake sticker
          // straight back out of style.stickerBadge whenever the real
          // array is empty but this field is still set -- so a delete via
          // this path silently "undid itself" on the very next render,
          // while EditorShell.jsx's handleDeleteSticker (the Inspector's
          // own delete button) already cleared it correctly. Confirmed via
          // live debugging: prev.stickers filtered to [] correctly, but
          // the sticker reappeared because this field was never cleared.
          style: {
            ...prev.style,
            stickerBadge: nextStickers.length > 0 ? nextStickers[0].badge : '',
          },
        };
      });
      setSelection(null);
    } else if (selection?.type === 'effect') {
      set((prev) => ({
        ...prev,
        effects: removeItemById(prev.effects, selection.id),
      }));
      setSelection(null);
    }
  }, [handleDeleteOverlay, markCuesDirty, selectedClipIds, selection, set, setSelection]);

  // ──────────────── Ripple Delete (rippleRange.js) ────────────────
  // Not bound to any key or button yet. One ripple = ONE set(): clips, captions,
  // overlays, stickers, effects and the voice cuts change together, so one
  // Ctrl+Z puts everything back.

  /** Voiceover present -> 'all' (picture + voice + captions), otherwise 'video'. */
  const defaultRippleScope = useCallback(
    (voicePresent = hasVoice) => defaultRippleScopeFor(voicePresent),
    [hasVoice],
  );

  const rippleOptions = useCallback((scope, extra) => ({
    scope: scope || defaultRippleScopeFor(hasVoice),
    durations,
    hasVoice,
    audioDuration,
    newId,
    ...(extra || {}),
  }), [audioDuration, durations, hasVoice, newId]);

  // Dry run for the confirm dialog. Returns the plan (see planRippleRanges;
  // `describeRipplePlan(plan)` gives the Thai text) and changes nothing.
  const planRipple = useCallback((ranges, scope, extra) => (
    planRippleRanges(editorState || {}, ranges, rippleOptions(scope, extra))
  ), [editorState, rippleOptions]);

  // Apply `ranges` (program seconds) now. The plan is made again against the
  // newest state inside the updater, so a stale dialog can never apply old numbers.
  // Returns the plan; `plan.blocked` (Thai) says why nothing happened.
  const rippleRanges = useCallback((ranges, scope, extra) => {
    let applied = null;
    set((prev) => {
      applied = planRippleRanges(prev, ranges, rippleOptions(scope, extra));
      return applied.changed && !applied.blocked ? applyRipplePlan(prev, applied) : prev;
    });
    const plan = applied
      || (editorState ? planRippleRanges(editorState, ranges, rippleOptions(scope, extra)) : null);
    if (!plan) return null;
    if (plan.blocked || !plan.changed) {
      if (plan.blocked) onNotify?.(plan.blocked);
      return plan;
    }
    const { summary } = plan;
    if (summary.cues.removed || summary.cues.retimed || summary.microCues.removed || summary.microCues.retimed) {
      markCuesDirty();
    }
    setSelection(null);
    onSeek?.(plan.playhead);
    return plan;
  }, [editorState, markCuesDirty, onNotify, onSeek, rippleOptions, set, setSelection]);

  const rippleDeleteRange = useCallback(
    ({ t0, t1, scope } = {}, extra) => rippleRanges([{ start: t0, end: t1 }], scope, extra),
    [rippleRanges],
  );

  // ──────────────── Caption Commands ────────────────

  const addTextAtPlayhead = useCallback(() => {
    const curTime = Number(playhead.toFixed(2));
    const dur = 2.5;
    const newCue = {
      start: curTime,
      end: Number((curTime + dur).toFixed(2)),
      text: 'ข้อความใหม่',
      translation: 'New text',
      scale: 1.0,
      _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    };
    set((prev) => {
      const next = [...prev.cuesList, newCue].sort((a, b) => a.start - b.start);
      return { ...prev, cuesList: next };
    });
    setSelection({ type: 'caption', id: newCue._uid });
    markCuesDirty();
  }, [markCuesDirty, playhead, set, setSelection]);

  // Typing one caption field coalesces into one undo step (L3-10); a text or
  // time change keeps the cue's word_reveal track in step (L3-02).
  const patchCaption = useCallback((cueUid, patch, silent = false, options = undefined) => {
    markCuesDirty();
    const updater = (prev) => {
      const nextList = prev.cuesList.map((c) => ((c._uid === cueUid || c.id === cueUid)
        ? reconcileCueReveal(c, { ...c, ...patch })
        : c));
      const sorted = (!silent && ('start' in patch || 'end' in patch))
        ? [...nextList].sort((a, b) => a.start - b.start)
        : nextList;
      return { ...prev, cuesList: sorted };
    };
    if (silent) setSilent(updater);
    else set(updater, captionPatchHistoryOptions(cueUid, patch, options));
  }, [markCuesDirty, set, setSilent]);

  const patchAllCaptions = useCallback((patch, silent = false, options = undefined) => {
    markCuesDirty();
    (silent ? setSilent : set)((prev) => ({
      ...prev,
      cuesList: prev.cuesList.map((c) => ({ ...c, ...patch })),
    }), options);
  }, [markCuesDirty, set, setSilent]);

  const handleUpdateCuesList = useCallback((newCues, silent = false) => {
    markCuesDirty();
    (silent ? setSilent : set)((prev) => ({ ...prev, cuesList: reconcileCuesReveal(prev.cuesList, newCues) }));
  }, [markCuesDirty, set, setSilent]);

  const handleSplitCue = useCallback((cueUid, cursorIndex) => {
    set((prev) => {
      const idx = prev.cuesList.findIndex((c) => c._uid === cueUid);
      if (idx === -1) return prev;
      const target = prev.cuesList[idx];
      const fullText = target.text || '';
      const splitIdx = Math.max(1, Math.min(fullText.length - 1, cursorIndex || Math.floor(fullText.length / 2)));

      const text1 = fullText.slice(0, splitIdx).trim();
      const text2 = fullText.slice(splitIdx).trim();

      const ratio = text1.length / (text1.length + text2.length || 1);
      const dur = target.end - target.start;
      const splitTime = Number((target.start + dur * ratio).toFixed(2));

      const fullTrans = (target.translation || '').trim();
      let trans1 = fullTrans;
      let trans2 = '';
      if (fullTrans) {
        const words = fullTrans.split(/\s+/);
        if (words.length > 1) {
          const splitWordIdx = Math.max(1, Math.min(words.length - 1, Math.round(words.length * ratio)));
          trans1 = words.slice(0, splitWordIdx).join(' ');
          trans2 = words.slice(splitWordIdx).join(' ');
        }
      }

      // Each half carries only its own words (L3-02), never the whole sentence.
      const [reveal1, reveal2] = splitCueReveal(target, text1, text2, splitTime);
      const cue1 = withReveal({ ...target, end: splitTime, text: text1, translation: trans1 }, reveal1);
      const cue2 = withReveal({
        ...target,
        start: splitTime,
        text: text2,
        translation: trans2,
        _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
      }, reveal2);

      const next = [...prev.cuesList];
      next.splice(idx, 1, cue1, cue2);
      markCuesDirty();
      return { ...prev, cuesList: next };
    });
  }, [markCuesDirty, set]);

  const handleSplitCueAtPlayhead = useCallback((cueUid, playheadTime) => {
    set((prev) => {
      const idx = prev.cuesList.findIndex((c) => c._uid === cueUid);
      if (idx === -1) return prev;
      const target = prev.cuesList[idx];
      if (playheadTime <= target.start + 0.1 || playheadTime >= target.end - 0.1) return prev;

      const fullText = target.text || '';
      const timeRatio = (playheadTime - target.start) / (target.end - target.start);
      const splitCharIdx = Math.round(fullText.length * timeRatio);

      const text1 = fullText.slice(0, splitCharIdx).trim() || fullText.slice(0, Math.floor(fullText.length / 2)).trim();
      const text2 = fullText.slice(splitCharIdx).trim() || fullText.slice(Math.floor(fullText.length / 2)).trim();

      const fullTrans = (target.translation || '').trim();
      let trans1 = fullTrans;
      let trans2 = '';
      if (fullTrans) {
        const words = fullTrans.split(/\s+/);
        if (words.length > 1) {
          const splitWordIdx = Math.max(1, Math.min(words.length - 1, Math.round(words.length * timeRatio)));
          trans1 = words.slice(0, splitWordIdx).join(' ');
          trans2 = words.slice(splitWordIdx).join(' ');
        }
      }

      const cutTime = Number(playheadTime.toFixed(2));
      const [reveal1, reveal2] = splitCueReveal(target, text1, text2, cutTime);
      const cue1 = withReveal({ ...target, end: cutTime, text: text1, translation: trans1 }, reveal1);
      const cue2 = withReveal({
        ...target,
        start: cutTime,
        text: text2,
        translation: trans2,
        _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
      }, reveal2);

      const next = [...prev.cuesList];
      next.splice(idx, 1, cue1, cue2);
      markCuesDirty();
      return { ...prev, cuesList: next };
    });
  }, [markCuesDirty, set]);

  const handleMergeCue = useCallback((cueUid) => {
    set((prev) => {
      const idx = prev.cuesList.findIndex((c) => c._uid === cueUid);
      if (idx === -1 || idx >= prev.cuesList.length - 1) return prev;
      const cur = prev.cuesList[idx];
      const next = prev.cuesList[idx + 1];

      const mergedBase = {
        ...cur,
        end: next.end,
        text: `${cur.text || ''} ${next.text || ''}`.trim(),
        translation: `${cur.translation || ''} ${next.translation || ''}`.trim(),
      };
      const merged = withReveal(mergedBase, mergeCueReveals(cur, next, mergedBase));

      const list = [...prev.cuesList];
      list.splice(idx, 2, merged);
      markCuesDirty();
      return { ...prev, cuesList: list };
    });
  }, [markCuesDirty, set]);

  const handleMergeWithPrevious = useCallback((cueUid) => {
    set((prev) => {
      const idx = prev.cuesList.findIndex((c) => c._uid === cueUid);
      if (idx <= 0) return prev;
      const prevCue = prev.cuesList[idx - 1];
      const curCue = prev.cuesList[idx];

      const mergedBase = {
        ...prevCue,
        end: curCue.end,
        text: `${prevCue.text || ''} ${curCue.text || ''}`.trim(),
        translation: `${prevCue.translation || ''} ${curCue.translation || ''}`.trim(),
      };
      const merged = withReveal(mergedBase, mergeCueReveals(prevCue, curCue, mergedBase));

      const list = [...prev.cuesList];
      list.splice(idx - 1, 2, merged);
      markCuesDirty();
      return { ...prev, cuesList: list };
    });
  }, [markCuesDirty, set]);

  const handleReorderCues = useCallback((fromIdx, toIdx) => {
    set((prev) => {
      if (fromIdx < 0 || fromIdx >= prev.cuesList.length || toIdx < 0 || toIdx >= prev.cuesList.length) return prev;
      const list = [...prev.cuesList];
      const [moved] = list.splice(fromIdx, 1);
      list.splice(toIdx, 0, moved);
      markCuesDirty();
      return { ...prev, cuesList: list };
    });
  }, [markCuesDirty, set]);

  const handleBatchFindAndReplace = useCallback((findText, replaceText) => {
    if (!findText) return 0;
    let count = 0;
    set((prev) => {
      const regex = new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      const list = prev.cuesList.map((c) => {
        const hasMatch = regex.test(c.text || '') || regex.test(c.translation || '');
        if (hasMatch) {
          count++;
          return reconcileCueReveal(c, {
            ...c,
            text: (c.text || '').replace(regex, replaceText),
            translation: c.translation ? c.translation.replace(regex, replaceText) : c.translation,
          });
        }
        return c;
      });
      if (count > 0) markCuesDirty();
      return { ...prev, cuesList: list };
    });
    return count;
  }, [markCuesDirty, set]);

  const handleBatchFormatClean = useCallback(() => {
    set((prev) => {
      const list = prev.cuesList.map((c) => {
        const txt = (c.text || '')
          .replace(/\s+/g, ' ')
          .replace(/^[,\.\-_\s]+|[,\.\-_\s]+$/g, '')
          .trim();
        return reconcileCueReveal(c, { ...c, text: txt });
      });
      markCuesDirty();
      return { ...prev, cuesList: list };
    });
  }, [markCuesDirty, set]);

  const handleImportCues = useCallback((importedCues) => {
    if (!Array.isArray(importedCues) || importedCues.length === 0) return;
    set((prev) => {
      const normalized = importedCues.map((c, i) => ({
        start: Number(c.start) || 0,
        end: Number(c.end) || 0,
        text: c.text || '',
        translation: c.translation || '',
        sfx: c.sfx || null,
        _uid: `cue-${Date.now().toString(36)}-${i}-${Math.random().toString(36).slice(2, 6)}`,
      }));
      markCuesDirty();
      return { ...prev, cuesList: normalized };
    });
    onImportSuccess?.();
  }, [markCuesDirty, onImportSuccess, set]);

  const handleDeleteCue = useCallback((cueUid) => {
    markCuesDirty();
    set((prev) => ({ ...prev, cuesList: prev.cuesList.filter((c) => c._uid !== cueUid) }));
    setSelection(null);
  }, [markCuesDirty, set, setSelection]);

  const handleInsertCueAfter = useCallback((afterCueUid) => {
    set((prev) => {
      const list = [...prev.cuesList];
      if (!afterCueUid) {
        const newCue = {
          start: 0,
          end: 3.0,
          text: 'ข้อความคำบรรยายใหม่...',
          translation: '',
          sfx: null,
          _uid: `cue-${Date.now().toString(36)}`,
        };
        markCuesDirty();
        return { ...prev, cuesList: [newCue] };
      }

      const idx = list.findIndex((c) => c._uid === afterCueUid);
      if (idx === -1) return prev;
      const cur = list[idx];
      const start = cur.end;
      const end = Number((cur.end + 2.5).toFixed(2));
      const newCue = {
        start,
        end,
        text: 'ข้อความคำบรรยายใหม่...',
        translation: '',
        sfx: null,
        _uid: `cue-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
      };
      list.splice(idx + 1, 0, newCue);
      markCuesDirty();
      return { ...prev, cuesList: list };
    });
  }, [markCuesDirty, set]);

  return {
    addClip,
    patchClip,
    patchAllClips,
    reorderClip,
    splitAtPlayhead,
    trimHeadAtPlayhead,
    trimTailAtPlayhead,
    duplicateSelected,
    copyClipSettings: copyClipSettingsFromPrimary,
    pasteClipSettings: pasteClipSettingsToSelected,
    hasCopiedClipSettings: Boolean(copiedClipSettings),
    deleteSelected,
    defaultRippleScope,
    planRipple,
    rippleRanges,
    rippleDeleteRange,
    addTextAtPlayhead,
    patchCaption,
    patchAllCaptions,
    handleUpdateCuesList,
    handleSplitCue,
    handleSplitCueAtPlayhead,
    handleMergeCue,
    handleMergeWithPrevious,
    handleReorderCues,
    handleBatchFindAndReplace,
    handleBatchFormatClean,
    handleDeleteCue,
    handleInsertCueAfter,
    handleImportCues,
  };
}

