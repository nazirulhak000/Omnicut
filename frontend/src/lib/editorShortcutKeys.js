/**
 * Pure keyboard-shortcut decision for the editor timeline.
 *
 * Kept free of React/DOM so it can be unit tested. The hook maps the returned
 * action to a handler; `preventDefault` tells it whether to swallow the event.
 *
 * Modifier rule: with Ctrl/Meta/Alt held, only the explicit combos below are
 * claimed (Ctrl+Z, Shift+Ctrl+Z, Ctrl+Y, Ctrl+B). Everything else (Ctrl+S,
 * Ctrl++, Ctrl+-, Alt+...) is left to the browser/app, never touching the
 * unmodified single-key verbs.
 */

const NONE = Object.freeze({ action: 'none', preventDefault: false });

// <input> types that take typed characters (and so own Backspace, Delete,
// Space and the arrow keys). Every other type -- range, checkbox, radio,
// button, color, file ... -- only holds a value, so the editor may keep the
// history keys working while one of them has focus.
const TEXT_ENTRY_INPUT_TYPES = new Set([
  'text', 'search', 'number', 'email', 'url', 'password', 'tel',
  'date', 'time', 'datetime-local', 'month', 'week',
]);

const inputTypeOf = (el) => String(el.type || 'text').toLowerCase();

