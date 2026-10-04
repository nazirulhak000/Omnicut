import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeRenderPreflight, formatPreflightTime, preflightBlockingMessage } from './renderPreflight.js';
import { manifestToEditorState } from './editorProjectState.js';

const clip = (extra = {}) => ({ id: 'a', source_path: 'synthetic.mp4', trim_start: 0, trim_end: 2, ...extra });
const codes = (report) => report.issues.map((issue) => issue.code);

test('valid continuous timeline has no findings', () => {
  const report = analyzeRenderPreflight({ clips: [clip(), clip({ id: 'b' })] });
  assert.equal(report.canRender, true);
  assert.deepEqual(report.issues, []);
});
test('automatic shortage gives precise speed/transition-aware hold interval and permits render', () => {
  const report = analyzeRenderPreflight({ clips: [clip(), clip({ id: 'b', trim_end: 4, speed: 2,
    freeze_tail: 3, transition_in: 'fade', transition_duration: 0.4,
    source_window: { start: 0, end: 4 }, footage_shortage: { reason: 'source_window_exhausted' } })] });
  assert.equal(report.canRender, true);
  assert.deepEqual(codes(report), ['footage_hold']);
  assert.ok(Math.abs(report.issues[0].start - 3.6) < 1e-9);
  assert.equal(report.issues[0].end, 6.6);
});
test('manual freeze and approved hold remain covered, with hold capped like renderer', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ freeze_tail: 40,
    footage_shortage: { reason: 'source_window_exhausted' } }), clip({ id: 'b', freeze_tail: 2 })], expectedDuration: 16 });
  assert.equal(report.canRender, true);
  assert.deepEqual(codes(report), ['footage_hold']);
  assert.equal(report.issues[0].end - report.issues[0].start, 10);
});
test('missing source blocks and reports its timeline range', () => {
  const report = analyzeRenderPreflight({ clips: [clip(), clip({ id: 'b', source_path: ' ' }), clip({ id: 'c' })] });
  assert.equal(report.canRender, false);
  assert.deepEqual(report.errors.map(({ code, start, end }) => [code, start, end]), [['missing_source', 2, 4]]);
  assert.equal(report.warnings[0].code, 'structural_gap');
  assert.match(preflightBlockingMessage(report), /ช็อต 2 00:02.00/);
});
test('empty timeline blocks without a fake footage finding', () => {
  assert.deepEqual(codes(analyzeRenderPreflight()), ['empty_timeline']);
});
test('negative/reversed/nonfinite trims and nonpositive speed block', () => {
  for (const extra of [{ trim_start: -1 }, { trim_end: 0 }, { trim_end: 'bad' }, { speed: 0 }, { speed: -1 }, { speed: Infinity },
    { trim_start: '  ' }, { trim_end: [2] }, { speed: [1] }]) {
    const report = analyzeRenderPreflight({ clips: [clip(extra)] });
    assert.equal(report.canRender, false, JSON.stringify(extra));
    assert.ok(codes(report).includes('invalid_timing'));
  }
});
test('unknown media duration is advisory and does not invent a gap', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ trim_end: null })], expectedDuration: 20 });
  assert.equal(report.canRender, true);
  assert.deepEqual(codes(report), ['unknown_duration']);
});
test('loaded metadata resolves omitted trim end', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ trim_end: null })], durations: { a: 7 }, expectedDuration: 7 });
  assert.deepEqual(report.issues, []);
});
test('known source length and topic boundary overrun are advisory', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ trim_start: 1, trim_end: 5, source_window: { start: 1, end: 3 } })], durations: { a: 4 } });
  assert.equal(report.canRender, true);
  assert.deepEqual(codes(report), ['source_bounds', 'source_window_bounds']);
});
test('structural intervals union overlaps and locate middle and trailing uncovered ranges', () => {
  const clips = [clip(), clip({ id: 'b' }), clip({ id: 'c' })];
  const report = analyzeRenderPreflight({ clips, segments: [
    { segStart: 0, segEnd: 3 }, { segStart: 2, segEnd: 4 }, { segStart: 6, segEnd: 8 }], expectedDuration: 10 });
  assert.equal(report.canRender, true);
  assert.deepEqual(report.warnings.map(({ start, end }) => [start, end]), [[4, 6], [8, 10]]);
  assert.ok(report.issues.every((issue) => !issue.message.includes('เฟรมดำ')));
});
test('numeric edge tolerance prevents phantom holes', () => {
  const report = analyzeRenderPreflight({ clips: [clip(), clip({ id: 'b' })], segments: [
    { segStart: 0, segEnd: 2 }, { segStart: 2.00000001, segEnd: 4 }], expectedDuration: 4.00000001 });
  assert.deepEqual(report.issues, []);
});
test('one actual frame of uncovered timeline is reported', () => {
  const report = analyzeRenderPreflight({ clips: [clip(), clip({ id: 'b' })], segments: [
    { segStart: 0, segEnd: 2 }, { segStart: 2 + 1 / 30, segEnd: 4 }] });
  assert.deepEqual(codes(report), ['structural_gap']);
  assert.equal(report.issues[0].start, 2);
  assert.equal(report.issues[0].end, 2 + 1 / 30);
});
test('pending duration does not fabricate later shortage positions', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ trim_end: null }), clip({ id: 'b', freeze_tail: 3,
    footage_shortage: { reason: 'source_window_exhausted' } })] });
  assert.equal(report.canRender, true);
  assert.ok(codes(report).includes('unknown_duration'));
  const hold = report.issues.find((issue) => issue.code === 'footage_hold');
  assert.equal(hold.start, null);
  assert.equal(hold.end, null);
});

