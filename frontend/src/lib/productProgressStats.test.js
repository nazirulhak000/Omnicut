import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { getProductProgressStats, getAngleEngineBadge } from './productProgressStats.js';

describe('getProductProgressStats', () => {
  it('returns zeroes when product has no renders', () => {
    const product = {
      id: 'p1',
      angles: [{ angle_id: 'ang_01', status: 'scripted' }],
      export_stats: { native_count: 0, flow_count: 0, hyperframes_count: 0, total_rendered: 0 },
    };
    const res = getProductProgressStats(product);
    assert.equal(res.total, 1);
    assert.equal(res.totalDone, 0);
    assert.equal(res.displayDone, 0);
    assert.equal(res.nativePct, 0);
    assert.equal(res.flowPct, 0);
    assert.equal(res.hfPct, 0);
    assert.equal(res.isComplete, false);
    assert.equal(res.colorClass, 'text-slate-400');
  });

  it('calculates 3-segment percentages when native, flow, and HF renders all exist under target', () => {
    const product = {
      id: 'p2',
      angles: Array.from({ length: 20 }, (_, i) => ({ angle_id: `ang_${i + 1}` })),
      export_stats: { native_count: 4, flow_count: 2, hyperframes_count: 6, total_rendered: 12 },
    };
    const res = getProductProgressStats(product);
    assert.equal(res.total, 20);
    assert.equal(res.totalDone, 12);
    assert.equal(res.displayDone, 12);
    // 4 / 20 = 20%
    assert.equal(res.nativePct, 20);
    // 2 / 20 = 10%
    assert.equal(res.flowPct, 10);
    // 6 / 20 = 30%
    assert.equal(res.hfPct, 30);
    assert.equal(res.isComplete, false);
    assert.equal(res.colorClass, 'text-[#25F4EE]');
  });

  it('fills 100% tube when renders reach or exceed target across all 3 mixed segments', () => {
    const product = {
      id: 'hoy01',
      angles: Array.from({ length: 20 }, (_, i) => ({ angle_id: `ang_${i + 1}` })),
      export_stats: { native_count: 6, flow_count: 4, hyperframes_count: 16, total_rendered: 26 },
    };
    const res = getProductProgressStats(product);
    assert.equal(res.total, 20);
    assert.equal(res.totalDone, 26);
    assert.equal(res.displayDone, 20); // capped at total
    assert.equal(res.isComplete, true);
    // 6 / 26 = 23%, 4 / 26 = 15%, hfPct = 100 - (23 + 15) = 62%
    assert.equal(res.nativePct + res.flowPct + res.hfPct, 100);
    assert.equal(res.nativePct, 23);
    assert.equal(res.flowPct, 15);
    assert.equal(res.hfPct, 62);
    assert.equal(res.colorClass, 'text-[#25F4EE]');
  });

  it('handles Flow-only product (e.g. VEO01)', () => {
    const product = {
      id: 'veo01',
      angles: Array.from({ length: 10 }, (_, i) => ({ angle_id: `ang_${i + 1}` })),
      export_stats: { native_count: 0, flow_count: 10, hyperframes_count: 0, total_rendered: 10 },
    };
    const res = getProductProgressStats(product);
    assert.equal(res.total, 10);
    assert.equal(res.totalDone, 10);
    assert.equal(res.displayDone, 10);
    assert.equal(res.nativePct, 0);
    assert.equal(res.flowPct, 100);
    assert.equal(res.hfPct, 0);
    assert.equal(res.isComplete, true);
    assert.equal(res.colorClass, 'text-amber-400');
  });

  it('handles Flow+Native product like ESS04 (6 Native + 1 Flow = 7/7)', () => {
    const product = {
      id: 'ess04',
      angles: Array.from({ length: 7 }, (_, i) => ({ angle_id: `ang_${i + 1}` })),
      export_stats: { native_count: 6, flow_count: 1, hyperframes_count: 0, total_rendered: 7 },
    };
    const res = getProductProgressStats(product);
    assert.equal(res.total, 7);
    assert.equal(res.totalDone, 7);
    assert.equal(res.displayDone, 7);
    // 6/7 = 86%, 1/7 = 14%, hf = 0%
    assert.equal(res.nativePct, 86);
    assert.equal(res.flowPct, 14);
    assert.equal(res.hfPct, 0);
    assert.equal(res.nativePct + res.flowPct + res.hfPct, 100);
    assert.equal(res.isComplete, true);
    // Mixed native + flow is mixed
    assert.equal(res.colorClass, 'text-[#25F4EE]');
  });

  it('handles 100% HyperFrames-only product (e.g. HAT02, RED01)', () => {
    const product = {
      id: 'hat02',
      angles: Array.from({ length: 20 }, (_, i) => ({ angle_id: `ang_${i + 1}` })),
      export_stats: { native_count: 0, flow_count: 0, hyperframes_count: 20, total_rendered: 20 },
    };
    const res = getProductProgressStats(product);
    assert.equal(res.total, 20);
    assert.equal(res.totalDone, 20);
    assert.equal(res.displayDone, 20);
    assert.equal(res.nativePct, 0);
    assert.equal(res.flowPct, 0);
    assert.equal(res.hfPct, 100);
    assert.equal(res.isComplete, true);
    assert.equal(res.colorClass, 'text-sky-400');
  });

  it('handles 100% Native-only product', () => {
    const product = {
      id: 'nat01',
      angles: Array.from({ length: 7 }, (_, i) => ({ angle_id: `ang_${i + 1}` })),
      export_stats: { native_count: 7, flow_count: 0, hyperframes_count: 0, total_rendered: 7 },
    };
    const res = getProductProgressStats(product);
    assert.equal(res.total, 7);
    assert.equal(res.totalDone, 7);
    assert.equal(res.displayDone, 7);
    assert.equal(res.nativePct, 100);
    assert.equal(res.flowPct, 0);
    assert.equal(res.hfPct, 0);
    assert.equal(res.isComplete, true);
    assert.equal(res.colorClass, 'text-emerald-400');
  });

  it('falls back to angle status inspection if export_stats is missing and detects Flow, HF, and Native', () => {
    const product = {
      id: 'mix01',
      product_code: 'MIX01',
      angles: [
        { angle_id: 'ang_01', status: 'rendered', video_url: '04_Exports/Ready_to_post/20261114_mix01_ai_veo_v1.mp4' },
        { angle_id: 'ang_02', status: 'rendered', video_url: '04_Exports/Ready_to_post/20261015_mix01-pov-s01_v1.mp4' },
        { angle_id: 'ang_03', status: 'rendered', video_url: '04_Exports/Ready_to_post/20261015_mix01-review_v1.mp4' },
        { angle_id: 'ang_04', status: 'scripted' },
      ],
    };
    const res = getProductProgressStats(product);
    assert.equal(res.total, 4);
    assert.equal(res.totalDone, 3);
    assert.equal(res.displayDone, 3);
    assert.equal(res.effectiveFlow, 1);
    assert.equal(res.effectiveHf, 1);
    assert.equal(res.effectiveNative, 1);
    assert.equal(res.flowPct, 25);   // 1 / 4 = 25%
    assert.equal(res.hfPct, 25);     // 1 / 4 = 25%
    assert.equal(res.nativePct, 25); // 1 / 4 = 25%
    assert.equal(res.colorClass, 'text-[#25F4EE]');
  });
});

