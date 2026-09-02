// Interface size. Now that every type size in the app is a rem, this single
// number scales all of it -- text, and any control sized in rem with it.
// Applied to <html> as --ui-scale, which index.css multiplies the 16px base by.

export const UI_SCALES = [
  { id: 'compact', label: 'กะทัดรัด', scale: 0.94, hint: 'เห็นข้อมูลได้มากขึ้นต่อหน้าจอ' },
  { id: 'normal', label: 'ปกติ', scale: 1, hint: 'ตัวอักษรพื้นฐาน 16px' },
  { id: 'large', label: 'ใหญ่', scale: 1.13, hint: 'อ่านง่ายที่สุด เหมาะกับจอใหญ่' },
];

const KEY = 'capcut_ui_scale';

export function getUiScaleId() {
  try {
    const saved = localStorage.getItem(KEY);
    if (UI_SCALES.some((s) => s.id === saved)) return saved;
  } catch (err) { /* private mode */ }
  return 'normal';
}

export function applyUiScale(id) {
  const entry = UI_SCALES.find((s) => s.id === id) || UI_SCALES[1];
  document.documentElement.style.setProperty('--ui-scale', String(entry.scale));
  try {
    localStorage.setItem(KEY, entry.id);
  } catch (err) { /* the choice just will not survive a reload */ }
  return entry.id;
}

/** Call once at startup so a saved choice is in effect before first paint. */
export function initUiScale() {
  return applyUiScale(getUiScaleId());
}

export default applyUiScale;
