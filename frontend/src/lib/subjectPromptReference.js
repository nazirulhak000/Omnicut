import { groupBackgroundIsolationClips } from './backgroundIsolationPreview.js';
import { getDrawPlan } from './timelineMath.js';

/** Manual prompts initialize frame zero of the grouped worker window. */
export function subjectPromptReference(segments, time, { sourceDurations = {}, config = {} } = {}) {
  const plan = getDrawPlan(segments, time);
  if (plan.length !== 1) return null;
  const selected = plan[0].seg;
  const activeIds = config.scope_mode === 'behind_text_windows' && Array.isArray(config.active_clip_ids)
    ? new Set(config.active_clip_ids) : null;
  const clips = segments.map((seg) => seg.clip).filter((clip) =>
    (!activeIds || activeIds.has(clip.id))
    // Scoped workers retain each clip's full trim as their tracking window.
    && (config.scope_mode !== 'behind_text_windows' || clip.id === selected.clip.id));
  const group = groupBackgroundIsolationClips(clips, { sourceDurations })
    .find((candidate) => candidate.clips.some((clip) => clip.id === selected.clip.id));
  if (!group || group.unresolved) return null;
  // Overlapping trims share one worker; its first frame may belong to another
  // timeline segment of the same source. Show that actual reference segment.
  const firstClip = group.clips.find((clip) => Number(clip.trim_start || 0) === group.start);
  const first = segments.find((seg) => seg.clip.id === firstClip?.id);
  if (!first) return null;
  return { clipId: first.clip.id, sourcePath: first.clip.source_path,
    sourceStart: group.start, timelineTime: first.segStart };
}
