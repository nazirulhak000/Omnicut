import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_STORY_FORMAT,
  STORY_FORMAT_OPTIONS,
  TARGET_DURATION_OPTIONS,
  clipFormatPayload,
  normalizeStoryFormat,
  normalizeTargetDuration,
  storyFormatLabel,
} from './clipFormatOptions.js';
import { DEFAULT_STUDIO_FORM, migrateSavedStudioForm } from './studioDefaults.js';

test('duration choices are auto plus 15/25/35/45 seconds', () => {
  assert.deepEqual(TARGET_DURATION_OPTIONS.map((o) => o.value), [null, 15, 25, 35, 45]);
  assert.equal(TARGET_DURATION_OPTIONS[0].label, 'อัตโนมัติ');
});

test('story formats are classic plus the four AIBridge hint keys', () => {
  assert.deepEqual(
    STORY_FORMAT_OPTIONS.map((o) => o.id),
    ['classic', 'countdown', 'problem_reveal', 'myth_buster', 'loop'],
  );
  assert.equal(DEFAULT_STORY_FORMAT, 'classic');
  assert.equal(storyFormatLabel('countdown'), 'นับถอยหลัง 3 เหตุผล');
  assert.equal(storyFormatLabel('problem_reveal'), 'ปัญหา → ทางแก้');
  assert.equal(storyFormatLabel('myth_buster'), 'เข้าใจผิดมาตลอด');
  assert.equal(storyFormatLabel('loop'), 'วนต่อเนื่อง');
  assert.equal(storyFormatLabel('listicle'), 'listicle');
});

test('labels carry no emoji or leading symbol (ui_clean_standard)', () => {
  for (const o of [...TARGET_DURATION_OPTIONS, ...STORY_FORMAT_OPTIONS]) {
    assert.doesNotMatch(o.label, /\p{Extended_Pictographic}/u, o.label);
    assert.doesNotMatch(o.label, /^[+\-*•]/, o.label);
  }
});

test('normalizers keep known values and fall back safely', () => {
  assert.equal(normalizeTargetDuration(25), 25);
  assert.equal(normalizeTargetDuration('35'), 35);
  assert.equal(normalizeTargetDuration(null), null);
  assert.equal(normalizeTargetDuration(''), null);
  assert.equal(normalizeTargetDuration(60), null);
  assert.equal(normalizeTargetDuration('abc'), null);
  assert.equal(normalizeStoryFormat('Loop'), 'loop');
  assert.equal(normalizeStoryFormat('unknown'), 'classic');
  assert.equal(normalizeStoryFormat(undefined), 'classic');
});

test('render payload: auto sends a null target_duration and classic story_format', () => {
  assert.deepEqual(clipFormatPayload({}), { target_duration: null, story_format: 'classic' });
  assert.deepEqual(clipFormatPayload(DEFAULT_STUDIO_FORM), { target_duration: null, story_format: 'classic' });
  assert.deepEqual(
    clipFormatPayload({ targetDuration: 15, storyFormat: 'countdown' }),
    { target_duration: 15, story_format: 'countdown' },
  );
});

test('a saved form from before these fields opens on auto + classic and keeps a later choice', () => {
  const old = migrateSavedStudioForm({ productName: 'X', stylePresetVersion: DEFAULT_STUDIO_FORM.stylePresetVersion });
  assert.equal(old.targetDuration, null);
  assert.equal(old.storyFormat, 'classic');
  const chosen = migrateSavedStudioForm({ ...old, targetDuration: 45, storyFormat: 'loop' });
  assert.deepEqual(clipFormatPayload(chosen), { target_duration: 45, story_format: 'loop' });
});
