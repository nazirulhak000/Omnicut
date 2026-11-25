import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SRC_ROOT = fileURLToPath(new URL('../', import.meta.url));

function walkRuntimeFiles(dir, extRe) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkRuntimeFiles(full, extRe));
    } else if (extRe.test(entry.name) && !entry.name.endsWith('.test.js')) {
      out.push(full);
    }
  }
  return out;
}

function extractClassNameAttributes(source) {
  const attrs = [];
  // Double-quoted className="..."
  for (const m of source.matchAll(/className\s*=\s*"([^"]*)"/g)) {
    attrs.push({ text: m[1], index: m.index });
  }
  // Template-literal className={`...`} (no nested backticks in Tailwind attributes)
  for (const m of source.matchAll(/className\s*=\s*\{`([^`]*)`\}/g)) {
    attrs.push({ text: m[1], index: m.index });
  }
  return attrs;
}

const SCALE_UTILITY_RE = /(?:^|[\s'"])(?:active:|hover:|focus:|disabled:active:|group-hover(?:\/[\w-]+)?:|\[[^\]]+\]:)*scale-(?:\d+|\[[^\]]+\])/;
const SCALE_INTERACTION_RE = /(?:active:|hover:|group-hover(?:\/[\w-]+)?:)scale-(?:\d+|\[[^\]]+\])/;

test('index.css defines @utility motion-press with transform, translate, scale, rotate (D2)', () => {
  const css = readFileSync(join(SRC_ROOT, 'index.css'), 'utf8');
  const match = css.match(/@utility\s+motion-press\s*\{([^}]*)\}/);
  assert.ok(match, 'index.css must define @utility motion-press');
  const body = match[1];
  for (const prop of ['transform', 'translate', 'scale', 'rotate']) {
    assert.match(body, new RegExp(`\\b${prop}\\b`), `@utility motion-press must transition ${prop}`);
  }
});

test('runtime frontend/src files contain zero transition-all utilities (D2)', () => {
  const files = walkRuntimeFiles(SRC_ROOT, /\.(jsx|js)$/);
  const hits = [];
  for (const file of files) {
    const src = readFileSync(file, 'utf8');
    if (/\btransition-all\b/.test(src)) {
      hits.push(file);
    }
  }
  assert.deepEqual(hits, [], `Unexpected transition-all in: ${hits.join(', ')}`);
});

test('no runtime .jsx element combines scale utilities with transition-[...transform...] missing scale (D2)', () => {
  const jsxFiles = walkRuntimeFiles(SRC_ROOT, /\.jsx$/);
  const badTransformWithoutScale = [];
  const missingScaleTransition = [];

  for (const file of jsxFiles) {
    const src = readFileSync(file, 'utf8');
    const rel = file.slice(SRC_ROOT.length).replace(/\\/g, '/');
    for (const attr of extractClassNameAttributes(src)) {
      const hasScale = SCALE_UTILITY_RE.test(attr.text);
      const hasScaleInteraction = SCALE_INTERACTION_RE.test(attr.text);

      for (const tm of attr.text.matchAll(/(?<!after:)transition-\[([^\]]+)\]/g)) {
        const props = tm[1].split(',').map((s) => s.trim());
        if (props.includes('transform') && !props.includes('scale') && hasScale) {
          badTransformWithoutScale.push(`${rel}: ${tm[0]}`);
        }
      }

      if (hasScaleInteraction) {
        const hasMotionPress = /\bmotion-press\b/.test(attr.text);
        const hasTransitionTransform = /\btransition-transform\b/.test(attr.text);
        const hasTransitionWithScale = /transition-\[[^\]]*\bscale\b[^\]]*\]/.test(attr.text);
        if (!hasMotionPress && !hasTransitionTransform && !hasTransitionWithScale) {
          missingScaleTransition.push(`${rel}: ${attr.text.replace(/\s+/g, ' ').slice(0, 120)}`);
        }
      }
    }
  }

  assert.deepEqual(
    badTransformWithoutScale,
    [],
    `Found transition-[...transform...] without scale on scaled elements:\n${badTransformWithoutScale.join('\n')}`
  );
  assert.deepEqual(
    missingScaleTransition,
    [],
    `Found active:/hover:scale-* elements without motion-press / transition-transform / scale transition:\n${missingScaleTransition.join('\n')}`
  );
});

test('specific D2 targets restore scale/translate transitions', () => {
  const coverModal = readFileSync(join(SRC_ROOT, 'components/CoverStudioModal.jsx'), 'utf8');
  const sidebar = readFileSync(join(SRC_ROOT, 'components/Sidebar.jsx'), 'utf8');
  const exportGallery = readFileSync(join(SRC_ROOT, 'components/ExportGallery.jsx'), 'utf8');
  const storyboardModal = readFileSync(join(SRC_ROOT, 'components/ManualStoryboardModal.jsx'), 'utf8');
  const productToClip = readFileSync(join(SRC_ROOT, 'components/ProductToClip.jsx'), 'utf8');
  const assetPanel = readFileSync(join(SRC_ROOT, 'components/editor/AssetPanel.jsx'), 'utf8');

  assert.match(coverModal, /after:transition-\[[^\]]*\btranslate\b[^\]]*\]/);
  assert.match(sidebar, /desktopTooltipClass[\s\S]*transition-\[opacity,transform,translate,scale\]/);
  assert.match(sidebar, /motion-press duration-250/);
  assert.match(exportGallery, /motion-press/);
  assert.match(storyboardModal, /motion-press/);
  assert.match(productToClip, /motion-press/);
  assert.match(assetPanel, /motion-press/);
});

test('index.css enter keyframes avoid forwards transform trap and remove dead .fade-out (D4, D5)', () => {
  const css = readFileSync(join(SRC_ROOT, 'index.css'), 'utf8');
  for (const cls of ['.animate-fadeIn', '.animate-scaleUp', '.animate-slideDown', '.animate-slideUp', '.animate-slideLeft', '.popover-menu', '.animate-in']) {
    const re = new RegExp(`^${cls.replace('.', '\\.')}\\s*\\{[^}]*\\}`, 'm');
    const m = css.match(re);
    assert.ok(m, `${cls} rule must exist in index.css`);
    assert.match(m[0], /\bbackwards\b/, `${cls} must use backwards fill-mode (D4)`);
    assert.doesNotMatch(m[0], /\bforwards\b/, `${cls} must not keep forwards fill-mode (D4)`);
  }
  assert.doesNotMatch(css, /\.fade-out\s*\{\s*--tw-exit-opacity:\s*1/, 'dead .fade-out rule must be removed (D5)');
});

test('Sidebar tooltip warm-up timer waits past initial 150ms delay + 150ms fade (D7)', () => {
  const sidebar = readFileSync(join(SRC_ROOT, 'components/Sidebar.jsx'), 'utf8');
  const match = sidebar.match(/setNavTooltipWarm\(true\)[\s\S]{0,120}\},\s*(\d+)\)/);
  assert.ok(match, 'Sidebar must schedule navTooltipWarm warmup timeout');
  assert.ok(Number(match[1]) > 150, `Expected warmup delay > 150ms to avoid cutting off first fade, got ${match[1]}ms`);
});

test('ProductToClip tracks scene scanning per clip video_path and avoids flicker (D3)', () => {
  const ptc = readFileSync(join(SRC_ROOT, 'components/ProductToClip.jsx'), 'utf8');
  assert.match(ptc, /'scene_indexing'/);
  assert.match(ptc, /const isClipScanning = useCallback/);
  assert.match(ptc, /payload\.video_path/);
  assert.match(ptc, /setPendingSceneScans/);
});

test('CoverStudioModal strips banned symbols, segments Thai graphemes, avoids ลดพิเศษ, and aligns tech_neon CSS (B12/D6)', () => {
  const modal = readFileSync(join(SRC_ROOT, 'components/CoverStudioModal.jsx'), 'utf8');
  assert.doesNotMatch(modal, /propProductName|propInitialHook/);
  assert.match(modal, /Intl\.Segmenter\(['"]th['"],\s*\{\s*granularity:\s*['"]grapheme['"]\s*\}/);
  assert.doesNotMatch(modal, /ลดพิเศษ/);
  assert.doesNotMatch(modal, /template === 'tech_neon'[\s\S]{0,600}?\buppercase\b/);
  assert.doesNotMatch(modal, /template === 'tech_neon'[\s\S]{0,600}?\bitalic\b/);
});
