import React from 'react';

/**
 * MetricKpiCard - Obsidian Pro Dark NLE KPI Display Card
 * Displays high-density key performance indicators with crisp typography,
 * semantic color accents, optional trend/badge, and accessible data contrast.
 */
export default function MetricKpiCard({
  title,
  value,
  unit = null,
  subtitle = null,
  icon: Icon = null,
  accentColor = 'text-cyan-400',
  borderColor = 'border-white/[0.08]',
  bgColor = 'bg-[#0D111A]/90',
  badge = null,
  badgeColor = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  rightElement = null,
  trend = null, // e.g. { direction: 'up' | 'down' | 'neutral', label: '+12%' }
  tooltip = null,
  className = '',
}) {
  const displayValue = value ?? '-';

  return (
    <div
      className={`relative p-4 rounded-2xl border ${borderColor} ${bgColor} backdrop-blur-xl shadow-sm hover:border-white/[0.16] hover:bg-[#0D111A] min-h-[136px] flex flex-col justify-between transition-all duration-200 group ${className}`}
      title={tooltip || undefined}
    >
      {/* Header: Title & Icon */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium text-slate-400 leading-tight">
          {title}
        </span>
        {Icon && (
          <div className={`p-2 rounded-xl bg-white/[0.04] border border-white/[0.08] ${accentColor} flex-shrink-0 transition-colors group-hover:bg-white/[0.08]`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Main Metric Value & Right Action/Graphic */}
      <div className="my-2 flex items-center justify-between gap-2">
        <div className="text-2xl font-black tracking-tight text-white flex items-baseline gap-2 flex-wrap font-mono tabular-nums">
          <span>{displayValue}</span>
          {unit && (
            <span className="text-xs font-medium text-slate-400 font-sans">{unit}</span>
          )}
          {badge && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeColor} font-sans tracking-wide`}>
              {badge}
            </span>
          )}
          {trend && (
            <span
              className={`text-[11px] font-bold px-1.5 py-0.5 rounded flex items-center gap-0.5 font-sans ${
                trend.direction === 'up'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : trend.direction === 'down'
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  : 'bg-white/[0.05] text-slate-400 border border-white/[0.08]'
              }`}
            >
              {trend.label}
            </span>
          )}
        </div>
        {rightElement && (
          <div className="shrink-0">{rightElement}</div>
        )}
      </div>

      {/* Contextual Subtitle */}
      {subtitle && (
        <div className="text-[11px] text-slate-400 truncate leading-normal pt-1.5 border-t border-white/[0.04] min-h-[1.5rem] mt-auto">
          {subtitle}
        </div>
      )}
    </div>
  );
}
