import { assertChannelId } from './channelId.js';
import { readActiveChannel, writeActiveChannel, createChannelRequestGuard } from './channelState.js';

let selectionFailure = null;
function initialChannel() {
  if (typeof window === 'undefined') return 'main';
  const query = new URLSearchParams(window.location.search).get('channel');
  if (query !== null) {
    try { return assertChannelId(query); }
    catch { selectionFailure = 'รหัสช่องในลิงก์ไม่ถูกต้อง กรุณาเลือกช่องก่อนเริ่มทำงาน'; return 'main'; }
  }
  try { return readActiveChannel(window.sessionStorage); } catch { return 'main'; }
}

let current = initialChannel();
let revision = 0;
const guard = createChannelRequestGuard(current);
const listeners = new Set();
const switchParticipants = new Set();
export const activeChannel = () => current;
export const channelRuntimeRevision = () => revision;
export const channelSelectionError = () => selectionFailure;
export const captureChannel = () => guard.capture();
export const isCurrentChannel = token => guard.isCurrent(token);
export const subscribeChannel = listener => { listeners.add(listener); return () => listeners.delete(listener); };

export function activateChannel(next) {
  assertChannelId(next);
  if (next === current && !selectionFailure) return;
  // Persist first: a storage failure cannot partially change the active UI.
  if (typeof window !== 'undefined') writeActiveChannel(window.sessionStorage, next);
  current = next;
  revision += 1;
  selectionFailure = null;
  guard.activate(next);
  if (typeof window !== 'undefined') {
    const url = new URL(window.location.href);
    url.searchParams.set('channel', next);
    // A project/session in the old channel cannot become the new entry intent.
    for (const key of ['project', 'session', 'session_id', 'mobile_session', 'product', 'product_id', 'angle', 'angle_id',
      'quick_post', 'mobile_post', 'pid', 'aid', 'eid', 'video', 'cover', 'hook', 'caption', 'hashtags', 'film', 'return']) url.searchParams.delete(key);
    window.history.replaceState(null, '', url);
  }
  for (const listener of listeners) listener();
}

export function registerChannelSwitchParticipant(participant) {
  switchParticipants.add(participant);
  return () => switchParticipants.delete(participant);
}

export function dirtyChannelParticipants() {
  return [...switchParticipants].filter(item => item.isDirty());
}

export async function saveBeforeChannelSwitch() {
  for (const participant of dirtyChannelParticipants()) await participant.save();
  if (dirtyChannelParticipants().length) throw new Error('บันทึกการแก้ไขยังไม่เสร็จ กรุณาลองใหม่');
}

export async function discardBeforeChannelSwitch() {
  for (const participant of dirtyChannelParticipants()) await participant.discard();
}
