const {test} = require('node:test');
const assert = require('node:assert/strict');
const evidence = require('./draft_evidence.js');
const url = 'https://www.tiktok.com/tiktokstudio/content?tab=draft';
const job = {caption: 'Same product review NEW', hashtags: '#EP2'};
const row = caption => `${caption}\n00:30\nNov 12, 2026`;
const page = rows => ({url, rows, draftCount: rows.length});
const baseline = rows => ({complete: true, rows});
test('old common prefix and a different EP never confirm a new draft', () => {
  const old = row('Same product review OLD #EP1');
  assert.equal(evidence.evaluate(page([old]), job, baseline([old])).created, false);
  assert.equal(evidence.matches(old, job), false);
});
test('a single matching EP needs absence in a complete pre-click inventory', () => {
  const current = row('Same product review NEW #EP2');
  assert.equal(evidence.evaluate(page([current]), job, baseline([])).created, true);
  assert.equal(evidence.evaluate(page([current]), job).created, false);
  assert.equal(evidence.evaluate(page([current]), job, baseline([current])).created, false);
  assert.equal(evidence.evaluate(page([current]), job, {rows: [], complete: false}).created, false);
});
test('ambiguous EP, heading-only text, empty caption and URL/count are insufficient', () => {
  const current = row('Same product review NEW #EP2');
  assert.equal(evidence.evaluate(page([current, current]), job, baseline([])).created, false);
  assert.equal(evidence.evaluate({...page([]),text: current},job,baseline([])).created,false);
  assert.equal(evidence.evaluate(page([current]),{caption:''},baseline([])).created,false);
  assert.equal(evidence.matches(row('title #EP2 #EP3'),job),false);
});
test('full-caption fallback refuses truncation and longer prefix collisions', () => {
  const noEp = {caption:'Same product review NEW'};
  assert.equal(evidence.evaluate(page([row(noEp.caption)]),noEp,baseline([])).created,true);
  assert.equal(evidence.matches(row('Same product review NEW extended'),noEp),false);
  assert.equal(evidence.matches(row('Same product review...'),noEp),false);
  assert.equal(evidence.evaluate(page([row(noEp.caption)]),noEp,baseline([row('Same product review...')])).created,false);
});
test('EP identity accepts truncated title but requires the exact episode', () => {
  assert.equal(evidence.matches(row('Same prod... #EP2'),job),true);
  assert.equal(evidence.matches(row('Same prod... #EP20'),job),false);
  assert.equal(evidence.hasPriorCandidate([row('Same prod...')],job),true);
});
test('a baseline from a different job or channel cannot confirm creation', () => {
  const current = row('Same product review NEW #EP2');
  for (const extra of [{jobId:'another-job'}, {channelId:'another-channel'}]) {
    assert.equal(evidence.evaluate(page([current]),job,{...baseline([]),...extra}).created,false);
  }
});
