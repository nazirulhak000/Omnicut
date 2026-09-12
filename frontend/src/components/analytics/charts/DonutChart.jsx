import React, { useState, useMemo } from 'react';

const DEFAULT_PALETTE = [
  '#25F4EE', // TikTok Cyan
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#F59E0B', // Amber
  '#10B981', // Emerald
  '#F97316', // Orange
  '#6366F1', // Indigo
];

/**
 * Pure SVG Multi-Segment Donut Chart
 * Supports hover segment highlighting, responsive layout, center metrics, and interactive legend.
 */
export default function DonutChart({
  data = [],
  size = 140,
  strokeWidth = 18,
  centerLabel = 'ทั้งหมด',
  centerValue,
  unit = '',
  palette = DEFAULT_PALETTE,
  showLegend = true,
  legendLayout = 'vertical', // 'vertical' | 'horizontal'
  maxSlices = 5,
  formatValue = (v) => (typeof v === 'number' ? v.toLocaleString() : v),
}) {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  // Group data to maxSlices (Top N - 1 + "อื่นๆ") to prevent thin slices and vertical explosion
  const processedData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    if (!maxSlices || data.length <= maxSlices) return data;

    // Sort descending by numeric value
    const sorted = [...data].sort((a, b) => (Number(b.value) || 0) - (Number(a.value) || 0));
    const top = sorted.slice(0, maxSlices - 1);
    const rest = sorted.slice(maxSlices - 1);
    const otherVal = rest.reduce((sum, item) => sum + (Number(item.value) || 0), 0);

    if (otherVal > 0) {
      top.push({
        label: 'อื่นๆ',
        name: 'อื่นๆ',
        value: otherVal,
        color: '#64748B',
      });
    }
    return top;
  }, [data, maxSlices]);

  const total = useMemo(() => {
    return processedData.reduce((acc, item) => acc + (Number(item.value) || 0), 0);
  }, [processedData]);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  // Calculate slice angles & stroke offsets
  const slices = useMemo(() => {
    if (total === 0) return [];
    let accumulatedAngle = 0;

    return processedData.map((item, idx) => {
      const val = Number(item.value) || 0;
      const fraction = val / total;
      const strokeLength = fraction * circumference;
      const strokeDasharray = `${strokeLength} ${circumference - strokeLength}`;
      const rotation = accumulatedAngle * 360 - 90;
      accumulatedAngle += fraction;

      const color = item.color || palette[idx % palette.length];
      const percent = Math.round(fraction * 100);
      const displayName = item.label || item.name || `หมวด ${idx + 1}`;

      return {
        ...item,
        name: displayName,
        label: displayName,
        value: val,
        percent,
        strokeDasharray,
        rotation,
        color,
        index: idx,
      };
    });
  }, [processedData, total, circumference, palette]);

  if (!data || data.length === 0 || total === 0) {
    return (
      <div className="flex items-center justify-center p-6 text-xs text-slate-500 bg-white/[0.02] rounded-2xl border border-white/[0.06]">
        ไม่มีข้อมูลสำหรับแสดงกราฟโดนัท
      </div>
    );
  }

  const activeSlice = hoveredIdx !== null ? slices[hoveredIdx] : null;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-5 sm:gap-7 justify-center w-full">
      {/* ── SVG Donut Visual ── */}
      <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="overflow-visible"
        >
          {/* Background Track Circle */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.04)"
            strokeWidth={strokeWidth - 4}
          />

          {/* Slices */}
          {slices.map((slice) => {
            const isHovered = hoveredIdx === slice.index;
            return (
              <circle
                key={slice.index}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={slice.strokeDasharray}
                strokeDashoffset={0}
                transform={`rotate(${slice.rotation} ${center} ${center})`}
                className="transition-all duration-200 cursor-pointer"
                onMouseEnter={() => setHoveredIdx(slice.index)}
                onMouseLeave={() => setHoveredIdx(null)}
                style={{
                  filter: isHovered ? `drop-shadow(0 0 8px ${slice.color}80)` : 'none',
                  opacity: hoveredIdx !== null && !isHovered ? 0.45 : 1,
                }}
              />
            );
          })}
        </svg>

        {/* ── Center Metric Display ── */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center px-2">
          <span className="text-[10px] font-medium text-slate-400 truncate max-w-[85px]">
            {activeSlice ? (activeSlice.label || activeSlice.name) : centerLabel}
          </span>
          <div className="text-base sm:text-lg font-black text-white font-mono tracking-tight leading-tight">
            {activeSlice ? formatValue(activeSlice.value) : (centerValue !== undefined ? centerValue : formatValue(total))}
          </div>
          {activeSlice ? (
            <span className="text-[10px] font-bold font-mono text-cyan-300">
              {activeSlice.percent}%
            </span>
          ) : unit ? (
            <span className="text-[10px] text-slate-400 font-sans">
              {unit}
            </span>
          ) : null}
        </div>
      </div>

      {/* ── Responsive Compact Legend ── */}
      {showLegend && (
        <div className="flex-1 w-full max-w-xs space-y-1 sm:space-y-1.5">
          {slices.map((slice) => {
            const isHovered = hoveredIdx === slice.index;
            return (
              <div
                key={slice.index}
                onMouseEnter={() => setHoveredIdx(slice.index)}
                onMouseLeave={() => setHoveredIdx(null)}
                className={`flex items-center justify-between p-1 px-2 rounded-lg transition-all cursor-pointer ${
                  isHovered
                    ? 'bg-white/[0.08] ring-1 ring-white/20'
                    : 'hover:bg-white/[0.03]'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0 shadow-sm"
                    style={{ backgroundColor: slice.color }}
                  />
                  <span className={`text-xs truncate font-medium ${isHovered ? 'text-white font-bold' : 'text-slate-300'}`}>
                    {slice.label || slice.name}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-xs font-mono flex-shrink-0 ml-2">
                  <span className="text-white font-bold">{formatValue(slice.value)}</span>
                  <span className="text-slate-400 text-[10px] w-8 text-right">({slice.percent}%)</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
