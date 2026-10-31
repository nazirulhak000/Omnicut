import { normalizeThemePreferences } from './themeResolver.js';
import { readThemePreferences, saveThemePreferences } from './themeStorage.js';

/** Reactive preferences transaction, independent of React and the browser DOM. */
export function createUiThemeSession(storage) {
  const listeners = new Set();
  let stored = readThemePreferences(storage);
  let snapshot = {
    preferences: stored.preferences, readOnly: stored.readOnly, revision: 0,
    status: { kind: stored.readOnly ? 'error' : 'idle', message: stored.readOnly ? 'ข้อมูลธีมมาจากเวอร์ชันใหม่กว่า จึงเปิดแบบอ่านอย่างเดียว' : '' },
  };
  const publish = (next) => {
    snapshot = next;
    for (const listener of listeners) listener();
  };
  const reloadPreferences = () => {
    const next = readThemePreferences(storage);
    if (next.revision === stored.revision && next.readOnly === stored.readOnly && next.error === stored.error) return snapshot;
    stored = next;
    publish({
      preferences: next.preferences, readOnly: next.readOnly, revision: snapshot.revision + 1,
      status: { kind: next.readOnly ? 'error' : 'idle', message: next.readOnly ? 'ข้อมูลธีมมาจากเวอร์ชันใหม่กว่า จึงเปิดแบบอ่านอย่างเดียว' : 'โหลดค่าธีมที่เปลี่ยนจากอีกแท็บแล้ว' },
    });
    return snapshot;
  };
  const applyPreferences = (draft, { expectedRevision = snapshot.revision } = {}) => {
    if (snapshot.readOnly) return { ok: false, error: 'future-schema' };
    if (expectedRevision !== snapshot.revision) return { ok: false, conflict: true, error: 'conflict' };
    const next = normalizeThemePreferences(draft);
    const result = saveThemePreferences(next, storage, { expectedRevision: stored.revision });
    if (!result.ok && result.error !== 'storage-unavailable') {
      reloadPreferences();
      return { ...result, conflict: result.error === 'conflict' };
    }
    if (result.ok) stored = { ...stored, preferences: next, revision: result.revision, error: null };
    publish({
      preferences: next, readOnly: false, revision: snapshot.revision + 1,
      status: result.ok
        ? { kind: 'saved', message: 'ใช้ธีมและบันทึกแล้ว' }
        : { kind: 'session', message: 'ใช้ธีมชั่วคราวในแท็บนี้ แต่บันทึกลงเครื่องไม่ได้' },
    });
    return { ok: true, persisted: result.ok, preferences: next, error: result.error };
  };
  return {
    getSnapshot: () => snapshot,
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener); },
    applyPreferences, reloadPreferences,
  };
}
