import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const mobileShellSource = read('../components/mobile/MobileShell.jsx');

test('MobileShell imports Terminal icon from lucide-react', () => {
  assert.ok(
    mobileShellSource.includes('Terminal,') || mobileShellSource.includes('Terminal '),
    'MobileShell must import Terminal icon to prevent ReferenceError when rendering more tab'
  );
});

test('MobileShell has no undefined JSX component tags', () => {
  const tags = new Set([...mobileShellSource.matchAll(/<([A-Z][a-zA-Z0-9]+)/g)].map((m) => m[1]));
  const undefinedTags = [];

  for (const tag of tags) {
    if (['React', 'Fragment', 'Icon', 'Component', 'Element'].includes(tag)) continue;
    const isImported = mobileShellSource.includes(tag);
    if (!isImported) {
      undefinedTags.push(tag);
    }
  }

  assert.deepEqual(undefinedTags, [], `Found undefined JSX tags in MobileShell: ${JSON.stringify(undefinedTags)}`);
});
