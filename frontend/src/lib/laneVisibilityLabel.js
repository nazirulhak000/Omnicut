/**
 * Label state for a timeline lane whose eye hides it in the PREVIEW ONLY.
 *
 * The caption, sticker and cutout eyes are local state in EditorShell: they are
 * never saved, never undone, and never reach the render, so a lane hidden this
 * way is still burned into the exported clip. The eye alone does not say so
 * (the text-overlay and hook eyes look identical but write `hidden` into the
 * project, and the render honours that), so the lane name itself is swapped for
 * a status while the eye is closed.
 */

export const PREVIEW_ONLY_HIDDEN_TEXT = 'ซ่อนเฉพาะพรีวิว';

/**
 * @param {string} name   lane name, e.g. 'คำบรรยาย'
 * @param {boolean} hidden whether the preview-only eye is closed
 * @returns {{ text: string, title: string | undefined, labelClass: string }}
 */
export function previewOnlyLaneLabel(name, hidden) {
  if (!hidden) return { text: name, title: undefined, labelClass: '' };
  return {
    text: PREVIEW_ONLY_HIDDEN_TEXT,
    title: `${name}: ${PREVIEW_ONLY_HIDDEN_TEXT} (ตอน render ยังมี${name}อยู่)`,
    labelClass: 'text-[10px] font-bold text-amber-400',
  };
}

/** Tooltip for the eye button itself; `noun` is what it toggles on the preview. */
export function previewOnlyEyeTitle(noun, hidden) {
  return hidden
    ? `${PREVIEW_ONLY_HIDDEN_TEXT} (ตอน render ยังมี${noun}อยู่) · คลิกเพื่อแสดง${noun}บนพรีวิว`
    : `คลิกเพื่อซ่อน${noun}บนพรีวิว`;
}
