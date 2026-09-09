import React from 'react';

/**
 * Shared visual shell for timeline items with a left trim handle, draggable
 * body, and right trim handle. Timing policy and update callbacks stay with
 * the caller because captions, stickers, effects, and text overlays do not
 * share the same clamp or persistence rules.
 */
export default function TimelineIntervalItem({
  dataType,
  title,
  className,
  style,
  bodyClassName,
  handleClassName,
  leftHandleTitle,
  rightHandleTitle,
  showLeftHandle = true,
  showRightHandle = true,
  onClick,
  onTrimStart,
  onTrimMove,
  onTrimEnd,
  onBodyStart,
  onBodyMove,
  onBodyEnd,
  children,
}) {
  return (
    <div
      data-timeline-item={dataType}
      onClick={onClick}
      title={title}
      className={`group absolute touch-none select-none rounded text-left text-xs transition-colors duration-150 flex items-center ${className || ''}`}
      style={style}
    >
      {showLeftHandle && (
        <div
          onPointerDown={(e) => onTrimStart?.(e, 'left')}
          onPointerMove={onTrimMove}
          onPointerUp={onTrimEnd}
          onPointerCancel={onTrimEnd}
          title={leftHandleTitle}
          className={`h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-l bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100 ${handleClassName || ''}`}
        >
          <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
        </div>
      )}

      <div
        onPointerDown={onBodyStart}
        onPointerMove={onBodyMove}
        onPointerUp={onBodyEnd}
        onPointerCancel={onBodyEnd}
        className={bodyClassName || 'flex-1 min-w-0 h-full flex items-center overflow-hidden cursor-move'}
      >
        {children}
      </div>

      {showRightHandle && (
        <div
          onPointerDown={(e) => onTrimStart?.(e, 'right')}
          onPointerMove={onTrimMove}
          onPointerUp={onTrimEnd}
          onPointerCancel={onTrimEnd}
          title={rightHandleTitle}
          className={`h-full w-2.5 flex-shrink-0 cursor-ew-resize rounded-r bg-white/[0.04] transition-colors flex items-center justify-center z-10 opacity-60 group-hover:opacity-100 ${handleClassName || ''}`}
        >
          <div className="h-2.5 w-0.5 rounded-full bg-white/40" />
        </div>
      )}
    </div>
  );
}
