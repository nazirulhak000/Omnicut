"""Offline Python shot allocation -> production JS preflight/preview contracts."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tests.test_shot_matching_cut_quality import _context, _run

from tests.legacy_shot_pacing import legacy_body_pacing  # noqa: F401  (fixture)

# Body-planner contracts: the M2 pacing curve is tested in test_pacing_curve.py.
pytestmark = pytest.mark.usefixtures("legacy_body_pacing")


@pytest.mark.parametrize("revisit", [False, True])
def test_generated_exhausted_scene_plan_remains_renderable_and_seekable(revisit):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for production frontend integration")
    cues = [{"start": i * 2, "end": (i + 1) * 2, "text": f"feature {i} ครับ"} for i in range(4)]
    matches = []
    for i in range(4):
        other = revisit and i == 1
        start, end = (10, 15) if other else (2, 3)
        matches.append({"cue_ids": [i + 1], "scene_id": 2 if other else 1,
                        "scene_start": start, "scene_end": end, "start_time": start,
                        "end_time": end, "punch_zoom": 1.15})
    clips = _run(_context(cues, 8, use_ai_vision=True), raw_duration=20, ai_shots=matches)
    for index, clip in enumerate(clips):
        clip["id"] = f"fixture-{index}"
    payload = {"clips": clips, "durations": {clip["id"]: 20 for clip in clips}, "expectedDuration": 8}
    script = """
      import fs from 'node:fs';
      import {analyzeRenderPreflight} from './frontend/src/lib/renderPreflight.js';
      import {buildSegments, getDrawPlan} from './frontend/src/lib/timelineMath.js';
      import {createPreviewTimelineIndex} from './frontend/src/lib/previewTimelineScheduler.js';
      const input=JSON.parse(fs.readFileSync(0,'utf8'));
      const segments=buildSegments(input.clips,input.durations);
      const indexed=createPreviewTimelineIndex(segments);
      const report=analyzeRenderPreflight({...input,segments});
      let frames=0;
      for(let t=0;t<8;t+=1/30){
        const plan=indexed.planAt(t);
        if(JSON.stringify(plan)!==JSON.stringify(getDrawPlan(segments,t))) throw Error('indexed seek parity');
        if(!plan.length || plan.some(x=>!Number.isFinite(x.localTime))) throw Error('empty/invalid picture');
        frames++;
      }
      console.log(JSON.stringify({canRender:report.canRender,issues:report.issues,frames}));
    """
    result = subprocess.run([node, "--input-type=module", "-e", script], input=json.dumps(payload),
                            text=True, encoding="utf-8", capture_output=True, cwd=Path(__file__).resolve().parents[1],
                            timeout=15, check=True)
    report = json.loads(result.stdout)
    assert report["canRender"], report
    assert all(issue["code"] == "footage_hold" for issue in report["issues"]), report
    assert report["issues"]
    assert report["frames"] >= 240
    for issue in report["issues"]:
        assert 0 <= issue["start"] < issue["end"] <= 8 + 1 / 30
