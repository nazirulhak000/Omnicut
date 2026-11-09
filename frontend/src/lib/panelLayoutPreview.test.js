import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MOBILE_PREVIEW_MIN_H,
  MOBILE_SEPARATOR_H,
  MOBILE_TAB_ROW_H,
  clampMobilePreviewH,
  isPreviewEnlarged,
  mobilePanelStyles,
  mobilePreviewMaxH,
  nextPreviewMode,
} from './panelLayoutPreview.js';

// S4-02: the flag the phone's toggle shows and the way it moves must come from
// one rule. The audit's case: innerHeight 844, column 706 (navbars shown) or
// 844 (immersive), preview 470 / 520 / 590 -- the old shell said "enlarged"
// while the hook grew the preview to 792 and dropped immersive.
test('isPreviewEnlarged and nextPreviewMode always agree (S4-02)', () => {
  for (const full of [false, true]) {
    for (const immersive of [false, true]) {
      const enlarged = isPreviewEnlarged({ full, immersive });
      const next = nextPreviewMode({ full, immersive });
      if (enlarged) {
        assert.deepEqual(next, { full: false, immersive: false }, `shrink from ${JSON.stringify({ full, immersive })}`);
      } else {
        assert.deepEqual(next, { full: true, immersive: true }, 'grow from normal');
      }
      assert.equal(isPreviewEnlarged(next), !enlarged, 'one press always flips what the icon shows');
    }
  }
});

test('the decision does not depend on a pixel height (no 0.55 vs 0.75 thresholds)', () => {
  // Same mode, any column / preview size -> same answer.
  for (const boxH of [706, 844]) {
    for (const previewH of [470, 520, 590, 792]) {
      const ctx = { full: false, immersive: true, boxH, previewH, innerHeight: 844 };
      assert.equal(isPreviewEnlarged(ctx), true);
      assert.deepEqual(nextPreviewMode(ctx), { full: false, immersive: false });
    }
  }
});

// S4-03: normal mode keeps room for the timeline; full mode gives the preview
// the whole column.
test('normal-mode clamp reserves the tab row, drag handle and timeline', () => {
  const box = { boxH: 706, innerHeight: 844, reserve: 250 };
  const max = mobilePreviewMaxH(box);
  assert.equal(max, 706 - MOBILE_SEPARATOR_H - MOBILE_TAB_ROW_H - 250);
  assert.equal(clampMobilePreviewH(648, box), max, 'the old 648 request no longer squeezes the tracks');
  assert.equal(clampMobilePreviewH(200, box), 200, 'inside the range the handle follows the pointer exactly');
  assert.equal(clampMobilePreviewH(10, box), MOBILE_PREVIEW_MIN_H);
  assert.equal(clampMobilePreviewH(Number.POSITIVE_INFINITY, box), max);
  assert.equal(clampMobilePreviewH(Number.NaN, box), max);
});

test('a column too short for the reserve still keeps the preview minimum', () => {
  assert.equal(mobilePreviewMaxH({ boxH: 300, reserve: 400 }), MOBILE_PREVIEW_MIN_H);
  // Before the column is measured, fall back to the window height.
  assert.equal(mobilePreviewMaxH({ innerHeight: 844, reserve: 0 }), Math.round(844 * 0.9) - MOBILE_SEPARATOR_H - MOBILE_TAB_ROW_H);
});

test('full preview collapses the bottom panel to zero and lets the preview fill', () => {
  const { preview, panel } = mobilePanelStyles({ full: true, previewH: 300, panelH: 250 });
  assert.equal(panel.flex, '0 0 0px');
  assert.equal(panel.height, 0);
  assert.equal(panel.maxHeight, 0);
  assert.equal(panel.visibility, 'hidden');
  assert.equal(preview.flex, '1 1 0%');
  assert.equal('height' in preview, false, 'no fixed height caps the full preview');
});

test('normal mode restores the timeline height and makes the preview give way first', () => {
  const { preview, panel } = mobilePanelStyles({ full: false, previewH: 300, panelH: 250 });
  assert.equal(panel.height, 250);
  assert.equal(panel.maxHeight, 250);
  assert.equal(preview.height, 300);
  assert.equal(preview.minHeight, MOBILE_PREVIEW_MIN_H);
  const [, previewShrink] = preview.flex.split(' ').map(Number);
  const [, panelShrink] = panel.flex.split(' ').map(Number);
  assert.ok(previewShrink >= 100 * panelShrink, 'preview shrinks before the tracks do');
  // Assets / inspector tabs: the panel scrolls in the remaining space.
  const other = mobilePanelStyles({ full: false, previewH: 300, panelH: null });
  assert.equal(other.panel.flex, '1 1 0%');
});
