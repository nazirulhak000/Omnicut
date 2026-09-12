import React from 'react';

// Shared top command-bar shell used by every main page (ProductToClip,
// ContentTrackerHub, EditorShell, ExportGallery, MediaAssetsHub,
// SystemSettings). Extracted so the icon box, eyebrow/title typography, and
// outer card chrome can't drift apart page-to-page the way they had before
// this existed -- each page still owns its own badges/actions/second row.
export function PageHeader({
  icon: Icon,
  iconGradient = 'from-[#25F4EE]/20 to-[#FE2C55]/20',
  iconColor = 'text-[#25F4EE]',
  eyebrow,
  title,
  titlePrefix,
  badges,
  quickSwitcher,
  actions,
  secondRow,
  titleClassName = 'text-base sm:text-lg md:text-xl font-black text-white tracking-tight',
}) {
  return (
    <div className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-3 sm:p-3.5 shadow-lg space-y-2.5 sm:space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-3">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <div className={`w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-tr ${iconGradient} border border-white/[0.1] flex items-center justify-center flex-shrink-0`}>
            {Icon && <Icon className={`w-4 h-4 sm:w-5 sm:h-5 ${iconColor}`} />}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
              <span className="text-[10px] sm:text-xs font-bold text-slate-400 uppercase tracking-wider">
                {eyebrow}
              </span>
              {badges}
            </div>
            <h1 className={`flex items-center gap-1.5 ${titleClassName}`}>
              {titlePrefix}
              <span className="truncate">{title}</span>
            </h1>
          </div>

          {quickSwitcher}
        </div>

        {actions && (
          <div className="flex items-center gap-1.5 sm:gap-2.5 flex-wrap justify-between sm:justify-end flex-shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-white/[0.06]">
            {actions}
          </div>
        )}
      </div>

      {secondRow}
    </div>
  );
}
