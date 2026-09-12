import test from 'node:test';
import assert from 'node:assert/strict';

import {
  FRESH_EDITOR_PROJECT,
  editorProjectIntentFromPayload,
  resolveEditorProjectName,
  withEditorProjectAction,
  filterActiveProjects,
} from './editorEntry.js';

test('send-to-edit payload opens a fresh One Click project even when stale project fallbacks exist', () => {
  const intent = editorProjectIntentFromPayload({
    productId: 'product-1',
    angleId: 'angle-1',
  });

  assert.equal(intent, FRESH_EDITOR_PROJECT);
  assert.equal(resolveEditorProjectName({
    intent,
    urlProject: 'old-from-url',
    storedProject: 'old-from-storage',
    angleProject: 'old-from-angle',
  }), '');
});

test('explicit open-timeline payload keeps opening the requested existing project', () => {
  const intent = editorProjectIntentFromPayload({ openProjectName: 'GOC01-existing_1' });

  assert.equal(intent, 'GOC01-existing_1');
  assert.equal(resolveEditorProjectName({
    intent,
    urlProject: 'wrong-url-project',
    storedProject: 'wrong-storage-project',
    angleProject: 'wrong-angle-project',
  }), 'GOC01-existing_1');
});

test('tracker actions omit stale project names for recut and include them only for open timeline', () => {
  const base = { productId: 'product-1', angleId: 'angle-1' };

  assert.deepEqual(withEditorProjectAction(base, {
    existingProjectName: 'stale-project',
  }), base);
  assert.deepEqual(withEditorProjectAction(base, {
    openExisting: true,
    existingProjectName: 'existing-project',
  }), { ...base, openProjectName: 'existing-project' });
  assert.equal(base.openProjectName, undefined);
});

test('ordinary editor navigation restores URL, storage, then angle project in priority order', () => {
  assert.equal(resolveEditorProjectName({
    intent: null,
    urlProject: 'url-project',
    storedProject: 'stored-project',
    angleProject: 'angle-project',
  }), 'url-project');
  assert.equal(resolveEditorProjectName({
    intent: null,
    storedProject: 'stored-project',
    angleProject: 'angle-project',
  }), 'stored-project');
  assert.equal(resolveEditorProjectName({
    intent: null,
    angleProject: 'angle-project',
  }), 'angle-project');
});

test('filterActiveProjects filters out posted projects and keeps active ones', () => {
  const projects = [
    { project_name: 'LOG01-ปัญหาก่อนใช้_1', status: 'posted' },
    { project_name: 'LOG02-รีวิวสเปก_1', status: 'in_production' },
    { project_name: 'GOC01-เทียบของเดิม_1', status: 'rendered' },
    { project_name: 'BLU01-โปรไฟลุก_1', status: 'scripted' },
    { project_name: 'ESS01-โปรไฟลุก_1', is_posted: true },
  ];
  const active = filterActiveProjects(projects, {});
  assert.equal(active.length, 3);
  assert.deepEqual(active.map(p => p.project_name), [
    'LOG02-รีวิวสเปก_1',
    'GOC01-เทียบของเดิม_1',
    'BLU01-โปรไฟลุก_1',
  ]);
});

test('filterActiveProjects accounts for statusByProject map correctly', () => {
  const projects = [
    { project_name: 'PROJ-1' },
    { project_name: 'PROJ-2' },
  ];
  const statusByProject = {
    'PROJ-1': 'posted',
    'PROJ-2': 'in_production',
  };
  const active = filterActiveProjects(projects, statusByProject);
  assert.equal(active.length, 1);
  assert.equal(active[0].project_name, 'PROJ-2');
});
