import test from 'node:test';
import assert from 'node:assert/strict';

import {
  canRenderProject,
  projectDisplayName,
  timelineWithClips,
} from './gadgetMediaProject.js';


test('projectDisplayName keeps brand and model names intact', () => {
  assert.equal(projectDisplayName({
    product_identity: { brand: 'Xiaomi', model: '14T Pro', variant: 'Titan Black' },
  }), 'Xiaomi 14T Pro Titan Black');
});


test('timelineWithClips recomputes played duration from trims and speed', () => {
  const timeline = timelineWithClips({ project_id: 'one' }, [
    { id: 'a', trim_start: 2, trim_end: 12, speed: 2 },
    { id: 'b', trim_start: 0, trim_end: 4, speed: 1, freeze_tail: 1 },
  ]);
  assert.equal(timeline.duration, 10);
  assert.equal(timeline.clips, timeline.clip_list);
});


test('render is allowed only after hard gates and ready_to_render state', () => {
  assert.equal(canRenderProject({ status: 'ready_to_render', quality_report: { passed: true } }), true);
  assert.equal(canRenderProject({ status: 'ready_to_render', quality_report: { passed: false } }), false);
  assert.equal(canRenderProject({ status: 'rendered', quality_report: { passed: true } }), false);
});
