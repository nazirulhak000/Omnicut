/**
 * Pure calculation model for SVG Area & Line Charts.
 * Decouples chart geometry, scale math, Bezier curves, and hover tracking
 * so they can be unit-tested without browser/DOM dependencies.
 */

export const DEFAULT_CHART_PADDING = Object.freeze({
  top: 14,
  right: 20,
  bottom: 28,
  left: 42,
});

export function computeAreaLineChart({
  data = [],
  valueKey = 'tokens',
  dateKey = 'date',
  viewBoxWidth = 800,
  viewBoxHeight = 130,
  padding = DEFAULT_CHART_PADDING,
} = {}) {
  if (!Array.isArray(data) || data.length === 0) {
    return {
      points: [],
      areaPath: '',
      linePath: '',
      maxVal: 0,
      minVal: 0,
      yTicks: [],
      innerWidth: 0,
      innerHeight: 0,
    };
  }

  const innerWidth = viewBoxWidth - padding.left - padding.right;
  const innerHeight = viewBoxHeight - padding.top - padding.bottom;

  const values = data.map((d) => (d && typeof d === 'object' && d[valueKey] != null ? Number(d[valueKey]) || 0 : 0));
  const rawMax = Math.max(...values, 10);
  const rawMin = 0;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawMax))) || 1;
  const maxVal = Math.ceil(rawMax / magnitude) * magnitude;
  const minVal = 0;
  const valRange = maxVal - minVal || 1;

  const stepX = data.length > 1 ? innerWidth / (data.length - 1) : innerWidth / 2;
  const points = data.map((d, i) => {
    const val = d && typeof d === 'object' && d[valueKey] != null ? Number(d[valueKey]) || 0 : 0;
    const x = padding.left + (data.length > 1 ? i * stepX : innerWidth / 2);
    const y = padding.top + innerHeight - ((val - minVal) / valRange) * innerHeight;
    const label = d && typeof d === 'object' ? String(d[dateKey] ?? '') : '';
    return { x, y, data: d, index: i, value: val, label };
  });

  const yTicks = [0, Math.round(maxVal / 2), maxVal];

  if (points.length === 1) {
    const singlePt = points[0];
    const lp = `M ${padding.left} ${singlePt.y} L ${padding.left + innerWidth} ${singlePt.y}`;
    const ap = `M ${padding.left} ${singlePt.y} L ${padding.left + innerWidth} ${singlePt.y} L ${padding.left + innerWidth} ${padding.top + innerHeight} L ${padding.left} ${padding.top + innerHeight} Z`;
    return { points, areaPath: ap, linePath: lp, maxVal, minVal, yTicks, innerWidth, innerHeight };
  }

  // Generate Bezier path
  let lp = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = i > 0 ? points[i - 1] : points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = i !== points.length - 2 ? points[i + 2] : p2;

    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;

    lp += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.x ? p2.y.toFixed(1) : '0'}`;
  }

  const lastPt = points[points.length - 1];
  const firstPt = points[0];
  const ap = `${lp} L ${lastPt.x} ${padding.top + innerHeight} L ${firstPt.x} ${padding.top + innerHeight} Z`;

  return { points, areaPath: ap, linePath: lp, maxVal, minVal, yTicks, innerWidth, innerHeight };
}

export function findClosestChartPoint(points, svgX) {
  if (!Array.isArray(points) || points.length === 0) return null;
  let closestIdx = 0;
  let minDiff = Infinity;
  for (let i = 0; i < points.length; i++) {
    const diff = Math.abs(points[i].x - svgX);
    if (diff < minDiff) {
      minDiff = diff;
      closestIdx = i;
    }
  }
  return { index: closestIdx, point: points[closestIdx] };
}
