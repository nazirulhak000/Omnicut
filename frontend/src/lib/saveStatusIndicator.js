/**
 * The small save-state dot on the immersive studio capsule.
 *
 * The capsule used to show a pulsing green dot whatever the save state was,
 * so a phone user (where the mini capsule is the default) saw "fine" while an
 * edit was unsaved or a save had failed. Colour and label now follow the real
 * saveStatus; anything that is not a confirmed 'saved' reads as not saved.
 *
 * @param {string} saveStatus 'saved' | 'dirty' | 'unsaved' | 'saving' | 'error'
 * @returns {{ tone: string, className: string, label: string }}
 */
export function saveStatusDot(saveStatus) {
  switch (saveStatus) {
    case 'saved':
      return { tone: 'saved', className: 'bg-emerald-400', label: 'บันทึกแล้ว' };
    case 'saving':
      return { tone: 'saving', className: 'bg-amber-400 animate-pulse', label: 'กำลังบันทึกโปรเจกต์' };
    case 'error':
      return { tone: 'error', className: 'bg-red-500', label: 'บันทึกไม่สำเร็จ' };
    default:
      return { tone: 'dirty', className: 'bg-amber-400', label: 'มีการแก้ไขที่ยังไม่ได้บันทึก' };
  }
}
