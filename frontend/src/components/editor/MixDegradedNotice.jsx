import React from 'react';
import { AlertTriangle } from 'lucide-react';

import { mixDegradedNotice } from '../../lib/mixDegradedNotice.js';

/**
 * Amber bar inside the "render finished" card when the full audio mix failed
 * and the backend fell back to voice-only. Renders nothing for a healthy mix.
 */
export default function MixDegradedNotice({ result }) {
  const notice = mixDegradedNotice(result);
  if (!notice) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-[11px] leading-snug text-amber-200"
    >
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-amber-400" />
      <span>
        <span className="font-bold">{notice.title}</span>
        {' '}
        {notice.message}
      </span>
    </div>
  );
}
