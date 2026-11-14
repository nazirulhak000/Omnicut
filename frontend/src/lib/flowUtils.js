/**
 * Utilities for Google Flow (Veo AI) Video Generation.
 */

/**
 * Maps a human or shot-list camera direction into a supported Flow camera technique.
 * @param {string} direction - The camera direction string (Thai or English).
 * @returns {'orbit' | 'macro' | 'dolly_in' | 'reveal' | 'floating'}
 */
export function mapCameraTechnique(direction = '') {
  if (!direction) return 'orbit';
  const dir = direction.toLowerCase();
  if (dir.includes('orbit') || dir.includes('หมุน') || dir.includes('360')) return 'orbit';
  if (dir.includes('macro') || dir.includes('close') || dir.includes('โคลส') || dir.includes('detail') || dir.includes('ดีเทล')) return 'macro';
  if (dir.includes('dolly') || dir.includes('ดัน') || dir.includes('เข้าหา') || dir.includes('zoom in')) return 'dolly_in';
  if (dir.includes('reveal') || dir.includes('เสย') || dir.includes('มุมต่ำ') || dir.includes('low angle')) return 'reveal';
  if (dir.includes('float') || dir.includes('ลอย') || dir.includes('slow') || dir.includes('สโลว์')) return 'floating';
  return 'orbit';
}

/**
 * Checks whether a given beat has an AI Flow clip available or generating.
 * @param {object} beat - The shot beat object.
 * @param {Array} jobsList - List of flow jobs from getFlowJobs.
 * @returns {{ status: 'ready' | 'generating', path?: string, job: object } | null}
 */
export function findFlowClipForBeat(beat, jobsList = []) {
  if (!jobsList || jobsList.length === 0 || !beat) return null;
  const shotNum = (beat.beat_index !== undefined ? beat.beat_index : 0) + 1;
  const beatIndex = beat.beat_index;

  // 1. Search completed jobs first
  for (const job of jobsList) {
    if (job.status !== 'completed') continue;

    // A. Check scenes with matching shot_index or shot_label
    const hasMatchingScene = job.scenes?.some(
      (s) => s.shot_index === beatIndex ||
             s.shot_label === `shot_${shotNum}` ||
             (typeof s.shot_label === 'string' && s.shot_label.startsWith(`shot_${shotNum}_`))
    );

    if (hasMatchingScene) {
      const ingested = job.ingested_files?.[0];
      const resultPath = job.results?.[0]?.path || job.results?.[0]?.file_path;
      if (ingested || resultPath) {
        return { status: 'ready', path: ingested || resultPath, job };
      }
    }

    // B. Check ingested_files filenames for shot pattern
    for (const f of job.ingested_files || []) {
      if (typeof f === 'string' && (f.includes(`shot_${shotNum}_`) || f.includes(`shot_${shotNum}.`))) {
        return { status: 'ready', path: f, job };
      }
    }
  }

  // 2. Search running or queued jobs
  for (const job of jobsList) {
    if (job.status === 'running' || job.status === 'queued') {
      const hasMatchingScene = job.scenes?.some(
        (s) => s.shot_index === beatIndex ||
               s.shot_label === `shot_${shotNum}` ||
               (typeof s.shot_label === 'string' && s.shot_label.startsWith(`shot_${shotNum}_`))
      );
      if (hasMatchingScene) {
        return { status: 'generating', job };
      }
    }
  }

  return null;
}
