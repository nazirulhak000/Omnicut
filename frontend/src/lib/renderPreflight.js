import { buildSegments, FPS, TRANSITIONS, sequenceFrameIndex } from './timelineMath.js';

const finite = (value) => (typeof value === 'number' || (typeof value === 'string' && value.trim() !== ''))
  && Number.isFinite(Number(value));
const EPSILON = 1 / FPS;
const transitionKinds = new Set(['cut', ...TRANSITIONS.map(({ id }) => id)]);

export function formatPreflightTime(seconds) {
  if (!Number.isFinite(seconds)) return 'ไม่ทราบเวลา';
  const centiseconds = Math.round(Math.max(0, seconds) * 100);
  return `${String(Math.floor(centiseconds / 6000)).padStart(2, '0')}:${String(Math.floor(centiseconds / 100) % 60).padStart(2, '0')}.${String(centiseconds % 100).padStart(2, '0')}`;
}

/** Metadata inspection only. A source reference is not proof a file exists or
 * decodes, and a structural gap is not evidence of actual black frames. */
export function analyzeRenderPreflight({ clips = [], durations = {}, segments, expectedDuration = 0 } = {}) {
  const layout = segments ?? buildSegments(clips, durations);
  const issues = [];
  const covered = [];
  let uncertainCoverage = false;
  let uncertainPosition = false;
  const add = (code, severity, message, clipIndex, start, end) => {
    issues.push({ code, severity, message, clipIndex, clipId: clips[clipIndex]?.id ?? null,
      start: Number.isFinite(start) ? start : null, end: Number.isFinite(end) ? end : null });
  };
  if (!clips.length) add('empty_timeline', 'error', 'เพิ่มคลิปวิดีโอในไทม์ไลน์ก่อนเรนเดอร์', null, 0, 0);
  clips.forEach((clip, index) => {
    const segment = layout[index];
    const duration = durations[clip.id];
    const durationPending = clip.trim_end == null && !(finite(duration) && Number(duration) > 0);
    let start = uncertainPosition || (durationPending && index > 0 && clip.transition_in && clip.transition_in !== 'cut')
      ? null : segment?.segStart;
    let end = uncertainPosition || durationPending ? null : segment?.segEnd;
    if (Number.isFinite(start) && Number.isFinite(end) && (start < 0 || end <= start)) {
      start = null;
      end = null;
    }
    const trimStart = clip.trim_start ?? 0;
    const trimEnd = clip.trim_end;
    const speed = clip.speed ?? 1;
    const hold = Math.min(10, Math.max(0, Number(clip.freeze_tail) || 0));
    let valid = true;
    if (typeof clip.source_path !== 'string' || !clip.source_path.trim()) {
      add('missing_source', 'error', 'คลิปไม่มีตำแหน่งไฟล์ต้นฉบับ เลือกไฟล์วิดีโอให้คลิปนี้', index, start, end);
      valid = false;
    }
    if (!finite(trimStart) || Number(trimStart) < 0 || !finite(speed) || Number(speed) <= 0
      || (trimEnd != null && (!finite(trimEnd) || Number(trimEnd) <= Number(trimStart)))) {
      add('invalid_timing', 'error', 'ช่วงตัดหรือความเร็วคลิปไม่ถูกต้อง แก้เวลาเริ่ม เวลาจบ และความเร็ว', index, start, null);
      valid = false;
      uncertainCoverage = true;
      uncertainPosition = true;
    }
    if (durationPending) {
      add('unknown_duration', 'warning', 'ยังไม่มีความยาวต้นฉบับ จึงยืนยันช่วงภาพของคลิปนี้ไม่ได้', index, start, null);
      uncertainCoverage = true;
      uncertainPosition = true;
    }
    if (valid && !durationPending && (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start)) {
      add('unknown_position', 'warning', 'ยังยืนยันตำแหน่งหรือความยาวคลิปในไทม์ไลน์ไม่ได้ ตรวจข้อมูลช่วงเวลาและรอยต่อ', index, null, null);
      uncertainCoverage = true;
    }
    if (valid && (Number(speed) < 0.25 || Number(speed) > 4)) {
      add('normalized_speed', 'warning', 'ความเร็วอยู่นอกช่วง 0.25–4 ที่ renderer รองรับ เวลาพรีวิวอาจต่างจากผลเรนเดอร์', index, start, end);
    }
    if (!transitionKinds.has(clip.transition_in || 'cut')
      || (clip.transition_in && clip.transition_in !== 'cut' && clip.transition_duration != null && !finite(clip.transition_duration))) {
      add('invalid_transition', 'warning', 'ข้อมูลรอยต่อไม่รองรับหรือเวลาไม่เป็นตัวเลข ตรวจชนิดและระยะเวลารอยต่อ', index, start, end);
    }
    if (valid && finite(duration) && Number(duration) > 0
      && (Number(trimStart) >= Number(duration) || (finite(trimEnd) && Number(trimEnd) > Number(duration) + EPSILON))) {
      add('source_bounds', 'warning', 'ช่วงตัดเกินความยาวต้นฉบับที่รายงาน ตรวจไฟล์และช่วงตัดก่อนเรนเดอร์', index, start, end);
    }
    const window = clip.source_window;
    const windowValid = window && typeof window === 'object' && !Array.isArray(window)
      && finite(window.start) && finite(window.end) && Number(window.start) >= 0 && Number(window.end) > Number(window.start);
    if (window != null && !windowValid) {
      add('invalid_source_window', 'warning', 'ขอบเขตภาพตรงหัวข้อไม่ถูกต้อง ตรวจเวลาเริ่มและจบของ source_window', index, start, end);
    }
    if (valid && windowValid
      && (Number(trimStart) < Number(window.start) - EPSILON
        || (finite(trimEnd) && Number(trimEnd) > Number(window.end) + EPSILON))) {
      add('source_window_bounds', 'warning', 'ช่วงตัดเลยขอบเขตภาพตรงหัวข้อที่กำหนด ตรวจช่วงต้นฉบับของช็อตนี้', index, start, end);
    }
    const heldSource = clip.held_source_time;
    const heldSourceValid = typeof heldSource === 'number' && Number.isFinite(heldSource) && heldSource >= 0
      && heldSource >= Number(trimStart) - 1e-6 && (!finite(trimEnd) || heldSource < Number(trimEnd))
      && (!(finite(duration) && Number(duration) > 0) || heldSource < Number(duration))
      && (!windowValid || (heldSource >= Number(window.start) - 1e-6 && heldSource < Number(window.end)));
    if (hold > 0 && heldSource != null && !heldSourceValid) {
      add('invalid_held_source', 'warning', 'เวลาเฟรมค้างไม่ถูกต้องหรืออยู่นอกช่วงต้นฉบับ ตรวจ held_source_time', index, start, end);
    }
    if (valid && hold > 0 && clip.footage_shortage?.reason === 'source_window_exhausted') {
      add('footage_hold', 'warning', `ภาพตรงบทไม่พอ ค้างภาพสุดท้าย ${hold.toFixed(2)} วินาทีตามแผนที่อนุญาต`,
        index, Number.isFinite(end) && Number.isFinite(start) ? (heldSourceValid ? start : Math.max(start, end - hold)) : null, end);
      issues[issues.length - 1].holdSeconds = hold;
    }
    if (valid && Number.isFinite(start) && Number.isFinite(end) && end > start
      && !(trimEnd == null && !(finite(duration) && Number(duration) > 0))) covered.push([start, end]);
    if (!Number.isFinite(start) || !Number.isFinite(end)) uncertainCoverage = true;
  });
  const timelineEnd = layout.reduce((end, segment) => Math.max(end, Number.isFinite(segment.segEnd) ? segment.segEnd : 0), 0);
  const horizon = Math.max(timelineEnd, finite(expectedDuration) ? Number(expectedDuration) : 0);
  if (!uncertainCoverage) {
    let cursor = 0;
    for (const [start, end] of covered.sort((a, b) => a[0] - b[0])) {
      if (sequenceFrameIndex(start) > sequenceFrameIndex(cursor)) add('structural_gap', 'warning', 'ไม่มีคลิปวิดีโอครอบคลุมช่วงนี้ในไทม์ไลน์ ตรวจแผนภาพหรือการค้างภาพปลายคลิป', null, cursor, start);
      cursor = Math.max(cursor, end);
    }
    if (sequenceFrameIndex(horizon) > sequenceFrameIndex(cursor)) add('structural_gap', 'warning', 'ไม่มีคลิปวิดีโอครอบคลุมช่วงนี้ในไทม์ไลน์ ตรวจแผนภาพหรือการค้างภาพปลายคลิป', null, cursor, horizon);
  }
  issues.sort((a, b) => (a.start ?? Infinity) - (b.start ?? Infinity));
  return { issues, errors: issues.filter((issue) => issue.severity === 'error'),
    warnings: issues.filter((issue) => issue.severity === 'warning'), canRender: !issues.some((issue) => issue.severity === 'error') };
}

export function preflightBlockingMessage(report) {
  return report.errors.map((issue) => `${issue.clipIndex == null ? '' : `ช็อต ${issue.clipIndex + 1} `}${formatPreflightTime(issue.start)}: ${issue.message}`).join('\n');
}
