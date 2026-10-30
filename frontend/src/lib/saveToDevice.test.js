import test from 'node:test';
import assert from 'node:assert/strict';

import {
  clearPrefetchCache,
  getCachedVideoFile,
  parseContentRange,
  prefetchVideoFile,
  resolveVideoFilename,
  sharePreparedFileSync,
  withDownloadParam,
} from './saveToDevice.js';

function makeDeterministicBytes(length) {
  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i += 1) {
    bytes[i] = (i * 31 + 7) & 0xff;
  }
  return bytes;
}

test('parseContentRange and withDownloadParam handle standard headers and URLs', () => {
  assert.deepEqual(parseContentRange('bytes 0-4194303/31457280'), {
    start: 0,
    end: 4194303,
    total: 31457280,
  });
  assert.deepEqual(parseContentRange('bytes 100-199/*'), {
    start: 100,
    end: 199,
    total: null,
  });
  assert.equal(parseContentRange('invalid'), null);

  assert.equal(
    withDownloadParam('/api/media/04_Exports/clip01.mp4?channel=main'),
    '/api/media/04_Exports/clip01.mp4?channel=main&download=1',
  );
  assert.equal(
    withDownloadParam('https://studio.example.com/api/media/clip.mp4'),
    'https://studio.example.com/api/media/clip.mp4?download=1',
  );
  assert.equal(resolveVideoFilename('/api/media/04_Exports/ttz_s01.mp4'), 'ttz_s01.mp4');
  assert.equal(resolveVideoFilename('/api/media/04_Exports/ttz_s01', 'custom_name'), 'custom_name.mp4');
});

test('prefetchVideoFile downloads in 206 Range chunks, reports progress, and caches assembled File', async () => {
  clearPrefetchCache();
  const totalSize = 300 * 1024; // 300 KiB
  const chunkSize = 100 * 1024; // 100 KiB (3 chunks)
  const sourceBytes = makeDeterministicBytes(totalSize);
  const requestedRanges = [];
  const progressEvents = [];

  const fakeFetch = async (_url, options = {}) => {
    const rangeHeader = options.headers?.Range || '';
    requestedRanges.push(rangeHeader);
    const match = rangeHeader.match(/^bytes=(\d+)-(\d+)$/);
    assert.ok(match, `Expected Range header, got ${rangeHeader}`);
    const start = Number(match[1]);
    const end = Math.min(Number(match[2]), totalSize - 1);
    const slice = sourceBytes.slice(start, end + 1);
    return {
      ok: true,
      status: 206,
      headers: new Map([
        ['content-range', `bytes ${start}-${end}/${totalSize}`],
        ['content-length', String(slice.byteLength)],
      ]),
      arrayBuffer: async () => slice.buffer.slice(slice.byteOffset, slice.byteOffset + slice.byteLength),
    };
  };

  const url = '/api/media/04_Exports/Ready_to_post/20261030_ttz_s01.mp4?channel=main';
  const file = await prefetchVideoFile(url, {
    filename: '20261030_ttz_s01.mp4',
    chunkSize,
    fetchImpl: fakeFetch,
    onProgress: (p) => progressEvents.push(p),
  });

  assert.equal(file.name, '20261030_ttz_s01.mp4');
  assert.equal(file.type, 'video/mp4');
  assert.equal(file.size, totalSize);
  assert.deepEqual(requestedRanges, [
    `bytes=0-${chunkSize - 1}`,
    `bytes=${chunkSize}-${2 * chunkSize - 1}`,
    `bytes=${2 * chunkSize}-${3 * chunkSize - 1}`,
  ]);
  assert.equal(progressEvents.length, 3);
  assert.equal(progressEvents[0].loaded, chunkSize);
  assert.equal(progressEvents[2].loaded, totalSize);
  assert.equal(progressEvents[2].percent, 100);

  const assembled = new Uint8Array(await file.arrayBuffer());
  assert.deepEqual(assembled, sourceBytes);

  // Second call hits LRU cache with zero extra network calls
  const cachedFile = await prefetchVideoFile(url, {
    filename: '20261030_ttz_s01.mp4',
    chunkSize,
    fetchImpl: fakeFetch,
  });
  assert.equal(requestedRanges.length, 3);
  assert.equal(cachedFile.size, totalSize);
  assert.ok(getCachedVideoFile(url));
});

