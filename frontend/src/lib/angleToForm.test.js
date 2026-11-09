import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_AD_TONE,
  DEFAULT_VOICE_PRESET,
  angleToForm,
  normalizeAdTone,
  normalizeVoicePreset,
} from './angleToForm.js';

// D4 / S2-07: canonical defaults are Gemini Fenrir + commercial_premium,
// mirrored from scripts/config.py (DEFAULT_VOICE_PRESET / DEFAULT_AD_TONE).
test('canonical voice defaults match the backend constants', () => {
  assert.equal(DEFAULT_VOICE_PRESET, 'gemini_fenrir_male_strong');
  assert.equal(DEFAULT_AD_TONE, 'commercial_premium');
});

test('normalizeAdTone keeps every known tone, premium included', () => {
  assert.equal(normalizeAdTone('commercial_premium'), 'commercial_premium');
  assert.equal(normalizeAdTone('commercial_hype'), 'commercial_hype');
  assert.equal(normalizeAdTone('commercial_expert'), 'commercial_expert');
});

test('normalizeAdTone sends unknown/empty tones to the default', () => {
  assert.equal(normalizeAdTone(undefined), DEFAULT_AD_TONE);
  assert.equal(normalizeAdTone(''), DEFAULT_AD_TONE);
  assert.equal(normalizeAdTone('not_a_tone'), DEFAULT_AD_TONE);
});

test('normalizeVoicePreset keeps a stored preset, defaults an empty one', () => {
  assert.equal(normalizeVoicePreset('gemini_puck_male_hype'), 'gemini_puck_male_hype');
  assert.equal(normalizeVoicePreset(''), DEFAULT_VOICE_PRESET);
  assert.equal(normalizeVoicePreset(null), DEFAULT_VOICE_PRESET);
});

test('angleToForm no longer coerces premium to hype and defaults to Fenrir', () => {
  const premium = angleToForm({ script_lines: ['a'], ad_tone: 'commercial_premium' });
  assert.equal(premium.adTone, 'commercial_premium');
  assert.equal(premium.voicePreset, DEFAULT_VOICE_PRESET);

  const stored = angleToForm({ script_lines: ['a'], ad_tone: 'commercial_hype', voice_preset: 'gemini_kore_female_bright' });
  assert.equal(stored.adTone, 'commercial_hype');
  assert.equal(stored.voicePreset, 'gemini_kore_female_bright');

  const bare = angleToForm({ script_lines: ['a'] });
  assert.equal(bare.adTone, DEFAULT_AD_TONE);
});

test('no component falls back to a hard-coded hype tone or coerces premium', async () => {
  const { readFileSync } = await import('node:fs');
  const files = [
    '../components/ProductToClip.jsx',
    '../components/ContentTrackerHub.jsx',
    '../components/editor/NewClipPanel.jsx',
    '../components/BatchRenderModal.jsx',
    '../components/gadget-media/stages/StageForms.jsx',
    '../components/VoicePickerModal.jsx',
    '../components/ShotListModal.jsx',
  ];
  for (const rel of files) {
    const src = readFileSync(new URL(rel, import.meta.url), 'utf8');
    assert.ok(!/\|\|\s*'commercial_hype'/.test(src), `${rel}: hype fallback`);
    assert.ok(!/ad_tone:\s*'commercial_(hype|expert)'/.test(src), `${rel}: hard-coded tone`);
    assert.ok(!/!==\s*'commercial_premium'/.test(src), `${rel}: premium coercion`);
  }
});
