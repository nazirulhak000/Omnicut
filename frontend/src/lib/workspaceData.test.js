import test from 'node:test';
import assert from 'node:assert/strict';
import { createWorkspaceDataCoordinator } from './workspaceData.js';

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

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

test('workspace coordinator ignores an old response after invalidation', async () => {
  const oldRequest = deferred();
  const newRequest = deferred();
  let calls = 0;
  const coordinator = createWorkspaceDataCoordinator({
    getSystemStatus: async () => ({ ok: true }),
    getRawVideos: async () => ({ videos: [] }),
    getExports: () => (++calls === 1 ? oldRequest.promise : newRequest.promise),
  });

  const old = coordinator.loadExports();
  coordinator.invalidate('exports');
  const fresh = coordinator.loadExports();
  newRequest.resolve({ exports: ['new'] });
  assert.deepEqual(await fresh, { exports: ['new'] });
  oldRequest.resolve({ exports: ['old'] });
  await old;
  assert.deepEqual(await coordinator.loadExports(), { exports: ['new'] });
});

test('workspace coordinator coalesces tracker products and queue reads', async () => {
  let productCalls = 0;
  let queueCalls = 0;
  const coordinator = createWorkspaceDataCoordinator({
    getSystemStatus: async () => ({ ok: true }),
    getRawVideos: async () => ({ videos: [] }),
    getExports: async () => ({ exports: [] }),
    getProducts: async () => ({ products: [{ id: ++productCalls }] }),
    getScheduleQueue: async () => ({ items: [{ id: ++queueCalls }] }),
  });

  const [first, second] = await Promise.all([
    coordinator.loadTrackerData(),
    coordinator.loadTrackerData(),
  ]);

  assert.equal(productCalls, 1);
  assert.equal(queueCalls, 1);
  assert.deepEqual(first, second);
  assert.deepEqual((await coordinator.loadTrackerData()).products, { products: [{ id: 1 }] });
});

test('workspace coordinator shares the product projection across tracker and editor consumers', async () => {
  let productCalls = 0;
  const coordinator = createWorkspaceDataCoordinator({
    getSystemStatus: async () => ({ ok: true }),
    getRawVideos: async () => ({ videos: [] }),
    getExports: async () => ({ exports: [] }),
    getProducts: async () => ({ products: [{ id: ++productCalls }] }),
    getScheduleQueue: async () => ({ items: [] }),
  });

  const [editorProducts, trackerData] = await Promise.all([
    coordinator.loadProducts(),
    coordinator.loadTrackerData(),
  ]);

  assert.equal(productCalls, 1);
  assert.deepEqual(editorProducts, trackerData.products);
});

test('tracker invalidation refreshes products and queue together', async () => {
  let productCalls = 0;
  let queueCalls = 0;
  const coordinator = createWorkspaceDataCoordinator({
    getSystemStatus: async () => ({ ok: true }),
    getRawVideos: async () => ({ videos: [] }),
    getExports: async () => ({ exports: [] }),
    getProducts: async () => ({ products: [++productCalls] }),
    getScheduleQueue: async () => ({ items: [++queueCalls] }),
  });

  await coordinator.loadTrackerData();
  coordinator.invalidateTrackerData();
  const refreshed = await coordinator.loadTrackerData();
  assert.deepEqual(refreshed, { products: { products: [2] }, scheduleQueue: { items: [2] } });
});
