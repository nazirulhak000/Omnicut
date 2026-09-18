import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const exportGalleryPath = path.resolve(process.cwd(), 'src/components/ExportGallery.jsx');

test('Export Gallery pagination does not reference an undefined loading state', () => {
  const source = fs.readFileSync(exportGalleryPath, 'utf8');

  assert.doesNotMatch(source, /disabled=\{loading\}/);
});
