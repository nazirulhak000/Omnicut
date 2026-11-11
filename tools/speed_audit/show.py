"""Print a compact view of one harness result."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
d = json.loads((Path(__file__).resolve().parents[2] / ".tmp" / "speed_audit" / "out" / f"{sys.argv[1]}.json").read_text(encoding="utf-8"))
print("total", d["total_s"], "import", d.get("import_s"), "dur", d.get("total_duration"), "err", d.get("error"))
print("stages", d["stage_seconds"])
minimum = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
for e in d["events"]:
    if e["seconds"] < minimum:
        continue
    if e["kind"] == "subprocess":
        argv = e.get("argv") or []
        text = " ".join(argv)
        tail = argv[-1] if argv else ""
        flags = [a for a in argv if a.startswith("-") and a in (
            "-f", "-c:v", "-vf", "-filter_complex", "-filter_complex_script", "-ss", "-frames:v", "-af")]
        hint = ""
        for key in ("blackdetect", "freezedetect", "ssim", "atempo", "amix", "volumedetect", "null", "lavfi", "showwavespic", "sidechain", "loudnorm"):
            if key in text:
                hint += key + " "
        print(f"{e['t_start']:8.2f} +{e['seconds']:7.2f}s {e['name']:8s} argc={e['argc']:4d} len={len(text):6d} [{hint.strip()}] -> {Path(tail).name[:60]}")
    else:
        print(f"{e['t_start']:8.2f} +{e['seconds']:7.2f}s FUNC {e['name']}")
