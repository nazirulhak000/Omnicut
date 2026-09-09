import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_ANIM,
  HOOK_ANIM,
  OVERLAY_RENDER_PROFILES,
  overlayRenderProfile,
} from './overlayModel.js';

test('overlay render profiles keep hook and text policy differences explicit', () => {
  assert.equal(overlayRenderProfile({ kind: 'hook' }), OVERLAY_RENDER_PROFILES.hook);
  assert.equal(overlayRenderProfile({ kind: 'text' }), OVERLAY_RENDER_PROFILES.text);

  assert.equal(OVERLAY_RENDER_PROFILES.hook.defaultAnim, HOOK_ANIM);
  assert.equal(OVERLAY_RENDER_PROFILES.hook.supportsWordStagger, false);
  assert.equal(OVERLAY_RENDER_PROFILES.hook.clearLayout, true);
  assert.equal(OVERLAY_RENDER_PROFILES.hook.boundsType, 'hook');

  assert.equal(OVERLAY_RENDER_PROFILES.text.defaultAnim, DEFAULT_ANIM);
  assert.equal(OVERLAY_RENDER_PROFILES.text.supportsWordStagger, true);
  assert.equal(OVERLAY_RENDER_PROFILES.text.clearLayout, false);
  assert.equal(OVERLAY_RENDER_PROFILES.text.boundsType, 'text_overlay');
});

test('unknown frontend kinds preserve the existing text-render fallback', () => {
  assert.equal(overlayRenderProfile({ kind: 'future_overlay' }), OVERLAY_RENDER_PROFILES.text);
  assert.equal(overlayRenderProfile(null), OVERLAY_RENDER_PROFILES.text);
});
