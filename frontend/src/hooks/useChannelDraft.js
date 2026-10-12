import { useEffect, useRef } from 'react';
import { registerChannelSwitchParticipant } from '../lib/channelRuntime.js';
import { createChannelDraftParticipant } from '../lib/channelDraft.js';

export function useChannelDraft(value, handlers) {
  const ref = useRef(null);
  if (!ref.current) ref.current = createChannelDraftParticipant(value);
  ref.current.observe(value, handlers);
  useEffect(() => registerChannelSwitchParticipant({
    isDirty: () => ref.current.isDirty(),
    save: () => ref.current.save({ forSwitch: true }),
    discard: () => ref.current.discard(),
  }), []);
  useEffect(() => {
    const guardUnload = event => {
      if (!ref.current.isDirty()) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', guardUnload);
    return () => window.removeEventListener('beforeunload', guardUnload);
  }, []);
  return ref.current;
}
