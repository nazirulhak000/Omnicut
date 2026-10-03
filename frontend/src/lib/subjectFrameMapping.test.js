import test from 'node:test';
import assert from 'node:assert/strict';
import { previewPointToSource, sourcePointToPreview } from './subjectFrameMapping.js';

const vertical = { sourceWidth: 1080, sourceHeight: 1920 };
function close(actual, expected) {
  assert.ok(actual);
  assert.ok(Math.abs(actual.x - expected.x) < 1e-7, `${actual.x} != ${expected.x}`);
  assert.ok(Math.abs(actual.y - expected.y) < 1e-7, `${actual.y} != ${expected.y}`);
  assert.equal(actual.label, expected.label ?? 1);
}

test('inverse prompts account for zoom/pan/mirror rather than display coordinates', () => {
  close(previewPointToSource({ x: 0.2, y: 0.8 }, { ...vertical, clip: { zoom: 2, pan_x: 1, pan_y: -1 } }), { x: 0.6, y: 0.4 });
  close(previewPointToSource({ x: 0.2, y: 0.8, label: 0 }, { ...vertical, clip: { mirror: true } }), { x: 0.8, y: 0.8, label: 0 });
  close(previewPointToSource({ x: 0.2, y: 0.8 }, { ...vertical, clip: { rotation: 180 } }), { x: 0.8, y: 0.2 });
});

test('a mirrored, zoomed and panned pick lands where the render shows it (L2-10)', () => {
  // Render: hflip, then a zoom-2 window panned fully right of the flipped
  // frame -- screen x u shows raw x 540 - 540u. Pan is a screen direction.
  const options = { ...vertical, clip: { zoom: 2, pan_x: 1, mirror: true } };
  close(previewPointToSource({ x: 0.25, y: 0.5 }, options), { x: 0.375, y: 0.5 });
  close(previewPointToSource({ x: 0.75, y: 0.5 }, options), { x: 0.125, y: 0.5 });
  close(sourcePointToPreview({ x: 0.375, y: 0.5 }, options), { x: 0.25, y: 0.5 });
  // Unmirrored, the same pan shows the right half of the raw frame.
  close(previewPointToSource({ x: 0.25, y: 0.5 }, { ...vertical, clip: { zoom: 2, pan_x: 1 } }), { x: 0.625, y: 0.5 });
});

test('landscape cover-fit picks become worker letterbox points', () => {
  const options = { sourceWidth: 1920, sourceHeight: 1080 };
  // Preview left/right edges are center-cropped raw source, not raw 0 and 1.
  close(previewPointToSource({ x: 0, y: 0 }, options), { x: 0.341796875, y: 0.341796875 });
  close(previewPointToSource({ x: 1, y: 1 }, options), { x: 0.658203125, y: 0.658203125 });
  assert.equal(sourcePointToPreview({ x: 0.1, y: 0.5 }, options), null);
  assert.equal(sourcePointToPreview({ x: 0.5, y: 0.1 }, options), null);
});

test('ready Cutout picks use the letterboxed frame actually painted', () => {
  const options = { sourceWidth: 1920, sourceHeight: 1080, sourceIsLetterboxed: true };
  close(previewPointToSource({ x: 0.2, y: 0.6 }, options), { x: 0.2, y: 0.6 });
  close(sourcePointToPreview({ x: 0.2, y: 0.6 }, options), { x: 0.2, y: 0.6 });
});

test('rotated landscape raw points and animated camera preserve marker locations', () => {
  close(previewPointToSource({ x: 0.25, y: 0.75 }, { sourceWidth: 1920, sourceHeight: 1080, clip: { rotation: 90 } }), { x: 0.75, y: 0.5791015625 });
  for (const rotation of [0, 90, 180, 270]) for (const mirror of [false, true]) {
    const options = { sourceWidth: 1920, sourceHeight: 1080, clip: { rotation, mirror,
      pan_x: 0.3, pan_y: -0.2, keyframes: [{ time: 0, zoom: 1 }, { time: 2, zoom: 2 }] }, motionTime: 1 };
    const point = { x: 0.25, y: 0.75, label: 0 };
    close(sourcePointToPreview(previewPointToSource(point, options), options), point);
  }
});

test('blurred padding cannot produce a foreground product point', () => {
  const options = { sourceWidth: 1920, sourceHeight: 1080, clip: { bg_blur: true } };
  assert.equal(previewPointToSource({ x: 0.5, y: 0.1 }, options), null);
  close(previewPointToSource({ x: 0.25, y: 0.5 }, options), { x: 0.25, y: 0.5 });
  assert.equal(previewPointToSource({ x: 0.5, y: 0.5 }, {}), null);
});
