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

/** True when focus is in a text-entry control that owns its own keystrokes. */
export function isEditableTarget(el) {
  if (!el) return false;
  return el.tagName === 'INPUT'
    || el.tagName === 'TEXTAREA'
    || el.tagName === 'SELECT'
    || Boolean(el.isContentEditable);
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
