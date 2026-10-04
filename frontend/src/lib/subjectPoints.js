/**
 * Product-point helpers shared by the Cutout panel and the preview.
 *
 * Mirrors `scripts/cutout_prompt.py`: a point is `{ x, y, label }` with
 * normalized 0..1 coordinates, label 1 = the product and 0 = background.
 * The worker clamps and caps the list again, so this is a shared contract
 * rather than a security boundary -- keeping both sides identical avoids the
 * "the UI showed 9 points but the worker used 8" class of surprise.
 */

export const SUBJECT_POINT_LIMIT = 8;

function clampUnit(value) {
  const number = typeof value === 'string' && value.trim() !== '' ? Number(value) : value;
  if (typeof number !== 'number' || !Number.isFinite(number)) return null;
  return Math.min(1, Math.max(0, number));
}

function pointFrom(value) {
  if (Array.isArray(value)) {
    if (value.length < 2) return null;
    const x = clampUnit(value[0]);
    const y = clampUnit(value[1]);
    if (x === null || y === null) return null;
    return { x, y, label: normalizeLabel(value[2]) };
  }
  if (!value || typeof value !== 'object') return null;
  const x = clampUnit(value.x);
  const y = clampUnit(value.y);
  if (x === null || y === null) return null;
  return { x, y, label: normalizeLabel(value.label) };
}

function normalizeLabel(value) {
  if (value === undefined || value === null) return 1;
  return Number(value) === 0 ? 0 : 1;
}

export function normalizeSubjectPoints(value) {
  if (!Array.isArray(value)) return [];
  const points = [];
  for (const item of value) {
    const point = pointFrom(item);
    if (!point) continue;
    points.push(point);
    if (points.length >= SUBJECT_POINT_LIMIT) break;
  }
  return points;
}

export function subjectPointsEqual(a, b) {
  const ptsA = normalizeSubjectPoints(a);
  const ptsB = normalizeSubjectPoints(b);
  if (ptsA.length !== ptsB.length) return false;
  for (let i = 0; i < ptsA.length; i++) {
    const pA = ptsA[i];
    const pB = ptsB[i];
    if (pA.label !== pB.label) return false;
    if (Math.abs(pA.x - pB.x) > 0.002 || Math.abs(pA.y - pB.y) > 0.002) return false;
  }
  return true;
}

/** Append a picked point, ignoring duplicates of the same subject location. */
export function withSubjectPoint(points, point) {
  const existing = normalizeSubjectPoints(points);
  const next = pointFrom(point);
  if (!next) return existing;
  if (existing.some((item) => item.label === next.label
    && Math.abs(item.x - next.x) < 0.002
    && Math.abs(item.y - next.y) < 0.002)) {
    return existing;
  }
  return [...existing, next].slice(0, SUBJECT_POINT_LIMIT);
}

function clampFrameCoordinate(clientValue, rectStart, rectSize) {
  return clampUnit((clientValue - rectStart) / rectSize);
}

/**
 * Convert a pointer position inside the preview frame into a normalized point.
 * Returns null for a degenerate rect so a hidden preview cannot record a point
 * at 0,0 by accident.
 */
export function subjectPointFromFramePointer(pointer, rect) {
  if (!rect || !(rect.width > 0) || !(rect.height > 0)) return null;
  // `rect` may be a DOMRect and `pointer` a React synthetic event; both are
  // read defensively so a hidden preview cannot record a point by accident.
  const { clientX, clientY } = pointer || {};
  const x = clampFrameCoordinate(clientX, rect.left, rect.width);
  const y = clampFrameCoordinate(clientY, rect.top, rect.height);
  if (x === null || y === null) return null;
  return { x, y, label: 1 };
}

export function subjectPointMarkerStyle(point) {
  const x = clampUnit(point?.x) ?? 0;
  const y = clampUnit(point?.y) ?? 0;
  return { left: `${x * 100}%`, top: `${y * 100}%` };
}

export function describeSubjectPointCount(points) {
  const normalized = normalizeSubjectPoints(points);
  const count = normalized.length;
  if (count === 0) return 'ยังไม่ได้จิ้มจุดสินค้า';
  const pos = normalized.filter((p) => p.label === 1).length;
  const neg = normalized.filter((p) => p.label === 0).length;
  if (neg > 0) {
    return `จิ้มจุดแล้ว ${count} จุด (เก็บสินค้า ${pos}, ตัดพื้นหลัง ${neg})`;
  }
  return `จิ้มจุดสินค้าแล้ว ${count} จุด`;
}