test('prefetchVideoFile retries a failed chunk without re-downloading earlier chunks', async () => {
  clearPrefetchCache();
  const totalSize = 200 * 1024;
  const chunkSize = 100 * 1024;
  const sourceBytes = makeDeterministicBytes(totalSize);
  const calls = [];
  let secondChunkFailures = 0;

  const fakeFetch = async (_url, options = {}) => {
    const rangeHeader = options.headers?.Range || '';
    calls.push(rangeHeader);
    const match = rangeHeader.match(/^bytes=(\d+)-(\d+)$/);
    const start = Number(match[1]);
    const end = Math.min(Number(match[2]), totalSize - 1);

    if (start === chunkSize && secondChunkFailures < 2) {
      secondChunkFailures += 1;
      throw new Error('Transient tunnel network reset');
    }

    const slice = sourceBytes.slice(start, end + 1);
    return {
      ok: true,
      status: 206,
      headers: {
        'content-range': `bytes ${start}-${end}/${totalSize}`,
      },
      arrayBuffer: async () => slice.buffer.slice(slice.byteOffset, slice.byteOffset + slice.byteLength),
    };
  };

  const file = await prefetchVideoFile('/api/media/retry_clip.mp4', {
    filename: 'retry_clip.mp4',
    chunkSize,
    fetchImpl: fakeFetch,
    maxRetries: 3,
    retryDelayMs: 1,
  });

  assert.equal(file.size, totalSize);
  // First chunk fetched once, second chunk attempted 3 times (2 failures + 1 success)
  assert.deepEqual(calls, [
    `bytes=0-${chunkSize - 1}`,
    `bytes=${chunkSize}-${2 * chunkSize - 1}`,
    `bytes=${chunkSize}-${2 * chunkSize - 1}`,
    `bytes=${chunkSize}-${2 * chunkSize - 1}`,
  ]);
  const assembled = new Uint8Array(await file.arrayBuffer());
  assert.deepEqual(assembled, sourceBytes);
});

test('prefetchVideoFile falls back to single GET when server returns 200 instead of 206', async () => {
  clearPrefetchCache();
  const sourceBytes = makeDeterministicBytes(90 * 1024);
  let fetchCount = 0;

  const fakeFetch = async () => {
    fetchCount += 1;
    return {
      ok: true,
      status: 200,
      headers: { 'content-length': String(sourceBytes.byteLength) },
      arrayBuffer: async () => sourceBytes.buffer.slice(0),
    };
  };

  const file = await prefetchVideoFile('/api/media/fallback200.mp4', {
    filename: 'fallback200.mp4',
    fetchImpl: fakeFetch,
  });

  assert.equal(fetchCount, 1);
  assert.equal(file.size, sourceBytes.byteLength);
  assert.deepEqual(new Uint8Array(await file.arrayBuffer()), sourceBytes);
});

test('sharePreparedFileSync calls navigator.share synchronously before any microtask', async () => {
  const events = [];
  let sharedPayload = null;

  const fakeNav = {
    canShare: (data) => {
      events.push('canShare:sync');
      return Array.isArray(data?.files) && data.files.length === 1;
    },
    share: (data) => {
      events.push('share:sync');
      sharedPayload = data;
      return Promise.resolve();
    },
  };

  const dummyFile = new File([new Uint8Array([1, 2, 3, 4])], 'clip.mp4', { type: 'video/mp4' });

  // Schedule a microtask right after invoking sharePreparedFileSync to prove
  // nav.share() already ran synchronously on the click call stack!
  const resultPromise = sharePreparedFileSync(dummyFile, {
    title: 'น้องนุ้ย & พี่บ่าว',
    text: 'แคปชันทดสอบ #รีวิวของดี',
    nav: fakeNav,
  });
  Promise.resolve().then(() => events.push('microtask'));

  assert.deepEqual(events, ['canShare:sync', 'share:sync']);
  assert.equal(sharedPayload.files[0], dummyFile);
  assert.equal(sharedPayload.title, 'น้องนุ้ย & พี่บ่าว');

  const outcome = await resultPromise;
  assert.deepEqual(outcome, { shared: true, method: 'share' });
  assert.deepEqual(events, ['canShare:sync', 'share:sync', 'microtask']);
});

test('sharePreparedFileSync falls back to <a download> with ?download=1 when Web Share is unavailable', async () => {
  const clickedAnchors = [];
  const fakeDoc = {
    body: {
      appendChild: () => {},
      removeChild: () => {},
    },
    createElement: (tag) => {
      assert.equal(tag, 'a');
      const el = {
        href: '',
        download: '',
        rel: '',
        click() {
          clickedAnchors.push({ href: this.href, download: this.download });
        },
      };
      return el;
    },
  };

  const dummyFile = new File([new Uint8Array([9, 8, 7])], '20261030_ttz_s02.mp4', {
    type: 'video/mp4',
  });

  const outcome = await sharePreparedFileSync(dummyFile, {
    fallbackDownloadUrl: '/api/media/04_Exports/Ready_to_post/20261030_ttz_s02.mp4?channel=main',
    nav: {}, // No share / canShare
    doc: fakeDoc,
  });

  assert.equal(outcome.shared, false);
  assert.equal(outcome.method, 'download');
  assert.equal(
    outcome.downloadUrl,
    '/api/media/04_Exports/Ready_to_post/20261030_ttz_s02.mp4?channel=main&download=1',
  );
  assert.equal(clickedAnchors.length, 1);
  assert.equal(
    clickedAnchors[0].href,
    '/api/media/04_Exports/Ready_to_post/20261030_ttz_s02.mp4?channel=main&download=1',
  );
  assert.equal(clickedAnchors[0].download, '20261030_ttz_s02.mp4');
});
