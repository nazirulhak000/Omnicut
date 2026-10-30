import assert from 'node:assert/strict';
import * as nodeTest from 'node:test';
import {
  registerServiceWorker,
  checkServerHealth,
  createHealthMonitor,
  SW_SCRIPT_URL,
  HEALTH_ENDPOINT,
} from './swRegistration.js';

const testFn = globalThis.it || globalThis.test || nodeTest.test;

testFn('registerServiceWorker registers /sw.js when navigator.serviceWorker is available', async () => {
  const calls = [];
  const fakeReg = { scope: '/' };
  const fakeNav = {
    serviceWorker: {
      async register(url, opts) {
        calls.push({ url, opts });
        return fakeReg;
      },
    },
  };

  const res = await registerServiceWorker({ nav: fakeNav });
  assert.equal(res.registered, true);
  assert.equal(res.registration, fakeReg);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, SW_SCRIPT_URL);
  assert.deepEqual(calls[0].opts, { scope: '/' });
});

testFn('registerServiceWorker safely returns registered:false when serviceWorker is unsupported or throws', async () => {
  const noSw = await registerServiceWorker({ nav: {} });
  assert.equal(noSw.registered, false);
  assert.equal(noSw.registration, null);

  const nullNav = await registerServiceWorker({ nav: null });
  assert.equal(nullNav.registered, false);

  const throwingNav = {
    serviceWorker: {
      async register() {
        throw new Error('SW blocked');
      },
    },
  };
  const errRes = await registerServiceWorker({ nav: throwingNav });
  assert.equal(errRes.registered, false);
  assert.equal(errRes.registration, null);
  assert.ok(errRes.error instanceof Error);
});

testFn('checkServerHealth returns online:true on 200 OK and online:false on 502/network error/timeout', async () => {
  let requestedUrl = null;
  const okFetch = async (url) => {
    requestedUrl = url;
    return { ok: true, status: 200 };
  };
  const okRes = await checkServerHealth(okFetch, { now: () => 1700000000000 });
  assert.equal(requestedUrl, HEALTH_ENDPOINT);
  assert.equal(okRes.online, true);
  assert.equal(okRes.status, 200);
  assert.equal(okRes.timestamp, 1700000000000);

  const badGatewayFetch = async () => ({ ok: false, status: 502 });
  const badRes = await checkServerHealth(badGatewayFetch, { now: () => 1700000001000 });
  assert.equal(badRes.online, false);
  assert.equal(badRes.status, 502);

  const throwingFetch = async () => {
    throw new Error('Network down');
  };
  const errRes = await checkServerHealth(throwingFetch, { now: () => 1700000002000 });
  assert.equal(errRes.online, false);
  assert.equal(errRes.status, 0);

  // Timeout test (25ms timeout against slow fetch)
  const slowFetch = (_url, { signal } = {}) =>
    new Promise((resolve, reject) => {
      const t = setTimeout(() => resolve({ ok: true, status: 200 }), 200);
      if (signal) {
        signal.addEventListener('abort', () => {
          clearTimeout(t);
          reject(new Error('Aborted'));
        });
      }
    });
  const timeoutRes = await checkServerHealth(slowFetch, { timeoutMs: 25 });
  assert.equal(timeoutRes.online, false);
  assert.equal(timeoutRes.status, 0);
});

testFn('createHealthMonitor pauses when document.hidden is true and re-checks on visibilitychange and online', async () => {
  const docListeners = {};
  const winListeners = {};
  const fakeDoc = {
    hidden: false,
    addEventListener(type, fn) {
      docListeners[type] = fn;
    },
    removeEventListener(type, fn) {
      if (docListeners[type] === fn) delete docListeners[type];
    },
  };
  const fakeWin = {
    addEventListener(type, fn) {
      winListeners[type] = fn;
    },
    removeEventListener(type, fn) {
      if (winListeners[type] === fn) delete winListeners[type];
    },
  };

  let fetchCount = 0;
  const fakeFetch = async () => {
    fetchCount += 1;
    return { ok: true, status: 200 };
  };

  const results = [];
  const monitor = createHealthMonitor({
    intervalMs: 100000,
    fetchImpl: fakeFetch,
    doc: fakeDoc,
    win: fakeWin,
    onChange: (r) => results.push(r),
  });

  // Initial check runs immediately when visible
  await new Promise((r) => setTimeout(r, 15));
  assert.equal(fetchCount, 1);
  assert.equal(results.length, 1);
  assert.equal(results[0].online, true);
  assert.equal(monitor.isRunning(), true);

  // Hide document -> pauses timer and does not trigger new check
  fakeDoc.hidden = true;
  docListeners.visibilitychange();
  assert.equal(monitor.isRunning(), false);
  assert.equal(fetchCount, 1);

  // Become visible again -> immediately re-checks and restarts timer
  fakeDoc.hidden = false;
  docListeners.visibilitychange();
  await new Promise((r) => setTimeout(r, 15));
  assert.equal(fetchCount, 2);
  assert.equal(monitor.isRunning(), true);

  // Trigger window 'online' event -> immediately re-checks
  winListeners.online();
  await new Promise((r) => setTimeout(r, 15));
  assert.equal(fetchCount, 3);

  monitor.stop();
  assert.equal(monitor.isRunning(), false);
});
