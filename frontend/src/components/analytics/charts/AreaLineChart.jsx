import React, { useState, useRef, useMemo } from 'react';
import {
  computeAreaLineChart,
  findClosestChartPoint,
  computeXAxisTicks,
  DEFAULT_CHART_PADDING,
} from '../../../lib/chartModel';

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
  valueLabel = 'ปริมาณ',
  lineColor = '#25F4EE',
  gradientFrom = '#25F4EE',
  gradientTo = '#3B82F6',
  customTooltip = null,
}) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const containerRef = useRef(null);

  // Filter valid data
  const chartData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data;
  }, [data]);

  const padding = DEFAULT_CHART_PADDING;
  const viewBoxWidth = 800;
  const viewBoxHeight = height;
  const innerWidth = viewBoxWidth - padding.left - padding.right;
  const innerHeight = viewBoxHeight - padding.top - padding.bottom;

  const { points, areaPath, linePath, maxVal, minVal, yTicks } = useMemo(() => {
    return computeAreaLineChart({
      data: chartData,
      valueKey,
      dateKey,
      viewBoxWidth,
      viewBoxHeight,
      padding,
    });
  }, [chartData, viewBoxWidth, viewBoxHeight, padding, valueKey, dateKey]);

  // Compute non-colliding tick indices
  const tickIndices = useMemo(() => {
    return new Set(computeXAxisTicks(points, { maxTicks: 7, dateKey }));
  }, [points, dateKey]);

  // Handle pointer tracking
  const handlePointerMove = (e) => {
    if (!containerRef.current || points.length === 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const scaleX = viewBoxWidth / rect.width;
    const svgX = mouseX * scaleX;

    const match = findClosestChartPoint(points, svgX);
    setHoverIndex(match ? match.index : null);
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

  // Clamped tooltip coordinates
  const leftPct = activePoint ? (activePoint.x / viewBoxWidth) * 100 : 50;
  const topPct = activePoint ? (activePoint.y / viewBoxHeight) * 100 : 50;
  const xTransform = leftPct < 18 ? 'translate-x-0' : leftPct > 82 ? '-translate-x-full' : '-translate-x-1/2';
  const yTransform = topPct < 32 ? 'translate-y-3' : '-translate-y-full mb-3';

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
                className="text-[10px] fill-slate-500"
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
          if (!tickIndices.has(idx)) return null;

          const dateStr = String(pt.data[dateKey] || pt.label || '');
          const shortDate = dateStr.length > 5 ? dateStr.slice(5) : dateStr;

          return (
            <text
              key={idx}
              x={pt.x}
              y={padding.top + innerHeight + 17}
              textAnchor="middle"
              className="text-[10px] fill-slate-400 font-medium"
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
          className={`absolute z-20 pointer-events-none transform ${xTransform} ${yTransform}`}
          style={{
            left: `${leftPct}%`,
            top: `${topPct}%`,
          }}
        >
          {customTooltip ? (
            customTooltip(activePoint)
          ) : (
            <div className="px-3.5 py-2.5 rounded-xl bg-[#080B11]/95 border border-[#25F4EE]/40 shadow-xl shadow-black/80 backdrop-blur-md text-left min-w-[140px] max-w-[260px] space-y-1.5 animate-fadeIn">
              <div className="flex items-center justify-between gap-2 text-[10px] text-slate-400 border-b border-white/[0.08] pb-1">
                <span className="font-mono">{activePoint.data[dateKey] || activePoint.label}</span>
                {activePoint.data.time && (
                  <span className="text-cyan-400 font-mono">{activePoint.data.time}</span>
                )}
              </div>

              {activePoint.data.product && (
                <div className="text-xs font-bold text-white truncate">
                  {activePoint.data.product}
                </div>
              )}
              {activePoint.data.angle && (
                <div className="text-[10px] text-slate-400 truncate">
                  {activePoint.data.angle}
                </div>
              )}

              <div className="flex items-baseline justify-between gap-2 pt-0.5">
                <span className="text-[11px] text-slate-300 font-medium">{valueLabel}:</span>
                <span className="text-xs font-bold text-white">
                  {activePoint.value.toLocaleString()} {unit}
                </span>
              </div>

              {activePoint.data.count != null && activePoint.data.count > 1 && (
                <div className="text-[10px] text-cyan-300">
                  รวม {activePoint.data.count} คลิป (เฉลี่ย {Math.round(activePoint.value / activePoint.data.count).toLocaleString()} {unit}/คลิป)
                </div>
              )}

              {activePoint.data.engagement != null && activePoint.data.engagement > 0 && (
                <div className="text-[10px] text-amber-300 font-medium">
                  Engagement {activePoint.data.engagement}%
                </div>
              )}

              {activePoint.data[secondaryKey] != null && (
                <div className="text-[10px] font-semibold text-emerald-400">
                  {formatSecondary(activePoint.data[secondaryKey])}
                </div>
              )}

              {activePoint.data.calls != null && (
                <div className="text-[10px] text-slate-400">
                  เรียกใช้งาน {activePoint.data.calls} ครั้ง
                </div>
              )}

              {(activePoint.data.likes != null || activePoint.data.comments != null) && (
                <div className="text-[10px] text-slate-400 flex items-center gap-2 pt-0.5 border-t border-white/[0.06]">
                  {activePoint.data.likes != null && <span>❤️ {activePoint.data.likes}</span>}
                  {activePoint.data.comments != null && <span>💬 {activePoint.data.comments}</span>}
                  {activePoint.data.shares != null && <span>🔗 {activePoint.data.shares}</span>}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

