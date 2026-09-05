import React from 'react';
import { Eye, EyeOff, Lock, Unlock, Volume2, VolumeX } from 'lucide-react';

/**
 * Track header control component for Timeline v2.
 * Provides Mute, Lock, and Visibility toggles adhering strictly to ui_clean_standard.
 */
export function TrackHeader({
  track,
  onToggleMute,
  onToggleLock,
  onToggleVisibility,
}) {
  if (!track) return null;

  const isMuted = Boolean(track.muted);
  const isLocked = Boolean(track.locked);
  const isVisible = track.visible !== false;

  return (
    <div className="flex items-center justify-between px-3 py-1.5 bg-neutral-900 border-b border-neutral-800 text-xs select-none">
      <div className="flex items-center gap-2 min-w-0">
        <span
          className={`font-mono font-bold px-1.5 py-0.5 rounded text-[10px] ${
            track.type === 'video'
              ? 'bg-blue-900/60 text-blue-300 border border-blue-700/50'
              : track.type === 'audio'
              ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50'
              : 'bg-amber-900/60 text-amber-300 border border-amber-700/50'
          }`}
        >
          {track.id.replace('track-', '').toUpperCase()}
        </span>
        <span className="truncate text-neutral-300 font-medium" title={track.name}>
          {track.name}
        </span>
      </div>

      <div className="flex items-center gap-1 shrink-0 ml-2">
        {track.type !== 'overlay' && (
          <button
            type="button"
            onClick={() => onToggleMute?.(track.id, !isMuted)}
            title={isMuted ? 'เปิดเสียง' : 'ปิดเสียง'}
            className={`p-1 rounded transition-colors ${
              isMuted
                ? 'text-red-400 bg-red-950/50 hover:bg-red-900/50'
                : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800'
            }`}
          >
            {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
        )}

        <button
          type="button"
          onClick={() => onToggleVisibility?.(track.id, !isVisible)}
          title={isVisible ? 'ซ่อนแทร็ก' : 'แสดงแทร็ก'}
          className={`p-1 rounded transition-colors ${
            !isVisible
              ? 'text-amber-400 bg-amber-950/50 hover:bg-amber-900/50'
              : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800'
          }`}
        >
          {isVisible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
        </button>

        <button
          type="button"
          onClick={() => onToggleLock?.(track.id, !isLocked)}
          title={isLocked ? 'ปลดล็อกแทร็ก' : 'ล็อกแทร็ก'}
          className={`p-1 rounded transition-colors ${
            isLocked
              ? 'text-yellow-400 bg-yellow-950/50 hover:bg-yellow-900/50'
              : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800'
          }`}
        >
          {isLocked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  );
}

export default TrackHeader;