describe('getAngleEngineBadge', () => {
  it('returns null for null angle or unrendered angle without video', () => {
    assert.equal(getAngleEngineBadge(null), null);
    assert.equal(getAngleEngineBadge({ status: 'scripted' }), null);
    assert.equal(getAngleEngineBadge({ status: 'in_production' }), null);
  });

  it('detects Google Flow (Veo AI) from source_kind or video_url', () => {
    const b1 = getAngleEngineBadge({ status: 'rendered', source_kind: 'flow', video_url: '04_Exports/clip.mp4' });
    assert.equal(b1?.type, 'flow');
    assert.equal(b1?.label, '⚡ Flow');
    assert.match(b1?.chipClass, /amber/);

    const b2 = getAngleEngineBadge({ status: 'rendered', video_url: '04_Exports/Ready_to_post/20261115_001759_สายชาร์จเร็ว_Essager_100W_pain_point_AI_Veo_v1.mp4' });
    assert.equal(b2?.type, 'flow');
    assert.equal(b2?.label, '⚡ Flow');
  });

  it('detects HyperFrames from source_kind or couple POV naming', () => {
    const b1 = getAngleEngineBadge({ status: 'rendered', source_kind: 'hyperframes', video_url: '04_Exports/clip.mp4' });
    assert.equal(b1?.type, 'hyperframes');
    assert.equal(b1?.label, 'HyperFrames');
    assert.match(b1?.chipClass, /sky/);

    const b2 = getAngleEngineBadge({ status: 'rendered', video_url: '04_Exports/Ready_to_post/20261015_hat02-pov-s01_v1.mp4' });
    assert.equal(b2?.type, 'hyperframes');
    assert.equal(b2?.label, 'HyperFrames');
  });

  it('detects Native Program for standard rendered footage', () => {
    const b1 = getAngleEngineBadge({ status: 'rendered', video_url: '04_Exports/Posted/ESS04-รีวิวสเปก_1_20261109_001645.mp4' });
    assert.equal(b1?.type, 'native');
    assert.equal(b1?.label, 'ปกติ');
    assert.match(b1?.chipClass, /emerald/);
  });
});