/** True when focus is in a text-entry control that owns its own keystrokes. */
export function isEditableTarget(el) {
  if (!el) return false;
  if (el.isContentEditable) return true;
  if (el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') return true;
  if (el.tagName === 'INPUT') return TEXT_ENTRY_INPUT_TYPES.has(inputTypeOf(el));
  return false;
}

/** True for an <input> that is not a text field: slider, checkbox, radio, button... */
export function isNonTextInput(el) {
  return Boolean(el) && el.tagName === 'INPUT' && !TEXT_ENTRY_INPUT_TYPES.has(inputTypeOf(el));
}

/**
 * Whether the editor must leave `action` alone because of where focus is.
 *
 * A text field owns every key. A slider/checkbox/radio/button input owns Space,
 * the arrows and Delete/Backspace (nudging a value, toggling it, or -- for
 * Delete -- removing a clip by accident while the user meant the control), so
 * only undo/redo get through: those are what a user reaches for right after
 * dragging a slider, and no such control uses Ctrl+Z or Ctrl+Y itself.
 *
 * @param {{ tagName?: string, type?: string, isContentEditable?: boolean } | null} el
 * @param {string} action result of classifyShortcut
 */
export function shouldIgnoreShortcutTarget(el, action) {
  if (isEditableTarget(el)) return true;
  if (isNonTextInput(el)) return action !== 'undo' && action !== 'redo';
  return false;
}

const act = (action, extra = {}) => ({ action, preventDefault: true, ...extra });

/**
 * @param {{ key?: string, ctrlKey?: boolean, metaKey?: boolean, altKey?: boolean, shiftKey?: boolean }} event
 * @param {{ zen?: boolean }} [context]
 * @returns {{ action: string, preventDefault: boolean, delta?: number }}
 */
export function classifyShortcut(event, context = {}) {
  const key = event && typeof event.key === 'string' ? event.key : '';
  if (!key) return NONE;

  const mod = Boolean(event.ctrlKey || event.metaKey);
  if (mod) {
    const k = key.toLowerCase();
    if (!event.altKey) {
      if (k === 'z') return act(event.shiftKey ? 'redo' : 'undo');
      if (k === 'y') return act('redo');
      if (k === 'b') return act('split');
    }
    return NONE;
  }
  // Alt-modified keys belong to the browser/OS menu bar, not the editor.
  if (event.altKey) return NONE;

  if (key === 'Escape') return context.zen ? act('exitZen') : NONE;

  switch (key) {
    case ' ': return act('togglePlay');
    case 's': case 'S': return act('split');
    case 'j': case 'J': return act('jump', { delta: -1.0 });
    case 'k': case 'K': return act('togglePlay');
    case 'l': case 'L': return act('jump', { delta: 1.0 });
    case 'Delete': case 'Backspace': return act('delete');
    case 'ArrowLeft': return act('jump', { delta: -(event.shiftKey ? 1 : 1 / 30) });
    case 'ArrowRight': return act('jump', { delta: event.shiftKey ? 1 : 1 / 30 });
    case '+': case '=': return act('zoomIn');
    case '-': case '_': return act('zoomOut');
    // preventDefault is decided by the hook (needs a selected, non-first clip).
    case 'f': case 'F': return { action: 'toggleFade', preventDefault: false };
    case 'n': case 'N': return act('toggleSnap');
    case 'm': case 'M': return act('cycleCutout');
    default: return NONE;
  }
}

/**
 * The list the shortcuts dialog shows, kept beside classifyShortcut so the two
 * are edited together. A row that classifyShortcut decides carries `probes`:
 * events and the action they must come back as. editorShortcutKeys.test.js
 * replays them, so the dialog cannot advertise a key the editor stopped
 * handling. Rows without probes are handled elsewhere (named in the comment).
 *
 * The five tab rows mirror Sidebar's labels and useKeyboardShortcuts' tabMap;
 * a contract test compares all three, and there is no "6": that key does nothing.
 */
export const SHORTCUT_GROUPS = Object.freeze([
  {
    category: 'การสลับแท็บเมนูหลัก',
    shortcuts: [
      { keys: '1', desc: '1. สินค้า → คลิป' },
      { keys: '2', desc: '2. แทร็กเกอร์ 4 เฟส' },
      { keys: '3', desc: '3. ตัดต่อ & สร้างคลิป' },
      { keys: '4', desc: '4. Export Gallery' },
      { keys: '5', desc: '5. Media Assets Hub' },
    ],
  },
  {
    category: 'ไทม์ไลน์และการตัดต่อ',
    shortcuts: [
      {
        keys: 'S / Ctrl+B',
        desc: 'ตัดแบ่งคลิปตรงหัวอ่าน',
        probes: [{ event: { key: 's' }, action: 'split' }, { event: { key: 'b', ctrlKey: true }, action: 'split' }],
      },
      {
        keys: 'Del / Backspace',
        desc: 'ลบคลิปหรือคำบรรยายที่เลือก',
        probes: [{ event: { key: 'Delete' }, action: 'delete' }, { event: { key: 'Backspace' }, action: 'delete' }],
      },
      { keys: 'Ctrl+Z', desc: 'ย้อนกลับ', probes: [{ event: { key: 'z', ctrlKey: true }, action: 'undo' }] },
      {
        keys: 'Ctrl+Y / Ctrl+Shift+Z',
        desc: 'ทำซ้ำ',
        probes: [
          { event: { key: 'y', ctrlKey: true }, action: 'redo' },
          { event: { key: 'z', ctrlKey: true, shiftKey: true }, action: 'redo' },
        ],
      },
      {
        keys: 'J / K / L',
        desc: 'ถอยหลัง 1s / เล่น-หยุด / เดินหน้า 1s',
        probes: [
          { event: { key: 'j' }, action: 'jump', delta: -1 },
          { event: { key: 'k' }, action: 'togglePlay' },
          { event: { key: 'l' }, action: 'jump', delta: 1 },
        ],
      },
      {
        keys: '← / →',
        desc: 'ขยับหัวอ่านทีละ 1 เฟรม (กด Shift ขยับทีละ 1s)',
        probes: [
          { event: { key: 'ArrowLeft' }, action: 'jump', delta: -1 / 30 },
          { event: { key: 'ArrowRight', shiftKey: true }, action: 'jump', delta: 1 },
        ],
      },
      {
        keys: '+ / -',
        desc: 'ปรับระดับการซูมไทม์ไลน์',
        probes: [{ event: { key: '+' }, action: 'zoomIn' }, { event: { key: '-' }, action: 'zoomOut' }],
      },
      { keys: 'Ctrl + Scroll', desc: 'ซูมไทม์ไลน์เข้า / ออก' }, // useTimelineKeyboard (wheel)
      {
        keys: 'N',
        desc: 'เปิด / ปิด แม่เหล็กดูดคลิป (Magnetic Snap)',
        probes: [{ event: { key: 'n' }, action: 'toggleSnap' }],
      },
      {
        keys: 'M',
        desc: 'สลับโหมดพรีวิว Cutout (ปกติ / หมากรุก / มาสก์)',
        probes: [{ event: { key: 'm' }, action: 'cycleCutout' }],
      },
      {
        keys: 'F',
        desc: 'เปิด / ปิด เฟดเข้าที่คลิปที่เลือก (ไม่รวมคลิปแรก)',
        probes: [{ event: { key: 'f' }, action: 'toggleFade' }],
      },
      { keys: '[ / ]', desc: 'ย้ายคลิปที่โฟกัสอยู่ไปก่อน / หลัง 1 ลำดับ' }, // TimelineClip onKeyDown
      { keys: 'Enter', desc: 'ตัดแบ่งท่อนคำบรรยายตรงเคอร์เซอร์' }, // CuesTranscriptInspector
    ],
  },
  {
    category: 'การควบคุมมีเดีย & ระบบ',
    shortcuts: [
      { keys: 'Space', desc: 'เล่น / หยุด วิดีโอ', probes: [{ event: { key: ' ' }, action: 'togglePlay' }] },
      {
        keys: 'Esc',
        desc: 'ปิดหน้าต่างป๊อปอัป / ออกจากโหมดพรีวิวเต็มพื้นที่',
        probes: [{ event: { key: 'Escape' }, context: { zen: true }, action: 'exitZen' }],
      },
      { keys: 'Ctrl + S', desc: 'บันทึกโปรเจกต์' }, // EditorShell
      { keys: '?', desc: 'เปิดหน้าต่างคีย์ลัด' }, // useKeyboardShortcuts
    ],
  },
]);