test('saved hold-only source frame is valid and reports full static interval', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ trim_start: 6.9666666667, trim_end: 7,
    source_window: { start: 2, end: 7 }, freeze_tail: 3.9666666667,
    held_source_time: 6.975, footage_shortage: { reason: 'source_window_exhausted' } })] });
  assert.equal(report.canRender, true);
  assert.deepEqual(codes(report), ['footage_hold']);
  assert.equal(report.issues[0].start, 0);
  assert.equal(report.issues[0].end, 4);
});
test('malformed declared source windows are advisory rather than silently ignored', () => {
  for (const window of [{ start: 2, end: 1 }, { start: -1, end: 2 }, { start: 0, end: 'bad' }, {}]) {
    const report = analyzeRenderPreflight({ clips: [clip({ source_window: window })] });
    assert.equal(report.canRender, true);
    assert.ok(codes(report).includes('invalid_source_window'));
  }
});
test('invalid held source times are advisory and do not block approved shortage', () => {
  for (const held of [-1, 2, 3, Infinity, NaN, 'bad', '1.5']) {
    const report = analyzeRenderPreflight({ clips: [clip({ source_window: { start: 0, end: 2 },
      freeze_tail: 3, held_source_time: held, footage_shortage: { reason: 'source_window_exhausted' } })] });
    assert.equal(report.canRender, true);
    assert.ok(codes(report).includes('invalid_held_source'));
    assert.ok(codes(report).includes('footage_hold'));
  }
});
test('missing segment position is explicit pending and does not manufacture gap', () => {
  const report = analyzeRenderPreflight({ clips: [clip()], segments: [], expectedDuration: 20 });
  assert.equal(report.canRender, true);
  assert.deepEqual(codes(report), ['unknown_position']);
  assert.equal(report.issues[0].start, null);
  assert.equal(report.issues[0].end, null);
});
test('invalid supplied interval does not fabricate a hold range', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ freeze_tail: 3, footage_shortage: { reason: 'source_window_exhausted' } })],
    segments: [{ segStart: 5, segEnd: 2 }] });
  assert.equal(report.canRender, true);
  const hold = report.issues.find((issue) => issue.code === 'footage_hold');
  assert.equal(hold.start, null);
  assert.equal(hold.end, null);
});
test('unknown clip duration cannot assign an incoming transition start', () => {
  const report = analyzeRenderPreflight({ clips: [clip(), clip({ id: 'b', trim_end: null,
    transition_in: 'fade', transition_duration: 1 })] });
  const pending = report.issues.find((issue) => issue.code === 'unknown_duration');
  assert.equal(pending.start, null);
});
test('nonfinite transition metadata is advisory and later positions are unknown', () => {
  const report = analyzeRenderPreflight({ clips: [clip(), clip({ id: 'b', transition_in: 'fade', transition_duration: 'bad' })] });
  assert.equal(report.canRender, true);
  assert.ok(codes(report).includes('invalid_transition'));
  assert.ok(codes(report).includes('unknown_position'));
});
test('unsupported transition kind is advisory without blocking timeline', () => {
  const report = analyzeRenderPreflight({ clips: [clip(), clip({ id: 'b', transition_in: 'unsupported-effect' })] });
  assert.equal(report.canRender, true);
  assert.deepEqual(codes(report), ['invalid_transition']);
});
test('held timestamp outside semantic window warns even when within source trim', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ trim_end: 4, source_window: { start: 0, end: 2 },
    freeze_tail: 3, held_source_time: 3, footage_shortage: { reason: 'source_window_exhausted' } })] });
  assert.equal(report.canRender, true);
  assert.ok(codes(report).includes('invalid_held_source'));
});
test('saved normalized speed bounds are advisory while actual invalid speed still blocks', () => {
  for (const speed of [0.1, 8]) {
    const report = analyzeRenderPreflight({ clips: [clip({ speed })] });
    assert.equal(report.canRender, true);
    assert.ok(codes(report).includes('normalized_speed'));
  }
});
test('legacy separate transitions hydrate into continuous saved-plan coverage', () => {
  // Synthetic source references and plan, no production manifest reads.
  const manifest = { clip_list: [clip({ id: undefined, trim_start: 33, trim_end: 37.89, speed: .8291 }),
    clip({ id: undefined, trim_start: 67, trim_end: 72.347, speed: .9913 }),
    clip({ id: undefined, trim_start: 0, trim_end: 6.673, speed: 1.0662 }),
    clip({ id: undefined, trim_start: 85, trim_end: 92.648, speed: 1.2809 }),
    clip({ id: undefined, trim_start: 49, trim_end: 55, speed: 1.1728 })],
    transitions: ['circleclose', 'circleopen', 'circleclose', 'circleopen'].map((type) => ({ type, duration: .35 })) };
  const state = manifestToEditorState(manifest);
  const report = analyzeRenderPreflight({ clips: state.clipList, expectedDuration: 27.237667 });
  assert.equal(state.clipList[1].transition_in, 'circleclose');
  assert.deepEqual(report.issues, []);
});
test('transition handles clamp to available frames without a phantom hole', () => {
  const report = analyzeRenderPreflight({ clips: [clip({ trim_end: .3 }), clip({ id: 'b', trim_end: .3,
    transition_in: 'fade', transition_duration: 20 })] });
  assert.equal(report.canRender, true);
  assert.deepEqual(report.issues, []);
});
test('timestamps round and carry minutes correctly and preserve unknown values', () => {
  assert.equal(formatPreflightTime(59.999), '01:00.00');
  assert.equal(formatPreflightTime(125.25), '02:05.25');
  assert.equal(formatPreflightTime(null), 'ไม่ทราบเวลา');
});
