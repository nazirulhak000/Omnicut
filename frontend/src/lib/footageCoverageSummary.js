const finite = (value) => typeof value === 'number' && Number.isFinite(value);

/** Seconds a clip holds a frame: its freeze tail, or -- for a hold-only clip
 * (`held_source_time`, shot planner `hold_reason`) -- the whole played span. */
function heldSeconds(clip) {
  const freeze = Math.min(10, Math.max(0, Number(clip.freeze_tail) || 0));
  if (!clip.hold_reason || !finite(clip.held_source_time)) return freeze;
  const trimStart = Number(clip.trim_start) || 0;
  const trimEnd = Number(clip.trim_end);
  const speed = Number(clip.speed) > 0 ? Number(clip.speed) : 1;
  const played = Number.isFinite(trimEnd) && trimEnd > trimStart ? (trimEnd - trimStart) / speed : 0;
  return played + freeze;
}

/** Clips that hold a frame because no matching footage was left: the automatic
 * shortage (`footage_shortage`) and the shot planner's allowed holds
 * (`hold_reason`, which Viral Lint reports as HOLD instead of LONG_SHOT). */
export function footageCoverageSummary(clips = []) {
  let count = 0;
  let seconds = 0;
  for (const clip of clips) {
    const shortage = clip.footage_shortage?.reason === 'source_window_exhausted';
    if (!shortage && !clip.hold_reason) continue;
    const hold = heldSeconds(clip);
    if (!Number.isFinite(hold) || hold <= 0) continue;
    count += 1;
    seconds += hold;
  }
  return { count, seconds };
}
