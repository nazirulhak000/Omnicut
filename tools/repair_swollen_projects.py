"""
Utility tool to repair swollen project clip durations caused by
the previous compounding transition overlap bug.

For each project, it calculates:
  target_sum = total_duration + sum(non_cut_transition_overlaps)
If current clip sum exceeds target_sum by more than 0.1s, it normalizes
durations and trim_ends back to target_sum while preserving proportional
timing and trim_start in-points.
"""

import json
import shutil
from pathlib import Path

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "03_Projects"


def normalize_project(project_json_path: Path, dry_run: bool = False) -> bool:
    with open(project_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_duration = float(data.get("total_duration") or 0.0)
    if total_duration <= 0:
        return False

    clips = data.get("clip_list") or []
    if not clips or len(clips) < 2:
        return False

    transitions = data.get("transitions") or []
    overlaps = 0.0
    for i, b in enumerate(transitions[: len(clips) - 1]):
        kind = b.get("type") if isinstance(b, dict) else str(b)
        if kind and kind != "cut":
            overlaps += float(b.get("duration") or 0.25)

    target_sum = round(total_duration + overlaps, 3)
    current_sum = round(sum(float(c.get("duration") or 0.0) for c in clips), 3)

    inflation = current_sum - target_sum
    if inflation <= 0.08:
        print(f"  [OK] {project_json_path.parent.name}: Already within tolerance (diff={inflation:+.3f}s)")
        return False

    print(f"  [REPAIR] Repairing {project_json_path.parent.name}:")
    print(f"     total_duration={total_duration:.3f}s, overlaps={overlaps:.3f}s")
    print(f"     current_sum={current_sum:.3f}s -> target_sum={target_sum:.3f}s (inflation: {inflation:+.3f}s)")

    factor = target_sum / current_sum

    # Backup original before modifying
    if not dry_run:
        bak_path = project_json_path.with_suffix(".json.bak_swollen")
        if not bak_path.exists():
            shutil.copy2(project_json_path, bak_path)
            print(f"     Backup saved to: {bak_path.name}")

    acc_dur = 0.0
    for i, clip in enumerate(clips):
        old_dur = float(clip.get("duration") or 0.0)
        new_dur = round(old_dur * factor, 3)
        acc_dur += new_dur
        clip["duration"] = new_dur
        if "trim_start" in clip:
            t_start = float(clip["trim_start"])
            clip["trim_end"] = round(t_start + new_dur, 3)

    # Adjust rounding remainder on the last clip
    diff_rem = round(target_sum - acc_dur, 3)
    if abs(diff_rem) > 0.001 and len(clips) > 0:
        last = clips[-1]
        last["duration"] = round(last["duration"] + diff_rem, 3)
        if "trim_start" in last:
            last["trim_end"] = round(float(last["trim_start"]) + last["duration"], 3)

    if not dry_run:
        data["clip_list"] = clips
        if "render_params" in data and isinstance(data["render_params"], dict):
            data["render_params"]["clip_list"] = clips

        with open(project_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"     Normalized and saved successfully.")

    return True


def main():
    print(f"Scanning projects in: {PROJECTS_DIR}")
    count = 0
    repaired = 0
    for p in PROJECTS_DIR.glob("*/project.json"):
        count += 1
        if normalize_project(p, dry_run=False):
            repaired += 1
    print(f"\nDone! Inspected {count} projects, repaired {repaired} projects.")


if __name__ == "__main__":
    main()
