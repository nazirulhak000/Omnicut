import test from 'node:test';
import assert from 'node:assert/strict';

import { shouldShowHighResolutionStillPreview } from './highResolutionStillPreview.js';

const currentPreview = { key: 'frame-30', src: 'data:image/png;base64,frame' };

test('shows the sharp still only for the current paused frame when enabled', () => {
  assert.equal(shouldShowHighResolutionStillPreview({
    enabled: true,
    isPlaying: false,
    currentKey: 'frame-30',
    preview: currentPreview,
  }), true);
});

test('hides the sharp still during playback or when the user disables it', () => {
  for (const state of [
    { enabled: true, isPlaying: true },
    { enabled: false, isPlaying: false },
  ]) {
    assert.equal(shouldShowHighResolutionStillPreview({
      ...state,
      currentKey: 'frame-30',
      preview: currentPreview,
    }), false);
  }
});

test('never leaves an older high-resolution frame over a newer playhead', () => {
  assert.equal(shouldShowHighResolutionStillPreview({
    enabled: true,
    isPlaying: false,
    currentKey: 'frame-31',
    preview: currentPreview,
  }), false);
});

test('does not report a sharp preview before a capture completes', () => {
  assert.equal(shouldShowHighResolutionStillPreview({
    enabled: true,
    isPlaying: false,
    currentKey: 'frame-30',
    preview: null,
  }), false);
});
