import fs from 'node:fs';
import { MOTION_PRESETS } from '../../frontend/src/lib/motion/motionPresets.js';
import { sampleCanvasMotion } from '../../frontend/src/lib/motion/rendererAdapter.js';

const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const frames = [];

for (const presetId of input.preset_ids) {
  const preset = MOTION_PRESETS[presetId];
  if (!preset) throw new Error(`Unknown motion preset: ${presetId}`);
  for (const normalizedTime of input.sample_times) {
    const sample = sampleCanvasMotion(preset, normalizedTime);
    frames.push({
      preset_id: presetId,
      normalized_time: normalizedTime,
      state: sample.state,
      metadata: sample.metadata,
    });
  }
}

process.stdout.write(JSON.stringify({ width: input.width, height: input.height, frames }));
