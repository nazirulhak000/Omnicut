// Hook/text motion easing in the preview (SequencePlayer.jsx) must use the
// same power-law curve libass applies to `\t(t1,t2,accel,...)`:
// value = v1 + (v2 - v1) * progress ** accel. Round EDITOR-CUT-QUALITY-R2.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { sampleMotionContract } from './motion/motionContract.js';
import { MOTION_PRESETS } from './motion/motionPresets.js';

const source = readFileSync(new URL('../components/SequencePlayer.jsx', import.meta.url), 'utf8');
const start = source.indexOf('const ACCEL_SOFT_OUT');
const end = source.indexOf('// Motion contracts are deliberately opt-in.');

function loadMotion() {
  assert.ok(start >= 0 && end > start, 'motion region moved');
  // eslint-disable-next-line no-new-func
  return new Function(
    'HOOK_DIM_OPACITY',
    `${source.slice(start, end)}; return { ACCEL_SOFT_OUT, ACCEL_SNAP_IN, OVERLAY_IN_TRANSFORMS, OVERLAY_LOOP_TRANSFORMS, OVERLAY_OUT_TRANSFORMS };`,
  )(0.85);
}

const power = (v1, v2, p, accel) => v1 + (v2 - v1) * p ** accel;
const close = (a, b, msg) => assert.ok(Math.abs(a - b) < 1e-9, `${msg}: ${a} vs ${b}`);

test('bounce eases every segment with ACCEL_SOFT_OUT and rests at 1.0', () => {
  const m = loadMotion();
  const kf = [[0, 0.6], [150, 1.25], [280, 0.92], [380, 1.05], [450, 1.0]];
  for (let i = 0; i < kf.length - 1; i++) {
    const [t1, v1] = kf[i];
    const [t2, v2] = kf[i + 1];
    for (const f of [0.25, 0.5, 0.75]) {
      const ms = t1 + (t2 - t1) * f;
      close(m.OVERLAY_IN_TRANSFORMS.bounce.at(ms).scale, power(v1, v2, f, m.ACCEL_SOFT_OUT), `bounce@${ms}`);
    }
  }
  assert.equal(m.OVERLAY_IN_TRANSFORMS.bounce.at(450).scale, 1.0);
  assert.equal(m.OVERLAY_IN_TRANSFORMS.bounce.at(9999).scale, 1.0);
});

test('pop and zoom entrances settle with ACCEL_SOFT_OUT onto 1.0', () => {
  const m = loadMotion();
  close(m.OVERLAY_IN_TRANSFORMS.pop.at(60).scale, power(0.55, 1.18, 0.5, m.ACCEL_SOFT_OUT), 'pop rise');
  close(m.OVERLAY_IN_TRANSFORMS.pop.at(160).scale, power(1.18, 1.0, 0.5, m.ACCEL_SOFT_OUT), 'pop settle');
  close(m.OVERLAY_IN_TRANSFORMS.zoom.at(150).scale, power(1.8, 1.0, 0.5, m.ACCEL_SOFT_OUT), 'zoom');
  assert.equal(m.OVERLAY_IN_TRANSFORMS.pop.at(200).scale, 1.0);
  assert.equal(m.OVERLAY_IN_TRANSFORMS.zoom.at(300).scale, 1.0);
});

test('fade/zoom exits ease in with ACCEL_SNAP_IN and end fully transparent', () => {
  const m = loadMotion();
  const p = 0.5;
  close(m.OVERLAY_OUT_TRANSFORMS.fade(1.075, 1.0, 1.15).alpha, 1 - p ** m.ACCEL_SNAP_IN, 'fade');
  close(m.OVERLAY_OUT_TRANSFORMS.zoom(1.075, 1.0, 1.15).scale, 1 + 0.4 * p ** m.ACCEL_SNAP_IN, 'zoom scale');
  close(m.OVERLAY_OUT_TRANSFORMS.fade(1.15, 1.0, 1.15).alpha, 0, 'fade end');
});

