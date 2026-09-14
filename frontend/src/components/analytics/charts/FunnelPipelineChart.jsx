import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, AlertTriangle, Play, FileText, Film, Share2 } from 'lucide-react';

const STAGE_ICONS = {
  scripted: FileText,
  in_production: Film,
  rendered: Play,
  posted: CheckCircle2,
};

const STAGE_THEMES = {
  scripted: {
    border: 'border-cyan-500/30',
    hoverBorder: 'hover:border-cyan-400/60',
    bg: 'bg-cyan-500/10',
    glow: 'from-cyan-500/20 to-blue-500/10',
    text: 'text-cyan-400',
    badge: 'bg-cyan-500/20 text-cyan-300',
    bar: 'bg-cyan-400',
  },
  in_production: {
    border: 'border-amber-500/30',
    hoverBorder: 'hover:border-amber-400/60',
    bg: 'bg-amber-500/10',
    glow: 'from-amber-500/20 to-orange-500/10',
    text: 'text-amber-400',
    badge: 'bg-amber-500/20 text-amber-300',
    bar: 'bg-amber-400',
  },
  rendered: {
    border: 'border-purple-500/30',
    hoverBorder: 'hover:border-purple-400/60',
    bg: 'bg-purple-500/10',
    glow: 'from-purple-500/20 to-indigo-500/10',
    text: 'text-purple-400',
    badge: 'bg-purple-500/20 text-purple-300',
    bar: 'bg-purple-400',
  },
  posted: {
    border: 'border-emerald-500/30',
    hoverBorder: 'hover:border-emerald-400/60',
    bg: 'bg-emerald-500/10',
    glow: 'from-emerald-500/20 to-teal-500/10',
    text: 'text-emerald-400',
    badge: 'bg-emerald-500/20 text-emerald-300',
    bar: 'bg-emerald-400',
  },
};

/**
 * FunnelPipelineChart - Interactive 4-stage pipeline flow
 * Renders an interconnected funnel pipeline with step cards, glow connectors, conversion rates, and bottleneck alerts.
 */
export default function FunnelPipelineChart({
  stages = [],
  conversionRates = {},
  bottleneck = null,
  totalProjects = 0,
}) {
  const [hoveredKey, setHoveredKey] = useState(null);

  const defaultStages = [
    { key: 'scripted', label: 'สคริปต์พร้อม', count: 0, percentage: 0 },
    { key: 'in_production', label: 'กำลังตัดต่อ', count: 0, percentage: 0 },
    { key: 'rendered', label: 'ตัดต่อเสร็จ', count: 0, percentage: 0 },
    { key: 'posted', label: 'ลงโพสต์แล้ว', count: 0, percentage: 0 },
  ];

  const pipelineStages = stages.length === 4 ? stages : defaultStages;
  const maxCount = Math.max(...pipelineStages.map((s) => s.count), 1);

  return (
    <div className="w-full space-y-4">
      {/* Funnel Connected Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 relative">
        {pipelineStages.map((stage, idx) => {
          const theme = STAGE_THEMES[stage.key] || STAGE_THEMES.scripted;
          const Icon = STAGE_ICONS[stage.key] || FileText;
          const isBottleneck = bottleneck?.stage === stage.key;
          const isHovered = hoveredKey === stage.key;
          const prevStage = idx > 0 ? pipelineStages[idx - 1] : null;
          
          // Conversion rate from previous stage
          const convRate = prevStage && prevStage.count > 0
            ? Math.round((stage.count / prevStage.count) * 100)
            : null;

          return (
            <div
              key={stage.key}
              onMouseEnter={() => setHoveredKey(stage.key)}
              onMouseLeave={() => setHoveredKey(null)}
              className={`relative rounded-xl border p-4 transition-all duration-300 flex flex-col justify-between overflow-hidden cursor-default ${
                isHovered
                  ? `${theme.hoverBorder} shadow-lg shadow-black/40 scale-[1.02] bg-zinc-900/90`
                  : `${theme.border} bg-zinc-900/50 hover:bg-zinc-900/70`
              }`}
            >
              {/* Background Neon Ambient Glow */}
              <div
                className={`absolute -top-12 -right-12 w-28 h-28 rounded-full bg-gradient-to-br ${theme.glow} blur-2xl pointer-events-none transition-opacity duration-300 ${
                  isHovered ? 'opacity-100' : 'opacity-40'
                }`}
              />

              {/* Header: Stage Step & Icon */}
              <div>
                <div className="flex items-center justify-between mb-3 relative z-10">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <span className="text-xs font-semibold text-zinc-300">{stage.label}</span>
                  </div>
                  <div className={`p-1.5 rounded-lg ${theme.bg} ${theme.text}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                </div>

                {/* Primary Metric Count */}
                <div className="flex items-baseline gap-2 mb-1 relative z-10">
                  <span className={`text-2xl font-black tracking-tight ${theme.text}`}>
                    {stage.count}
                  </span>
                  <span className="text-xs text-zinc-400 font-medium">คลิป</span>
                  <span className="text-xs font-medium text-zinc-400 ml-auto">
                    {stage.percentage || (totalProjects > 0 ? Math.round((stage.count / totalProjects) * 100) : 0)}%
                  </span>
                </div>

                {/* Relative Volume Bar */}
                <div className="w-full bg-zinc-800/80 h-1.5 rounded-full overflow-hidden my-2 relative z-10">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${theme.bar}`}
                    style={{ width: `${Math.min(100, Math.max(6, (stage.count / maxCount) * 100))}%` }}
                  />
                </div>
              </div>

              {/* Footer: Conversion & Bottleneck alerts */}
              <div className="pt-2 border-t border-zinc-800/60 mt-2 flex items-center justify-between text-[11px] relative z-10">
                {idx === 0 ? (
                  <span className="text-zinc-400">จุดเริ่มต้นกระบวนการ</span>
                ) : (
                  <div className="flex items-center gap-1">
                    <span className="text-zinc-400">ส่งต่อจากขั้นก่อน:</span>
                    <span className={`font-semibold ${convRate != null && convRate < 50 ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {convRate != null ? `${convRate}%` : '—'}
                    </span>
                  </div>
                )}

                {isBottleneck && (
                  <span className="flex items-center gap-1 text-amber-400 font-medium bg-amber-500/10 px-1.5 py-0.5 rounded text-[10px]">
                    <AlertTriangle className="w-3 h-3" />
                    คอขวด
                  </span>
                )}
              </div>

              {/* Connecting arrow indicator for desktop (between cards) */}
              {idx < pipelineStages.length - 1 && (
                <div className="hidden md:flex absolute -right-3.5 top-1/2 -translate-y-1/2 z-20 w-7 h-7 rounded-full bg-zinc-950 border border-zinc-700 items-center justify-center text-zinc-400 shadow-md">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Conversion Rate Ribbon */}
      <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-zinc-400">อัตราความสำเร็จรวม (End-to-End Success Rate):</span>
          <span className="font-bold text-emerald-400 text-sm">
            {pipelineStages[0]?.count > 0
              ? `${Math.round((pipelineStages[3]?.count / pipelineStages[0]?.count) * 100)}%`
              : '0%'}
          </span>
          <span className="text-zinc-400 text-[11px]">(แปลงจากสคริปต์สู่โพสต์จริง)</span>
        </div>

        {bottleneck && (
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg text-amber-300 text-[11px]">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>
              จุดติดค้างหลักอยู่ที่ช่วง <strong className="text-amber-200">{bottleneck.stage_label || bottleneck.stage}</strong> ({bottleneck.count} คลิป)
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
