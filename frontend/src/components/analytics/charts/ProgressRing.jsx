import React from 'react';

/**
 * ProgressRing - Pure SVG Single Circular Progress Ring
 */
export function ProgressRing({
  percentage = 0,
  size = 64,
  strokeWidth = 6,
  color = '#25F4EE',
  trackColor = '#27272a',
  glow = true,
  children,
}) {
  const cleanPercent = Math.min(100, Math.max(0, Number(percentage) || 0));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (cleanPercent / 100) * circumference;
  const center = size / 2;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="transform -rotate-90"
      >
        {glow && (
          <filter id={`glow-${size}-${color.replace('#', '')}`}>
            <feDropShadow dx="0" dy="0" stdDeviation="2.5" floodColor={color} floodOpacity="0.4" />
          </filter>
        )}
        {/* Track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          stroke={trackColor}
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Progress Arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          filter={glow ? `url(#glow-${size}-${color.replace('#', '')})` : undefined}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      {/* Center slot */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
        {children || (
          <span className="text-xs font-bold font-mono text-zinc-200">
            {Math.round(cleanPercent)}%
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * ConcentricRings - Multi-tier concentric rings (Activity Ring style)
 * Perfect for showing media readiness: Images (Outer), Videos (Middle), Scripts (Inner).
 */
export function ConcentricRings({
  rings = [], // Array of { label, percentage, color, icon, detail }
  size = 170,
  strokeWidth = 10,
  gap = 4,
}) {
  const center = size / 2;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      {/* SVG Concentric Rings */}
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="transform -rotate-90"
        >
          {rings.map((ring, idx) => {
            const currentRadius = center - (strokeWidth / 2) - idx * (strokeWidth + gap);
            if (currentRadius <= strokeWidth) return null;

            const circumference = 2 * Math.PI * currentRadius;
            const cleanPercent = Math.min(100, Math.max(0, Number(ring.percentage) || 0));
            const strokeDashoffset = circumference - (cleanPercent / 100) * circumference;

            return (
              <g key={ring.label || idx}>
                {/* Track */}
                <circle
                  cx={center}
                  cy={center}
                  r={currentRadius}
                  stroke="#27272a"
                  strokeWidth={strokeWidth}
                  fill="transparent"
                  strokeOpacity="0.5"
                />
                {/* Ring Arc */}
                <circle
                  cx={center}
                  cy={center}
                  r={currentRadius}
                  stroke={ring.color || '#25F4EE'}
                  strokeWidth={strokeWidth}
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  fill="transparent"
                  className="transition-all duration-700 ease-out"
                />
              </g>
            );
          })}
        </svg>

        {/* Center aggregate percentage or icon */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
          <span className="text-xl font-black font-mono text-zinc-100">
            {rings.length > 0
              ? Math.round(rings.reduce((acc, r) => acc + (r.percentage || 0), 0) / rings.length)
              : 0}%
          </span>
          <span className="text-[10px] text-zinc-400 font-medium">ความพร้อมเฉลี่ย</span>
        </div>
      </div>

      {/* Legend & Details */}
      <div className="flex-1 w-full space-y-2.5">
        {rings.map((ring) => (
          <div
            key={ring.label}
            className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700 transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <span
                className="w-3 h-3 rounded-full shrink-0 shadow-sm"
                style={{ backgroundColor: ring.color, boxShadow: `0 0 8px ${ring.color}60` }}
              />
              <div>
                <span className="text-xs font-semibold text-zinc-200">{ring.label}</span>
                {ring.detail && (
                  <p className="text-[11px] text-zinc-400">{ring.detail}</p>
                )}
              </div>
            </div>
            <span className="text-xs font-mono font-bold text-zinc-200">
              {Math.round(ring.percentage || 0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * RadialGauge - Semi-circular arc gauge for storage/quota capacity (180 degrees)
 */
export function RadialGauge({
  percentage = 0,
  size = 180,
  strokeWidth = 14,
  label = 'พื้นที่ใช้ไป',
  sublabel = '',
  statusText = 'ปลอดภัย',
}) {
  const cleanPercent = Math.min(100, Math.max(0, Number(percentage) || 0));
  const center = size / 2;
  const radius = center - strokeWidth;
  const arcLength = Math.PI * radius; // 180 degrees half circumference
  const strokeDashoffset = arcLength - (cleanPercent / 100) * arcLength;

  // Determine color based on threshold
  let gaugeColor = '#10B981'; // Emerald (< 70%)
  if (cleanPercent >= 85) {
    gaugeColor = '#EF4444'; // Red
  } else if (cleanPercent >= 70) {
    gaugeColor = '#F59E0B'; // Amber
  }

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size / 2 + 15 }}>
        <svg
          width={size}
          height={size / 2 + 15}
          viewBox={`0 0 ${size} ${size / 2 + 15}`}
        >
          {/* Background Half Arc */}
          <path
            d={`M ${strokeWidth},${center} A ${radius},${radius} 0 0,1 ${size - strokeWidth},${center}`}
            fill="none"
            stroke="#27272a"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Progress Half Arc */}
          <path
            d={`M ${strokeWidth},${center} A ${radius},${radius} 0 0,1 ${size - strokeWidth},${center}`}
            fill="none"
            stroke={gaugeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={arcLength}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center reading inside arc */}
        <div className="absolute inset-x-0 bottom-0 flex flex-col items-center justify-center text-center">
          <span className="text-2xl font-black font-mono text-zinc-100">
            {cleanPercent.toFixed(1)}%
          </span>
          <span className="text-[11px] text-zinc-400">{label}</span>
        </div>
      </div>

      {sublabel && (
        <div className="mt-2 text-center">
          <p className="text-xs text-zinc-400">{sublabel}</p>
          <span
            className={`inline-block mt-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
              cleanPercent >= 85
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : cleanPercent >= 70
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
            }`}
          >
            {statusText}
          </span>
        </div>
      )}
    </div>
  );
}

export default ProgressRing;
