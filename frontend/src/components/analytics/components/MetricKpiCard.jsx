import React from 'react';

export default function MetricKpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  accentColor = 'text-cyan-400',
  borderColor = 'border-white/[0.08]',
  bgColor = 'bg-white/[0.02]',
  badge = null,
  badgeColor = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  rightElement = null
}) {
  return (
    <div data-oc-surface="data" className={`relative p-4 rounded-2xl border ${borderColor} ${bgColor} backdrop-blur-xl shadow-lg flex flex-col justify-between transition-all hover:border-white/[0.15]`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold text-slate-400">{title}</span>
        {Icon && (
          <div className={`p-2 rounded-xl bg-white/[0.05] border border-white/[0.08] ${accentColor}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="my-2 flex items-center justify-between gap-2">
        <div className="text-2xl font-black tracking-tight text-white flex items-baseline gap-2">
          <span>{value}</span>
          {badge && (
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${badgeColor}`}>
              {badge}
            </span>
          )}
        </div>
        {rightElement && (
          <div className="shrink-0">{rightElement}</div>
        )}
      </div>

      {subtitle && (
        <div className="text-[11px] text-slate-400 truncate">
          {subtitle}
        </div>
      )}
    </div>
  );
}
