import React from 'react';
import { AlertTriangle } from 'lucide-react';

/**
 * Amber bar under the editor header when the server says the saved voice cuts
 * could not be used (the voiceover was re-made, or its file no longer matches
 * the one that was cut). The reason is the backend's own Thai text; the bar
 * stays until the user acknowledges it, and it says what happened -- never a
 * silent drop. Same look as ProjectRevisionNotice, a plain dismiss button.
 */
export default function VoiceEditNotice({ notice, onDismiss }) {
  if (!notice?.reason) return null;
  return (
    <div
      role="alert"
      data-voice-edit-notice={notice.kind || 'notice'}
      className="flex flex-shrink-0 flex-wrap items-center gap-2 border-b border-amber-500/25 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-200"
    >
      <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
      <span className="min-w-0 flex-1">{notice.reason}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-md border border-white/10 px-2 py-1 text-amber-100/80 hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757]"
        >
          รับทราบ
        </button>
      )}
    </div>
  );
}
