const { test } = require('node:test');
const assert = require('node:assert/strict');
const { redact, createRunRecorder, KEY } = require('./run_history.js');

function memoryStorage() {
  const data = {};
  return { data, get: async (key) => (key in data ? { [key]: JSON.parse(JSON.stringify(data[key])) } : {}), set: async (obj) => { Object.assign(data, JSON.parse(JSON.stringify(obj))); } };
}

test('redact removes handles, e-mails, long numbers and URL queries', () => {
  const out = redact('โพสต์โดย @rizanntry โทร 081-234-5678 mail me@example.com https://www.tiktok.com/x?token=abc123&id=99 เหลือ 5 วัน');
  assert.doesNotMatch(out, /rizanntry|081|example\.com|token=|abc123/);
  assert.match(out, /@\[handle\]/);
  assert.match(out, /\[number\]/);
  assert.match(out, /\?\[query\]/);
  assert.match(out, /เหลือ 5 วัน/);   // short numbers are left alone
});

test('a run is persisted with job ids on each line and survives a "new panel" (fresh recorder, same storage)', async () => {
  const storage = memoryStorage();
  let t = 1_700_000_000_000;
  const rec = createRunRecorder({ storage, now: () => (t += 1000), flushEvery: 2 });
  await rec.start({ mode: 'smart', clips: 2 });
  rec.log('info', 'เริ่ม');
  rec.setJob('job-1', 'คลิปแรก');
  rec.log('success', 'สำเร็จ');
  rec.log('warn', 'บรรทัดที่สาม');
  await rec.finish({ finalKind: 'success' });
  const reopened = createRunRecorder({ storage });
  const text = await reopened.exportText();
  assert.match(text, /\{job-1\}.*สำเร็จ/);
  assert.doesNotMatch(text.split('\n').find((l) => l.includes('เริ่ม') && l.includes('[info]')) || '', /\{job-/);   // before any job
  assert.match(text, /สรุป: .*success/);
  assert.match(text, /job-1 \(คลิปแรก\)/);
});

test('a run cut off mid-way is still readable and marked as unfinished', async () => {
  const storage = memoryStorage();
  const rec = createRunRecorder({ storage, flushEvery: 1 });
  await rec.start({});
  rec.log('info', 'กำลังทำ');
  await rec.flush();
  const text = await createRunRecorder({ storage }).exportText();
  assert.match(text, /ยังไม่จบ\/ถูกตัดกลางคัน/);
  assert.match(text, /กำลังทำ/);
});

test('evidence is redacted before it is stored, capped, and tied to the current job', async () => {
  const storage = memoryStorage();
  const rec = createRunRecorder({ storage, maxEvidence: 2 });
  await rec.start({});
  rec.setJob('job-9', 'x');
  await rec.addEvidence({ kind: 'failed', stage: 'FILL_METADATA', error: 'boom @secretuser', url: 'https://www.tiktok.com/upload?a=1', title: 'Studio', text: 'user @secretuser 0812345678 ' + 'z'.repeat(5000) });
  const stored = storage.data[KEY][0].evidence[0];
  assert.equal(stored.job, 'job-9');
  assert.doesNotMatch(JSON.stringify(stored), /secretuser|0812345678|a=1/);
  assert.ok(stored.text.length <= 1800);
  await rec.addEvidence({ kind: 'k2' }); await rec.addEvidence({ kind: 'k3' });
  assert.deepEqual(storage.data[KEY][0].evidence.map((e) => e.kind), ['k2', 'k3']);
});

test('only the newest runs are kept and the line list is bounded (start and newest lines survive)', async () => {
  const storage = memoryStorage();
  const rec = createRunRecorder({ storage, maxRuns: 2, maxLines: 30, flushEvery: 1000 });
  for (let i = 0; i < 3; i += 1) { await rec.start({ n: i }); rec.log('info', `run${i}`); await rec.finish({}); }
  assert.deepEqual(storage.data[KEY].map((r) => r.meta.n), [2, 1]);
  await rec.start({});
  for (let i = 0; i < 100; i += 1) rec.log('info', `line${i}`);
  const lines = rec.current.lines.map((l) => l.message);
  assert.equal(lines.length, 30);
  assert.equal(lines[0], 'line0');
  assert.equal(lines[lines.length - 1], 'line99');
});

test('storage failures never break a run (history is best effort)', async () => {
  const rec = createRunRecorder({ storage: { get: async () => { throw new Error('nope'); }, set: async () => { throw new Error('full'); } }, flushEvery: 1 });
  await rec.start({});
  rec.log('info', 'x');
  await rec.finish({});
  assert.equal(await rec.exportText(), await rec.exportText());
});
