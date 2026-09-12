import React, { useState, useRef, useMemo } from 'react';

/**
 * Pure SVG Smooth Curved Area & Line Chart
 * Supports Bezier smoothing, gradient glow, gridlines, and interactive hover tooltip.
 */
export default function AreaLineChart({
  data = [],
  height = 130,
  valueKey = 'tokens',
  dateKey = 'date',
  secondaryKey = 'cost_saved_thb',
  formatValue = (v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v?.toLocaleString?.() || v),
  formatSecondary = (v) => (v != null ? `ประหยัด ฿${v}` : null),
  unit = 'tok',
  lineColor = '#25F4EE',
  gradientFrom = '#25F4EE',
  gradientTo = '#3B82F6',
}) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const containerRef = useRef(null);

  // Filter valid data
  const chartData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data;
  }, [data]);

  const padding = { top: 14, right: 20, bottom: 28, left: 42 };
  const viewBoxWidth = 800;
  const viewBoxHeight = height;
  const innerWidth = viewBoxWidth - padding.left - padding.right;
  const innerHeight = viewBoxHeight - padding.top - padding.bottom;

  const { points, areaPath, linePath, maxVal, minVal, yTicks } = useMemo(() => {
    if (chartData.length === 0) {
      return { points: [], areaPath: '', linePath: '', maxVal: 0, minVal: 0, yTicks: [] };
    }

    const values = chartData.map((d) => Number(d[valueKey]) || 0);
    const rawMax = Math.max(...values, 10);
    const rawMin = 0;
    // Round max up to clean boundary
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawMax)));
    const maxVal = Math.ceil(rawMax / magnitude) * magnitude;
    const minVal = 0;

    const valRange = maxVal - minVal || 1;

    // Generate points
    const stepX = chartData.length > 1 ? innerWidth / (chartData.length - 1) : innerWidth / 2;
    const pts = chartData.map((d, i) => {
      const val = Number(d[valueKey]) || 0;
      const x = padding.left + (chartData.length > 1 ? i * stepX : innerWidth / 2);
      const y = padding.top + innerHeight - ((val - minVal) / valRange) * innerHeight;
      return { x, y, data: d, index: i, value: val };
    });

    if (pts.length === 1) {
      const singlePt = pts[0];
      const lp = `M ${padding.left} ${singlePt.y} L ${padding.left + innerWidth} ${singlePt.y}`;
      const ap = `M ${padding.left} ${singlePt.y} L ${padding.left + innerWidth} ${singlePt.y} L ${padding.left + innerWidth} ${padding.top + innerHeight} L ${padding.left} ${padding.top + innerHeight} Z`;
      return { points: pts, areaPath: ap, linePath: lp, maxVal, minVal, yTicks: [0, maxVal / 2, maxVal] };
    }

    // Generate Catmull-Rom or Cubic Bezier path
    let lp = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = i > 0 ? pts[i - 1] : pts[i];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = i != pts.length - 2 ? pts[i + 2] : p2;

      // Tension factor
      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      lp += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }

    // Closed Area path
    const lastPt = pts[pts.length - 1];
    const firstPt = pts[0];
    const ap = `${lp} L ${lastPt.x} ${padding.top + innerHeight} L ${firstPt.x} ${padding.top + innerHeight} Z`;

    const yTicks = [0, Math.round(maxVal / 2), maxVal];

    return { points: pts, areaPath: ap, linePath: lp, maxVal, minVal, yTicks };
  }, [chartData, innerWidth, innerHeight, padding.left, padding.top, valueKey]);

  // Handle pointer tracking
  const handlePointerMove = (e) => {
    if (!containerRef.current || points.length === 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const scaleX = viewBoxWidth / rect.width;
    const svgX = mouseX * scaleX;

    // Find closest point
    let closestIdx = 0;
    let minDiff = Infinity;
    points.forEach((pt, i) => {
      const diff = Math.abs(pt.x - svgX);
      if (diff < minDiff) {
        minDiff = diff;
        closestIdx = i;
      }
    });
    setHoverIndex(closestIdx);
  };

  const handlePointerLeave = () => {
    setHoverIndex(null);
  };

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 text-xs text-slate-500 bg-white/[0.02] rounded-2xl border border-white/[0.06]">
        ไม่มีข้อมูลประวัติย้อนหลังสำหรับแสดงกราฟ
      </div>
    );
  }

  const activePoint = hoverIndex !== null && points[hoverIndex] ? points[hoverIndex] : null;

  return (
    <div className="relative w-full select-none" onPointerLeave={handlePointerLeave}>
      <svg
        ref={containerRef}
        viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
        className="w-full h-auto overflow-visible cursor-crosshair"
        onPointerMove={handlePointerMove}
      >
        <defs>
          {/* Area gradient */}
          <linearGradient id="areaGlowGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={gradientFrom} stopOpacity="0.32" />
            <stop offset="50%" stopColor={gradientTo} stopOpacity="0.12" />
            <stop offset="100%" stopColor={gradientTo} stopOpacity="0.0" />
          </linearGradient>

          {/* Stroke gradient */}
          <linearGradient id="lineStrokeGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={gradientFrom} />
            <stop offset="100%" stopColor={gradientTo} />
          </linearGradient>

          {/* Glow filter */}
          <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ── Background Grid Lines ── */}
        {yTicks.map((tick, idx) => {
          const y = padding.top + innerHeight - (tick / (maxVal || 1)) * innerHeight;
          return (
            <g key={idx} className="transition-all">
              <line
                x1={padding.left}
                y1={y}
                x2={padding.left + innerWidth}
                y2={y}
                stroke="rgba(255,255,255,0.06)"
                strokeDasharray="4 4"
                strokeWidth="1"
              />
              <text
                x={padding.left - 8}
                y={y + 3.5}
                textAnchor="end"
                className="text-[10px] fill-slate-500 font-mono"
              >
                {formatValue(tick)}
              </text>
            </g>
          );
        })}

        {/* ── Filled Area with Gradient Glow ── */}
        <path d={areaPath} fill="url(#areaGlowGrad)" className="transition-all duration-300" />

        {/* ── Outer Glow Line ── */}
        <path
          d={linePath}
          fill="none"
          stroke={lineColor}
          strokeWidth="3"
          strokeOpacity="0.3"
          filter="url(#neonGlow)"
        />

        {/* ── Sharp Foreground Line ── */}
        <path
          d={linePath}
          fill="none"
          stroke="url(#lineStrokeGrad)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* ── X Axis Dates ── */}
        {points.map((pt, idx) => {
          // Show label if reasonable spacing
          const showLabel =
            points.length <= 8 ||
            idx === 0 ||
            idx === points.length - 1 ||
            idx % Math.ceil(points.length / 7) === 0;

          if (!showLabel) return null;

          const dateStr = String(pt.data[dateKey] || '');
          const shortDate = dateStr.length > 5 ? dateStr.slice(5) : dateStr;

          return (
            <text
              key={idx}
              x={pt.x}
              y={padding.top + innerHeight + 17}
              textAnchor="middle"
              className="text-[10px] fill-slate-400 font-mono font-medium"
            >
              {shortDate}
            </text>
          );
        })}

        {/* ── Data Points ── */}
        {points.map((pt, idx) => {
          const isHovered = hoverIndex === idx;
          return (
            <g key={idx} className="transition-all">
              {/* Outer halo */}
              <circle
                cx={pt.x}
                cy={pt.y}
                r={isHovered ? 5 : 3}
                fill="#0B0F19"
                stroke={lineColor}
                strokeWidth={isHovered ? 2 : 1.5}
                className="transition-all duration-150"
              />
              {/* Inner core */}
              <circle
                cx={pt.x}
                cy={pt.y}
                r={isHovered ? 2.5 : 1.2}
                fill={isHovered ? '#FFFFFF' : lineColor}
                className="transition-all duration-150"
              />
            </g>
          );
        })}

        {/* ── Active Hover Vertical Crosshair ── */}
        {activePoint && (
          <g>
            <line
              x1={activePoint.x}
              y1={padding.top}
              x2={activePoint.x}
              y2={padding.top + innerHeight}
              stroke="rgba(37, 244, 238, 0.4)"
              strokeDasharray="2 2"
              strokeWidth="1.5"
            />
            <circle
              cx={activePoint.x}
              cy={activePoint.y}
              r="7"
              fill="none"
              stroke="#25F4EE"
              strokeWidth="2"
              className="animate-ping opacity-75"
            />
          </g>
        )}
      </svg>

      {/* ── Glassmorphic Hover Floating Tooltip Card ── */}
      {activePoint && (
        <div
          className="absolute z-20 pointer-events-none transform -translate-x-1/2 -translate-y-full mb-3"
          style={{
            left: `${(activePoint.x / viewBoxWidth) * 100}%`,
            top: `${(activePoint.y / viewBoxHeight) * 100}%`,
          }}
        >
          <div className="px-3 py-2 rounded-xl bg-[#080B11]/95 border border-[#25F4EE]/40 shadow-xl shadow-black/80 backdrop-blur-md text-left min-w-[130px] space-y-1 animate-fadeIn">
            <div className="text-[10px] font-mono text-slate-400 border-b border-white/[0.08] pb-1">
              {activePoint.data[dateKey]}
            </div>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[11px] text-slate-300">ปริมาณ:</span>
              <span className="text-xs font-mono font-bold text-white">
                {activePoint.value.toLocaleString()} {unit}
              </span>
            </div>
            {activePoint.data[secondaryKey] != null && (
              <div className="text-[10px] font-mono text-emerald-400">
                {formatSecondary(activePoint.data[secondaryKey])}
              </div>
            )}
            {activePoint.data.calls != null && (
              <div className="text-[10px] text-slate-400">
                เรียกใช้งาน {activePoint.data.calls} ครั้ง
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
