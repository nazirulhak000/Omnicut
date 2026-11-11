import React from 'react';
import Toolbar from './Toolbar';
import { useLivePlayheadSelector } from '../../hooks/usePlayhead';
import { resolveSplitTarget } from '../../lib/timelineMath';
import { resolveTrimHead, resolveTrimTail } from '../../lib/timelineTrimOps.js';

const SEP = '\u0001';

/**
 * Toolbar whose Split / Trim-head / Trim-tail availability follows the live
 * playhead.
 *
 * Whether those three commands can run depends on where the playhead is, so
 * the answer changes as a clip plays. The button state comes from the same
 * resolvers the commands run. This wrapper subscribes to the playhead but
 * re-renders the toolbar only when one of the six answers actually changes
 * (the playhead crossing into another clip), not on every tick.
 */
export default function LiveToolbar({ segments, selectedSeg, playhead = 0, ...toolbarProps }) {
  const answers = useLivePlayheadSelector((time) => {
    const splitTarget = resolveSplitTarget(segments, selectedSeg, time);
    const trimHeadTarget = resolveTrimHead(segments, selectedSeg, time);
    const trimTailTarget = resolveTrimTail(segments, selectedSeg, time);
    return [
      splitTarget.seg ? '1' : '', splitTarget.message ?? '',
      trimHeadTarget.seg ? '1' : '', trimHeadTarget.message ?? '',
      trimTailTarget.seg ? '1' : '', trimTailTarget.message ?? '',
    ].join(SEP);
  }, playhead);
  const [canSplit, splitReason, canTrimHead, trimHeadReason, canTrimTail, trimTailReason] = answers.split(SEP);

  return (
    <Toolbar
      {...toolbarProps}
      playhead={playhead}
      canSplit={Boolean(canSplit)}
      splitBlockedReason={splitReason || undefined}
      canTrimHead={Boolean(canTrimHead)}
      trimHeadBlockedReason={trimHeadReason || undefined}
      canTrimTail={Boolean(canTrimTail)}
      trimTailBlockedReason={trimTailReason || undefined}
    />
  );
}
