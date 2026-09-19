import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const exportGalleryPath = path.resolve(process.cwd(), 'src/components/ExportGallery.jsx');
const appPath = path.resolve(process.cwd(), 'src/App.jsx');

test('Export Gallery and App contract enforces optimistic delete and forced export sync', () => {
  const gallerySource = fs.readFileSync(exportGalleryPath, 'utf8');
  const appSource = fs.readFileSync(appPath, 'utf8');

  // ExportGallery receives and uses onDeleteExport
  assert.match(gallerySource, /onDeleteExport/, 'ExportGallery should have onDeleteExport prop');
  assert.match(gallerySource, /onDeleteExport\?\.\(deletedPaths\)/, 'ExportGallery confirmDelete should call onDeleteExport');
  assert.match(gallerySource, /onDeleteExport\?\.\(deletablePaths\)/, 'ExportGallery confirmBatchDelete should call onDeleteExport');

  // ExportGallery triggers forced exports refresh on gallery actions
  assert.match(gallerySource, /includeExports:\s*true,\s*force:\s*true/, 'ExportGallery should request force exports refresh');

  // App provides optimistic deletion and wired onRefresh for gallery
  assert.match(appSource, /handleExportDeleted/, 'App should declare handleExportDeleted handler');
  assert.match(appSource, /onDeleteExport=\{handleExportDeleted\}/, 'App should pass onDeleteExport to ExportGallery');
  assert.match(appSource, /invalidate\('exports'\)/, 'App should invalidate exports cache upon deletion');
});
