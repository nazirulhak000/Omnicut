import React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

const GUTTER = 144;

/**
 * Shared label-gutter primitive for Timeline rows.
 *
 * Track-specific rows still own their label text and action behavior; this
 * component only owns the repeated gutter layout, icon slot, fold control and
 * event-propagation rules.
 */
export default function TrackLabel({
  icon: Icon,
  children,
  action,
  iconTitle,
  iconClass,
  onIconClick,
  dot,
  labelClass,
  labelTitle,
  fold,
  width,
  slotWidth = 26,
}) {
  return (
    <div
      className="flex items-center gap-1 px-2 text-xs font-medium text-[#9C968F]"
      style={{ width: width ?? GUTTER }}
    >
      <div className="flex min-w-0 flex-1 items-center gap-1.5">
        <span className="flex flex-shrink-0 items-center gap-1.5" style={{ width: slotWidth }}>
          {fold && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); fold.onToggle?.(); }}
              title={fold.title}
              aria-expanded={!fold.collapsed}
              className="-m-0.5 flex-shrink-0 rounded p-0.5 text-[#6F6A64] transition-colors hover:bg-[#2C2B27] hover:text-[#EDE9E3]"
            >
              {fold.collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
          )}
          {Icon && onIconClick ? (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onIconClick(); }}
              title={iconTitle}
              className="-m-0.5 flex-shrink-0 rounded p-0.5 transition-colors hover:bg-[#2C2B27] hover:text-[#EDE9E3]"
            >
              <Icon className={`h-3 w-3 ${iconClass || ''}`} />
            </button>
          ) : Icon ? (
            <Icon className="h-3 w-3 flex-shrink-0" />
          ) : null}
          {dot && (
            <span
              className="h-[7px] w-[7px] flex-shrink-0 rounded-full"
              style={dot.hollow
                ? { boxShadow: `inset 0 0 0 1.5px ${dot.colour}`, opacity: 0.5 }
                : { background: dot.colour }}
            />
          )}
        </span>
        <span className={`truncate ${labelClass || ''}`} title={labelTitle ?? (typeof children === 'string' ? children : undefined)}>
          {children}
        </span>
      </div>
      {action}
    </div>
  );
}
