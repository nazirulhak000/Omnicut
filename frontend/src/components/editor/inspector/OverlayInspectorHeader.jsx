import React from 'react';

/**
 * Shared identity/timing header for overlay inspectors. The caller supplies
 * the media preview and visual identity because Sticker and Effect use
 * different preview elements, icons, labels, and accent colours.
 */
export default function OverlayInspectorHeader({
  preview,
  icon: Icon,
  kindLabel,
  title,
  duration,
  start,
  end,
  accentClass = 'text-[#25F4EE]',
  previewClassName = 'w-14 h-14 rounded-xl bg-black/50 border border-white/[0.08] flex items-center justify-center p-1.5 flex-shrink-0',
}) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-2xl bg-white/[0.04] border border-white/[0.08]">
      <div className={previewClassName}>
        {preview}
      </div>
      <div className="min-w-0 flex-1">
        <div className={`flex items-center gap-1.5 text-xs font-semibold ${accentClass}`}>
          {Icon && <Icon className="w-3.5 h-3.5" />}
          <span>{kindLabel}</span>
        </div>
        <h3 className="text-sm font-bold text-white truncate mt-0.5">{title}</h3>
        <p className="text-[11px] text-slate-400 font-mono mt-0.5">
          {duration.toFixed(1)}s ({start.toFixed(1)}s – {end.toFixed(1)}s)
        </p>
      </div>
    </div>
  );
}
