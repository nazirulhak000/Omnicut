// Clip length and story format choices for a new clip.
//
// Sent to /api/render as `target_duration` (seconds, or null for "let the
// script decide") and `story_format` (classic by default). The story format
// ids are the keys of AIBridge.STORY_FORMAT_HINTS in scripts/ai_bridge.py plus
// the default `classic` (DEFAULT_STORY_FORMAT in scripts/export_registry.py /
// post_log.py), so the Performance tab groups by the same ids.

export const AUTO_TARGET_DURATION = null;

export const TARGET_DURATION_OPTIONS = Object.freeze([
  Object.freeze({ value: AUTO_TARGET_DURATION, label: 'อัตโนมัติ', hint: 'ยาวตามบท' }),
  Object.freeze({ value: 15, label: '15 วิ', hint: 'สั้นมาก' }),
  Object.freeze({ value: 25, label: '25 วิ', hint: 'กระชับ' }),
  Object.freeze({ value: 35, label: '35 วิ', hint: 'มาตรฐาน' }),
  Object.freeze({ value: 45, label: '45 วิ', hint: 'เล่าครบ' }),
]);

const TARGET_DURATION_VALUES = new Set(
  TARGET_DURATION_OPTIONS.map((o) => o.value).filter((v) => v !== AUTO_TARGET_DURATION),
);

export const DEFAULT_STORY_FORMAT = 'classic';

export const STORY_FORMAT_OPTIONS = Object.freeze([
  Object.freeze({ id: 'classic', label: 'คลาสสิก', hint: 'Hook → จุดเด่น → CTA ตามสูตรเดิม' }),
  Object.freeze({ id: 'countdown', label: 'นับถอยหลัง 3 เหตุผล', hint: 'ข้อ 3 → 2 → 1 เก็บข้อเด็ดไว้ท้าย' }),
  Object.freeze({ id: 'problem_reveal', label: 'ปัญหา → ทางแก้', hint: 'เปิดด้วยปัญหา แล้วเฉลยตัวช่วย' }),
  Object.freeze({ id: 'myth_buster', label: 'เข้าใจผิดมาตลอด', hint: 'แก้ความเชื่อผิดด้วยสเปกจริง' }),
  Object.freeze({ id: 'loop', label: 'วนต่อเนื่อง', hint: 'ประโยคท้ายต่อกลับประโยคแรก' }),
]);

const STORY_FORMAT_IDS = new Set(STORY_FORMAT_OPTIONS.map((o) => o.id));

/** 15/25/35/45 stay; anything else (auto, blank, junk, old values) is null. */
export function normalizeTargetDuration(value) {
  if (value === null || value === undefined || value === '') return AUTO_TARGET_DURATION;
  const n = Number(value);
  return TARGET_DURATION_VALUES.has(n) ? n : AUTO_TARGET_DURATION;
}

/** A known story format id, or classic. */
export function normalizeStoryFormat(value) {
  const key = String(value ?? '').trim().toLowerCase();
  return STORY_FORMAT_IDS.has(key) ? key : DEFAULT_STORY_FORMAT;
}

/** Thai label for a story format id; unknown ids are shown as they are. */
export function storyFormatLabel(id) {
  const key = String(id ?? '').trim().toLowerCase();
  return STORY_FORMAT_OPTIONS.find((o) => o.id === key)?.label || String(id ?? '');
}

/** The two render fields, from the studio form's camelCase keys. */
export function clipFormatPayload(form = {}) {
  return {
    target_duration: normalizeTargetDuration(form?.targetDuration),
    story_format: normalizeStoryFormat(form?.storyFormat),
  };
}
