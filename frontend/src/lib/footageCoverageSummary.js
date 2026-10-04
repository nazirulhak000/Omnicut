export function footageCoverageSummary(clips = []) {
  let count = 0;
  let seconds = 0;
  for (const clip of clips) {
    const hold = Math.min(10, Number(clip.freeze_tail));
    if (clip.footage_shortage?.reason !== 'source_window_exhausted' || !Number.isFinite(hold) || hold <= 0) continue;
    count += 1;
    seconds += hold;
  }
  return { count, seconds };
}
