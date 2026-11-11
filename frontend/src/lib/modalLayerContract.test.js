import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const srcDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function jsxFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return jsxFiles(full);
    return entry.name.endsWith('.jsx') ? [full] : [];
  });
}

// Opening tag of every <ModalLayer ...>, read to the first '>' outside {...}.
function modalLayerTags(source) {
  const tags = [];
  let from = 0;
  for (;;) {
    const start = source.indexOf('<ModalLayer', from);
    if (start === -1) return tags;
    let depth = 0;
    let i = start + '<ModalLayer'.length;
    for (; i < source.length; i += 1) {
      const ch = source[i];
      if (ch === '{') depth += 1;
      else if (ch === '}') depth -= 1;
      else if (ch === '>' && depth === 0 && source[i - 1] !== '=') break;
    }
    tags.push({ tag: source.slice(start, i + 1), line: source.slice(0, start).split('\n').length });
    from = i;
  }
}

const files = jsxFiles(srcDir);

test('every modal dialog has an accessible name', () => {
  const unnamed = [];
  for (const file of files) {
    for (const { tag, line } of modalLayerTags(fs.readFileSync(file, 'utf8'))) {
      if (!/aria-label(ledby)?=/.test(tag)) unnamed.push(`${path.relative(srcDir, file)}:${line}`);
    }
  }
  assert.deepEqual(unnamed, [], 'ModalLayer needs aria-label or aria-labelledby');
});

test('overlays go through the shared primitives, not hand-rolled ones', () => {
  const offenders = [];
  for (const file of files) {
    const rel = path.relative(srcDir, file).split(path.sep).join('/');
    const source = fs.readFileSync(file, 'utf8');
    if (/aria-modal=/.test(source)) offenders.push(`${rel}: aria-modal (a native modal <dialog> already is one)`);
    if (/(^|[^\w.])(window\.)?(alert|confirm)\(/.test(source) && !rel.endsWith('ui/dialogService.jsx')) {
      offenders.push(`${rel}: window.alert/confirm (use confirmDialog/notify)`);
    }
    if (/document\.(body|documentElement)\.style\.overflow\s*=/.test(source)) {
      offenders.push(`${rel}: body scroll lock (the modal dialog contains scroll itself)`);
    }
  }
  assert.deepEqual(offenders, []);
});

test('ModalLayer survives StrictMode: its own close() is not mistaken for the user closing', () => {
  const layer = fs.readFileSync(path.join(srcDir, 'components/ui/ModalLayer.jsx'), 'utf8');
  // every close() the component issues itself is counted, and that event is ignored
  assert.match(layer, /selfClosesRef\.current \+= 1;\s*el\.close\(\);/);
  assert.match(layer, /if \(selfClosesRef\.current > 0\) \{\s*selfClosesRef\.current -= 1;\s*return;/);
  // the browser fixture runs under StrictMode like the real app does in development
  const fixture = fs.readFileSync(path.join(srcDir, 'overlayPrimitivesFixture.jsx'), 'utf8');
  assert.match(fixture, /<StrictMode><Fixture \/><\/StrictMode>/);
});