test('shake and glitch steps are whole 30 fps frames', () => {
  const frame = 1 / 30;
  for (const step of [0.1, 0.033]) {
    const frames = Math.max(1, Math.round(step / frame));
    assert.ok(Math.abs(step - frames * frame) <= 0.001, `${step}s off grid`);
  }
  assert.match(source, /shake: \(t, s, e\) => \(\{ rot: hookCycleAt\(t, s, e, 0\.1,/);
  assert.match(source, /hookCycleAt\(t, s, Math\.max\(s \+ 0\.001, e - 0\.033\), 0\.033,/);
});

// ---- catalog (motionPresets.js) <-> preview evaluators --------------------
// The declarative catalog must sample to the same values as the live preview
// presets, so it cannot drift from the eased builders again (round R2, lane E2b).
// tests/test_motion_catalog_builder_tie.py ties the same catalog to the ASS
// builders and to the Python catalog.
const FRACTIONS = [0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1];
const CATALOG_TRACK_OF_PREVIEW = { scale: 'scale', alpha: 'alpha', dy: 'dy', blur: 'blur', reveal: 'reveal', rot: 'rotation' };

function assertCatalogMatchesPreview(id, contract, livePreview, label) {
  for (const f of FRACTIONS) {
    const sampled = sampleMotionContract(contract, f);
    const live = livePreview(f);
    for (const [liveKey, trackName] of Object.entries(CATALOG_TRACK_OF_PREVIEW)) {
      if (live[liveKey] === undefined && sampled[trackName] === undefined) continue;
      assert.notEqual(sampled[trackName], undefined, `${id}: preview animates ${liveKey} but the catalog has no ${trackName} track`);
      assert.notEqual(live[liveKey], undefined, `${id}: catalog animates ${trackName} but the preview has no ${liveKey}`);
      close(live[liveKey], sampled[trackName], `${id}.${trackName}@${label(f)}`);
    }
  }
}

test('catalog In presets sample exactly like the preview In transforms', () => {
  const m = loadMotion();
  for (const [name, preset] of Object.entries(m.OVERLAY_IN_TRANSFORMS)) {
    const contract = MOTION_PRESETS[`hook.in.${name}`];
    assert.ok(contract, `hook.in.${name} missing from the catalog`);
    close(preset.durSec * 1000, contract.duration_ms, `hook.in.${name} duration`);
    if (!contract.duration_ms) continue;
    assertCatalogMatchesPreview(`hook.in.${name}`, contract, (f) => preset.at(f * contract.duration_ms), (f) => `${f * contract.duration_ms}ms`);
  }
});

test('catalog Out presets sample exactly like the preview Out transforms', () => {
  const m = loadMotion();
  // out.none is a 1 ms hard cut whose preview edge sits on the window start; compared by value below.
  for (const name of ['fade', 'slide', 'zoom', 'glitch']) {
    const contract = MOTION_PRESETS[`hook.out.${name}`];
    const spanSec = contract.duration_ms / 1000;
    assertCatalogMatchesPreview(
      `hook.out.${name}`,
      contract,
      (f) => m.OVERLAY_OUT_TRANSFORMS[name](1.0 + f * spanSec, 1.0, 1.0 + spanSec),
      (f) => `${f * contract.duration_ms}ms`,
    );
  }
  assert.equal(MOTION_PRESETS['hook.out.none'].duration_ms, 1);
});

test('catalog shake and wave cycles equal the preview step chains', () => {
  const m = loadMotion();
  for (const [name, stepSec, steps] of [['shake', 0.1, 5], ['wave', 0.4, 3]]) {
    const contract = MOTION_PRESETS[`hook.loop.${name}`];
    close(contract.duration_ms, stepSec * steps * 1000, `${name} cycle ms`);
    close(contract.tracks.rotation.cycle_duration_ms, contract.duration_ms, `${name} cycle_duration_ms`);
    for (const cycle of [0, 1]) {
      for (const f of FRACTIONS.filter((v) => v < 1)) {
        const tSec = (cycle + f) * contract.duration_ms / 1000;
        close(m.OVERLAY_LOOP_TRANSFORMS[name](tSec, 0, 5).rot, sampleMotionContract(contract, f).rotation, `${name}@cycle${cycle}+${f}`);
      }
    }
  }
});
