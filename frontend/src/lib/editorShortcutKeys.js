/**
 * Pure keyboard-shortcut decision for the editor timeline.
 *
 * Kept free of React/DOM so it can be unit tested. The hook maps the returned
 * action to a handler; `preventDefault` tells it whether to swallow the event.
 *
 * Modifier rule: with Ctrl/Meta/Alt held, only the explicit combos below are
 * claimed (Ctrl+Z, Shift+Ctrl+Z, Ctrl+Y, Ctrl+B, Ctrl+Alt+C/V). Everything else (Ctrl+S,
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
 * @param {{ zen?: boolean, multiSelect?: boolean, hasRange?: boolean }} [context]
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
    // Ctrl+Alt+C / Ctrl+Alt+V: copy / paste clip settings (the Premiere-style
    // "paste attributes" combo). Plain Ctrl+C / Ctrl+V stay with the browser,
    // and Cmd+Alt+C (DevTools on macOS) is not claimed.
    if (event.altKey && event.ctrlKey && !event.metaKey && !event.shiftKey) {
      if (k === 'c') return act('copySettings');
      if (k === 'v') return act('pasteSettings');
    }
    return NONE;
  }
  // Alt-modified keys belong to the browser/OS menu bar, not the editor.
  if (event.altKey) return NONE;

  // Zen mode takes Escape first, then a marked In/Out range, then a multi-clip
  // selection (and nothing -- NONE -- when only one thing is selected).
  if (key === 'Escape') {
    if (context.zen) return act('exitZen');
    if (context.hasRange) return act('clearRange');
    return context.multiSelect ? act('clearSelection') : NONE;
  }

  switch (key) {
    case ' ': return act('togglePlay');
    case 's': case 'S': return act('split');
    case 'j': case 'J': return act('jump', { delta: -1.0 });
    case 'k': case 'K': return act('togglePlay');
    case 'l': case 'L': return act('jump', { delta: 1.0 });
    // Shift+Delete ripples the marked In-Out range (the hook falls back to a
    // plain delete while no range is marked). Backspace stays a plain delete.
    case 'Delete': return act(event.shiftKey ? 'rippleRange' : 'delete');
    case 'Backspace': return act('delete');
    // In / Out marks at the playhead for a range cut. Free keys: the tab keys
    // are digits, and Ctrl/Alt combos never reach this switch.
    case 'i': case 'I': return act('markIn');
    case 'o': case 'O': return act('markOut');
    case 'ArrowLeft': return act('jump', { delta: -(event.shiftKey ? 1 : 1 / 30) });
    case 'ArrowRight': return act('jump', { delta: event.shiftKey ? 1 : 1 / 30 });
    // Manual-cut verbs. Up/Down and Home/End are free in the editor; Ctrl+Q/W
    // never reach here (the modifier branch above leaves them to the browser).
    case 'q': case 'Q': return act('trimHead');
    case 'w': case 'W': return act('trimTail');
    case 'ArrowUp': return act('prevEdit');
    case 'ArrowDown': return act('nextEdit');
    case 'Home': return act('seekStart');
    case 'End': return act('seekEnd');
    case '+': case '=': return act('zoomIn');
    case '-': case '_': return act('zoomOut');
    // preventDefault is decided by the hook (needs a selected, non-first clip).
    case 'f': case 'F': return { action: 'toggleFade', preventDefault: false };
    case 'n': case 'N': return act('toggleSnap');
    case 'm': case 'M': return act('cycleCutout');
    // Camera keyframes of the selected clip: D toggles a diamond at the
    // playhead, , / . (the < / > keys) jump to the previous / next one.
    case 'd': case 'D': return act('toggleKeyframe');
    case ',': case '<': return act('prevKeyframe');
    case '.': case '>': return act('nextKeyframe');
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
    category: 'ตัดและแก้คลิป',
    shortcuts: [
      {
        keys: 'S / Ctrl+B',
        desc: 'ตัดแบ่งคลิปตรงหัวอ่าน',
        probes: [{ event: { key: 's' }, action: 'split' }, { event: { key: 'b', ctrlKey: true }, action: 'split' }],
      },
      {
        keys: 'Q / W',
        desc: 'ตัดหัวคลิปทิ้งถึงหัวอ่าน / ตัดท้ายคลิปทิ้งตั้งแต่หัวอ่าน (ปุ่ม ตัดหัว / ตัดท้าย บนแถบเครื่องมือ)',
        probes: [{ event: { key: 'q' }, action: 'trimHead' }, { event: { key: 'w' }, action: 'trimTail' }],
      },
      {
        keys: 'Del / Backspace',
        desc: 'ลบคลิปหรือคำบรรยายที่เลือก (หลายคลิป: ลบทั้งหมดในครั้งเดียว) · โปรเจกต์ที่มีเสียงพากย์จะถามยืนยันก่อน แล้วตัดภาพ เสียงพากย์ และซับพร้อมกัน (สลับเป็นลบเฉพาะภาพได้ที่แถบเครื่องมือ)',
        probes: [{ event: { key: 'Delete' }, action: 'delete' }, { event: { key: 'Backspace' }, action: 'delete' }],
      },
      {
        keys: 'I / O',
        desc: 'ตั้งจุดเข้า / จุดออกที่หัวอ่าน เพื่อตัดช่วง (แสดงเป็นแถบสีส้มบนไม้บรรทัดเวลา)',
        probes: [{ event: { key: 'i' }, action: 'markIn' }, { event: { key: 'o' }, action: 'markOut' }],
      },
      {
        keys: 'Shift+Del',
        desc: 'ตัดช่วงระหว่างจุดเข้า-จุดออกทิ้ง แล้วดึงส่วนที่เหลือมาชิด (ถ้ายังไม่ตั้งช่วง = ลบตามปกติ)',
        probes: [{ event: { key: 'Delete', shiftKey: true }, action: 'rippleRange' }],
      },
      {
        keys: 'Ctrl+Alt+C / Ctrl+Alt+V',
        desc: 'คัดลอกการตั้งค่าของคลิปหลัก (ความเร็ว ซูม/แพน+คีย์เฟรมกล้อง สี ทรานซิชัน) / วางลงคลิปที่เลือก (ปุ่ม คัดลอกค่า / วางค่า)',
        probes: [
          { event: { key: 'c', ctrlKey: true, altKey: true }, action: 'copySettings' },
          { event: { key: 'v', ctrlKey: true, altKey: true }, action: 'pasteSettings' },
        ],
      },
      {
        keys: 'F',
        desc: 'เปิด / ปิด เฟดเข้าที่คลิปที่เลือก (ไม่รวมคลิปแรก)',
        probes: [{ event: { key: 'f' }, action: 'toggleFade' }],
      },
      { keys: 'Ctrl / Shift + คลิก', desc: 'เลือกหลายคลิปบนไทม์ไลน์: Ctrl สลับทีละคลิป, Shift เลือกเป็นช่วง' }, // TimelineClip click
      { keys: '[ / ]', desc: 'ย้ายคลิปที่โฟกัสอยู่ไปก่อน / หลัง 1 ลำดับ' }, // TimelineClip onKeyDown
      { keys: 'Enter', desc: 'ตัดแบ่งท่อนคำบรรยายตรงเคอร์เซอร์' }, // CuesTranscriptInspector
      { keys: 'Ctrl+Z', desc: 'ย้อนกลับ', probes: [{ event: { key: 'z', ctrlKey: true }, action: 'undo' }] },
      {
        keys: 'Ctrl+Y / Ctrl+Shift+Z',
        desc: 'ทำซ้ำ',
        probes: [
          { event: { key: 'y', ctrlKey: true }, action: 'redo' },
          { event: { key: 'z', ctrlKey: true, shiftKey: true }, action: 'redo' },
        ],
      },
    ],
  },
  {
    category: 'คีย์เฟรมกล้อง (ซูม/เลื่อน)',
    shortcuts: [
      {
        keys: 'D',
        desc: 'เพิ่ม / ลบคีย์เฟรม ◆ ที่หัวอ่าน บนคลิปที่เลือก (เก็บค่าซูม/เลื่อนปัจจุบัน)',
        probes: [{ event: { key: 'd' }, action: 'toggleKeyframe' }],
      },
      {
        keys: ', / .',
        desc: 'กระโดดไปคีย์เฟรมก่อนหน้า / ถัดไป ของคลิปที่เลือก',
        probes: [{ event: { key: ',' }, action: 'prevKeyframe' }, { event: { key: '.' }, action: 'nextKeyframe' }],
      },
    ],
  },
  {
    category: 'เล่นและเลื่อนหัวอ่าน',
    shortcuts: [
      { keys: 'Space', desc: 'เล่น / หยุด วิดีโอ', probes: [{ event: { key: ' ' }, action: 'togglePlay' }] },
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
        keys: '↑ / ↓',
        desc: 'ข้ามไปจุดตัดก่อนหน้า / ถัดไป (ขอบคลิปและขอบคำบรรยาย)',
        probes: [{ event: { key: 'ArrowUp' }, action: 'prevEdit' }, { event: { key: 'ArrowDown' }, action: 'nextEdit' }],
      },
      {
        keys: 'Home / End',
        desc: 'ไปจุดเริ่ม / จุดจบของไทม์ไลน์',
        probes: [{ event: { key: 'Home' }, action: 'seekStart' }, { event: { key: 'End' }, action: 'seekEnd' }],
      },
    ],
  },
  {
    category: 'ซูมและมุมมองไทม์ไลน์',
    shortcuts: [
      {
        keys: '+ / -',
        desc: 'ซูมไทม์ไลน์เข้า / ออกทีละขั้น',
        probes: [{ event: { key: '+' }, action: 'zoomIn' }, { event: { key: '-' }, action: 'zoomOut' }],
      },
      { keys: 'Ctrl + Scroll', desc: 'ซูมไทม์ไลน์แบบต่อเนื่องรอบเมาส์ (หรือลากแถบซูมบนแถบเครื่องมือ)' }, // useTimelineKeyboard (wheel)
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
    ],
  },
  {
    category: 'ระบบ',
    shortcuts: [
      {
        keys: 'Esc',
        desc: 'ปิดหน้าต่างป๊อปอัป / ออกจากโหมดพรีวิวเต็มพื้นที่ / ล้างจุดเข้า-จุดออก / ยกเลิกการเลือกหลายคลิป',
        probes: [
          { event: { key: 'Escape' }, context: { zen: true }, action: 'exitZen' },
          { event: { key: 'Escape' }, context: { hasRange: true }, action: 'clearRange' },
          { event: { key: 'Escape' }, context: { multiSelect: true }, action: 'clearSelection' },
        ],
      },
      { keys: 'Ctrl + S', desc: 'บันทึกโปรเจกต์' }, // EditorShell
      { keys: '?', desc: 'เปิดหน้าต่างคีย์ลัด' }, // useKeyboardShortcuts
    ],
  },
]);
