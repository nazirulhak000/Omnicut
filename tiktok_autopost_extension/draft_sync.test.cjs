const { test } = require('node:test');
const assert = require('node:assert/strict');
const sync = require('./draft_sync.js');

const DAY = sync.DAY_MS;
test('a partial Drafts scan cannot prove a missing or externally posted draft',()=>{
  for(const match of [true,false])assert.equal(sync.classifyDraft({present:false,match,complete:true,draftComplete:false}).state,'unknown');
  assert.equal(sync.classifyDraft({present:false,match:false,complete:true,draftComplete:true}).state,'deleted');
});

test('sync response must contain one known verdict for every requested id', () => {
  const drafts = [{id:'a'},{id:'b'}];
  const good = {success:true,results:[{id:'a',state:'ok'},{id:'b',state:'ok'}]};
  assert.equal(sync.validateResults(drafts,good).ok,true);
  for (const bad of [undefined, {}, {success:false,results:good.results}, {success:true,results:[]},
    {success:true,results:[{id:'a',state:'ok'}]},
    {success:true,results:[{id:'a',state:'ok'},{id:'a',state:'ok'}]},
    {success:true,results:[{id:'a',state:'ok'},{id:'x',state:'ok'}]},
    {success:true,results:[{id:'a',state:'ok'},{id:'b',state:'unexpected'}]}]) {
    const verdict=sync.validateResults(drafts,bad);
    assert.equal(verdict.ok,false);
    assert.deepEqual(verdict.results.map(r=>r.state),['unknown','unknown']);
  }
  for (const state of ['unknown','deleted','posted_outside','duplicate_risk']) {
    assert.equal(sync.validateResults(drafts,{success:true,results:[{id:'a',state:'ok'},{id:'b',state}]}).ok,false);
  }
});

test('look-back: from the oldest draft save time (minus one day), never beyond a draft lifetime, whole window when unknown', () => {
  const now = Date.UTC(2026, 10, 10, 12, 0, 0);
  assert.equal(sync.lookbackCutoff([{ savedAtMs: now - 3 * DAY }, { savedAtMs: now - DAY }], now), now - 4 * DAY);        // oldest - 1 day
  assert.equal(sync.lookbackCutoff([{ savedAtMs: now - 100 * DAY }], now), now - 60 * DAY);                              // TikTok deletes drafts after 60 days
  assert.equal(sync.lookbackCutoff([{ savedAtMs: now - DAY }, { savedAtMs: null }], now), now - 60 * DAY);               // one unknown -> safe full window
  assert.equal(sync.lookbackCutoff([], now), now - 60 * DAY);
});

test('verdicts: ok / duplicate risk / posted outside / deleted / unknown (scan not complete)', () => {
  assert.equal(sync.classifyDraft({ present: true, match: false, complete: true }).state, 'ok');
  assert.equal(sync.classifyDraft({ present: true, match: true, complete: true }).state, 'duplicate_risk');
  assert.equal(sync.classifyDraft({ present: false, match: true, complete: false }).state, 'posted_outside');
  assert.equal(sync.classifyDraft({ present: false, match: false, complete: true }).state, 'deleted');
  // never claim "deleted" from a scan that was cut short
  assert.equal(sync.classifyDraft({ present: false, match: false, complete: false }).state, 'unknown');
});

test('only deleted / posted-outside / duplicate-risk block a run; summary lists the problems', () => {
  for (const state of ['deleted', 'posted_outside', 'duplicate_risk']) assert.equal(sync.isBlocking(state), true);
  for (const state of ['ok', 'unknown', undefined]) assert.equal(sync.isBlocking(state), false);
  const summary = sync.summarize([{ id: 'a', state: 'ok' }, { id: 'b', state: 'deleted' }, { id: 'c', state: 'ok' }]);
  assert.equal(summary.ok, false);
  assert.deepEqual(summary.problems.map((p) => p.id), ['b']);
  assert.deepEqual(summary.counts, { ok: 2, deleted: 1 });
  assert.equal(sync.summarize([{ state: 'ok' }]).ok, true);
});
