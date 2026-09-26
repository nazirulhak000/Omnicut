import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

/**
 * The "hide cutout" button is a preview convenience: it shows the frame
 * without the cut-out subject so the user can check what sits behind it. It
 * must never change the saved project.
 *
 * It did. EditorShell handed the masked config -- a copy with enabled:false --
 * to AssetPanel, and AssetPanel's toggle spreads whatever it receives straight
 * back through onChange. Pressing the cutout switch while previewing hidden
 * therefore wrote enabled:false into real state, which autosaved to the
 * project and rode along in the render payload. The export came out with the
 * hook text over the product while the editor still showed "Cutout ready",
 * and nothing reported an error.
 *
 * These are source assertions rather than behavioural ones because the bug
 * lives in which object is passed where -- both versions render identically,
 * and only one of them corrupts state.
 */

const SHELL = readFileSync(
  fileURLToPath(new URL('../components/editor/EditorShell.jsx', import.meta.url)),
  'utf8',
);

/** Line index of each `<Component` opening tag, for ownership checks. */
function openingTagLines(source, component) {
  return source
    .split('\n')
    .map((line, index) => (line.trim().startsWith(`<${component}`) ? index : -1))
    .filter((index) => index >= 0);
}

function backgroundIsolationPropLines(source) {
  return source
    .split('\n')
    .map((line, index) => ({ line: line.trim(), index }))
    .filter(({ line }) => line.startsWith('backgroundIsolation={'));
}

/** Which component's opening tag most recently preceded this line. */
function ownerOf(index, playerLines, panelLines) {
  const lastBefore = (lines) => lines.filter((l) => l < index).pop() ?? -1;
  return lastBefore(playerLines) > lastBefore(panelLines) ? 'SequencePlayer' : 'AssetPanel';
}

test('the hidden-cutout mask is never built inline in a prop', () => {
  // Inlining `isCutoutHidden ? {...enabled: false} : ...` at a call site is
  // how this bug was written the first time: it reads as a display concern
  // while silently becoming the object a child writes back. Building it once
  // in a named memo is fine -- that is the one place it should appear.
  const inlineInProp = SHELL.split('\n').filter((line) => {
    const text = line.trim();
    return text.startsWith('backgroundIsolation={') && text.includes('isCutoutHidden');
  });
  assert.deepEqual(
    inlineInProp,
    [],
    'build the mask once in a named value, not inline where it can be passed to a writer',
  );
});

test('every backgroundIsolation prop is either the real config or the named mask', () => {
  const props = backgroundIsolationPropLines(SHELL);
  assert.ok(props.length >= 2, 'expected the player and the panel to receive this prop');
  for (const { line, index } of props) {
    assert.match(
      line,
      /^backgroundIsolation=\{(backgroundIsolation|previewBackgroundIsolation)\}$/,
      `line ${index + 1} passes a derived object: ${line}`,
    );
  }
});

test('AssetPanel receives the real config, never the preview mask', () => {
  // AssetPanel's toggle spreads its prop into onChange, so a masked copy here
  // becomes persisted state.
  const playerLines = openingTagLines(SHELL, 'SequencePlayer');
  const panelLines = openingTagLines(SHELL, 'AssetPanel');
  assert.ok(panelLines.length > 0 && playerLines.length > 0);

  const panelProps = backgroundIsolationPropLines(SHELL)
    .filter(({ index }) => ownerOf(index, playerLines, panelLines) === 'AssetPanel');

  assert.ok(panelProps.length > 0, 'AssetPanel should receive backgroundIsolation');
  for (const { line, index } of panelProps) {
    assert.equal(
      line,
      'backgroundIsolation={backgroundIsolation}',
      `AssetPanel at line ${index + 1} must get the real config, not a mask`,
    );
  }
});

test('the preview mask exists and is derived from the hide toggle', () => {
  assert.match(
    SHELL,
    /const previewBackgroundIsolation = useMemo\(/,
    'the mask should be a single named memo, so its purpose is visible',
  );
  assert.match(
    SHELL,
    /isCutoutHidden \? \{ \.\.\.\(backgroundIsolation \|\| \{\}\), enabled: false \}/,
    'the mask should still disable the cutout for the player while hidden',
  );
});
