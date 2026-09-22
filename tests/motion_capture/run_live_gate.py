"""Run the real Canvas-vs-FFmpeg motion gate without opt-in environment state."""

from __future__ import annotations

import json
from pathlib import Path

from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.frame_pair import compare_live_frame_pair, default_pair_config
from tests.motion_capture.vite_fixture import serve_motion_capture_fixture


def main() -> int:
    with temp_capture_dir("motion-live-gate-") as temp_root:
        with serve_motion_capture_fixture() as server:
            result = compare_live_frame_pair(
                default_pair_config(server.url, Path(temp_root) / "pair")
            )
        summary = {
            "status": result["status"],
            "pixel_parity_claim": result["pixel_parity_claim"],
            "pair_identity": result["pair_identity"]["all_match"],
            "comparison": result["comparison"],
            "thresholds": result["thresholds"],
            "runtime_clean": result["runtime"]["clean"],
            "blockers": result["blockers"],
            "artifacts_cleaned_after_run": True,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
