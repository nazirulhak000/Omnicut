import test from 'node:test';
import assert from 'node:assert/strict';
import { createWorkspaceDataCoordinator } from './workspaceData.js';

test('workspace coordinator coalesces duplicate shell and export reads', async () => {
  let statusCalls = 0;
  let videoCalls = 0;
  let exportCalls = 0;
  const coordinator = createWorkspaceDataCoordinator({
    getSystemStatus: async () => ({ ok: ++statusCalls }),
    getRawVideos: async () => ({ videos: [++videoCalls] }),
    getExports: async () => ({ exports: [++exportCalls] }),
  });

  const [first, second] = await Promise.all([coordinator.loadShell(), coordinator.loadShell()]);
  assert.equal(statusCalls, 1);
  assert.equal(videoCalls, 1);
  assert.deepEqual(first, second);

  await coordinator.loadExports();
  await coordinator.loadExports();
  assert.equal(exportCalls, 1);
});

test('workspace coordinator refreshes only explicitly forced resources', async () => {
  let tick = 0;
  let exports = 0;
  const coordinator = createWorkspaceDataCoordinator({
    getSystemStatus: async () => ({ status: 'online' }),
    getRawVideos: async () => ({ videos: [] }),
    getExports: async () => ({ exports: [++exports] }),
  }, () => tick);

  assert.deepEqual((await coordinator.loadExports()).exports, [1]);
  tick = 1_000;
  assert.deepEqual((await coordinator.loadExports()).exports, [1]);
  assert.deepEqual((await coordinator.loadExports({ force: true })).exports, [2]);
});
